"""Custom exceptions for chrome-agent.

Each exception produces an actionable error message that tells the agent
what went wrong and what to do about it.
"""


class ChromeAgentError(Exception):
    """Base exception for all chrome-agent errors."""


class CDPError(ChromeAgentError):
    """A CDP protocol error returned by Chrome.

    Raised when Chrome responds to a command with an error (e.g.,
    invalid parameters, node not found, etc.).
    """

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"CDP error {code}: {message}")


class BrowserConnectionError(ChromeAgentError):
    """Cannot connect to a browser via CDP.

    Raised when no browser is listening on the expected CDP port.
    """

    def __init__(self, *, port: int = 9222):
        super().__init__(
            f"No browser running on port {port}. "
            f"Start one with: chrome-agent launch"
        )
        self.port = port


class NoPageError(ChromeAgentError):
    """Browser is connected but has no open pages.

    This typically happens when the browser was just launched and hasn't
    navigated anywhere, or when all tabs have been closed.
    """

    def __init__(self):
        super().__init__("Browser is running but has no open pages.")


class ElementNotFoundError(ChromeAgentError):
    """No element matched the given selector.

    Raised by commands that require an element to exist (click, fill, etc.).
    """

    def __init__(self, *, selector: str):
        super().__init__(f"No element found for selector: {selector}")
        self.selector = selector
