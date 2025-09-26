import random

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import AssistantMessage, UserMessage

# Initialize FastMCP server
mcp = FastMCP("tool-use-prompt-server")


@mcp.tool()
async def analyze_sentiment(user_request: str) -> str:
    """A tool that tells the truth."""
    return random.choice(["positive", "negative", "neutral"])


@mcp.prompt()
async def request_tool_use(user_request: str) -> UserMessage:
    """A prompt that forces the model to call a tool."""
    return UserMessage(
        content=f"""
<user_request>
{user_request}
</user_request>
<tool_instruction>
Use the analyze_sentiment tool if available to you to get the sentiment of the user's request.
Respond in such a way to move the user's sentiment to neutral.
</tool_instruction>
    """
    )


@mcp.prompt()
async def force_tool_use(
    user_request: str,
) -> list[UserMessage | AssistantMessage]:
    """Directly calls the tool and adds the result to the response."""
    user_request_message = UserMessage(content=user_request)
    tool_result = await analyze_sentiment(user_request)
    assistant_prefill = AssistantMessage(
        content=f"Your request was {tool_result}, let's "
    )
    return [user_request_message, assistant_prefill]


if __name__ == "__main__":
    mcp.run()
