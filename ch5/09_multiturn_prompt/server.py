from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import AssistantMessage, UserMessage

# Initialize FastMCP server
mcp = FastMCP("multiturn-prompt-server")


@mcp.prompt()
async def multiturn_prompt(
    main_idea_count: int, user_text: str
) -> list[UserMessage | AssistantMessage]:
    user_input = UserMessage(
        content=f"""
<instruction>
Create a list of {main_idea_count} main ideas from the following text:
</instruction>

<text>
{user_text}
</text>
    """
    )

    assistant_prefill_test = f"""
Here are {main_idea_count} main ideas from the text:
1.
"""
    assistant_prefill = AssistantMessage(content=assistant_prefill_test)
    return [user_input, assistant_prefill]


if __name__ == "__main__":
    mcp.run()
