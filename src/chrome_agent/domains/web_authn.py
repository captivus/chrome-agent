"""CDP WebAuthn domain.

This domain allows configuring virtual authenticators to test the WebAuthn
API.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


AuthenticatorId = str

AuthenticatorProtocol = str  # Literal enum: "u2f", "ctap2"

Ctap2Version = str  # Literal enum: "ctap2_0", "ctap2_1"

AuthenticatorTransport = str  # Literal enum: "usb", "nfc", "ble", "cable", "internal"

VirtualAuthenticatorOptions = dict  # Object type

Credential = dict  # Object type

class WebAuthn:
    """This domain allows configuring virtual authenticators to test the WebAuthn
API."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self, enable_ui: bool | None = None) -> dict:
        """Enable the WebAuthn domain and start intercepting credential storage and
retrieval with a virtual authenticator.
        """
        params: dict[str, Any] = {}
        if enable_ui is not None:
            params["enableUI"] = enable_ui
        return await self._client.send(method="WebAuthn.enable", params=params)

    async def disable(self) -> dict:
        """Disable the WebAuthn domain."""
        return await self._client.send(method="WebAuthn.disable")

    async def add_virtual_authenticator(self, options: VirtualAuthenticatorOptions) -> dict:
        """Creates and adds a virtual authenticator."""
        params: dict[str, Any] = {}
        params["options"] = options
        return await self._client.send(method="WebAuthn.addVirtualAuthenticator", params=params)

    async def set_response_override_bits(
        self,
        authenticator_id: AuthenticatorId,
        is_bogus_signature: bool | None = None,
        is_bad_uv: bool | None = None,
        is_bad_up: bool | None = None,
    ) -> dict:
        """Resets parameters isBogusSignature, isBadUV, isBadUP to false if they are not present."""
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        if is_bogus_signature is not None:
            params["isBogusSignature"] = is_bogus_signature
        if is_bad_uv is not None:
            params["isBadUV"] = is_bad_uv
        if is_bad_up is not None:
            params["isBadUP"] = is_bad_up
        return await self._client.send(method="WebAuthn.setResponseOverrideBits", params=params)

    async def remove_virtual_authenticator(self, authenticator_id: AuthenticatorId) -> dict:
        """Removes the given authenticator."""
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        return await self._client.send(method="WebAuthn.removeVirtualAuthenticator", params=params)

    async def add_credential(self, authenticator_id: AuthenticatorId, credential: Credential) -> dict:
        """Adds the credential to the specified authenticator."""
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        params["credential"] = credential
        return await self._client.send(method="WebAuthn.addCredential", params=params)

    async def get_credential(self, authenticator_id: AuthenticatorId, credential_id: str) -> dict:
        """Returns a single credential stored in the given virtual authenticator that
matches the credential ID.
        """
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        params["credentialId"] = credential_id
        return await self._client.send(method="WebAuthn.getCredential", params=params)

    async def get_credentials(self, authenticator_id: AuthenticatorId) -> dict:
        """Returns all the credentials stored in the given virtual authenticator."""
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        return await self._client.send(method="WebAuthn.getCredentials", params=params)

    async def remove_credential(self, authenticator_id: AuthenticatorId, credential_id: str) -> dict:
        """Removes a credential from the authenticator."""
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        params["credentialId"] = credential_id
        return await self._client.send(method="WebAuthn.removeCredential", params=params)

    async def clear_credentials(self, authenticator_id: AuthenticatorId) -> dict:
        """Clears all the credentials from the specified device."""
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        return await self._client.send(method="WebAuthn.clearCredentials", params=params)

    async def set_user_verified(self, authenticator_id: AuthenticatorId, is_user_verified: bool) -> dict:
        """Sets whether User Verification succeeds or fails for an authenticator.
The default is true.
        """
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        params["isUserVerified"] = is_user_verified
        return await self._client.send(method="WebAuthn.setUserVerified", params=params)

    async def set_automatic_presence_simulation(self, authenticator_id: AuthenticatorId, enabled: bool) -> dict:
        """Sets whether tests of user presence will succeed immediately (if true) or fail to resolve (if false) for an authenticator.
The default is true.
        """
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        params["enabled"] = enabled
        return await self._client.send(method="WebAuthn.setAutomaticPresenceSimulation", params=params)

    async def set_credential_properties(
        self,
        authenticator_id: AuthenticatorId,
        credential_id: str,
        backup_eligibility: bool | None = None,
        backup_state: bool | None = None,
    ) -> dict:
        """Allows setting credential properties.
https://w3c.github.io/webauthn/#sctn-automation-set-credential-properties
        """
        params: dict[str, Any] = {}
        params["authenticatorId"] = authenticator_id
        params["credentialId"] = credential_id
        if backup_eligibility is not None:
            params["backupEligibility"] = backup_eligibility
        if backup_state is not None:
            params["backupState"] = backup_state
        return await self._client.send(method="WebAuthn.setCredentialProperties", params=params)
