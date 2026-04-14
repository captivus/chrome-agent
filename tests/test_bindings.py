"""Tests for GEN-01: Typed Protocol Bindings.

Tests the code generator and the generated typed domain classes.
"""

import asyncio
import inspect
import os
import tempfile

import pytest

from chrome_agent.cdp_client import CDPClient, get_ws_url
from chrome_agent.protocol import fetch_protocol_schema

CDP_PORT = 9333


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------


def test_generate_from_browser(browser_session):
    """Generator produces Python files for every domain."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "generate_bindings",
        os.path.join(os.path.dirname(__file__), "..", "scripts", "generate_bindings.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    with tempfile.TemporaryDirectory() as tmp_dir:
        mod.generate_bindings(
            source=f"http://localhost:{CDP_PORT}/json/protocol",
            output_dir=tmp_dir,
        )
        files = [f for f in os.listdir(tmp_dir) if f.endswith(".py")]
        assert len(files) > 40, f"Expected >40 domain files, got {len(files)}"
        assert "page.py" in files
        assert "dom.py" in files
        assert "runtime.py" in files
        assert "__init__.py" in files


# ---------------------------------------------------------------------------
# Import tests
# ---------------------------------------------------------------------------


def test_generated_code_importable():
    """Generated domain classes are importable with expected methods."""
    from chrome_agent.domains.page import Page
    from chrome_agent.domains.dom import DOM
    from chrome_agent.domains.runtime import Runtime

    assert hasattr(Page, "navigate")
    assert hasattr(Page, "capture_screenshot")
    assert hasattr(DOM, "get_document")
    assert hasattr(Runtime, "evaluate")


# ---------------------------------------------------------------------------
# Parameter naming
# ---------------------------------------------------------------------------


def test_snake_case_params():
    """Generated methods use snake_case parameters."""
    from chrome_agent.domains.page import Page

    sig = inspect.signature(Page.navigate)
    param_names = list(sig.parameters.keys())
    assert "frame_id" in param_names, f"Expected frame_id, got {param_names}"
    assert "frameId" not in param_names
    assert "url" in param_names


# ---------------------------------------------------------------------------
# End-to-end
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generated_command_works(browser_session):
    """Typed Page.navigate produces same result as raw cdp.send."""
    from chrome_agent.domains.page import Page

    ws_url = get_ws_url(port=CDP_PORT, target_type="page")
    async with CDPClient(ws_url=ws_url) as cdp:
        page = Page(client=cdp)
        result = await page.navigate(url="https://example.com")
    assert "frameId" in result


@pytest.mark.asyncio
async def test_optional_params_omitted(browser_session):
    """Optional params not passed are omitted from the CDP message."""
    from chrome_agent.domains.page import Page

    sent_messages = []
    ws_url = get_ws_url(port=CDP_PORT, target_type="page")
    async with CDPClient(ws_url=ws_url) as cdp:
        # Monkey-patch send to capture the params
        original_send = cdp.send

        async def capturing_send(method, params=None, session_id=None):
            sent_messages.append({"method": method, "params": params})
            return await original_send(method=method, params=params, session_id=session_id)

        cdp.send = capturing_send
        page = Page(client=cdp)
        await page.navigate(url="https://example.com")

    # Find the navigate message
    nav_msg = next(m for m in sent_messages if m["method"] == "Page.navigate")
    assert nav_msg["params"] == {"url": "https://example.com"}, (
        f"Expected only url param, got: {nav_msg['params']}"
    )
