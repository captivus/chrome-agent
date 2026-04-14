"""CDP Debugger domain.

Debugger domain exposes JavaScript debugging capabilities. It allows setting and removing
breakpoints, stepping through execution, exploring stack traces, etc.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


BreakpointId = str

CallFrameId = str

# Location in the source code.
Location = dict  # Object type

# Location in the source code.
ScriptPosition = dict  # Object type

# Location range within one script.
LocationRange = dict  # Object type

# JavaScript call frame. Array of call frames form the call stack.
CallFrame = dict  # Object type

# Scope description.
Scope = dict  # Object type

# Search match for resource.
SearchMatch = dict  # Object type

BreakLocation = dict  # Object type

WasmDisassemblyChunk = dict  # Object type

# Enum of possible script languages.
ScriptLanguage = str  # Literal enum: "JavaScript", "WebAssembly"

# Debug symbols available for a wasm script.
DebugSymbols = dict  # Object type

ResolvedBreakpoint = dict  # Object type

class Debugger:
    """Debugger domain exposes JavaScript debugging capabilities. It allows setting and removing
breakpoints, stepping through execution, exploring stack traces, etc."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def continue_to_location(self, location: Location, target_call_frames: str | None = None) -> dict:
        """Continues execution until specific location is reached."""
        params: dict[str, Any] = {}
        params["location"] = location
        if target_call_frames is not None:
            params["targetCallFrames"] = target_call_frames
        return await self._client.send(method="Debugger.continueToLocation", params=params)

    async def disable(self) -> dict:
        """Disables debugger for given page."""
        return await self._client.send(method="Debugger.disable")

    async def enable(self, max_scripts_cache_size: float | None = None) -> dict:
        """Enables debugger for the given page. Clients should not assume that the debugging has been
enabled until the result for this command is received.
        """
        params: dict[str, Any] = {}
        if max_scripts_cache_size is not None:
            params["maxScriptsCacheSize"] = max_scripts_cache_size
        return await self._client.send(method="Debugger.enable", params=params)

    async def evaluate_on_call_frame(
        self,
        call_frame_id: CallFrameId,
        expression: str,
        object_group: str | None = None,
        include_command_line_api: bool | None = None,
        silent: bool | None = None,
        return_by_value: bool | None = None,
        generate_preview: bool | None = None,
        throw_on_side_effect: bool | None = None,
        timeout: str | None = None,
    ) -> dict:
        """Evaluates expression on a given call frame."""
        params: dict[str, Any] = {}
        params["callFrameId"] = call_frame_id
        params["expression"] = expression
        if object_group is not None:
            params["objectGroup"] = object_group
        if include_command_line_api is not None:
            params["includeCommandLineAPI"] = include_command_line_api
        if silent is not None:
            params["silent"] = silent
        if return_by_value is not None:
            params["returnByValue"] = return_by_value
        if generate_preview is not None:
            params["generatePreview"] = generate_preview
        if throw_on_side_effect is not None:
            params["throwOnSideEffect"] = throw_on_side_effect
        if timeout is not None:
            params["timeout"] = timeout
        return await self._client.send(method="Debugger.evaluateOnCallFrame", params=params)

    async def get_possible_breakpoints(
        self,
        start: Location,
        end: Location | None = None,
        restrict_to_function: bool | None = None,
    ) -> dict:
        """Returns possible locations for breakpoint. scriptId in start and end range locations should be
the same.
        """
        params: dict[str, Any] = {}
        params["start"] = start
        if end is not None:
            params["end"] = end
        if restrict_to_function is not None:
            params["restrictToFunction"] = restrict_to_function
        return await self._client.send(method="Debugger.getPossibleBreakpoints", params=params)

    async def get_script_source(self, script_id: str) -> dict:
        """Returns source for the script with given id."""
        params: dict[str, Any] = {}
        params["scriptId"] = script_id
        return await self._client.send(method="Debugger.getScriptSource", params=params)

    async def disassemble_wasm_module(self, script_id: str) -> dict:
        params: dict[str, Any] = {}
        params["scriptId"] = script_id
        return await self._client.send(method="Debugger.disassembleWasmModule", params=params)

    async def next_wasm_disassembly_chunk(self, stream_id: str) -> dict:
        """Disassemble the next chunk of lines for the module corresponding to the
stream. If disassembly is complete, this API will invalidate the streamId
and return an empty chunk. Any subsequent calls for the now invalid stream
will return errors.
        """
        params: dict[str, Any] = {}
        params["streamId"] = stream_id
        return await self._client.send(method="Debugger.nextWasmDisassemblyChunk", params=params)

    async def get_wasm_bytecode(self, script_id: str) -> dict:
        """This command is deprecated. Use getScriptSource instead."""
        params: dict[str, Any] = {}
        params["scriptId"] = script_id
        return await self._client.send(method="Debugger.getWasmBytecode", params=params)

    async def get_stack_trace(self, stack_trace_id: str) -> dict:
        """Returns stack trace with given `stackTraceId`."""
        params: dict[str, Any] = {}
        params["stackTraceId"] = stack_trace_id
        return await self._client.send(method="Debugger.getStackTrace", params=params)

    async def pause(self) -> dict:
        """Stops on the next JavaScript statement."""
        return await self._client.send(method="Debugger.pause")

    async def pause_on_async_call(self, parent_stack_trace_id: str) -> dict:
        params: dict[str, Any] = {}
        params["parentStackTraceId"] = parent_stack_trace_id
        return await self._client.send(method="Debugger.pauseOnAsyncCall", params=params)

    async def remove_breakpoint(self, breakpoint_id: BreakpointId) -> dict:
        """Removes JavaScript breakpoint."""
        params: dict[str, Any] = {}
        params["breakpointId"] = breakpoint_id
        return await self._client.send(method="Debugger.removeBreakpoint", params=params)

    async def restart_frame(self, call_frame_id: CallFrameId, mode: str | None = None) -> dict:
        """Restarts particular call frame from the beginning. The old, deprecated
behavior of `restartFrame` is to stay paused and allow further CDP commands
after a restart was scheduled. This can cause problems with restarting, so
we now continue execution immediatly after it has been scheduled until we
reach the beginning of the restarted frame.

To stay back-wards compatible, `restartFrame` now expects a `mode`
parameter to be present. If the `mode` parameter is missing, `restartFrame`
errors out.

The various return values are deprecated and `callFrames` is always empty.
Use the call frames from the `Debugger#paused` events instead, that fires
once V8 pauses at the beginning of the restarted function.
        """
        params: dict[str, Any] = {}
        params["callFrameId"] = call_frame_id
        if mode is not None:
            params["mode"] = mode
        return await self._client.send(method="Debugger.restartFrame", params=params)

    async def resume(self, terminate_on_resume: bool | None = None) -> dict:
        """Resumes JavaScript execution."""
        params: dict[str, Any] = {}
        if terminate_on_resume is not None:
            params["terminateOnResume"] = terminate_on_resume
        return await self._client.send(method="Debugger.resume", params=params)

    async def search_in_content(
        self,
        script_id: str,
        query: str,
        case_sensitive: bool | None = None,
        is_regex: bool | None = None,
    ) -> dict:
        """Searches for given string in script content."""
        params: dict[str, Any] = {}
        params["scriptId"] = script_id
        params["query"] = query
        if case_sensitive is not None:
            params["caseSensitive"] = case_sensitive
        if is_regex is not None:
            params["isRegex"] = is_regex
        return await self._client.send(method="Debugger.searchInContent", params=params)

    async def set_async_call_stack_depth(self, max_depth: int) -> dict:
        """Enables or disables async call stacks tracking."""
        params: dict[str, Any] = {}
        params["maxDepth"] = max_depth
        return await self._client.send(method="Debugger.setAsyncCallStackDepth", params=params)

    async def set_blackbox_execution_contexts(self, unique_ids: list[str]) -> dict:
        """Replace previous blackbox execution contexts with passed ones. Forces backend to skip
stepping/pausing in scripts in these execution contexts. VM will try to leave blackboxed script by
performing 'step in' several times, finally resorting to 'step out' if unsuccessful.
        """
        params: dict[str, Any] = {}
        params["uniqueIds"] = unique_ids
        return await self._client.send(method="Debugger.setBlackboxExecutionContexts", params=params)

    async def set_blackbox_patterns(self, patterns: list[str], skip_anonymous: bool | None = None) -> dict:
        """Replace previous blackbox patterns with passed ones. Forces backend to skip stepping/pausing in
scripts with url matching one of the patterns. VM will try to leave blackboxed script by
performing 'step in' several times, finally resorting to 'step out' if unsuccessful.
        """
        params: dict[str, Any] = {}
        params["patterns"] = patterns
        if skip_anonymous is not None:
            params["skipAnonymous"] = skip_anonymous
        return await self._client.send(method="Debugger.setBlackboxPatterns", params=params)

    async def set_blackboxed_ranges(self, script_id: str, positions: list[ScriptPosition]) -> dict:
        """Makes backend skip steps in the script in blackboxed ranges. VM will try leave blacklisted
scripts by performing 'step in' several times, finally resorting to 'step out' if unsuccessful.
Positions array contains positions where blackbox state is changed. First interval isn't
blackboxed. Array should be sorted.
        """
        params: dict[str, Any] = {}
        params["scriptId"] = script_id
        params["positions"] = positions
        return await self._client.send(method="Debugger.setBlackboxedRanges", params=params)

    async def set_breakpoint(self, location: Location, condition: str | None = None) -> dict:
        """Sets JavaScript breakpoint at a given location."""
        params: dict[str, Any] = {}
        params["location"] = location
        if condition is not None:
            params["condition"] = condition
        return await self._client.send(method="Debugger.setBreakpoint", params=params)

    async def set_instrumentation_breakpoint(self, instrumentation: str) -> dict:
        """Sets instrumentation breakpoint."""
        params: dict[str, Any] = {}
        params["instrumentation"] = instrumentation
        return await self._client.send(method="Debugger.setInstrumentationBreakpoint", params=params)

    async def set_breakpoint_by_url(
        self,
        line_number: int,
        url: str | None = None,
        url_regex: str | None = None,
        script_hash: str | None = None,
        column_number: int | None = None,
        condition: str | None = None,
    ) -> dict:
        """Sets JavaScript breakpoint at given location specified either by URL or URL regex. Once this
command is issued, all existing parsed scripts will have breakpoints resolved and returned in
`locations` property. Further matching script parsing will result in subsequent
`breakpointResolved` events issued. This logical breakpoint will survive page reloads.
        """
        params: dict[str, Any] = {}
        params["lineNumber"] = line_number
        if url is not None:
            params["url"] = url
        if url_regex is not None:
            params["urlRegex"] = url_regex
        if script_hash is not None:
            params["scriptHash"] = script_hash
        if column_number is not None:
            params["columnNumber"] = column_number
        if condition is not None:
            params["condition"] = condition
        return await self._client.send(method="Debugger.setBreakpointByUrl", params=params)

    async def set_breakpoint_on_function_call(self, object_id: str, condition: str | None = None) -> dict:
        """Sets JavaScript breakpoint before each call to the given function.
If another function was created from the same source as a given one,
calling it will also trigger the breakpoint.
        """
        params: dict[str, Any] = {}
        params["objectId"] = object_id
        if condition is not None:
            params["condition"] = condition
        return await self._client.send(method="Debugger.setBreakpointOnFunctionCall", params=params)

    async def set_breakpoints_active(self, active: bool) -> dict:
        """Activates / deactivates all breakpoints on the page."""
        params: dict[str, Any] = {}
        params["active"] = active
        return await self._client.send(method="Debugger.setBreakpointsActive", params=params)

    async def set_pause_on_exceptions(self, state: str) -> dict:
        """Defines pause on exceptions state. Can be set to stop on all exceptions, uncaught exceptions,
or caught exceptions, no exceptions. Initial pause on exceptions state is `none`.
        """
        params: dict[str, Any] = {}
        params["state"] = state
        return await self._client.send(method="Debugger.setPauseOnExceptions", params=params)

    async def set_return_value(self, new_value: str) -> dict:
        """Changes return value in top frame. Available only at return break position."""
        params: dict[str, Any] = {}
        params["newValue"] = new_value
        return await self._client.send(method="Debugger.setReturnValue", params=params)

    async def set_script_source(
        self,
        script_id: str,
        script_source: str,
        dry_run: bool | None = None,
        allow_top_frame_editing: bool | None = None,
    ) -> dict:
        """Edits JavaScript source live.

In general, functions that are currently on the stack can not be edited with
a single exception: If the edited function is the top-most stack frame and
that is the only activation of that function on the stack. In this case
the live edit will be successful and a `Debugger.restartFrame` for the
top-most function is automatically triggered.
        """
        params: dict[str, Any] = {}
        params["scriptId"] = script_id
        params["scriptSource"] = script_source
        if dry_run is not None:
            params["dryRun"] = dry_run
        if allow_top_frame_editing is not None:
            params["allowTopFrameEditing"] = allow_top_frame_editing
        return await self._client.send(method="Debugger.setScriptSource", params=params)

    async def set_skip_all_pauses(self, skip: bool) -> dict:
        """Makes page not interrupt on any pauses (breakpoint, exception, dom exception etc)."""
        params: dict[str, Any] = {}
        params["skip"] = skip
        return await self._client.send(method="Debugger.setSkipAllPauses", params=params)

    async def set_variable_value(
        self,
        scope_number: int,
        variable_name: str,
        new_value: str,
        call_frame_id: CallFrameId,
    ) -> dict:
        """Changes value of variable in a callframe. Object-based scopes are not supported and must be
mutated manually.
        """
        params: dict[str, Any] = {}
        params["scopeNumber"] = scope_number
        params["variableName"] = variable_name
        params["newValue"] = new_value
        params["callFrameId"] = call_frame_id
        return await self._client.send(method="Debugger.setVariableValue", params=params)

    async def step_into(self, break_on_async_call: bool | None = None, skip_list: list[LocationRange] | None = None) -> dict:
        """Steps into the function call."""
        params: dict[str, Any] = {}
        if break_on_async_call is not None:
            params["breakOnAsyncCall"] = break_on_async_call
        if skip_list is not None:
            params["skipList"] = skip_list
        return await self._client.send(method="Debugger.stepInto", params=params)

    async def step_out(self) -> dict:
        """Steps out of the function call."""
        return await self._client.send(method="Debugger.stepOut")

    async def step_over(self, skip_list: list[LocationRange] | None = None) -> dict:
        """Steps over the statement."""
        params: dict[str, Any] = {}
        if skip_list is not None:
            params["skipList"] = skip_list
        return await self._client.send(method="Debugger.stepOver", params=params)
