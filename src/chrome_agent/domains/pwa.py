"""CDP PWA domain.

This domain allows interacting with the browser to control PWAs.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# The following types are the replica of
# https://crsrc.org/c/chrome/browser/web_applications/proto/web_app_os_integration_state.proto;drc=9910d3be894c8f142c977ba1023f30a656bc13fc;l=67
FileHandlerAccept = dict  # Object type

FileHandler = dict  # Object type

# If user prefers opening the app in browser or an app window.
DisplayMode = str  # Literal enum: "standalone", "browser"

class PWA:
    """This domain allows interacting with the browser to control PWAs."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def get_os_app_state(self, manifest_id: str) -> dict:
        """Returns the following OS state for the given manifest id."""
        params: dict[str, Any] = {}
        params["manifestId"] = manifest_id
        return await self._client.send(method="PWA.getOsAppState", params=params)

    async def install(self, manifest_id: str, install_url_or_bundle_url: str | None = None) -> dict:
        """Installs the given manifest identity, optionally using the given installUrlOrBundleUrl

IWA-specific install description:
manifestId corresponds to isolated-app:// + web_package::SignedWebBundleId

File installation mode:
The installUrlOrBundleUrl can be either file:// or http(s):// pointing
to a signed web bundle (.swbn). In this case SignedWebBundleId must correspond to
The .swbn file's signing key.

Dev proxy installation mode:
installUrlOrBundleUrl must be http(s):// that serves dev mode IWA.
web_package::SignedWebBundleId must be of type dev proxy.

The advantage of dev proxy mode is that all changes to IWA
automatically will be reflected in the running app without
reinstallation.

To generate bundle id for proxy mode:
1. Generate 32 random bytes.
2. Add a specific suffix at the end following the documentation
   https://github.com/WICG/isolated-web-apps/blob/main/Scheme.md#suffix
3. Encode the entire sequence using Base32 without padding.

If Chrome is not in IWA dev
mode, the installation will fail, regardless of the state of the allowlist.
        """
        params: dict[str, Any] = {}
        params["manifestId"] = manifest_id
        if install_url_or_bundle_url is not None:
            params["installUrlOrBundleUrl"] = install_url_or_bundle_url
        return await self._client.send(method="PWA.install", params=params)

    async def uninstall(self, manifest_id: str) -> dict:
        """Uninstalls the given manifest_id and closes any opened app windows."""
        params: dict[str, Any] = {}
        params["manifestId"] = manifest_id
        return await self._client.send(method="PWA.uninstall", params=params)

    async def launch(self, manifest_id: str, url: str | None = None) -> dict:
        """Launches the installed web app, or an url in the same web app instead of the
default start url if it is provided. Returns a page Target.TargetID which
can be used to attach to via Target.attachToTarget or similar APIs.
        """
        params: dict[str, Any] = {}
        params["manifestId"] = manifest_id
        if url is not None:
            params["url"] = url
        return await self._client.send(method="PWA.launch", params=params)

    async def launch_files_in_app(self, manifest_id: str, files: list[str]) -> dict:
        """Opens one or more local files from an installed web app identified by its
manifestId. The web app needs to have file handlers registered to process
the files. The API returns one or more page Target.TargetIDs which can be
used to attach to via Target.attachToTarget or similar APIs.
If some files in the parameters cannot be handled by the web app, they will
be ignored. If none of the files can be handled, this API returns an error.
If no files are provided as the parameter, this API also returns an error.

According to the definition of the file handlers in the manifest file, one
Target.TargetID may represent a page handling one or more files. The order
of the returned Target.TargetIDs is not guaranteed.

TODO(crbug.com/339454034): Check the existences of the input files.
        """
        params: dict[str, Any] = {}
        params["manifestId"] = manifest_id
        params["files"] = files
        return await self._client.send(method="PWA.launchFilesInApp", params=params)

    async def open_current_page_in_app(self, manifest_id: str) -> dict:
        """Opens the current page in its web app identified by the manifest id, needs
to be called on a page target. This function returns immediately without
waiting for the app to finish loading.
        """
        params: dict[str, Any] = {}
        params["manifestId"] = manifest_id
        return await self._client.send(method="PWA.openCurrentPageInApp", params=params)

    async def change_app_user_settings(
        self,
        manifest_id: str,
        link_capturing: bool | None = None,
        display_mode: DisplayMode | None = None,
    ) -> dict:
        """Changes user settings of the web app identified by its manifestId. If the
app was not installed, this command returns an error. Unset parameters will
be ignored; unrecognized values will cause an error.

Unlike the ones defined in the manifest files of the web apps, these
settings are provided by the browser and controlled by the users, they
impact the way the browser handling the web apps.

See the comment of each parameter.
        """
        params: dict[str, Any] = {}
        params["manifestId"] = manifest_id
        if link_capturing is not None:
            params["linkCapturing"] = link_capturing
        if display_mode is not None:
            params["displayMode"] = display_mode
        return await self._client.send(method="PWA.changeAppUserSettings", params=params)
