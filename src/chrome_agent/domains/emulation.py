"""CDP Emulation domain.

This domain emulates different environments for the page.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


SafeAreaInsets = dict  # Object type

# Screen orientation.
ScreenOrientation = dict  # Object type

DisplayFeature = dict  # Object type

DevicePosture = dict  # Object type

MediaFeature = dict  # Object type

# advance: If the scheduler runs out of immediate work, the virtual time base may fast forward to
# allow the next delayed task (if any) to run; pause: The virtual time base may not advance;
# pauseIfNetworkFetchesPending: The virtual time base may not advance if there are any pending
# resource fetches.
VirtualTimePolicy = str  # Literal enum: "advance", "pause", "pauseIfNetworkFetchesPending"

# Used to specify User Agent Client Hints to emulate. See https://wicg.github.io/ua-client-hints
UserAgentBrandVersion = dict  # Object type

# Used to specify User Agent Client Hints to emulate. See https://wicg.github.io/ua-client-hints
# Missing optional values will be filled in by the target with what it would normally use.
UserAgentMetadata = dict  # Object type

# Used to specify sensor types to emulate.
# See https://w3c.github.io/sensors/#automation for more information.
SensorType = str  # Literal enum: "absolute-orientation", "accelerometer", "ambient-light", "gravity", "gyroscope", "linear-acceleration", "magnetometer", "relative-orientation"

SensorMetadata = dict  # Object type

SensorReadingSingle = dict  # Object type

SensorReadingXYZ = dict  # Object type

SensorReadingQuaternion = dict  # Object type

SensorReading = dict  # Object type

PressureSource = str  # Literal enum: "cpu"

PressureState = str  # Literal enum: "nominal", "fair", "serious", "critical"

PressureMetadata = dict  # Object type

WorkAreaInsets = dict  # Object type

ScreenId = str

# Screen information similar to the one returned by window.getScreenDetails() method,
# see https://w3c.github.io/window-management/#screendetailed.
ScreenInfo = dict  # Object type

# Enum of image types that can be disabled.
DisabledImageType = str  # Literal enum: "avif", "webp"

class Emulation:
    """This domain emulates different environments for the page."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def can_emulate(self) -> dict:
        """Tells whether emulation is supported."""
        return await self._client.send(method="Emulation.canEmulate")

    async def clear_device_metrics_override(self) -> dict:
        """Clears the overridden device metrics."""
        return await self._client.send(method="Emulation.clearDeviceMetricsOverride")

    async def clear_geolocation_override(self) -> dict:
        """Clears the overridden Geolocation Position and Error."""
        return await self._client.send(method="Emulation.clearGeolocationOverride")

    async def reset_page_scale_factor(self) -> dict:
        """Requests that page scale factor is reset to initial values."""
        return await self._client.send(method="Emulation.resetPageScaleFactor")

    async def set_focus_emulation_enabled(self, enabled: bool) -> dict:
        """Enables or disables simulating a focused and active page."""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="Emulation.setFocusEmulationEnabled", params=params)

    async def set_auto_dark_mode_override(self, enabled: bool | None = None) -> dict:
        """Automatically render all web contents using a dark theme."""
        params: dict[str, Any] = {}
        if enabled is not None:
            params["enabled"] = enabled
        return await self._client.send(method="Emulation.setAutoDarkModeOverride", params=params)

    async def set_cpu_throttling_rate(self, rate: float) -> dict:
        """Enables CPU throttling to emulate slow CPUs."""
        params: dict[str, Any] = {}
        params["rate"] = rate
        return await self._client.send(method="Emulation.setCPUThrottlingRate", params=params)

    async def set_default_background_color_override(self, color: str | None = None) -> dict:
        """Sets or clears an override of the default background color of the frame. This override is used
if the content does not specify one.
        """
        params: dict[str, Any] = {}
        if color is not None:
            params["color"] = color
        return await self._client.send(method="Emulation.setDefaultBackgroundColorOverride", params=params)

    async def set_safe_area_insets_override(self, insets: SafeAreaInsets) -> dict:
        """Overrides the values for env(safe-area-inset-*) and env(safe-area-max-inset-*). Unset values will cause the
respective variables to be undefined, even if previously overridden.
        """
        params: dict[str, Any] = {}
        params["insets"] = insets
        return await self._client.send(method="Emulation.setSafeAreaInsetsOverride", params=params)

    async def set_device_metrics_override(
        self,
        width: int,
        height: int,
        device_scale_factor: float,
        mobile: bool,
        scale: float | None = None,
        screen_width: int | None = None,
        screen_height: int | None = None,
        position_x: int | None = None,
        position_y: int | None = None,
        dont_set_visible_size: bool | None = None,
        screen_orientation: ScreenOrientation | None = None,
        viewport: str | None = None,
        display_feature: DisplayFeature | None = None,
        device_posture: DevicePosture | None = None,
    ) -> dict:
        """Overrides the values of device screen dimensions (window.screen.width, window.screen.height,
window.innerWidth, window.innerHeight, and "device-width"/"device-height"-related CSS media
query results).
        """
        params: dict[str, Any] = {}
        params["width"] = width
        params["height"] = height
        params["deviceScaleFactor"] = device_scale_factor
        params["mobile"] = mobile
        if scale is not None:
            params["scale"] = scale
        if screen_width is not None:
            params["screenWidth"] = screen_width
        if screen_height is not None:
            params["screenHeight"] = screen_height
        if position_x is not None:
            params["positionX"] = position_x
        if position_y is not None:
            params["positionY"] = position_y
        if dont_set_visible_size is not None:
            params["dontSetVisibleSize"] = dont_set_visible_size
        if screen_orientation is not None:
            params["screenOrientation"] = screen_orientation
        if viewport is not None:
            params["viewport"] = viewport
        if display_feature is not None:
            params["displayFeature"] = display_feature
        if device_posture is not None:
            params["devicePosture"] = device_posture
        return await self._client.send(method="Emulation.setDeviceMetricsOverride", params=params)

    async def set_device_posture_override(self, posture: DevicePosture) -> dict:
        """Start reporting the given posture value to the Device Posture API.
This override can also be set in setDeviceMetricsOverride().
        """
        params: dict[str, Any] = {}
        params["posture"] = posture
        return await self._client.send(method="Emulation.setDevicePostureOverride", params=params)

    async def clear_device_posture_override(self) -> dict:
        """Clears a device posture override set with either setDeviceMetricsOverride()
or setDevicePostureOverride() and starts using posture information from the
platform again.
Does nothing if no override is set.
        """
        return await self._client.send(method="Emulation.clearDevicePostureOverride")

    async def set_display_features_override(self, features: list[DisplayFeature]) -> dict:
        """Start using the given display features to pupulate the Viewport Segments API.
This override can also be set in setDeviceMetricsOverride().
        """
        params: dict[str, Any] = {}
        params["features"] = features
        return await self._client.send(method="Emulation.setDisplayFeaturesOverride", params=params)

    async def clear_display_features_override(self) -> dict:
        """Clears the display features override set with either setDeviceMetricsOverride()
or setDisplayFeaturesOverride() and starts using display features from the
platform again.
Does nothing if no override is set.
        """
        return await self._client.send(method="Emulation.clearDisplayFeaturesOverride")

    async def set_scrollbars_hidden(self, hidden: bool) -> dict:
        params: dict[str, Any] = {}
        params["hidden"] = hidden
        return await self._client.send(method="Emulation.setScrollbarsHidden", params=params)

    async def set_document_cookie_disabled(self, disabled: bool) -> dict:
        params: dict[str, Any] = {}
        params["disabled"] = disabled
        return await self._client.send(method="Emulation.setDocumentCookieDisabled", params=params)

    async def set_emit_touch_events_for_mouse(self, enabled: bool, configuration: str | None = None) -> dict:
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        if configuration is not None:
            params["configuration"] = configuration
        return await self._client.send(method="Emulation.setEmitTouchEventsForMouse", params=params)

    async def set_emulated_media(self, media: str | None = None, features: list[MediaFeature] | None = None) -> dict:
        """Emulates the given media type or media feature for CSS media queries."""
        params: dict[str, Any] = {}
        if media is not None:
            params["media"] = media
        if features is not None:
            params["features"] = features
        return await self._client.send(method="Emulation.setEmulatedMedia", params=params)

    async def set_emulated_vision_deficiency(self, type_: str) -> dict:
        """Emulates the given vision deficiency."""
        params: dict[str, Any] = {}
        params["type"] = type_
        return await self._client.send(method="Emulation.setEmulatedVisionDeficiency", params=params)

    async def set_emulated_os_text_scale(self, scale: float | None = None) -> dict:
        """Emulates the given OS text scale."""
        params: dict[str, Any] = {}
        if scale is not None:
            params["scale"] = scale
        return await self._client.send(method="Emulation.setEmulatedOSTextScale", params=params)

    async def set_geolocation_override(
        self,
        latitude: float | None = None,
        longitude: float | None = None,
        accuracy: float | None = None,
        altitude: float | None = None,
        altitude_accuracy: float | None = None,
        heading: float | None = None,
        speed: float | None = None,
    ) -> dict:
        """Overrides the Geolocation Position or Error. Omitting latitude, longitude or
accuracy emulates position unavailable.
        """
        params: dict[str, Any] = {}
        if latitude is not None:
            params["latitude"] = latitude
        if longitude is not None:
            params["longitude"] = longitude
        if accuracy is not None:
            params["accuracy"] = accuracy
        if altitude is not None:
            params["altitude"] = altitude
        if altitude_accuracy is not None:
            params["altitudeAccuracy"] = altitude_accuracy
        if heading is not None:
            params["heading"] = heading
        if speed is not None:
            params["speed"] = speed
        return await self._client.send(method="Emulation.setGeolocationOverride", params=params)

    async def get_overridden_sensor_information(self, type_: SensorType) -> dict:
        params: dict[str, Any] = {}
        params["type"] = type_
        return await self._client.send(method="Emulation.getOverriddenSensorInformation", params=params)

    async def set_sensor_override_enabled(
        self,
        enabled: bool,
        type_: SensorType,
        metadata: SensorMetadata | None = None,
    ) -> dict:
        """Overrides a platform sensor of a given type. If |enabled| is true, calls to
Sensor.start() will use a virtual sensor as backend rather than fetching
data from a real hardware sensor. Otherwise, existing virtual
sensor-backend Sensor objects will fire an error event and new calls to
Sensor.start() will attempt to use a real sensor instead.
        """
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        params["type"] = type_
        if metadata is not None:
            params["metadata"] = metadata
        return await self._client.send(method="Emulation.setSensorOverrideEnabled", params=params)

    async def set_sensor_override_readings(self, type_: SensorType, reading: SensorReading) -> dict:
        """Updates the sensor readings reported by a sensor type previously overridden
by setSensorOverrideEnabled.
        """
        params: dict[str, Any] = {}
        params["type"] = type_
        params["reading"] = reading
        return await self._client.send(method="Emulation.setSensorOverrideReadings", params=params)

    async def set_pressure_source_override_enabled(
        self,
        enabled: bool,
        source: PressureSource,
        metadata: PressureMetadata | None = None,
    ) -> dict:
        """Overrides a pressure source of a given type, as used by the Compute
Pressure API, so that updates to PressureObserver.observe() are provided
via setPressureStateOverride instead of being retrieved from
platform-provided telemetry data.
        """
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        params["source"] = source
        if metadata is not None:
            params["metadata"] = metadata
        return await self._client.send(method="Emulation.setPressureSourceOverrideEnabled", params=params)

    async def set_pressure_state_override(self, source: PressureSource, state: PressureState) -> dict:
        """TODO: OBSOLETE: To remove when setPressureDataOverride is merged.
Provides a given pressure state that will be processed and eventually be
delivered to PressureObserver users. |source| must have been previously
overridden by setPressureSourceOverrideEnabled.
        """
        params: dict[str, Any] = {}
        params["source"] = source
        params["state"] = state
        return await self._client.send(method="Emulation.setPressureStateOverride", params=params)

    async def set_pressure_data_override(
        self,
        source: PressureSource,
        state: PressureState,
        own_contribution_estimate: float | None = None,
    ) -> dict:
        """Provides a given pressure data set that will be processed and eventually be
delivered to PressureObserver users. |source| must have been previously
overridden by setPressureSourceOverrideEnabled.
        """
        params: dict[str, Any] = {}
        params["source"] = source
        params["state"] = state
        if own_contribution_estimate is not None:
            params["ownContributionEstimate"] = own_contribution_estimate
        return await self._client.send(method="Emulation.setPressureDataOverride", params=params)

    async def set_idle_override(self, is_user_active: bool, is_screen_unlocked: bool) -> dict:
        """Overrides the Idle state."""
        params: dict[str, Any] = {}
        params["isUserActive"] = is_user_active
        params["isScreenUnlocked"] = is_screen_unlocked
        return await self._client.send(method="Emulation.setIdleOverride", params=params)

    async def clear_idle_override(self) -> dict:
        """Clears Idle state overrides."""
        return await self._client.send(method="Emulation.clearIdleOverride")

    async def set_navigator_overrides(self, platform: str) -> dict:
        """Overrides value returned by the javascript navigator object."""
        params: dict[str, Any] = {}
        params["platform"] = platform
        return await self._client.send(method="Emulation.setNavigatorOverrides", params=params)

    async def set_page_scale_factor(self, page_scale_factor: float) -> dict:
        """Sets a specified page scale factor."""
        params: dict[str, Any] = {}
        params["pageScaleFactor"] = page_scale_factor
        return await self._client.send(method="Emulation.setPageScaleFactor", params=params)

    async def set_script_execution_disabled(self, value: bool) -> dict:
        """Switches script execution in the page."""
        params: dict[str, Any] = {}
        params["value"] = value
        return await self._client.send(method="Emulation.setScriptExecutionDisabled", params=params)

    async def set_touch_emulation_enabled(self, enabled: bool, max_touch_points: int | None = None) -> dict:
        """Enables touch on platforms which do not support them."""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        if max_touch_points is not None:
            params["maxTouchPoints"] = max_touch_points
        return await self._client.send(method="Emulation.setTouchEmulationEnabled", params=params)

    async def set_virtual_time_policy(
        self,
        policy: VirtualTimePolicy,
        budget: float | None = None,
        max_virtual_time_task_starvation_count: int | None = None,
        initial_virtual_time: str | None = None,
    ) -> dict:
        """Turns on virtual time for all frames (replacing real-time with a synthetic time source) and sets
the current virtual time policy.  Note this supersedes any previous time budget.
        """
        params: dict[str, Any] = {}
        params["policy"] = policy
        if budget is not None:
            params["budget"] = budget
        if max_virtual_time_task_starvation_count is not None:
            params["maxVirtualTimeTaskStarvationCount"] = max_virtual_time_task_starvation_count
        if initial_virtual_time is not None:
            params["initialVirtualTime"] = initial_virtual_time
        return await self._client.send(method="Emulation.setVirtualTimePolicy", params=params)

    async def set_locale_override(self, locale: str | None = None) -> dict:
        """Overrides default host system locale with the specified one."""
        params: dict[str, Any] = {}
        if locale is not None:
            params["locale"] = locale
        return await self._client.send(method="Emulation.setLocaleOverride", params=params)

    async def set_timezone_override(self, timezone_id: str) -> dict:
        """Overrides default host system timezone with the specified one."""
        params: dict[str, Any] = {}
        params["timezoneId"] = timezone_id
        return await self._client.send(method="Emulation.setTimezoneOverride", params=params)

    async def set_visible_size(self, width: int, height: int) -> dict:
        """Resizes the frame/viewport of the page. Note that this does not affect the frame's container
(e.g. browser window). Can be used to produce screenshots of the specified size. Not supported
on Android.
        """
        params: dict[str, Any] = {}
        params["width"] = width
        params["height"] = height
        return await self._client.send(method="Emulation.setVisibleSize", params=params)

    async def set_disabled_image_types(self, image_types: list[DisabledImageType]) -> dict:
        params: dict[str, Any] = {}
        params["imageTypes"] = image_types
        return await self._client.send(method="Emulation.setDisabledImageTypes", params=params)

    async def set_data_saver_override(self, data_saver_enabled: bool | None = None) -> dict:
        """Override the value of navigator.connection.saveData"""
        params: dict[str, Any] = {}
        if data_saver_enabled is not None:
            params["dataSaverEnabled"] = data_saver_enabled
        return await self._client.send(method="Emulation.setDataSaverOverride", params=params)

    async def set_hardware_concurrency_override(self, hardware_concurrency: int) -> dict:
        params: dict[str, Any] = {}
        params["hardwareConcurrency"] = hardware_concurrency
        return await self._client.send(method="Emulation.setHardwareConcurrencyOverride", params=params)

    async def set_user_agent_override(
        self,
        user_agent: str,
        accept_language: str | None = None,
        platform: str | None = None,
        user_agent_metadata: UserAgentMetadata | None = None,
    ) -> dict:
        """Allows overriding user agent with the given string.
`userAgentMetadata` must be set for Client Hint headers to be sent.
        """
        params: dict[str, Any] = {}
        params["userAgent"] = user_agent
        if accept_language is not None:
            params["acceptLanguage"] = accept_language
        if platform is not None:
            params["platform"] = platform
        if user_agent_metadata is not None:
            params["userAgentMetadata"] = user_agent_metadata
        return await self._client.send(method="Emulation.setUserAgentOverride", params=params)

    async def set_automation_override(self, enabled: bool) -> dict:
        """Allows overriding the automation flag."""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="Emulation.setAutomationOverride", params=params)

    async def set_small_viewport_height_difference_override(self, difference: int) -> dict:
        """Allows overriding the difference between the small and large viewport sizes, which determine the
value of the `svh` and `lvh` unit, respectively. Only supported for top-level frames.
        """
        params: dict[str, Any] = {}
        params["difference"] = difference
        return await self._client.send(method="Emulation.setSmallViewportHeightDifferenceOverride", params=params)

    async def get_screen_infos(self) -> dict:
        """Returns device's screen configuration."""
        return await self._client.send(method="Emulation.getScreenInfos")

    async def add_screen(
        self,
        left: int,
        top: int,
        width: int,
        height: int,
        work_area_insets: WorkAreaInsets | None = None,
        device_pixel_ratio: float | None = None,
        rotation: int | None = None,
        color_depth: int | None = None,
        label: str | None = None,
        is_internal: bool | None = None,
    ) -> dict:
        """Add a new screen to the device. Only supported in headless mode."""
        params: dict[str, Any] = {}
        params["left"] = left
        params["top"] = top
        params["width"] = width
        params["height"] = height
        if work_area_insets is not None:
            params["workAreaInsets"] = work_area_insets
        if device_pixel_ratio is not None:
            params["devicePixelRatio"] = device_pixel_ratio
        if rotation is not None:
            params["rotation"] = rotation
        if color_depth is not None:
            params["colorDepth"] = color_depth
        if label is not None:
            params["label"] = label
        if is_internal is not None:
            params["isInternal"] = is_internal
        return await self._client.send(method="Emulation.addScreen", params=params)

    async def remove_screen(self, screen_id: ScreenId) -> dict:
        """Remove screen from the device. Only supported in headless mode."""
        params: dict[str, Any] = {}
        params["screenId"] = screen_id
        return await self._client.send(method="Emulation.removeScreen", params=params)
