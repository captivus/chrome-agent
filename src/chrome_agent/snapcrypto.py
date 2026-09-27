"""Encryption at rest for session snapshots.

A snapshot is a credential bundle: the profile's cookie store (which
``--password-store=basic`` protects only with Chromium's hard-coded key),
plus localStorage and IndexedDB, where many sites keep their auth tokens in
the clear. So every snapshot file is encrypted with AES-256-GCM under one
per-user key held in the OS keyring (GNOME Keyring / KWallet via Secret
Service, macOS Keychain, Windows Credential Locker). The keyring unlocks at
login, so restores need no prompt; a snapshot copied off the machine, swept
into a backup, or synced somewhere is unreadable without the key.

``CHROME_AGENT_SNAPSHOT_KEY`` (base64) overrides the keyring, for hosts with no
keyring service (headless servers, sandboxes without a session bus).

Streams are encrypted in fixed-size chunks so a multi-hundred-megabyte profile
never has to sit in memory. Each chunk is sealed with its index and a
final-chunk flag as associated data, so chunks cannot be reordered, dropped,
or truncated without the decrypt failing.
"""

import base64
import io
import os
import struct

KEYRING_SERVICE = "chrome-agent"
KEYRING_USERNAME = "snapshot-key"
KEY_ENV = "CHROME_AGENT_SNAPSHOT_KEY"

_MAGIC = b"CASNAP1\0"
_PREFIX_LEN = 8
_CHUNK = 4 * 1024 * 1024


class SnapshotKeyError(Exception):
    """The snapshot key is unavailable, or does not open this snapshot."""


def _decode_key(text: str) -> bytes:
    try:
        key = base64.b64decode(text.strip(), validate=True)
    except ValueError as exc:
        raise SnapshotKeyError(f"snapshot key is not valid base64: {exc}") from exc
    if len(key) != 32:
        raise SnapshotKeyError("snapshot key must decode to 32 bytes")
    return key


def get_key(create: bool) -> bytes:
    """The snapshot key: from the environment override, else the OS keyring.

    With ``create``, a missing key is generated and stored -- that happens on
    the first save. Restores never create one: a new key could not open any
    existing snapshot, so a missing key is reported as the error it is.
    """
    env = os.environ.get(KEY_ENV)
    if env:
        return _decode_key(env)

    try:
        import keyring
        import keyring.errors
    except ImportError as exc:  # pragma: no cover - declared dependency
        raise SnapshotKeyError("the 'keyring' package is not installed") from exc

    try:
        stored = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
        if stored:
            return _decode_key(stored)
        if not create:
            raise SnapshotKeyError(
                "no snapshot key in the OS keyring -- snapshots saved on this "
                "machine cannot be opened without it (import a backed-up key "
                "with: chrome-agent snapshots import-key)"
            )
        key = os.urandom(32)
        keyring.set_password(
            KEYRING_SERVICE, KEYRING_USERNAME, base64.b64encode(key).decode()
        )
        return key
    except keyring.errors.KeyringError as exc:
        raise SnapshotKeyError(
            f"the OS keyring is unavailable ({exc}); set {KEY_ENV} to a "
            f"base64 key instead"
        ) from exc


def export_key() -> str:
    """The key as base64 text, for backing up or moving to another machine."""
    return base64.b64encode(get_key(create=False)).decode()


def import_key(text: str, replace: bool = False) -> None:
    """Store a backed-up key in the OS keyring."""
    import keyring

    key = _decode_key(text)
    existing = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    if existing and _decode_key(existing) != key and not replace:
        raise SnapshotKeyError(
            "a different snapshot key is already stored; snapshots saved under "
            "it would become unreadable (pass --replace to overwrite anyway)"
        )
    keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, base64.b64encode(key).decode())


def _aad(index: int, final: bool) -> bytes:
    return struct.pack(">Q?", index, final)


class EncryptingWriter(io.RawIOBase):
    """A write-only file object that encrypts into ``sink`` chunk by chunk."""

    def __init__(self, sink, key: bytes):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        self._sink = sink
        self._aead = AESGCM(key)
        self._prefix = os.urandom(_PREFIX_LEN)
        self._buffer = bytearray()
        self._index = 0
        self._finished = False
        sink.write(_MAGIC + self._prefix)

    def writable(self) -> bool:
        return True

    def write(self, data) -> int:
        self._buffer += data
        while len(self._buffer) > _CHUNK:
            self._emit(bytes(self._buffer[:_CHUNK]), final=False)
            del self._buffer[:_CHUNK]
        return len(data)

    def _emit(self, plain: bytes, final: bool) -> None:
        nonce = self._prefix + struct.pack(">I", self._index)
        sealed = self._aead.encrypt(nonce, plain, _aad(self._index, final))
        self._sink.write(struct.pack(">I", len(sealed)) + sealed)
        self._index += 1

    def close(self) -> None:
        if not self._finished:
            self._finished = True
            self._emit(bytes(self._buffer), final=True)
            self._buffer.clear()
        super().close()


class DecryptingReader(io.RawIOBase):
    """A read-only file object over an encrypted stream from ``source``."""

    def __init__(self, source, key: bytes):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        self._source = source
        self._aead = AESGCM(key)
        header = source.read(len(_MAGIC) + _PREFIX_LEN)
        if header[: len(_MAGIC)] != _MAGIC:
            raise SnapshotKeyError("not a chrome-agent snapshot file")
        self._prefix = header[len(_MAGIC):]
        self._buffer = b""
        self._offset = 0
        self._index = 0
        self._done = False

    def readable(self) -> bool:
        return True

    def _next_chunk(self) -> None:
        from cryptography.exceptions import InvalidTag

        raw_len = self._source.read(4)
        if len(raw_len) < 4:
            raise SnapshotKeyError("snapshot file is truncated")
        (length,) = struct.unpack(">I", raw_len)
        sealed = self._source.read(length)
        if len(sealed) < length:
            raise SnapshotKeyError("snapshot file is truncated")
        nonce = self._prefix + struct.pack(">I", self._index)
        # The final flag is not stored: try "more follows" first, then "last".
        for final in (False, True):
            try:
                plain = self._aead.decrypt(nonce, sealed, _aad(self._index, final))
                break
            except InvalidTag:
                continue
        else:
            raise SnapshotKeyError(
                "snapshot does not decrypt -- it was saved under a different "
                "key, or the file is corrupt"
            )
        self._index += 1
        self._buffer += plain
        self._done = final

    def readinto(self, target) -> int:
        while self._offset >= len(self._buffer) and not self._done:
            self._buffer, self._offset = b"", 0
            self._next_chunk()
        n = min(len(target), len(self._buffer) - self._offset)
        target[:n] = self._buffer[self._offset:self._offset + n]
        self._offset += n
        return n


def encrypt_bytes(data: bytes, key: bytes) -> bytes:
    sink = io.BytesIO()
    writer = EncryptingWriter(sink, key)
    writer.write(data)
    writer.close()
    return sink.getvalue()


def decrypt_bytes(data: bytes, key: bytes) -> bytes:
    reader = DecryptingReader(io.BytesIO(data), key)
    return reader.read()
