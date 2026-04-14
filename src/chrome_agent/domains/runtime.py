"""CDP Runtime domain.

Runtime domain exposes JavaScript runtime by means of remote evaluation and mirror objects.
Evaluation results are returned as mirror object that expose object type, string representation
and unique identifier that can be used for further object reference. Original objects are
maintained in memory unless they are either explicitly released or are released along with the
other objects in their object group.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


ScriptId = str

# Represents options for serialization. Overrides `generatePreview` and `returnByValue`.
SerializationOptions = dict  # Object type

# Represents deep serialized value.
DeepSerializedValue = dict  # Object type

RemoteObjectId = str

UnserializableValue = str

# Mirror object referencing original JavaScript object.
RemoteObject = dict  # Object type

CustomPreview = dict  # Object type

# Object containing abbreviated remote object value.
ObjectPreview = dict  # Object type

PropertyPreview = dict  # Object type

EntryPreview = dict  # Object type

# Object property descriptor.
PropertyDescriptor = dict  # Object type

# Object internal property descriptor. This property isn't normally visible in JavaScript code.
InternalPropertyDescriptor = dict  # Object type

# Object private field descriptor.
PrivatePropertyDescriptor = dict  # Object type

# Represents function call argument. Either remote object id `objectId`, primitive `value`,
# unserializable primitive value or neither of (for undefined) them should be specified.
CallArgument = dict  # Object type

ExecutionContextId = int

# Description of an isolated world.
ExecutionContextDescription = dict  # Object type

# Detailed information about exception (or error) that was thrown during script compilation or
# execution.
ExceptionDetails = dict  # Object type

Timestamp = float

TimeDelta = float

# Stack entry for runtime errors and assertions.
CallFrame = dict  # Object type

# Call frames for assertions or error messages.
StackTrace = dict  # Object type

UniqueDebuggerId = str

# If `debuggerId` is set stack trace comes from another debugger and can be resolved there. This
# allows to track cross-debugger calls. See `Runtime.StackTrace` and `Debugger.paused` for usages.
StackTraceId = dict  # Object type

class Runtime:
    """Runtime domain exposes JavaScript runtime by means of remote evaluation and mirror objects.
Evaluation results are returned as mirror object that expose object type, string representation
and unique identifier that can be used for further object reference. Original objects are
maintained in memory unless they are either explicitly released or are released along with the
other objects in their object group."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def await_promise(
        self,
        promise_object_id: RemoteObjectId,
        return_by_value: bool | None = None,
        generate_preview: bool | None = None,
    ) -> dict:
        """Add handler to promise with given promise object id."""
        params: dict[str, Any] = {}
        params["promiseObjectId"] = promise_object_id
        if return_by_value is not None:
            params["returnByValue"] = return_by_value
        if generate_preview is not None:
            params["generatePreview"] = generate_preview
        return await self._client.send(method="Runtime.awaitPromise", params=params)

    async def call_function_on(
        self,
        function_declaration: str,
        object_id: RemoteObjectId | None = None,
        arguments: list[CallArgument] | None = None,
        silent: bool | None = None,
        return_by_value: bool | None = None,
        generate_preview: bool | None = None,
        user_gesture: bool | None = None,
        await_promise: bool | None = None,
        execution_context_id: ExecutionContextId | None = None,
        object_group: str | None = None,
        throw_on_side_effect: bool | None = None,
        unique_context_id: str | None = None,
        serialization_options: SerializationOptions | None = None,
    ) -> dict:
        """Calls function with given declaration on the given object. Object group of the result is
inherited from the target object.
        """
        params: dict[str, Any] = {}
        params["functionDeclaration"] = function_declaration
        if object_id is not None:
            params["objectId"] = object_id
        if arguments is not None:
            params["arguments"] = arguments
        if silent is not None:
            params["silent"] = silent
        if return_by_value is not None:
            params["returnByValue"] = return_by_value
        if generate_preview is not None:
            params["generatePreview"] = generate_preview
        if user_gesture is not None:
            params["userGesture"] = user_gesture
        if await_promise is not None:
            params["awaitPromise"] = await_promise
        if execution_context_id is not None:
            params["executionContextId"] = execution_context_id
        if object_group is not None:
            params["objectGroup"] = object_group
        if throw_on_side_effect is not None:
            params["throwOnSideEffect"] = throw_on_side_effect
        if unique_context_id is not None:
            params["uniqueContextId"] = unique_context_id
        if serialization_options is not None:
            params["serializationOptions"] = serialization_options
        return await self._client.send(method="Runtime.callFunctionOn", params=params)

    async def compile_script(
        self,
        expression: str,
        source_url: str,
        persist_script: bool,
        execution_context_id: ExecutionContextId | None = None,
    ) -> dict:
        """Compiles expression."""
        params: dict[str, Any] = {}
        params["expression"] = expression
        params["sourceURL"] = source_url
        params["persistScript"] = persist_script
        if execution_context_id is not None:
            params["executionContextId"] = execution_context_id
        return await self._client.send(method="Runtime.compileScript", params=params)

    async def disable(self) -> dict:
        """Disables reporting of execution contexts creation."""
        return await self._client.send(method="Runtime.disable")

    async def discard_console_entries(self) -> dict:
        """Discards collected exceptions and console API calls."""
        return await self._client.send(method="Runtime.discardConsoleEntries")

    async def enable(self) -> dict:
        """Enables reporting of execution contexts creation by means of `executionContextCreated` event.
When the reporting gets enabled the event will be sent immediately for each existing execution
context.
        """
        return await self._client.send(method="Runtime.enable")

    async def evaluate(
        self,
        expression: str,
        object_group: str | None = None,
        include_command_line_api: bool | None = None,
        silent: bool | None = None,
        context_id: ExecutionContextId | None = None,
        return_by_value: bool | None = None,
        generate_preview: bool | None = None,
        user_gesture: bool | None = None,
        await_promise: bool | None = None,
        throw_on_side_effect: bool | None = None,
        timeout: TimeDelta | None = None,
        disable_breaks: bool | None = None,
        repl_mode: bool | None = None,
        allow_unsafe_eval_blocked_by_csp: bool | None = None,
        unique_context_id: str | None = None,
        serialization_options: SerializationOptions | None = None,
    ) -> dict:
        """Evaluates expression on global object."""
        params: dict[str, Any] = {}
        params["expression"] = expression
        if object_group is not None:
            params["objectGroup"] = object_group
        if include_command_line_api is not None:
            params["includeCommandLineAPI"] = include_command_line_api
        if silent is not None:
            params["silent"] = silent
        if context_id is not None:
            params["contextId"] = context_id
        if return_by_value is not None:
            params["returnByValue"] = return_by_value
        if generate_preview is not None:
            params["generatePreview"] = generate_preview
        if user_gesture is not None:
            params["userGesture"] = user_gesture
        if await_promise is not None:
            params["awaitPromise"] = await_promise
        if throw_on_side_effect is not None:
            params["throwOnSideEffect"] = throw_on_side_effect
        if timeout is not None:
            params["timeout"] = timeout
        if disable_breaks is not None:
            params["disableBreaks"] = disable_breaks
        if repl_mode is not None:
            params["replMode"] = repl_mode
        if allow_unsafe_eval_blocked_by_csp is not None:
            params["allowUnsafeEvalBlockedByCSP"] = allow_unsafe_eval_blocked_by_csp
        if unique_context_id is not None:
            params["uniqueContextId"] = unique_context_id
        if serialization_options is not None:
            params["serializationOptions"] = serialization_options
        return await self._client.send(method="Runtime.evaluate", params=params)

    async def get_isolate_id(self) -> dict:
        """Returns the isolate id."""
        return await self._client.send(method="Runtime.getIsolateId")

    async def get_heap_usage(self) -> dict:
        """Returns the JavaScript heap usage.
It is the total usage of the corresponding isolate not scoped to a particular Runtime.
        """
        return await self._client.send(method="Runtime.getHeapUsage")

    async def get_properties(
        self,
        object_id: RemoteObjectId,
        own_properties: bool | None = None,
        accessor_properties_only: bool | None = None,
        generate_preview: bool | None = None,
        non_indexed_properties_only: bool | None = None,
    ) -> dict:
        """Returns properties of a given object. Object group of the result is inherited from the target
object.
        """
        params: dict[str, Any] = {}
        params["objectId"] = object_id
        if own_properties is not None:
            params["ownProperties"] = own_properties
        if accessor_properties_only is not None:
            params["accessorPropertiesOnly"] = accessor_properties_only
        if generate_preview is not None:
            params["generatePreview"] = generate_preview
        if non_indexed_properties_only is not None:
            params["nonIndexedPropertiesOnly"] = non_indexed_properties_only
        return await self._client.send(method="Runtime.getProperties", params=params)

    async def global_lexical_scope_names(self, execution_context_id: ExecutionContextId | None = None) -> dict:
        """Returns all let, const and class variables from global scope."""
        params: dict[str, Any] = {}
        if execution_context_id is not None:
            params["executionContextId"] = execution_context_id
        return await self._client.send(method="Runtime.globalLexicalScopeNames", params=params)

    async def query_objects(self, prototype_object_id: RemoteObjectId, object_group: str | None = None) -> dict:
        params: dict[str, Any] = {}
        params["prototypeObjectId"] = prototype_object_id
        if object_group is not None:
            params["objectGroup"] = object_group
        return await self._client.send(method="Runtime.queryObjects", params=params)

    async def release_object(self, object_id: RemoteObjectId) -> dict:
        """Releases remote object with given id."""
        params: dict[str, Any] = {}
        params["objectId"] = object_id
        return await self._client.send(method="Runtime.releaseObject", params=params)

    async def release_object_group(self, object_group: str) -> dict:
        """Releases all remote objects that belong to a given group."""
        params: dict[str, Any] = {}
        params["objectGroup"] = object_group
        return await self._client.send(method="Runtime.releaseObjectGroup", params=params)

    async def run_if_waiting_for_debugger(self) -> dict:
        """Tells inspected instance to run if it was waiting for debugger to attach."""
        return await self._client.send(method="Runtime.runIfWaitingForDebugger")

    async def run_script(
        self,
        script_id: ScriptId,
        execution_context_id: ExecutionContextId | None = None,
        object_group: str | None = None,
        silent: bool | None = None,
        include_command_line_api: bool | None = None,
        return_by_value: bool | None = None,
        generate_preview: bool | None = None,
        await_promise: bool | None = None,
    ) -> dict:
        """Runs script with given id in a given context."""
        params: dict[str, Any] = {}
        params["scriptId"] = script_id
        if execution_context_id is not None:
            params["executionContextId"] = execution_context_id
        if object_group is not None:
            params["objectGroup"] = object_group
        if silent is not None:
            params["silent"] = silent
        if include_command_line_api is not None:
            params["includeCommandLineAPI"] = include_command_line_api
        if return_by_value is not None:
            params["returnByValue"] = return_by_value
        if generate_preview is not None:
            params["generatePreview"] = generate_preview
        if await_promise is not None:
            params["awaitPromise"] = await_promise
        return await self._client.send(method="Runtime.runScript", params=params)

    async def set_async_call_stack_depth(self, max_depth: int) -> dict:
        """Enables or disables async call stacks tracking."""
        params: dict[str, Any] = {}
        params["maxDepth"] = max_depth
        return await self._client.send(method="Runtime.setAsyncCallStackDepth", params=params)

    async def set_custom_object_formatter_enabled(self, enabled: bool) -> dict:
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="Runtime.setCustomObjectFormatterEnabled", params=params)

    async def set_max_call_stack_size_to_capture(self, size: int) -> dict:
        params: dict[str, Any] = {}
        params["size"] = size
        return await self._client.send(method="Runtime.setMaxCallStackSizeToCapture", params=params)

    async def terminate_execution(self) -> dict:
        """Terminate current or next JavaScript execution.
Will cancel the termination when the outer-most script execution ends.
        """
        return await self._client.send(method="Runtime.terminateExecution")

    async def add_binding(
        self,
        name: str,
        execution_context_id: ExecutionContextId | None = None,
        execution_context_name: str | None = None,
    ) -> dict:
        """If executionContextId is empty, adds binding with the given name on the
global objects of all inspected contexts, including those created later,
bindings survive reloads.
Binding function takes exactly one argument, this argument should be string,
in case of any other input, function throws an exception.
Each binding function call produces Runtime.bindingCalled notification.
        """
        params: dict[str, Any] = {}
        params["name"] = name
        if execution_context_id is not None:
            params["executionContextId"] = execution_context_id
        if execution_context_name is not None:
            params["executionContextName"] = execution_context_name
        return await self._client.send(method="Runtime.addBinding", params=params)

    async def remove_binding(self, name: str) -> dict:
        """This method does not remove binding function from global object but
unsubscribes current runtime agent from Runtime.bindingCalled notifications.
        """
        params: dict[str, Any] = {}
        params["name"] = name
        return await self._client.send(method="Runtime.removeBinding", params=params)

    async def get_exception_details(self, error_object_id: RemoteObjectId) -> dict:
        """This method tries to lookup and populate exception details for a
JavaScript Error object.
Note that the stackTrace portion of the resulting exceptionDetails will
only be populated if the Runtime domain was enabled at the time when the
Error was thrown.
        """
        params: dict[str, Any] = {}
        params["errorObjectId"] = error_object_id
        return await self._client.send(method="Runtime.getExceptionDetails", params=params)
