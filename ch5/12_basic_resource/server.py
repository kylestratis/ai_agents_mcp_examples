from pathlib import Path

from mcp import Resource
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("basic-resource-server")


@mcp.resource("file://knowledge.txt")
async def knowledge_base() -> Resource:
    """A resource that loads a test-based knowledge base."""

    # Get the absolute path to knowledge.txt relative to this script
    knowledge_path = Path(__file__).parent / "knowledge.txt"

    with open(knowledge_path, "r") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run()
