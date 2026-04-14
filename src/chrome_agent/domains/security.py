"""CDP Security domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


CertificateId = int

# A description of mixed content (HTTP resources on HTTPS pages), as defined by
# https://www.w3.org/TR/mixed-content/#categories
MixedContentType = str  # Literal enum: "blockable", "optionally-blockable", "none"

# The security level of a page or resource.
SecurityState = str  # Literal enum: "unknown", "neutral", "insecure", "secure", "info", "insecure-broken"

# Details about the security state of the page certificate.
CertificateSecurityState = dict  # Object type

SafetyTipStatus = str  # Literal enum: "badReputation", "lookalike"

SafetyTipInfo = dict  # Object type

# Security state information about the page.
VisibleSecurityState = dict  # Object type

# An explanation of an factor contributing to the security state.
SecurityStateExplanation = dict  # Object type

# Information about insecure content on the page.
InsecureContentStatus = dict  # Object type

# The action to take when a certificate error occurs. continue will continue processing the
# request and cancel will cancel the request.
CertificateErrorAction = str  # Literal enum: "continue", "cancel"

class Security:
    """CDP Security domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def disable(self) -> dict:
        """Disables tracking security state changes."""
        return await self._client.send(method="Security.disable")

    async def enable(self) -> dict:
        """Enables tracking security state changes."""
        return await self._client.send(method="Security.enable")

    async def set_ignore_certificate_errors(self, ignore: bool) -> dict:
        """Enable/disable whether all certificate errors should be ignored."""
        params: dict[str, Any] = {}
        params["ignore"] = ignore
        return await self._client.send(method="Security.setIgnoreCertificateErrors", params=params)

    async def handle_certificate_error(self, event_id: int, action: CertificateErrorAction) -> dict:
        """Handles a certificate error that fired a certificateError event."""
        params: dict[str, Any] = {}
        params["eventId"] = event_id
        params["action"] = action
        return await self._client.send(method="Security.handleCertificateError", params=params)

    async def set_override_certificate_errors(self, override: bool) -> dict:
        """Enable/disable overriding certificate errors. If enabled, all certificate error events need to
be handled by the DevTools client and should be answered with `handleCertificateError` commands.
        """
        params: dict[str, Any] = {}
        params["override"] = override
        return await self._client.send(method="Security.setOverrideCertificateErrors", params=params)
