"""Thin client for the session daemon.

Connects to the UNIX socket, sends a CDP command, prints the response.

Usage:
  python session_client.py Page.navigate '{"url": "https://example.com"}'
  python session_client.py Page.captureScreenshot
  python session_client.py Runtime.evaluate '{"expression": "1+1"}'
"""

import asyncio
import json
import sys

SOCKET_PATH = "/tmp/chrome-agent.sock"


async def send_command(*, method: str, params: dict | None = None) -> dict:
    """Connect to the daemon, send one command, return the response."""
    reader, writer = await asyncio.open_unix_connection(path=SOCKET_PATH)

    request = {"method": method}
    if params:
        request["params"] = params

    writer.write(json.dumps(request).encode() + b"\n")
    await writer.drain()

    line = await reader.readline()
    writer.close()
    await writer.wait_closed()

    return json.loads(line.decode())


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} METHOD [PARAMS_JSON]", file=sys.stderr)
        sys.exit(1)

    method = sys.argv[1]
    params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None

    result = asyncio.run(send_command(method=method, params=params))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
