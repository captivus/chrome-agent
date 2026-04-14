"""CDP CSS domain.

This domain exposes CSS read/write operations. All CSS objects (stylesheets, rules, and styles)
have an associated `id` used in subsequent operations on the related object. Each object type has
a specific `id` structure, and those are not interchangeable between objects of different kinds.
CSS objects can be loaded using the `get*ForNode()` calls (which accept a DOM node id). A client
can also keep track of stylesheets via the `styleSheetAdded`/`styleSheetRemoved` events and
subsequently load the required stylesheet contents using the `getStyleSheet[Text]()` methods.

Auto-generated from Chrome DevTools Protocol schema.
Do not edit manually. Re-run the generator to update.
"""

from __future__ import annotations

from typing import Any

from chrome_agent.cdp_client import CDPClient


# Stylesheet type: "injected" for stylesheets injected via extension, "user-agent" for user-agent
# stylesheets, "inspector" for stylesheets created by the inspector (i.e. those holding the "via
# inspector" rules), "regular" for regular stylesheets.
StyleSheetOrigin = str  # Literal enum: "injected", "user-agent", "inspector", "regular"

# CSS rule collection for a single pseudo style.
PseudoElementMatches = dict  # Object type

# CSS style coming from animations with the name of the animation.
CSSAnimationStyle = dict  # Object type

# Inherited CSS rule collection from ancestor node.
InheritedStyleEntry = dict  # Object type

# Inherited CSS style collection for animated styles from ancestor node.
InheritedAnimatedStyleEntry = dict  # Object type

# Inherited pseudo element matches from pseudos of an ancestor node.
InheritedPseudoElementMatches = dict  # Object type

# Match data for a CSS rule.
RuleMatch = dict  # Object type

# Data for a simple selector (these are delimited by commas in a selector list).
Value = dict  # Object type

# Specificity:
# https://drafts.csswg.org/selectors/#specificity-rules
Specificity = dict  # Object type

# Selector list data.
SelectorList = dict  # Object type

# CSS stylesheet metainformation.
CSSStyleSheetHeader = dict  # Object type

# CSS rule representation.
CSSRule = dict  # Object type

# Enum indicating the type of a CSS rule, used to represent the order of a style rule's ancestors.
# This list only contains rule types that are collected during the ancestor rule collection.
CSSRuleType = str  # Literal enum: "MediaRule", "SupportsRule", "ContainerRule", "LayerRule", "ScopeRule", "StyleRule", "StartingStyleRule"

# CSS coverage information.
RuleUsage = dict  # Object type

# Text range within a resource. All numbers are zero-based.
SourceRange = dict  # Object type

ShorthandEntry = dict  # Object type

CSSComputedStyleProperty = dict  # Object type

ComputedStyleExtraFields = dict  # Object type

# CSS style representation.
CSSStyle = dict  # Object type

# CSS property declaration data.
CSSProperty = dict  # Object type

# CSS media rule descriptor.
CSSMedia = dict  # Object type

# Media query descriptor.
MediaQuery = dict  # Object type

# Media query expression descriptor.
MediaQueryExpression = dict  # Object type

# CSS container query rule descriptor.
CSSContainerQuery = dict  # Object type

# CSS Supports at-rule descriptor.
CSSSupports = dict  # Object type

# CSS Scope at-rule descriptor.
CSSScope = dict  # Object type

# CSS Layer at-rule descriptor.
CSSLayer = dict  # Object type

# CSS Starting Style at-rule descriptor.
CSSStartingStyle = dict  # Object type

# CSS Layer data.
CSSLayerData = dict  # Object type

# Information about amount of glyphs that were rendered with given font.
PlatformFontUsage = dict  # Object type

# Information about font variation axes for variable fonts
FontVariationAxis = dict  # Object type

# Properties of a web font: https://www.w3.org/TR/2008/REC-CSS2-20080411/fonts.html#font-descriptions
# and additional information such as platformFontFamily and fontVariationAxes.
FontFace = dict  # Object type

# CSS try rule representation.
CSSTryRule = dict  # Object type

# CSS @position-try rule representation.
CSSPositionTryRule = dict  # Object type

# CSS keyframes rule representation.
CSSKeyframesRule = dict  # Object type

# Representation of a custom property registration through CSS.registerProperty
CSSPropertyRegistration = dict  # Object type

# CSS generic @rule representation.
CSSAtRule = dict  # Object type

# CSS property at-rule representation.
CSSPropertyRule = dict  # Object type

# CSS function argument representation.
CSSFunctionParameter = dict  # Object type

# CSS function conditional block representation.
CSSFunctionConditionNode = dict  # Object type

# Section of the body of a CSS function rule.
CSSFunctionNode = dict  # Object type

# CSS function at-rule representation.
CSSFunctionRule = dict  # Object type

# CSS keyframe rule representation.
CSSKeyframeRule = dict  # Object type

# A descriptor of operation to mutate style declaration text.
StyleDeclarationEdit = dict  # Object type

class CSS:
    """This domain exposes CSS read/write operations. All CSS objects (stylesheets, rules, and styles)
have an associated `id` used in subsequent operations on the related object. Each object type has
a specific `id` structure, and those are not interchangeable between objects of different kinds.
CSS objects can be loaded using the `get*ForNode()` calls (which accept a DOM node id). A client
can also keep track of stylesheets via the `styleSheetAdded`/`styleSheetRemoved` events and
subsequently load the required stylesheet contents using the `getStyleSheet[Text]()` methods."""

    def __init__(self, client: CDPClient):
        self._client = client

    async def add_rule(
        self,
        style_sheet_id: str,
        rule_text: str,
        location: SourceRange,
        node_for_property_syntax_validation: str | None = None,
    ) -> dict:
        """Inserts a new rule with the given `ruleText` in a stylesheet with given `styleSheetId`, at the
position specified by `location`.
        """
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["ruleText"] = rule_text
        params["location"] = location
        if node_for_property_syntax_validation is not None:
            params["nodeForPropertySyntaxValidation"] = node_for_property_syntax_validation
        return await self._client.send(method="CSS.addRule", params=params)

    async def collect_class_names(self, style_sheet_id: str) -> dict:
        """Returns all class names from specified stylesheet."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        return await self._client.send(method="CSS.collectClassNames", params=params)

    async def create_style_sheet(self, frame_id: str, force: bool | None = None) -> dict:
        """Creates a new special "via-inspector" stylesheet in the frame with given `frameId`."""
        params: dict[str, Any] = {}
        params["frameId"] = frame_id
        if force is not None:
            params["force"] = force
        return await self._client.send(method="CSS.createStyleSheet", params=params)

    async def disable(self) -> dict:
        """Disables the CSS agent for the given page."""
        return await self._client.send(method="CSS.disable")

    async def enable(self) -> dict:
        """Enables the CSS agent for the given page. Clients should not assume that the CSS agent has been
enabled until the result of this command is received.
        """
        return await self._client.send(method="CSS.enable")

    async def force_pseudo_state(self, node_id: str, forced_pseudo_classes: list[str]) -> dict:
        """Ensures that the given node will have specified pseudo-classes whenever its style is computed by
the browser.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["forcedPseudoClasses"] = forced_pseudo_classes
        return await self._client.send(method="CSS.forcePseudoState", params=params)

    async def force_starting_style(self, node_id: str, forced: bool) -> dict:
        """Ensures that the given node is in its starting-style state."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["forced"] = forced
        return await self._client.send(method="CSS.forceStartingStyle", params=params)

    async def get_background_colors(self, node_id: str) -> dict:
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="CSS.getBackgroundColors", params=params)

    async def get_computed_style_for_node(self, node_id: str) -> dict:
        """Returns the computed style for a DOM node identified by `nodeId`."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="CSS.getComputedStyleForNode", params=params)

    async def resolve_values(
        self,
        values: list[str],
        node_id: str,
        property_name: str | None = None,
        pseudo_type: str | None = None,
        pseudo_identifier: str | None = None,
    ) -> dict:
        """Resolve the specified values in the context of the provided element.
For example, a value of '1em' is evaluated according to the computed
'font-size' of the element and a value 'calc(1px + 2px)' will be
resolved to '3px'.
If the `propertyName` was specified the `values` are resolved as if
they were property's declaration. If a value cannot be parsed according
to the provided property syntax, the value is parsed using combined
syntax as if null `propertyName` was provided. If the value cannot be
resolved even then, return the provided value without any changes.
Note: this function currently does not resolve CSS random() function,
it returns unmodified random() function parts.`
        """
        params: dict[str, Any] = {}
        params["values"] = values
        params["nodeId"] = node_id
        if property_name is not None:
            params["propertyName"] = property_name
        if pseudo_type is not None:
            params["pseudoType"] = pseudo_type
        if pseudo_identifier is not None:
            params["pseudoIdentifier"] = pseudo_identifier
        return await self._client.send(method="CSS.resolveValues", params=params)

    async def get_longhand_properties(self, shorthand_name: str, value: str) -> dict:
        params: dict[str, Any] = {}
        params["shorthandName"] = shorthand_name
        params["value"] = value
        return await self._client.send(method="CSS.getLonghandProperties", params=params)

    async def get_inline_styles_for_node(self, node_id: str) -> dict:
        """Returns the styles defined inline (explicitly in the "style" attribute and implicitly, using DOM
attributes) for a DOM node identified by `nodeId`.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="CSS.getInlineStylesForNode", params=params)

    async def get_animated_styles_for_node(self, node_id: str) -> dict:
        """Returns the styles coming from animations & transitions
including the animation & transition styles coming from inheritance chain.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="CSS.getAnimatedStylesForNode", params=params)

    async def get_matched_styles_for_node(self, node_id: str) -> dict:
        """Returns requested styles for a DOM node identified by `nodeId`."""
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="CSS.getMatchedStylesForNode", params=params)

    async def get_environment_variables(self) -> dict:
        """Returns the values of the default UA-defined environment variables used in env()"""
        return await self._client.send(method="CSS.getEnvironmentVariables")

    async def get_media_queries(self) -> dict:
        """Returns all media queries parsed by the rendering engine."""
        return await self._client.send(method="CSS.getMediaQueries")

    async def get_platform_fonts_for_node(self, node_id: str) -> dict:
        """Requests information about platform fonts which we used to render child TextNodes in the given
node.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="CSS.getPlatformFontsForNode", params=params)

    async def get_style_sheet_text(self, style_sheet_id: str) -> dict:
        """Returns the current textual content for a stylesheet."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        return await self._client.send(method="CSS.getStyleSheetText", params=params)

    async def get_layers_for_node(self, node_id: str) -> dict:
        """Returns all layers parsed by the rendering engine for the tree scope of a node.
Given a DOM element identified by nodeId, getLayersForNode returns the root
layer for the nearest ancestor document or shadow root. The layer root contains
the full layer tree for the tree scope and their ordering.
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        return await self._client.send(method="CSS.getLayersForNode", params=params)

    async def get_location_for_selector(self, style_sheet_id: str, selector_text: str) -> dict:
        """Given a CSS selector text and a style sheet ID, getLocationForSelector
returns an array of locations of the CSS selector in the style sheet.
        """
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["selectorText"] = selector_text
        return await self._client.send(method="CSS.getLocationForSelector", params=params)

    async def track_computed_style_updates_for_node(self, node_id: str | None = None) -> dict:
        """Starts tracking the given node for the computed style updates
and whenever the computed style is updated for node, it queues
a `computedStyleUpdated` event with throttling.
There can only be 1 node tracked for computed style updates
so passing a new node id removes tracking from the previous node.
Pass `undefined` to disable tracking.
        """
        params: dict[str, Any] = {}
        if node_id is not None:
            params["nodeId"] = node_id
        return await self._client.send(method="CSS.trackComputedStyleUpdatesForNode", params=params)

    async def track_computed_style_updates(self, properties_to_track: list[CSSComputedStyleProperty]) -> dict:
        """Starts tracking the given computed styles for updates. The specified array of properties
replaces the one previously specified. Pass empty array to disable tracking.
Use takeComputedStyleUpdates to retrieve the list of nodes that had properties modified.
The changes to computed style properties are only tracked for nodes pushed to the front-end
by the DOM agent. If no changes to the tracked properties occur after the node has been pushed
to the front-end, no updates will be issued for the node.
        """
        params: dict[str, Any] = {}
        params["propertiesToTrack"] = properties_to_track
        return await self._client.send(method="CSS.trackComputedStyleUpdates", params=params)

    async def take_computed_style_updates(self) -> dict:
        """Polls the next batch of computed style updates."""
        return await self._client.send(method="CSS.takeComputedStyleUpdates")

    async def set_effective_property_value_for_node(
        self,
        node_id: str,
        property_name: str,
        value: str,
    ) -> dict:
        """Find a rule with the given active property for the given node and set the new value for this
property
        """
        params: dict[str, Any] = {}
        params["nodeId"] = node_id
        params["propertyName"] = property_name
        params["value"] = value
        return await self._client.send(method="CSS.setEffectivePropertyValueForNode", params=params)

    async def set_property_rule_property_name(
        self,
        style_sheet_id: str,
        range_: SourceRange,
        property_name: str,
    ) -> dict:
        """Modifies the property rule property name."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["range"] = range_
        params["propertyName"] = property_name
        return await self._client.send(method="CSS.setPropertyRulePropertyName", params=params)

    async def set_keyframe_key(
        self,
        style_sheet_id: str,
        range_: SourceRange,
        key_text: str,
    ) -> dict:
        """Modifies the keyframe rule key text."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["range"] = range_
        params["keyText"] = key_text
        return await self._client.send(method="CSS.setKeyframeKey", params=params)

    async def set_media_text(
        self,
        style_sheet_id: str,
        range_: SourceRange,
        text: str,
    ) -> dict:
        """Modifies the rule selector."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["range"] = range_
        params["text"] = text
        return await self._client.send(method="CSS.setMediaText", params=params)

    async def set_container_query_text(
        self,
        style_sheet_id: str,
        range_: SourceRange,
        text: str,
    ) -> dict:
        """Modifies the expression of a container query."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["range"] = range_
        params["text"] = text
        return await self._client.send(method="CSS.setContainerQueryText", params=params)

    async def set_supports_text(
        self,
        style_sheet_id: str,
        range_: SourceRange,
        text: str,
    ) -> dict:
        """Modifies the expression of a supports at-rule."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["range"] = range_
        params["text"] = text
        return await self._client.send(method="CSS.setSupportsText", params=params)

    async def set_scope_text(
        self,
        style_sheet_id: str,
        range_: SourceRange,
        text: str,
    ) -> dict:
        """Modifies the expression of a scope at-rule."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["range"] = range_
        params["text"] = text
        return await self._client.send(method="CSS.setScopeText", params=params)

    async def set_rule_selector(
        self,
        style_sheet_id: str,
        range_: SourceRange,
        selector: str,
    ) -> dict:
        """Modifies the rule selector."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["range"] = range_
        params["selector"] = selector
        return await self._client.send(method="CSS.setRuleSelector", params=params)

    async def set_style_sheet_text(self, style_sheet_id: str, text: str) -> dict:
        """Sets the new stylesheet text."""
        params: dict[str, Any] = {}
        params["styleSheetId"] = style_sheet_id
        params["text"] = text
        return await self._client.send(method="CSS.setStyleSheetText", params=params)

    async def set_style_texts(self, edits: list[StyleDeclarationEdit], node_for_property_syntax_validation: str | None = None) -> dict:
        """Applies specified style edits one after another in the given order."""
        params: dict[str, Any] = {}
        params["edits"] = edits
        if node_for_property_syntax_validation is not None:
            params["nodeForPropertySyntaxValidation"] = node_for_property_syntax_validation
        return await self._client.send(method="CSS.setStyleTexts", params=params)

    async def start_rule_usage_tracking(self) -> dict:
        """Enables the selector recording."""
        return await self._client.send(method="CSS.startRuleUsageTracking")

    async def stop_rule_usage_tracking(self) -> dict:
        """Stop tracking rule usage and return the list of rules that were used since last call to
`takeCoverageDelta` (or since start of coverage instrumentation).
        """
        return await self._client.send(method="CSS.stopRuleUsageTracking")

    async def take_coverage_delta(self) -> dict:
        """Obtain list of rules that became used since last call to this method (or since start of coverage
instrumentation).
        """
        return await self._client.send(method="CSS.takeCoverageDelta")

    async def set_local_fonts_enabled(self, enabled: bool) -> dict:
        """Enables/disables rendering of local CSS fonts (enabled by default)."""
        params: dict[str, Any] = {}
        params["enabled"] = enabled
        return await self._client.send(method="CSS.setLocalFontsEnabled", params=params)
