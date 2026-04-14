"""CDP Input domain.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


TouchPoint = dict  # Object type

GestureSourceType = str  # Literal enum: "default", "touch", "mouse"

MouseButton = str  # Literal enum: "none", "left", "middle", "right", "back", "forward"

TimeSinceEpoch = float

DragDataItem = dict  # Object type

DragData = dict  # Object type

class Input:
    """CDP Input domain."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def dispatch_drag_event(
        self,
        type_: str,
        x: float,
        y: float,
        data: DragData,
        modifiers: int | None = None,
    ) -> dict:
        """Dispatches a drag event into the page."""
        params: dict[str, Any] = {}
        params["type"] = type_
        params["x"] = x
        params["y"] = y
        params["data"] = data
        if modifiers is not None:
            params["modifiers"] = modifiers
        return await self._client.send(method="Input.dispatchDragEvent", params=params)

    async def dispatch_key_event(
        self,
        type_: str,
        modifiers: int | None = None,
        timestamp: TimeSinceEpoch | None = None,
        text: str | None = None,
        unmodified_text: str | None = None,
        key_identifier: str | None = None,
        code: str | None = None,
        key: str | None = None,
        windows_virtual_key_code: int | None = None,
        native_virtual_key_code: int | None = None,
        auto_repeat: bool | None = None,
        is_keypad: bool | None = None,
        is_system_key: bool | None = None,
        location: int | None = None,
        commands: list[str] | None = None,
    ) -> dict:
        """Dispatches a key event to the page."""
        params: dict[str, Any] = {}
        params["type"] = type_
        if modifiers is not None:
            params["modifiers"] = modifiers
        if timestamp is not None:
            params["timestamp"] = timestamp
        if text is not None:
            params["text"] = text
        if unmodified_text is not None:
            params["unmodifiedText"] = unmodified_text
        if key_identifier is not None:
            params["keyIdentifier"] = key_identifier
        if code is not None:
            params["code"] = code
        if key is not None:
            params["key"] = key
        if windows_virtual_key_code is not None:
            params["windowsVirtualKeyCode"] = windows_virtual_key_code
        if native_virtual_key_code is not None:
            params["nativeVirtualKeyCode"] = native_virtual_key_code
        if auto_repeat is not None:
            params["autoRepeat"] = auto_repeat
        if is_keypad is not None:
            params["isKeypad"] = is_keypad
        if is_system_key is not None:
            params["isSystemKey"] = is_system_key
        if location is not None:
            params["location"] = location
        if commands is not None:
            params["commands"] = commands
        return await self._client.send(method="Input.dispatchKeyEvent", params=params)

    async def insert_text(self, text: str) -> dict:
        """This method emulates inserting text that doesn't come from a key press,
for example an emoji keyboard or an IME.
        """
        params: dict[str, Any] = {}
        params["text"] = text
        return await self._client.send(method="Input.insertText", params=params)

    async def ime_set_composition(
        self,
        text: str,
        selection_start: int,
        selection_end: int,
        replacement_start: int | None = None,
        replacement_end: int | None = None,
    ) -> dict:
        """This method sets the current candidate text for IME.
Use imeCommitComposition to commit the final text.
Use imeSetComposition with empty string as text to cancel composition.
        """
        params: dict[str, Any] = {}
        params["text"] = text
        params["selectionStart"] = selection_start
        params["selectionEnd"] = selection_end
        if replacement_start is not None:
            params["replacementStart"] = replacement_start
        if replacement_end is not None:
            params["replacementEnd"] = replacement_end
        return await self._client.send(method="Input.imeSetComposition", params=params)

    async def dispatch_mouse_event(
        self,
        type_: str,
        x: float,
        y: float,
        modifiers: int | None = None,
        timestamp: TimeSinceEpoch | None = None,
        button: MouseButton | None = None,
        buttons: int | None = None,
        click_count: int | None = None,
        force: float | None = None,
        tangential_pressure: float | None = None,
        tilt_x: float | None = None,
        tilt_y: float | None = None,
        twist: int | None = None,
        delta_x: float | None = None,
        delta_y: float | None = None,
        pointer_type: str | None = None,
    ) -> dict:
        """Dispatches a mouse event to the page."""
        params: dict[str, Any] = {}
        params["type"] = type_
        params["x"] = x
        params["y"] = y
        if modifiers is not None:
            params["modifiers"] = modifiers
        if timestamp is not None:
            params["timestamp"] = timestamp
        if button is not None:
            params["button"] = button
        if buttons is not None:
            params["buttons"] = buttons
        if click_count is not None:
            params["clickCount"] = click_count
        if force is not None:
            params["force"] = force
        if tangential_pressure is not None:
            params["tangentialPressure"] = tangential_pressure
        if tilt_x is not None:
            params["tiltX"] = tilt_x
        if tilt_y is not None:
            params["tiltY"] = tilt_y
        if twist is not None:
            params["twist"] = twist
        if delta_x is not None:
            params["deltaX"] = delta_x
        if delta_y is not None:
            params["deltaY"] = delta_y
        if pointer_type is not None:
            params["pointerType"] = pointer_type
        return await self._client.send(method="Input.dispatchMouseEvent", params=params)

    async def dispatch_touch_event(
        self,
        type_: str,
        touch_points: list[TouchPoint],
        modifiers: int | None = None,
        timestamp: TimeSinceEpoch | None = None,
    ) -> dict:
        """Dispatches a touch event to the page."""
        params: dict[str, Any] = {}
        params["type"] = type_
        params["touchPoints"] = touch_points
        if modifiers is not None:
            params["modifiers"] = modifiers
        if timestamp is not None:
            params["timestamp"] = timestamp
        return await self._client.send(method="Input.dispatchTouchEvent", params=params)

    async def cancel_dragging(self) -> dict:
        """Cancels any active dragging in the page."""
        return await self._client.send(method="Input.cancelDragging")

    async def emulate_touch_from_mouse_event(
        self,
        type_: str,
        x: int,
        y: int,
        button: MouseButton,
        timestamp: TimeSinceEpoch | None = None,
        delta_x: float | None = None,
        delta_y: float | None = None,
        modifiers: int | None = None,
        click_count: int | None = None,
    ) -> dict:
        """Emulates touch event from the mouse event parameters."""
        params: dict[str, Any] = {}
        params["type"] = type_
        params["x"] = x
        params["y"] = y
        params["button"] = button
        if timestamp is not None:
            params["timestamp"] = timestamp
        if delta_x is not None:
            params["deltaX"] = delta_x
        if delta_y is not None:
            params["deltaY"] = delta_y
        if modifiers is not None:
            params["modifiers"] = modifiers
        if click_count is not None:
            params["clickCount"] = click_count
        return await self._client.send(method="Input.emulateTouchFromMouseEvent", params=params)

    async def set_ignore_input_events(self, ignore: bool) -> dict:
        """Ignores input events (useful while auditing page)."""
        params: dict[str, Any] = {}
        params["ignore"] = ignore
        return await self._client.send(method="Input.setIgnoreInputEvents", params=params)

    async def set_intercept_drags(self, enabled: bool) -> dict:
        """Prevents default drag and drop behavior and instead emits `Input.dragIntercepted` events.
Drag and drop behavior can be directly controlled via `Input.dispatchDragEvent`.
        """
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="Input.setInterceptDrags", params=params)

    async def synthesize_pinch_gesture(
        self,
        x: float,
        y: float,
        scale_factor: float,
        relative_speed: int | None = None,
        gesture_source_type: GestureSourceType | None = None,
    ) -> dict:
        """Synthesizes a pinch gesture over a time period by issuing appropriate touch events."""
        params: dict[str, Any] = {}
        params["x"] = x
        params["y"] = y
        params["scaleFactor"] = scale_factor
        if relative_speed is not None:
            params["relativeSpeed"] = relative_speed
        if gesture_source_type is not None:
            params["gestureSourceType"] = gesture_source_type
        return await self._client.send(method="Input.synthesizePinchGesture", params=params)

    async def synthesize_scroll_gesture(
        self,
        x: float,
        y: float,
        x_distance: float | None = None,
        y_distance: float | None = None,
        x_overscroll: float | None = None,
        y_overscroll: float | None = None,
        prevent_fling: bool | None = None,
        speed: int | None = None,
        gesture_source_type: GestureSourceType | None = None,
        repeat_count: int | None = None,
        repeat_delay_ms: int | None = None,
        interaction_marker_name: str | None = None,
    ) -> dict:
        """Synthesizes a scroll gesture over a time period by issuing appropriate touch events."""
        params: dict[str, Any] = {}
        params["x"] = x
        params["y"] = y
        if x_distance is not None:
            params["xDistance"] = x_distance
        if y_distance is not None:
            params["yDistance"] = y_distance
        if x_overscroll is not None:
            params["xOverscroll"] = x_overscroll
        if y_overscroll is not None:
            params["yOverscroll"] = y_overscroll
        if prevent_fling is not None:
            params["preventFling"] = prevent_fling
        if speed is not None:
            params["speed"] = speed
        if gesture_source_type is not None:
            params["gestureSourceType"] = gesture_source_type
        if repeat_count is not None:
            params["repeatCount"] = repeat_count
        if repeat_delay_ms is not None:
            params["repeatDelayMs"] = repeat_delay_ms
        if interaction_marker_name is not None:
            params["interactionMarkerName"] = interaction_marker_name
        return await self._client.send(method="Input.synthesizeScrollGesture", params=params)

    async def synthesize_tap_gesture(
        self,
        x: float,
        y: float,
        duration: int | None = None,
        tap_count: int | None = None,
        gesture_source_type: GestureSourceType | None = None,
    ) -> dict:
        """Synthesizes a tap gesture over a time period by issuing appropriate touch events."""
        params: dict[str, Any] = {}
        params["x"] = x
        params["y"] = y
        if duration is not None:
            params["duration"] = duration
        if tap_count is not None:
            params["tapCount"] = tap_count
        if gesture_source_type is not None:
            params["gestureSourceType"] = gesture_source_type
        return await self._client.send(method="Input.synthesizeTapGesture", params=params)
