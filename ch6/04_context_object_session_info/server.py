from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import Resource

mcp = FastMCP(
    "context-object-session-info-server",
)

KNOWLEDGE_BASE_FILENAME = "knowledge.txt"


@mcp.resource(uri=f"file://{KNOWLEDGE_BASE_FILENAME}")
async def knowledge_base() -> Resource:
    """A resource that loads a test-based knowledge base."""

    # Get the absolute path to knowledge.txt relative to this script
    knowledge_path = Path(__file__).parent / KNOWLEDGE_BASE_FILENAME

    with open(knowledge_path, "r") as f:
        return f.read()


@mcp.tool()
async def get_client_info(ctx: Context) -> dict:
    """Get information about the client."""
    return dict(ctx.session.client_params)


@mcp.tool()
async def add_fact_to_knowledge_base(fact: str, ctx: Context) -> None:
    """Adds a new fact to the knowledge base file and sends resource_changed notification."""

    knowledge_path = Path(__file__).parent / KNOWLEDGE_BASE_FILENAME
    with open(knowledge_path, "a") as f:
        f.write(fact + "\n")
    await ctx.session.send_resource_updated(uri=f"file://{KNOWLEDGE_BASE_FILENAME}")


if __name__ == "__main__":
    mcp.run()
