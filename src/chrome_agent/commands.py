"""Browser observation, navigation, and interaction commands.

Each command is an async function that accepts a Playwright Page (and
optionally Browser) as its first argument. Commands print their results
to stdout and raise exceptions on failure. The CLI layer handles
connection lifecycle and error presentation.
"""

import json

from playwright.async_api import Browser, Page

from .errors import ElementNotFoundError


# ---------------------------------------------------------------------------
# Observation commands
# ---------------------------------------------------------------------------


async def cmd_url(*, page: Page) -> None:
    """Print current URL and page title."""
    print(f"URL:   {page.url}")
    print(f"Title: {await page.title()}")


async def cmd_screenshot(*, page: Page, path: str = "/tmp/cdp-screenshot.png") -> None:
    """Save a screenshot of the current page."""
    await page.screenshot(path=path)
    print(f"Screenshot saved: {path}")


async def cmd_snapshot(*, page: Page) -> None:
    """Print the accessibility tree of the current page (ARIA snapshot)."""
    snapshot = await page.locator(":root").aria_snapshot()
    if snapshot:
        print(snapshot)
    else:
        print("(empty accessibility tree)")


async def cmd_text(*, page: Page) -> None:
    """Print visible text content of the page."""
    text = await page.inner_text("body")
    if len(text) > 5000:
        print(text[:5000])
        print(f"\n... (truncated, {len(text)} total chars)")
    else:
        print(text)


async def cmd_html(*, page: Page, selector: str | None = None) -> None:
    """Print page HTML source, or a specific element's outerHTML."""
    if selector:
        el = page.locator(selector).first
        if await el.count() > 0:
            html = await el.evaluate("el => el.outerHTML")
            print(html)
        else:
            raise ElementNotFoundError(selector=selector)
    else:
        html = await page.content()
        if len(html) > 10000:
            print(html[:10000])
            print(f"\n... (truncated, {len(html)} total chars)")
        else:
            print(html)


async def cmd_element(*, page: Page, selector: str) -> None:
    """Print detailed info about a specific element."""
    loc = page.locator(selector).first

    if await loc.count() == 0:
        raise ElementNotFoundError(selector=selector)

    info = await loc.evaluate("""el => {
        const cs = getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const attrs = {};
        for (const a of el.attributes) attrs[a.name] = a.value;
        return {
            tag: el.tagName,
            id: el.id,
            text: el.innerText?.substring(0, 200) || '',
            value: el.value || null,
            type: el.type || null,
            visible: el.offsetParent !== null || cs.display !== 'none',
            display: cs.display,
            visibility: cs.visibility,
            opacity: cs.opacity,
            dimensions: { width: rect.width, height: rect.height },
            position: { x: Math.round(rect.x), y: Math.round(rect.y) },
            inViewport: rect.top >= 0 && rect.left >= 0 &&
                        rect.bottom <= window.innerHeight &&
                        rect.right <= window.innerWidth,
            disabled: el.disabled || false,
            checked: el.checked ?? null,
            href: el.href || null,
            attributes: attrs,
        };
    }""")

    print(f"Selector:    {selector}")
    print(f"Tag:         {info['tag']}")
    if info["type"]:
        print(f"Type:        {info['type']}")
    if info["id"]:
        print(f"ID:          {info['id']}")
    print(f"Text:        {info['text'][:100] if info['text'] else '(empty)'}")
    if info["value"] is not None:
        print(f"Value:       {info['value']}")
    print(f"Visible:     {info['visible']}")
    print(f"Display:     {info['display']}")
    print(f"Visibility:  {info['visibility']}")
    print(f"Opacity:     {info['opacity']}")
    print(f"Dimensions:  {info['dimensions']['width']:.0f} x {info['dimensions']['height']:.0f}")
    print(f"Position:    ({info['position']['x']}, {info['position']['y']})")
    print(f"In viewport: {info['inViewport']}")
    if info["disabled"]:
        print(f"Disabled:    {info['disabled']}")
    if info["checked"] is not None:
        print(f"Checked:     {info['checked']}")
    if info["href"]:
        print(f"Href:        {info['href']}")
    if info["attributes"]:
        print(f"Attributes:  {json.dumps(info['attributes'], indent=2)}")


async def cmd_find(*, page: Page, selector: str) -> None:
    """Count and summarize elements matching a selector."""
    loc = page.locator(selector)
    count = await loc.count()

    print(f"Selector: {selector}")
    print(f"Count:    {count}")

    for i in range(min(count, 20)):
        item = loc.nth(i)
        summary = await item.evaluate("""el => ({
            tag: el.tagName,
            text: (el.innerText || '').substring(0, 80),
            visible: el.offsetParent !== null,
            id: el.id || null,
            cls: el.className?.substring?.(0, 60) || null,
        })""")
        vis = "visible" if summary["visible"] else "hidden"
        text = summary["text"].replace("\n", " ").strip()[:60]
        ident = summary["id"] or summary["cls"] or ""
        print(f"  [{i}] <{summary['tag']}> {vis} | {ident} | {text}")

    if count > 20:
        print(f"  ... ({count - 20} more)")


async def cmd_value(*, page: Page, selector: str) -> None:
    """Get the current value of an input element."""
    loc = page.locator(selector).first
    if await loc.count() == 0:
        raise ElementNotFoundError(selector=selector)
    val = await loc.input_value()
    print(val)


async def cmd_eval(*, page: Page, js_code: str) -> None:
    """Execute arbitrary JavaScript and print the result."""
    result = await page.evaluate(js_code)
    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2))
    else:
        print(result)


async def cmd_cookies(*, page: Page) -> None:
    """Dump all cookies for the current page."""
    context = page.context
    cookies = await context.cookies()
    for c in cookies:
        exp = c.get("expires", -1)
        exp_str = f"expires={exp}" if exp > 0 else "session"
        print(
            f"  {c['name']}={c['value'][:40]}"
            f"{'...' if len(c['value']) > 40 else ''}"
            f"  ({c['domain']}, {exp_str})"
        )
    if not cookies:
        print("(no cookies)")


async def cmd_tabs(*, page: Page, browser: Browser) -> None:
    """List all open pages/tabs in the browser."""
    for ctx in browser.contexts:
        for i, p in enumerate(ctx.pages):
            marker = " *" if p == page else ""
            print(f"  [{i}] {p.url}")
            print(f"       {await p.title()}{marker}")


async def cmd_wait(*, page: Page, target: str) -> None:
    """Wait for a selector, milliseconds, or load state."""
    if target.isdigit():
        ms = int(target)
        print(f"Waiting {ms}ms...")
        await page.wait_for_timeout(ms)
        print("Done")
    elif target in ("load", "domcontentloaded", "networkidle"):
        print(f"Waiting for {target}...")
        await page.wait_for_load_state(target)
        print("Done")
    else:
        print(f"Waiting for selector: {target}")
        await page.locator(target).first.wait_for(timeout=30000)
        print("Found")


# ---------------------------------------------------------------------------
# Navigation commands
# ---------------------------------------------------------------------------


async def cmd_navigate(*, page: Page, url: str) -> None:
    """Navigate to a URL and wait for load."""
    response = await page.goto(url)
    status = response.status if response else "unknown"
    print(f"Navigated to: {page.url}")
    print(f"Status: {status}")
    print(f"Title: {await page.title()}")


async def cmd_back(*, page: Page) -> None:
    """Go back in browser history."""
    await page.go_back()
    print(f"URL: {page.url}")


async def cmd_forward(*, page: Page) -> None:
    """Go forward in browser history."""
    await page.go_forward()
    print(f"URL: {page.url}")


async def cmd_reload(*, page: Page) -> None:
    """Reload the current page."""
    await page.reload()
    print(f"Reloaded: {page.url}")


# ---------------------------------------------------------------------------
# Interaction commands
# ---------------------------------------------------------------------------


async def cmd_click(*, page: Page, selector: str) -> None:
    """Click an element. Falls back to JS click if not actionable."""
    loc = page.locator(selector).first
    if await loc.count() == 0:
        raise ElementNotFoundError(selector=selector)

    try:
        await loc.click(timeout=5000)
        print(f"Clicked: {selector}")
    except Exception:
        # Fallback to JS click for hidden/obscured elements
        try:
            await loc.evaluate("el => el.click()")
            print(f"JS-clicked: {selector} (element was not actionable)")
        except Exception as e:
            print(f"ERROR clicking {selector}: {e}")


async def cmd_clickxy(*, page: Page, x: float, y: float) -> None:
    """Click at page coordinates."""
    await page.mouse.click(x=x, y=y)
    print(f"Clicked at ({x}, {y})")


async def cmd_fill(*, page: Page, selector: str, value: str) -> None:
    """Fill a form field (clears first, dispatches events)."""
    loc = page.locator(selector).first
    if await loc.count() == 0:
        raise ElementNotFoundError(selector=selector)
    await loc.fill(value)
    print(f"Filled {selector} with: {value}")


async def cmd_type(*, page: Page, selector: str, text: str) -> None:
    """Type text character by character into an element."""
    loc = page.locator(selector).first
    if await loc.count() == 0:
        raise ElementNotFoundError(selector=selector)
    await loc.type(text)
    print(f"Typed into {selector}: {text}")


async def cmd_press(*, page: Page, key: str) -> None:
    """Press a keyboard key (Enter, Escape, Tab, etc.)."""
    await page.keyboard.press(key)
    print(f"Pressed: {key}")


async def cmd_select(*, page: Page, selector: str, value: str) -> None:
    """Select an option from a dropdown."""
    loc = page.locator(selector).first
    if await loc.count() == 0:
        raise ElementNotFoundError(selector=selector)
    await loc.select_option(value=value)
    print(f"Selected {value} in {selector}")


async def cmd_check(*, page: Page, selector: str) -> None:
    """Check a checkbox."""
    loc = page.locator(selector).first
    if await loc.count() == 0:
        raise ElementNotFoundError(selector=selector)
    await loc.check()
    print(f"Checked: {selector}")


async def cmd_uncheck(*, page: Page, selector: str) -> None:
    """Uncheck a checkbox."""
    loc = page.locator(selector).first
    if await loc.count() == 0:
        raise ElementNotFoundError(selector=selector)
    await loc.uncheck()
    print(f"Unchecked: {selector}")


async def cmd_hover(*, page: Page, selector: str) -> None:
    """Hover over an element."""
    loc = page.locator(selector).first
    if await loc.count() == 0:
        raise ElementNotFoundError(selector=selector)
    await loc.hover()
    print(f"Hovering: {selector}")


async def cmd_scroll(*, page: Page, target: str) -> None:
    """Scroll to an element, or scroll the page (up/down)."""
    if target == "up":
        await page.mouse.wheel(delta_x=0, delta_y=-500)
        print("Scrolled up")
    elif target == "down":
        await page.mouse.wheel(delta_x=0, delta_y=500)
        print("Scrolled down")
    else:
        loc = page.locator(target).first
        if await loc.count() == 0:
            raise ElementNotFoundError(selector=target)
        await loc.scroll_into_view_if_needed()
        print(f"Scrolled to: {target}")


# ---------------------------------------------------------------------------
# Meta commands (operate on page/viewport, not elements)
# ---------------------------------------------------------------------------


async def cmd_close(*, page: Page) -> None:
    """Close the current page."""
    url = page.url
    await page.close()
    print(f"Closed: {url}")


async def cmd_viewport(*, page: Page, width: int, height: int) -> None:
    """Resize the viewport."""
    await page.set_viewport_size({"width": width, "height": height})
    print(f"Viewport set to {width}x{height}")


