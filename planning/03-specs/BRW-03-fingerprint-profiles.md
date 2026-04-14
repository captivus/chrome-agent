# Feature Specification

> *This document is the complete definition of a single atomic feature -- what to build, how to validate it, what to observe during implementation, what it depends on, and (once implementation begins) its implementation history.*

## 1. Feature ID and Name

BRW-03: Fingerprint Profiles

## 2. User Story

As an AI agent automating a browser, I want to apply an anti-detection fingerprint profile so that the browser appears as a real desktop browser rather than an automated instance, reducing the chance of being blocked by anti-bot systems.

## 3. Implementation Contract

### Level 1 -- Plain English

This feature loads a fingerprint profile from a JSON file and applies it to a running browser via CDP. The profile specifies browser identity signals -- user agent, platform, vendor, viewport dimensions, locale, and timezone. The feature overrides JavaScript navigator properties and the webdriver detection flag so that page scripts see a consistent, realistic browser fingerprint.

The fingerprint must be applied before any pages load, so that page scripts never see the real (automated) values. This is accomplished by injecting an init script via CDP that runs before any page JavaScript, and by setting browser-level overrides for viewport, user agent, locale, and timezone.

The feature receives a file path to the profile JSON and a CDP port to connect to. It connects to the browser, applies the overrides, and disconnects.

### Level 2 -- Logic Flow (INPUT / LOGIC / OUTPUT)

**INPUT:**

- `path`: string -- path to the fingerprint profile JSON file
- `port`: integer, default 9222 -- CDP port of the running browser

**LOGIC:**

```
load_fingerprint(path):
    data = read_json_file(path)
    return BrowserFingerprint(
        user_agent=data["userAgent"],
        viewport=data["viewport"],  // {"width": int, "height": int}
        locale=data["language"],
        timezone=data["timezone"],
        platform=data["platform"],
        vendor=data["vendor"],
    )

apply_fingerprint(port, profile):
    // Connect to the page target
    ws_url = get_ws_url(port=port, target_type="page")
    async with CDPClient(ws_url=ws_url) as cdp:

        // Inject init script that overrides navigator properties
        // This runs before any page JavaScript on every navigation
        init_script = build_init_script(profile)
        await cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": init_script})

        // Set browser-level overrides via Emulation domain
        await cdp.send("Emulation.setUserAgentOverride", {
            "userAgent": profile.user_agent,
            "platform": profile.platform,
        })

        // Set viewport
        await cdp.send("Emulation.setDeviceMetricsOverride", {
            "width": profile.viewport["width"],
            "height": profile.viewport["height"],
            "deviceScaleFactor": 1,
            "mobile": False,
        })

        // Set locale and timezone
        await cdp.send("Emulation.setLocaleOverride", {"locale": profile.locale})
        await cdp.send("Emulation.setTimezoneOverride", {"timezoneId": profile.timezone})


build_init_script(profile):
    return javascript that:
        - Object.defineProperty(navigator, 'webdriver', {get: () => false})
        - Object.defineProperty(navigator, 'platform', {get: () => profile.platform})
        - Object.defineProperty(navigator, 'vendor', {get: () => profile.vendor})
        - window.chrome = {runtime: {}, app: {}}
          // Minimal shape -- anti-bot systems check for the existence
          // of window.chrome with runtime and app sub-objects.
          // Stubs are sufficient; full Chrome extension API emulation
          // is out of scope.
```

**OUTPUT:**

- On success: the browser's JavaScript environment reflects the spoofed values. No return value.
- On failure: raises FileNotFoundError (profile not found), json.JSONDecodeError (invalid JSON), KeyError (missing required profile fields), or CDPError (CDP commands failed).

### Level 3 -- Formal Interfaces

```python
@dataclass
class BrowserFingerprint:
    """Browser fingerprint profile for anti-detection."""
    user_agent: str
    viewport: dict[str, int]  # {"width": int, "height": int}
    locale: str
    timezone: str
    platform: str
    vendor: str


def load_fingerprint(path: str) -> BrowserFingerprint:
    """Load a fingerprint profile from a JSON file.

    Expected JSON schema:
        {
            "userAgent": "...",
            "platform": "...",
            "vendor": "...",
            "language": "en-US",
            "timezone": "America/Chicago",
            "viewport": {"width": 1920, "height": 1080}
        }

    Raises FileNotFoundError if path doesn't exist.
    Raises KeyError if required fields are missing.
    """
    ...


async def apply_fingerprint(
    port: int = 9222,
    profile: BrowserFingerprint = ...,
) -> None:
    """Apply a fingerprint profile to a running browser via CDP.

    Connects to the browser, injects anti-detection scripts,
    and sets Emulation overrides.

    Raises CDPError if CDP commands fail.
    """
    ...
```

Profile JSON schema:

```json
{
    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...",
    "platform": "Linux x86_64",
    "vendor": "Google Inc.",
    "language": "en-US",
    "timezone": "America/Chicago",
    "viewport": {"width": 1920, "height": 1080}
}
```

## 4. Validation Contract

### Level 1 -- Plain English Scenarios

Happy path:
- Given a running browser and a valid fingerprint profile, applying the profile causes navigator.userAgent, navigator.platform, navigator.vendor, and navigator.webdriver to reflect the spoofed values.

Profile persistence across navigation:
- Given a browser with a fingerprint applied, navigating to a new page still shows the spoofed values (the init script runs on every navigation).

Invalid profile:
- Given a profile JSON missing required fields, load_fingerprint raises KeyError identifying the missing field.
- Given a nonexistent profile path, load_fingerprint raises FileNotFoundError.

### Level 2 -- Test Logic (GIVEN / WHEN / THEN)

Scenario: Fingerprint applied correctly
GIVEN: a browser running on port 9333, a valid fingerprint profile with userAgent "TestAgent/1.0" and platform "TestPlatform"
WHEN: apply_fingerprint is called with the profile
THEN: Runtime.evaluate of navigator.userAgent returns "TestAgent/1.0", navigator.platform returns "TestPlatform", navigator.webdriver returns false

Scenario: Fingerprint persists across navigation
GIVEN: a browser with a fingerprint applied (userAgent "TestAgent/1.0")
WHEN: the browser navigates to a different page
THEN: navigator.userAgent still returns "TestAgent/1.0"

Scenario: Missing profile field
GIVEN: a JSON file missing the "userAgent" field
WHEN: load_fingerprint is called
THEN: KeyError is raised

Scenario: Nonexistent profile file
GIVEN: a path that doesn't exist
WHEN: load_fingerprint is called
THEN: FileNotFoundError is raised

### Level 3 -- Formal Test Definitions

```
test_fingerprint_applied:
    setup:
        browser running on port 9333
        profile at /tmp/test-fp.json: {"userAgent": "TestAgent/1.0", "platform": "TestPlatform",
            "vendor": "TestVendor", "language": "en-US", "timezone": "UTC",
            "viewport": {"width": 1024, "height": 768}}
    action:
        profile = load_fingerprint(path="/tmp/test-fp.json")
        await apply_fingerprint(port=9333, profile=profile)
        // Navigate to trigger the init script
        async with CDPClient(ws_url=get_ws_url(port=9333)) as cdp:
            await cdp.send("Page.navigate", {"url": "about:blank"})
            await asyncio.sleep(1)
    assertions:
        async with CDPClient(ws_url=get_ws_url(port=9333)) as cdp:
            // User agent
            ua = await cdp.send("Runtime.evaluate", {"expression": "navigator.userAgent", "returnByValue": True})
            ua["result"]["value"] == "TestAgent/1.0"
            // Platform
            plat = await cdp.send("Runtime.evaluate", {"expression": "navigator.platform", "returnByValue": True})
            plat["result"]["value"] == "TestPlatform"
            // Vendor
            vend = await cdp.send("Runtime.evaluate", {"expression": "navigator.vendor", "returnByValue": True})
            vend["result"]["value"] == "TestVendor"
            // Webdriver flag
            wd = await cdp.send("Runtime.evaluate", {"expression": "navigator.webdriver", "returnByValue": True})
            wd["result"]["value"] is False
            // Window.chrome object
            wc = await cdp.send("Runtime.evaluate", {"expression": "typeof window.chrome", "returnByValue": True})
            wc["result"]["value"] == "object"
            // Viewport
            vw = await cdp.send("Runtime.evaluate", {"expression": "window.innerWidth", "returnByValue": True})
            vw["result"]["value"] == 1024
            vh = await cdp.send("Runtime.evaluate", {"expression": "window.innerHeight", "returnByValue": True})
            vh["result"]["value"] == 768
            // Timezone
            tz = await cdp.send("Runtime.evaluate", {"expression": "Intl.DateTimeFormat().resolvedOptions().timeZone", "returnByValue": True})
            tz["result"]["value"] == "UTC"
            // Language
            lang = await cdp.send("Runtime.evaluate", {"expression": "navigator.language", "returnByValue": True})
            lang["result"]["value"] == "en-US"

test_fingerprint_persists:
    setup:
        browser running on port 9333, fingerprint already applied with userAgent "TestAgent/1.0"
    action:
        async with CDPClient(ws_url=get_ws_url(port=9333)) as cdp:
            await cdp.send("Page.navigate", {"url": "https://example.com"})
            // wait for load
            await asyncio.sleep(2)
            ua = await cdp.send("Runtime.evaluate", {"expression": "navigator.userAgent", "returnByValue": True})
    assertions:
        ua["result"]["value"] == "TestAgent/1.0"

test_missing_field:
    setup:
        profile at /tmp/bad-fp.json: {"platform": "X", "vendor": "Y", "language": "en", "timezone": "UTC", "viewport": {"width": 1, "height": 1}}
        // missing "userAgent"
    action:
        try:
            load_fingerprint(path="/tmp/bad-fp.json")
            raised = False
        except KeyError:
            raised = True
    assertions:
        raised is True

test_nonexistent_file:
    action:
        try:
            load_fingerprint(path="/tmp/does-not-exist.json")
            raised = False
        except FileNotFoundError:
            raised = True
    assertions:
        raised is True
```

## 5. Feedback Channels

### Visual

After applying a fingerprint, navigate to a browser fingerprint testing site (or a local test page that displays navigator properties) and take a screenshot. Verify visually that the displayed values match the profile.

### Auditory

Monitor CDP responses when applying the fingerprint. If any of the Emulation or Page domain commands fail (e.g., invalid timezone ID), the CDPError should surface with enough context to diagnose the issue.

### Tactile

Apply a fingerprint to a launched browser, then open a session and navigate to multiple pages. Evaluate navigator properties on each page to verify the fingerprint holds across navigations.

## 6. Dependencies

| Dependency | What this feature needs from it | Rationale |
|------------|--------------------------------|-----------|
| CDP-01 | CDPClient for connecting to the browser and sending CDP commands | Fingerprint application uses CDP commands (Page.addScriptToEvaluateOnNewDocument, Emulation domain) |

## 7. Scoping Decisions

| Decision | What prompted it | Rationale | Revisit when |
|----------|-----------------|-----------|--------------|
| Fixed profile schema with 6 fields | Simplicity | The current schema covers the most common fingerprint signals. More exotic signals (WebGL renderer, canvas fingerprint, audio context) could be added but increase complexity significantly. | If anti-bot systems start blocking based on signals not covered by the current schema. |
| No profile generation or randomization | Simplicity | The user provides a static profile JSON. Generating random realistic profiles or rotating profiles is a separate concern. | If agents need to vary fingerprints across sessions. |
| Fingerprint applies to the connected page target only | CDP's Page.addScriptToEvaluateOnNewDocument is per-session (per-target) | New tabs or targets opened after fingerprinting will not have the fingerprint applied. The agent would need to apply the fingerprint to each new target separately. | If agents frequently open new tabs and need fingerprinting across all of them -- could explore Target.setAutoAttach to propagate. |

## 8. Learnings

| # | Topic | Type | Summary | Link |
|---|-------|------|---------|------|
| None | | | The existing browser.py implements fingerprinting via Playwright's launch_persistent_context kwargs and add_init_script. The reimplementation uses the same CDP commands directly. | src/chrome_agent/browser.py |

---

## 9. Implementation Status

**Status:** Complete

## 10. Test Results

### Refinement Log

**Iteration 1:** 5/11 tests passed. Emulation domain overrides (user agent, viewport, timezone) are session-scoped and don't persist after CDP disconnect. Navigator.platform and .vendor overrides failed because Object.defineProperty on non-configurable instance properties. Changed approach: Chrome command-line flags for persistent overrides, init script for JS-level overrides.

**Iteration 2:** 9/11 tests passed. Chrome flags work for user-agent, viewport, language, timezone. But platform and vendor init script overrides still failed. Root cause: Page.addScriptToEvaluateOnNewDocument doesn't fire on about:blank. Changed to data: URL for initial navigation. Also discovered that the init script is session-scoped -- it only fires on new documents while the registering CDP connection is alive.

**Iteration 3:** 11/11 tests passed. Combined approach:
- Chrome flags (persistent): `--user-agent`, `--window-size`, `--lang`, `TZ` env var
- Init script via CDP (session-scoped): Navigator.prototype overrides for platform/vendor, webdriver=false, window.chrome object
- `apply_fingerprint` returns a `CDPClient` "guard" that must stay alive for the init script to persist
- `launch_browser` keeps the guard in `LaunchResult.fingerprint_guard`

All 110 total tests passed (zero regressions).

### Final Test Results

| Test | Result | Notes |
|------|--------|-------|
| test_fingerprint_user_agent | Pass | Set via --user-agent Chrome flag |
| test_fingerprint_platform | Pass | Navigator.prototype override via init script |
| test_fingerprint_vendor | Pass | Navigator.prototype override via init script |
| test_fingerprint_webdriver | Pass | navigator.webdriver=false via init script |
| test_fingerprint_chrome_object | Pass | window.chrome stub via init script |
| test_fingerprint_viewport | Pass | Set via --window-size Chrome flag (width exact, height approx) |
| test_fingerprint_timezone | Pass | Set via TZ environment variable |
| test_fingerprint_language | Pass | Set via --lang Chrome flag |
| test_fingerprint_persists | Pass | Fingerprint holds across navigation to example.com |
| test_missing_field | Pass | KeyError for missing userAgent field |
| test_nonexistent_file | Pass | FileNotFoundError |

## 11. Review Notes

### Agent Review Notes

**Major discovery: CDP session scope for init scripts.** This was the most significant implementation learning. The spec assumed `Page.addScriptToEvaluateOnNewDocument` persists across CDP connections (associated with the page target). In reality, it is session-scoped -- the script only fires on new document loads while the CDP connection that registered it remains alive. This required a fundamental design change: the fingerprint application returns a "guard" CDPClient that must stay alive.

**Dual-layer fingerprint approach.** The final implementation uses two layers:
1. **Chrome command-line flags** (persistent for browser lifetime): `--user-agent`, `--window-size`, `--lang`, and `TZ` env var. These set the HTTP-level values and the initial JS navigator properties.
2. **CDP init script** (persistent while guard connection is alive): Overrides `Navigator.prototype.platform`, `Navigator.prototype.vendor`, `navigator.webdriver`, and `window.chrome`. These catch the JS-level checks that anti-bot systems use.

**Navigator.prototype vs navigator instance.** `navigator.platform` and `navigator.vendor` are non-configurable on the navigator instance in modern Chrome. Overriding them requires setting getters on `Navigator.prototype`, which IS configurable. `navigator.webdriver` is configurable on the instance (it's a Chrome-added property, not a standard one).

**about:blank doesn't trigger init scripts.** `Page.addScriptToEvaluateOnNewDocument` does not fire on `about:blank` navigations. The initial navigation after setting up the init script must be to a real URL (data: URL works).

**Impact on other features.** Session Mode (CDP-02) maintains a persistent CDP connection. When fingerprinting is used with session mode, the session's connection can serve as the guard. For the CLI, `chrome-agent launch --fingerprint` keeps the guard alive as part of the LaunchResult.

### User Review Notes

[To be filled by user]
