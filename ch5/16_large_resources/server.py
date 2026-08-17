from pathlib import Path

from mcp.server.mcpserver import MCPServer

# Initialize MCP server
mcp = MCPServer("large-resource-server")


@mcp.resource("exports://orders/latest")
async def latest_export() -> str:
    """A small pointer to a large file; clients fetch the URL directly."""
    return "https://data.example.com/exports/orders-2026.parquet?expires=1785000000"


@mcp.resource("logs://{filename}{?start,count}")
async def log_slice(filename: str, start: int = 0, count: int = 100) -> str:
    """A window of `count` log lines, starting at line `start`."""
    log_path = Path(__file__).parent / filename
    lines = log_path.read_text().splitlines()
    return "\n".join(lines[start : start + count])


if __name__ == "__main__":
    mcp.run()
