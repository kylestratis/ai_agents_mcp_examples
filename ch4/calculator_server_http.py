"""
Serve the calculator MCP server over Streamable HTTP for the examples
that need a remote-style connection (04_authorizing_oauth and
10_recovering_subscriptions). Run first, in a separate terminal:

    uv run calculator_server_http.py

The server listens on http://localhost:8000/mcp by default.
"""

from calculator_server import mcp

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
