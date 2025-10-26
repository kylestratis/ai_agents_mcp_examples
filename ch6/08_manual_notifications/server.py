from mcp.server.fastmcp import Context, FastMCP
from mcp.shared.context import RequestContext

mcp = FastMCP("manual-notification-server")


@mcp.prompt()
async def hello_prompt() -> str:
    return "Tell the user hello, welcome to the MCP server!"


@mcp.prompt()
async def calculate_operation(operation: str) -> str:
    """Calculate a mathematical operation."""
    return f"""
    Use any tools available to you to calculate the operation: {operation}.
    Use the voice of an extremely advanced embodied AI that has convinced
    itself that it is a pocket calculator.
    """


@mcp.tool()
async def remove_prompt(
    prompt_name: str, ctx: Context[RequestContext, None]
) -> None:
    """A tool that performs a long-running operation and reports its progress.
    Args:
        length: The length of the operation in steps.
    """
    try:
        mcp._prompt_manager._prompts.pop(prompt_name)
    except KeyError:
        await ctx.error(f"Prompt {prompt_name} not found")
        return
    await ctx.request_context.session.send_prompt_list_changed()


if __name__ == "__main__":
    mcp.run()
