"""CDP Autofill domain.

Defines commands and events for Autofill.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


CreditCard = dict  # Object type

AddressField = dict  # Object type

# A list of address fields.
AddressFields = dict  # Object type

Address = dict  # Object type

# Defines how an address can be displayed like in chrome://settings/addresses.
# Address UI is a two dimensional array, each inner array is an "address information line", and when rendered in a UI surface should be displayed as such.
# The following address UI for instance:
# [[{name: "GIVE_NAME", value: "Jon"}, {name: "FAMILY_NAME", value: "Doe"}], [{name: "CITY", value: "Munich"}, {name: "ZIP", value: "81456"}]]
# should allow the receiver to render:
# Jon Doe
# Munich 81456
AddressUI = dict  # Object type

# Specified whether a filled field was done so by using the html autocomplete attribute or autofill heuristics.
FillingStrategy = str  # Literal enum: "autocompleteAttribute", "autofillInferred"

FilledField = dict  # Object type

class Autofill:
    """Defines commands and events for Autofill."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def trigger(
        self,
        field_id: str,
        frame_id: str | None = None,
        card: CreditCard | None = None,
        address: Address | None = None,
    ) -> dict:
        """Trigger autofill on a form identified by the fieldId.
If the field and related form cannot be autofilled, returns an error.
        """
        params: dict[str, Any] = {}
        params["fieldId"] = field_id
        if frame_id is not None:
            params["frameId"] = frame_id
        if card is not None:
            params["card"] = card
        if address is not None:
            params["address"] = address
        return await self._client.send(method="Autofill.trigger", params=params)

    async def set_addresses(self, addresses: list[Address]) -> dict:
        """Set addresses so that developers can verify their forms implementation."""
        params: dict[str, Any] = {}
        params["addresses"] = addresses
        return await self._client.send(method="Autofill.setAddresses", params=params)

    async def disable(self) -> dict:
        """Disables autofill domain notifications."""
        return await self._client.send(method="Autofill.disable")

    async def enable(self) -> dict:
        """Enables autofill domain notifications."""
        return await self._client.send(method="Autofill.enable")
