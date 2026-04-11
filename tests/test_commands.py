"""Test every chrome-agent command against the fixture page.

Each test connects via CDP (the real code path), runs a command,
and asserts on the output.
"""

import asyncio
import json
import os
import tempfile

import pytest

from chrome_agent.commands import (
    cmd_back,
    cmd_check,
    cmd_click,
    cmd_clickxy,
    cmd_close,
    cmd_cookies,
    cmd_element,
    cmd_eval,
    cmd_fill,
    cmd_find,
    cmd_forward,
    cmd_hover,
    cmd_html,
    cmd_navigate,
    cmd_press,
    cmd_reload,
    cmd_screenshot,
    cmd_scroll,
    cmd_select,
    cmd_snapshot,
    cmd_tabs,
    cmd_text,
    cmd_type,
    cmd_uncheck,
    cmd_url,
    cmd_value,
    cmd_viewport,
    cmd_wait,
)
from chrome_agent.errors import ElementNotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(event_loop, coro):
    """Run an async coroutine in the session event loop."""
    return event_loop.run_until_complete(coro)


# ---------------------------------------------------------------------------
# Observation commands
# ---------------------------------------------------------------------------


class TestUrl:
    def test_reports_fixture_url(self, event_loop, cdp_connection, capsys, fixture_url):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_url(page=page))
        out = capsys.readouterr().out
        assert "URL:" in out
        assert "fixture.html" in out
        assert "Title:" in out
        assert "chrome-agent test fixture" in out


class TestText:
    def test_returns_visible_text(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_text(page=page))
        out = capsys.readouterr().out
        assert "Test Page" in out
        assert "This is a test paragraph" in out
        assert "Click Me" in out
        # Hidden content should NOT appear
        assert "Hidden content" not in out


class TestScreenshot:
    def test_saves_file(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            run(event_loop, cmd_screenshot(page=page, path=path))
            out = capsys.readouterr().out
            assert f"Screenshot saved: {path}" in out
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)


class TestSnapshot:
    def test_returns_accessibility_tree(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_snapshot(page=page))
        out = capsys.readouterr().out
        assert "Test Page" in out
        assert "heading" in out.lower() or "h1" in out.lower()


class TestHtml:
    def test_full_page(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_html(page=page))
        out = capsys.readouterr().out
        assert "<h1" in out
        assert "Test Page" in out

    def test_selector(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_html(page=page, selector="#heading"))
        out = capsys.readouterr().out
        assert "<h1" in out
        assert "Test Page" in out

    def test_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_html(page=page, selector="#nonexistent"))


class TestElement:
    def test_heading(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_element(page=page, selector="#heading"))
        out = capsys.readouterr().out
        assert "Tag:         H1" in out
        assert "Text:        Test Page" in out
        assert "Visible:     True" in out
        assert "ID:          heading" in out

    def test_hidden_element(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_element(page=page, selector="#hidden-div"))
        out = capsys.readouterr().out
        assert "Visible:     False" in out
        assert "Display:     none" in out

    def test_disabled_button(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_element(page=page, selector="#disabled-button"))
        out = capsys.readouterr().out
        assert "Disabled:    True" in out

    def test_link_href(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_element(page=page, selector="#link"))
        out = capsys.readouterr().out
        assert "Href:" in out
        assert "example.com" in out

    def test_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_element(page=page, selector="#nonexistent"))


class TestFind:
    def test_count_inputs(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_find(page=page, selector="input"))
        out = capsys.readouterr().out
        assert "Count:" in out
        # We have: text-input, password-input, checkbox-checked,
        # checkbox-unchecked = 4 inputs (textarea and select are not <input>)
        assert "Count:    4" in out

    def test_zero_matches(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_find(page=page, selector=".nonexistent-class"))
        out = capsys.readouterr().out
        assert "Count:    0" in out


class TestValue:
    def test_reads_input_value(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_value(page=page, selector="#text-input"))
        out = capsys.readouterr().out.strip()
        assert out == "initial"

    def test_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_value(page=page, selector="#nonexistent"))


class TestEval:
    def test_simple_expression(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_eval(page=page, js_code="document.title"))
        out = capsys.readouterr().out.strip()
        assert out == "chrome-agent test fixture"

    def test_returns_number(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_eval(page=page, js_code="document.querySelectorAll('input').length"))
        out = capsys.readouterr().out.strip()
        assert out == "4"

    def test_returns_object(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_eval(page=page, js_code="({a: 1, b: 2})"))
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data == {"a": 1, "b": 2}


class TestCookies:
    def test_reads_cookies(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        # Navigate to a real URL first (cookies don't work on file:// URLs)
        run(event_loop, page.goto("https://example.com"))
        run(event_loop, page.context.add_cookies([{
            "name": "test_cookie",
            "value": "hello123",
            "domain": "example.com",
            "path": "/",
        }]))
        run(event_loop, cmd_cookies(page=page))
        out = capsys.readouterr().out
        assert "test_cookie" in out
        assert "hello123" in out


class TestTabs:
    def test_lists_current_tab(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_tabs(page=page, browser=browser))
        out = capsys.readouterr().out
        assert "fixture.html" in out


class TestWait:
    def test_wait_milliseconds(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_wait(page=page, target="100"))
        out = capsys.readouterr().out
        assert "Waiting 100ms" in out
        assert "Done" in out

    def test_wait_selector(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_wait(page=page, target="#heading"))
        out = capsys.readouterr().out
        assert "Found" in out

    def test_wait_load(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_wait(page=page, target="load"))
        out = capsys.readouterr().out
        assert "Done" in out


# ---------------------------------------------------------------------------
# Navigation commands
# ---------------------------------------------------------------------------


class TestNavigate:
    def test_navigates_and_reports(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_navigate(page=page, url="https://example.com"))
        out = capsys.readouterr().out
        assert "Navigated to: https://example.com" in out
        assert "Status: 200" in out
        assert "Title: Example Domain" in out


class TestBackForward:
    def test_back_and_forward(self, event_loop, cdp_connection, capsys, fixture_url):
        pw, browser, page = cdp_connection
        # Navigate away from fixture
        run(event_loop, cmd_navigate(page=page, url="https://example.com"))
        capsys.readouterr()  # clear

        # Go back
        run(event_loop, cmd_back(page=page))
        out = capsys.readouterr().out
        assert "fixture.html" in out

        # Go forward
        run(event_loop, cmd_forward(page=page))
        out = capsys.readouterr().out
        assert "example.com" in out


class TestReload:
    def test_reloads(self, event_loop, cdp_connection, capsys, fixture_url):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_reload(page=page))
        out = capsys.readouterr().out
        assert "Reloaded:" in out
        assert "fixture.html" in out


# ---------------------------------------------------------------------------
# Interaction commands
# ---------------------------------------------------------------------------


class TestClick:
    def test_click_button(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_click(page=page, selector="#click-button"))
        out = capsys.readouterr().out
        assert "Clicked: #click-button" in out

        # Verify the click had the expected effect
        result = run(event_loop, page.evaluate(
            "document.getElementById('click-result').textContent"
        ))
        assert result == "clicked"

    def test_click_hidden_falls_back_to_js(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_click(page=page, selector="#hidden-div"))
        out = capsys.readouterr().out
        assert "JS-clicked" in out

    def test_click_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_click(page=page, selector="#nonexistent"))


class TestFill:
    def test_fill_input(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_fill(page=page, selector="#text-input", value="new value"))
        out = capsys.readouterr().out
        assert "Filled #text-input with: new value" in out

        # Read it back
        capsys.readouterr()  # clear
        run(event_loop, cmd_value(page=page, selector="#text-input"))
        out = capsys.readouterr().out.strip()
        assert out == "new value"

    def test_fill_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_fill(page=page, selector="#nonexistent", value="x"))


class TestType:
    def test_type_into_input(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        # Clear first
        run(event_loop, cmd_fill(page=page, selector="#password-input", value=""))
        capsys.readouterr()

        run(event_loop, cmd_type(page=page, selector="#password-input", text="secret"))
        out = capsys.readouterr().out
        assert "Typed into #password-input: secret" in out

    def test_type_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_type(page=page, selector="#nonexistent", text="x"))


class TestSelect:
    def test_select_option(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_select(page=page, selector="#dropdown", value="b"))
        out = capsys.readouterr().out
        assert "Selected b in #dropdown" in out

        # Verify
        result = run(event_loop, page.evaluate(
            "document.getElementById('dropdown').value"
        ))
        assert result == "b"

    def test_select_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_select(page=page, selector="#nonexistent", value="x"))


class TestCheck:
    def test_check_unchecked(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_check(page=page, selector="#checkbox-unchecked"))
        out = capsys.readouterr().out
        assert "Checked: #checkbox-unchecked" in out

        # Verify
        result = run(event_loop, page.evaluate(
            "document.getElementById('checkbox-unchecked').checked"
        ))
        assert result is True

    def test_check_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_check(page=page, selector="#nonexistent"))


class TestUncheck:
    def test_uncheck_checked(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_uncheck(page=page, selector="#checkbox-checked"))
        out = capsys.readouterr().out
        assert "Unchecked: #checkbox-checked" in out

        # Verify
        result = run(event_loop, page.evaluate(
            "document.getElementById('checkbox-checked').checked"
        ))
        assert result is False

    def test_uncheck_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_uncheck(page=page, selector="#nonexistent"))


class TestHover:
    def test_hover_element(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_hover(page=page, selector="#click-button"))
        out = capsys.readouterr().out
        assert "Hovering: #click-button" in out

    def test_hover_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_hover(page=page, selector="#nonexistent"))


class TestPress:
    def test_press_key(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_press(page=page, key="Escape"))
        out = capsys.readouterr().out
        assert "Pressed: Escape" in out


class TestScroll:
    def test_scroll_down(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_scroll(page=page, target="down"))
        out = capsys.readouterr().out
        assert "Scrolled down" in out

    def test_scroll_up(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_scroll(page=page, target="up"))
        out = capsys.readouterr().out
        assert "Scrolled up" in out

    def test_scroll_to_element(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_scroll(page=page, target="#scroll-top"))
        out = capsys.readouterr().out
        assert "Scrolled to: #scroll-top" in out

    def test_scroll_bad_selector(self, event_loop, cdp_connection):
        pw, browser, page = cdp_connection
        with pytest.raises(ElementNotFoundError):
            run(event_loop, cmd_scroll(page=page, target="#nonexistent"))


class TestClickxy:
    def test_click_coordinates(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_clickxy(page=page, x=100.0, y=100.0))
        out = capsys.readouterr().out
        assert "Clicked at (100.0, 100.0)" in out


class TestViewport:
    def test_resize(self, event_loop, cdp_connection, capsys):
        pw, browser, page = cdp_connection
        run(event_loop, cmd_viewport(page=page, width=800, height=600))
        out = capsys.readouterr().out
        assert "Viewport set to 800x600" in out


# ---------------------------------------------------------------------------
# Connection and status
# ---------------------------------------------------------------------------


class TestConnection:
    def test_check_cdp_port_running(self):
        from chrome_agent.connection import check_cdp_port
        status = check_cdp_port(port=9333)
        assert status.listening is True
        assert status.browser_version is not None

    def test_check_cdp_port_not_running(self):
        from chrome_agent.connection import check_cdp_port
        status = check_cdp_port(port=9444)
        assert status.listening is False

    def test_connect_wrong_port(self, event_loop):
        from chrome_agent.connection import connect
        from chrome_agent.errors import BrowserConnectionError
        with pytest.raises(BrowserConnectionError):
            run(event_loop, connect(port=9444))

    def test_connect_finds_launched_page(self, event_loop, browser_session, fixture_url):
        """Reconnecting via connect() must find the page that launch_browser() created.

        This is the core contract of the drive/attach model: launch a browser,
        navigate to a URL, then reconnect from a separate CDP connection and
        find the same page -- not about:blank.
        """
        from chrome_agent.connection import connect, disconnect

        # Navigate the launched page to a known URL
        run(event_loop, browser_session.page.goto(fixture_url))
        run(event_loop, browser_session.page.wait_for_load_state("load"))

        # Reconnect via CDP (simulates a separate chrome-agent invocation)
        pw, browser, page = run(event_loop, connect(port=9333))
        try:
            assert page.url != "about:blank", (
                "connect() returned about:blank -- the launched page is in "
                "a non-default context invisible to CDP reconnection"
            )
            # The page should be navigable and functional
            title = run(event_loop, page.title())
            assert title, "Reconnected page should have a title"
        finally:
            run(event_loop, disconnect(pw=pw))
