"""CDP FedCm domain.

This domain allows interacting with the FedCM dialog.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Whether this is a sign-up or sign-in action for this account, i.e.
# whether this account has ever been used to sign in to this RP before.
LoginState = str  # Literal enum: "SignIn", "SignUp"

# The types of FedCM dialogs.
DialogType = str  # Literal enum: "AccountChooser", "AutoReauthn", "ConfirmIdpLogin", "Error"

# The buttons on the FedCM dialog.
DialogButton = str  # Literal enum: "ConfirmIdpLoginContinue", "ErrorGotIt", "ErrorMoreDetails"

# The URLs that each account has
AccountUrlType = str  # Literal enum: "TermsOfService", "PrivacyPolicy"

# Corresponds to IdentityRequestAccount
Account = dict  # Object type

class FedCm:
    """This domain allows interacting with the FedCM dialog."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def enable(self, disable_rejection_delay: bool | None = None) -> dict:
        params: dict[str, Any] = {}
        if disable_rejection_delay is not None:
            params["disableRejectionDelay"] = disable_rejection_delay
        return await self._client.send(method="FedCm.enable", params=params)

    async def disable(self) -> dict:
        return await self._client.send(method="FedCm.disable")

    async def select_account(self, dialog_id: str, account_index: int) -> dict:
        params: dict[str, Any] = {}
        params["dialogId"] = dialog_id
        params["accountIndex"] = account_index
        return await self._client.send(method="FedCm.selectAccount", params=params)

    async def click_dialog_button(self, dialog_id: str, dialog_button: DialogButton) -> dict:
        params: dict[str, Any] = {}
        params["dialogId"] = dialog_id
        params["dialogButton"] = dialog_button
        return await self._client.send(method="FedCm.clickDialogButton", params=params)

    async def open_url(
        self,
        dialog_id: str,
        account_index: int,
        account_url_type: AccountUrlType,
    ) -> dict:
        params: dict[str, Any] = {}
        params["dialogId"] = dialog_id
        params["accountIndex"] = account_index
        params["accountUrlType"] = account_url_type
        return await self._client.send(method="FedCm.openUrl", params=params)

    async def dismiss_dialog(self, dialog_id: str, trigger_cooldown: bool | None = None) -> dict:
        params: dict[str, Any] = {}
        params["dialogId"] = dialog_id
        if trigger_cooldown is not None:
            params["triggerCooldown"] = trigger_cooldown
        return await self._client.send(method="FedCm.dismissDialog", params=params)

    async def reset_cooldown(self) -> dict:
        """Resets the cooldown time, if any, to allow the next FedCM call to show
a dialog even if one was recently dismissed by the user.
        """
        return await self._client.send(method="FedCm.resetCooldown")
