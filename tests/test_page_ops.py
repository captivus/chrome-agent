"""Tests for the page convenience verbs: eval, screenshot, wait.

Exercises the real functions against the session's headless browser, so a
regression in target attachment, value unwrapping, clipping, or event
subscription fails here rather than in an agent's session.
"""

import asyncio
import json
import struct

import pytest

from chrome_agent.page_ops import (
    AmbiguousInstanceError,
    EvaluationError,
    NavigationError,
    NoLiveInstanceError,
    attached_page_session,
    resolve_port,
    run_eval,
    run_navigate,
    run_screenshot,
    run_wait,
    target_selector,
)

CDP_PORT = 9333  # matches conftest's browser_session fixture


def _png_size(path) -> tuple[int, int]:
    """Width and height from a PNG's IHDR chunk."""
    with open(path, "rb") as handle:
        header = handle.read(24)
    assert header[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    return struct.unpack(">II", header[16:24])


async def _goto(url: str) -> None:
    """Navigate the browser's page target and wait for load."""
    async with attached_page_session(port=CDP_PORT) as (cdp, session_id):
        await cdp.send(method="Page.enable", session_id=session_id)
        await cdp.send(
            method="Page.navigate", params={"url": url}, session_id=session_id
        )
    # Give the load a moment; the fixture is a local file.
    await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# Instance resolution
# ---------------------------------------------------------------------------


def test_resolve_port_by_name(browser_session, tmp_path, monkeypatch):
    """A named instance resolves to its recorded port."""
    from chrome_agent import registry

    registry_path = str(tmp_path / "registry.json")
    registry.register(
        working_dir="/tmp/proj",
        pid=1,
        browser_version="Chrome/1",
        user_data_dir="/tmp/none",
        port_override=4321,
        registry_path=registry_path,
    )
    assert resolve_port(instance_name="proj-01", registry_path=registry_path) == 4321


def test_resolve_port_no_instances(tmp_path):
    """No registered instance is an error, not a silent default."""
    with pytest.raises(NoLiveInstanceError):
        resolve_port(registry_path=str(tmp_path / "empty.json"))


def test_resolve_port_ambiguous(tmp_path, monkeypatch):
    """Two live instances with no name given must not be guessed between."""
    from chrome_agent import registry

    fake = [
        registry.InstanceInfo(name="a-01", port=1, pid=1, browser_version="", alive=True),
        registry.InstanceInfo(name="b-01", port=2, pid=2, browser_version="", alive=True),
    ]
    monkeypatch.setattr(registry, "enumerate_instances", lambda registry_path=None: fake)
    with pytest.raises(AmbiguousInstanceError) as exc_info:
        resolve_port()
    assert "a-01" in str(exc_info.value) and "b-01" in str(exc_info.value)


def test_target_selector_forms():
    """--target digits mean index, non-digits mean id, --url means url."""
    assert target_selector(target_spec="2", url_spec=None) == ("2", "index")
    assert target_selector(target_spec="A1B2", url_spec=None) == ("A1B2", "id")
    assert target_selector(target_spec=None, url_spec="example") == ("example", "url")
    assert target_selector(target_spec=None, url_spec=None) == (None, None)


# ---------------------------------------------------------------------------
# eval
# ---------------------------------------------------------------------------


def test_eval_returns_string_unwrapped(browser_session, event_loop, fixture_url):
    """A string result prints as itself, not as a CDP envelope."""
    event_loop.run_until_complete(_goto(fixture_url))
    out = event_loop.run_until_complete(
        run_eval(expression="document.title", port=CDP_PORT)
    )
    assert out == "chrome-agent test fixture"


def test_eval_returns_object_as_json(browser_session, event_loop):
    """An object result is rendered as JSON the caller can parse."""
    out = event_loop.run_until_complete(
        run_eval(expression="({a: 1, b: [2, 3]})", port=CDP_PORT)
    )
    assert json.loads(out) == {"a": 1, "b": [2, 3]}


def test_eval_awaits_promises(browser_session, event_loop):
    """A promise is awaited rather than returned as an unresolved object."""
    out = event_loop.run_until_complete(
        run_eval(expression="Promise.resolve(7)", port=CDP_PORT)
    )
    assert out == "7"


def test_eval_raises_on_page_exception(browser_session, event_loop):
    """A thrown error surfaces as EvaluationError, not a silent success."""
    with pytest.raises(EvaluationError) as exc_info:
        event_loop.run_until_complete(
            run_eval(expression="throw new Error('boom')", port=CDP_PORT)
        )
    assert "boom" in str(exc_info.value)


def test_eval_raw_json_keeps_envelope(browser_session, event_loop):
    """--json returns the full Runtime.evaluate response."""
    out = event_loop.run_until_complete(
        run_eval(expression="1 + 1", port=CDP_PORT, raw_json=True)
    )
    assert json.loads(out)["result"]["value"] == 2


def test_eval_undefined_is_described(browser_session, event_loop):
    """An undefined result is reported, not printed as an empty line."""
    out = event_loop.run_until_complete(
        run_eval(expression="void 0", port=CDP_PORT)
    )
    assert out == "undefined"


# ---------------------------------------------------------------------------
# screenshot
# ---------------------------------------------------------------------------


def test_screenshot_writes_png(browser_session, event_loop, fixture_url, tmp_path):
    """Viewport capture writes a decodable PNG and reports its size."""
    event_loop.run_until_complete(_goto(fixture_url))
    out = tmp_path / "shot.png"
    path, size = event_loop.run_until_complete(
        run_screenshot(port=CDP_PORT, output_path=str(out))
    )
    assert path == str(out.resolve())
    assert size == out.stat().st_size > 0
    width, height = _png_size(out)
    assert width > 0 and height > 0


def test_screenshot_full_page_is_taller_than_viewport(
    browser_session, event_loop, tmp_path
):
    """--full-page captures scrollable content beyond the viewport."""
    event_loop.run_until_complete(
        _goto("data:text/html,<body style='margin:0'>"
              "<div style='height:4000px;background:linear-gradient(red,blue)'></div>")
    )
    viewport = tmp_path / "viewport.png"
    full = tmp_path / "full.png"
    event_loop.run_until_complete(
        run_screenshot(port=CDP_PORT, output_path=str(viewport))
    )
    event_loop.run_until_complete(
        run_screenshot(port=CDP_PORT, output_path=str(full), full_page=True)
    )
    assert _png_size(full)[1] > _png_size(viewport)[1]


def test_screenshot_selector_clips_to_element(browser_session, event_loop, tmp_path):
    """--selector captures only the matched element."""
    event_loop.run_until_complete(
        _goto("data:text/html,<body style='margin:0'>"
              "<div id='box' style='width:120px;height:60px;background:teal'></div>")
    )
    out = tmp_path / "el.png"
    event_loop.run_until_complete(
        run_screenshot(port=CDP_PORT, output_path=str(out), selector="#box")
    )
    width, height = _png_size(out)
    assert (width, height) == (120, 60)


def test_screenshot_missing_selector_errors(browser_session, event_loop, tmp_path):
    """A selector that matches nothing fails loudly and writes no file."""
    out = tmp_path / "missing.png"
    with pytest.raises(EvaluationError):
        event_loop.run_until_complete(
            run_screenshot(port=CDP_PORT, output_path=str(out), selector="#nope")
        )
    assert not out.exists()


def test_screenshot_creates_parent_directory(
    browser_session, event_loop, fixture_url, tmp_path
):
    """A path in a not-yet-existing directory is created, not rejected."""
    out = tmp_path / "nested" / "deep" / "shot.png"
    event_loop.run_until_complete(
        run_screenshot(port=CDP_PORT, output_path=str(out))
    )
    assert out.exists()


# ---------------------------------------------------------------------------
# wait
# ---------------------------------------------------------------------------


def test_wait_returns_matching_event(browser_session, event_loop, fixture_url):
    """wait returns the event that fires after subscription."""

    async def scenario():
        waiter = asyncio.ensure_future(
            run_wait(events=["Page.loadEventFired"], port=CDP_PORT, timeout=15.0)
        )
        await asyncio.sleep(0.5)  # let the subscription go live
        await _goto(fixture_url)
        return await waiter

    event = event_loop.run_until_complete(scenario())
    assert event is not None
    assert event["method"] == "Page.loadEventFired"


def test_wait_times_out_to_none(browser_session, event_loop):
    """A quiet page yields None so the CLI can exit non-zero."""
    event = event_loop.run_until_complete(
        run_wait(events=["Page.loadEventFired"], port=CDP_PORT, timeout=1.0)
    )
    assert event is None


def test_wait_contains_filters_non_matching_events(
    browser_session, event_loop, fixture_url
):
    """--contains rejects events that fire but do not hold the substring."""

    async def scenario():
        waiter = asyncio.ensure_future(
            run_wait(
                events=["Page.loadEventFired"],
                port=CDP_PORT,
                timeout=3.0,
                contains=["definitely-not-in-this-event"],
            )
        )
        await asyncio.sleep(0.5)
        await _goto(fixture_url)
        return await waiter

    assert event_loop.run_until_complete(scenario()) is None


# ---------------------------------------------------------------------------
# navigate
# ---------------------------------------------------------------------------


def test_navigate_reports_load_and_identity(browser_session, event_loop, fixture_url):
    """navigate waits for the load and returns the frame/loader identity."""
    result = event_loop.run_until_complete(
        run_navigate(url=fixture_url, port=CDP_PORT, timeout=15.0)
    )
    assert result["loaded"] is True
    assert result["frameId"] and result["loaderId"]
    assert result["elapsedMs"] >= 0


def test_navigate_surfaces_http_status(browser_session, event_loop):
    """The main document's status code is reported, so 404 != 200.

    A bare Page.navigate returns the same shape either way, which is how a
    404 page gets mistaken for content.
    """
    ok = event_loop.run_until_complete(
        run_navigate(
            url="data:text/html,<title>ok</title>", port=CDP_PORT, timeout=15.0
        )
    )
    # data: URLs have no HTTP status; the field is present and null, not absent.
    assert "status" in ok

    result = event_loop.run_until_complete(
        run_navigate(url="https://example.com/", port=CDP_PORT, timeout=20.0)
    )
    assert result["status"] == 200


def test_navigate_wait_none_reports_null_loaded(browser_session, event_loop, fixture_url):
    """--wait none must not claim a load it never observed."""
    result = event_loop.run_until_complete(
        run_navigate(url=fixture_url, port=CDP_PORT, wait_for="none")
    )
    assert result["loaded"] is None


def test_navigate_raises_on_refused_navigation(browser_session, event_loop):
    """A DNS failure is an error, not a silently "successful" navigation."""
    with pytest.raises(NavigationError) as exc_info:
        event_loop.run_until_complete(
            run_navigate(
                url="https://this-host-does-not-exist-zzz.invalid/",
                port=CDP_PORT,
                timeout=15.0,
            )
        )
    assert "ERR_NAME_NOT_RESOLVED" in str(exc_info.value)
