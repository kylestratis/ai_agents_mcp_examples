from pathlib import Path

from mcp.server.mcpserver import MCPServer

# Initialize MCP server
mcp = MCPServer("basic-resource-server")


@mcp.resource("file://knowledge.txt")
async def knowledge_base() -> str:
    """A resource that loads a text-based knowledge base."""

    # Get the absolute path to knowledge.txt relative to this script
    knowledge_path = Path(__file__).parent / "knowledge.txt"

    with open(knowledge_path, "r") as f:
        return f.read()


if __name__ == "__main__":
    mcp.run()
