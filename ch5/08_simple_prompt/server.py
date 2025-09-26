from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import UserMessage

# Initialize FastMCP server
mcp = FastMCP("simple-prompt-server")


@mcp.prompt()
async def simple_string_prompt() -> str:
    """A simple, static prompt that greets the user."""
    return "Say hello to the user."


@mcp.prompt()
async def simple_prompt_input(username: str) -> str:
    """A simple prompt that greets the user with their name."""
    return f"Say hello to the user using their name: {username}"


@mcp.prompt()
async def simple_example_prompt(user_text: str) -> UserMessage:
    """A simple prompt that summarizes the input text, using XML tags."""
    return UserMessage(
        content=f"""
<instruction>
Create a list of 3 main ideas from the following text:
</instruction>

<text>
{user_text}
</text>
    """
    )


if __name__ == "__main__":
    mcp.run()
