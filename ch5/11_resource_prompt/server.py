from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.prompts.base import UserMessage
from mcp_types import ResourceLink

# Initialize MCP server
mcp = MCPServer("resource-prompt-server")


@mcp.resource("file://knowledge.txt")
async def knowledge_base() -> str:
    """A resource that loads a text-based knowledge base."""

    # Get the absolute path to knowledge.txt relative to this script
    knowledge_path = Path(__file__).parent / "knowledge.txt"

    with open(knowledge_path, "r") as f:
        return f.read()


@mcp.prompt()
async def knowledge_base_prompt(user_request: str) -> list[UserMessage]:
    """A prompt that uses the knowledge base resource."""
    user_request_message = UserMessage(content=user_request)
    instruction_message = UserMessage(
        content="""
This prompt includes knowledge base from the resource URI: file://knowledge.txt,
please use this resource to answer the user's request. The resource follows
this message:
"""
    )
    resource_message = UserMessage(
        content=ResourceLink(
            name="knowledge_base", uri="file://knowledge.txt", type="resource_link"
        )
    )
    return [user_request_message, instruction_message, resource_message]


if __name__ == "__main__":
    mcp.run()
