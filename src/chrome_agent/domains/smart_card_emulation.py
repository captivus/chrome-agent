"""CDP SmartCardEmulation domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Indicates the PC/SC error code.
# 
# This maps to:
# PC/SC Lite: https://pcsclite.apdu.fr/api/group__ErrorCodes.html
# Microsoft: https://learn.microsoft.com/en-us/windows/win32/secauthn/authentication-return-values
ResultCode = str  # Literal enum: "success", "removed-card", "reset-card", "unpowered-card", "unresponsive-card", "unsupported-card", "reader-unavailable", "sharing-violation", "not-transacted", "no-smartcard", "proto-mismatch", "system-cancelled", "not-ready", "cancelled", "insufficient-buffer", "invalid-handle", "invalid-parameter", "invalid-value", "no-memory", "timeout", "unknown-reader", "unsupported-feature", "no-readers-available", "service-stopped", "no-service", "comm-error", "internal-error", "server-too-busy", "unexpected", "shutdown", "unknown-card", "unknown"

# Maps to the |SCARD_SHARE_*| values.
ShareMode = str  # Literal enum: "shared", "exclusive", "direct"

# Indicates what the reader should do with the card.
Disposition = str  # Literal enum: "leave-card", "reset-card", "unpower-card", "eject-card"

# Maps to |SCARD_*| connection state values.
ConnectionState = str  # Literal enum: "absent", "present", "swallowed", "powered", "negotiable", "specific"

# Maps to the |SCARD_STATE_*| flags.
ReaderStateFlags = dict  # Object type

# Maps to the |SCARD_PROTOCOL_*| flags.
ProtocolSet = dict  # Object type

# Maps to the |SCARD_PROTOCOL_*| values.
Protocol = str  # Literal enum: "t0", "t1", "raw"

ReaderStateIn = dict  # Object type

ReaderStateOut = dict  # Object type

class SmartCardEmulation:
    """CDP SmartCardEmulation domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self) -> dict:
        """Enables the |SmartCardEmulation| domain."""
        return await self._client.send(method="SmartCardEmulation.enable")

    async def disable(self) -> dict:
        """Disables the |SmartCardEmulation| domain."""
        return await self._client.send(method="SmartCardEmulation.disable")

    async def report_establish_context_result(self, request_id: str, context_id: int) -> dict:
        """Reports the successful result of a |SCardEstablishContext| call.

This maps to:
PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#gaa1b8970169fd4883a6dc4a8f43f19b67
Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardestablishcontext
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["contextId"] = context_id
        return await self._client.send(method="SmartCardEmulation.reportEstablishContextResult", params=params)

    async def report_release_context_result(self, request_id: str) -> dict:
        """Reports the successful result of a |SCardReleaseContext| call.

This maps to:
PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#ga6aabcba7744c5c9419fdd6404f73a934
Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardreleasecontext
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        return await self._client.send(method="SmartCardEmulation.reportReleaseContextResult", params=params)

    async def report_list_readers_result(self, request_id: str, readers: list[str]) -> dict:
        """Reports the successful result of a |SCardListReaders| call.

This maps to:
PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#ga93b07815789b3cf2629d439ecf20f0d9
Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardlistreadersa
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["readers"] = readers
        return await self._client.send(method="SmartCardEmulation.reportListReadersResult", params=params)

    async def report_get_status_change_result(self, request_id: str, reader_states: list[ReaderStateOut]) -> dict:
        """Reports the successful result of a |SCardGetStatusChange| call.

This maps to:
PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#ga33247d5d1257d59e55647c3bb717db24
Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardgetstatuschangea
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["readerStates"] = reader_states
        return await self._client.send(method="SmartCardEmulation.reportGetStatusChangeResult", params=params)

    async def report_begin_transaction_result(self, request_id: str, handle: int) -> dict:
        """Reports the result of a |SCardBeginTransaction| call.
On success, this creates a new transaction object.

This maps to:
PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#gaddb835dce01a0da1d6ca02d33ee7d861
Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardbegintransaction
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["handle"] = handle
        return await self._client.send(method="SmartCardEmulation.reportBeginTransactionResult", params=params)

    async def report_plain_result(self, request_id: str) -> dict:
        """Reports the successful result of a call that returns only a result code.
Used for: |SCardCancel|, |SCardDisconnect|, |SCardSetAttrib|, |SCardEndTransaction|.

This maps to:
1. SCardCancel
   PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#gaacbbc0c6d6c0cbbeb4f4debf6fbeeee6
   Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardcancel

2. SCardDisconnect
   PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#ga4be198045c73ec0deb79e66c0ca1738a
   Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scarddisconnect

3. SCardSetAttrib
   PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#ga060f0038a4ddfd5dd2b8fadf3c3a2e4f
   Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardsetattrib

4. SCardEndTransaction
   PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#gae8742473b404363e5c587f570d7e2f3b
   Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardendtransaction
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        return await self._client.send(method="SmartCardEmulation.reportPlainResult", params=params)

    async def report_connect_result(
        self,
        request_id: str,
        handle: int,
        active_protocol: Protocol | None = None,
    ) -> dict:
        """Reports the successful result of a |SCardConnect| call.

This maps to:
PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#ga4e515829752e0a8dbc4d630696a8d6a5
Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardconnecta
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["handle"] = handle
        if active_protocol is not None:
            params["activeProtocol"] = active_protocol
        return await self._client.send(method="SmartCardEmulation.reportConnectResult", params=params)

    async def report_data_result(self, request_id: str, data: str) -> dict:
        """Reports the successful result of a call that sends back data on success.
Used for |SCardTransmit|, |SCardControl|, and |SCardGetAttrib|.

This maps to:
1. SCardTransmit
   PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#ga9a2d77242a271310269065e64633ab99
   Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardtransmit

2. SCardControl
   PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#gac3454d4657110fd7f753b2d3d8f4e32f
   Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardcontrol

3. SCardGetAttrib
   PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#gaacfec51917255b7a25b94c5104961602
   Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardgetattrib
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["data"] = data
        return await self._client.send(method="SmartCardEmulation.reportDataResult", params=params)

    async def report_status_result(
        self,
        request_id: str,
        reader_name: str,
        state: ConnectionState,
        atr: str,
        protocol: Protocol | None = None,
    ) -> dict:
        """Reports the successful result of a |SCardStatus| call.

This maps to:
PC/SC Lite: https://pcsclite.apdu.fr/api/group__API.html#gae49c3c894ad7ac12a5b896bde70d0382
Microsoft: https://learn.microsoft.com/en-us/windows/win32/api/winscard/nf-winscard-scardstatusa
        """
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["readerName"] = reader_name
        params["state"] = state
        params["atr"] = atr
        if protocol is not None:
            params["protocol"] = protocol
        return await self._client.send(method="SmartCardEmulation.reportStatusResult", params=params)

    async def report_error(self, request_id: str, result_code: ResultCode) -> dict:
        """Reports an error result for the given request."""
        params: dict[str, Any] = {}
        params["requestId"] = request_id
        params["resultCode"] = result_code
        return await self._client.send(method="SmartCardEmulation.reportError", params=params)
