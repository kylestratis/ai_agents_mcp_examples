from mcp.server.mcpserver import Context, MCPServer

mcp = MCPServer("manual-notification-server")


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
async def remove_prompt(prompt_name: str, ctx: Context) -> None:
    """Remove a prompt from the server's prompt list by name.
    Args:
        prompt_name: The name of the prompt to remove.
    """
    try:
        mcp.remove_prompt(prompt_name)
    except ValueError:
        await ctx.error(f"Prompt {prompt_name} not found")
        return
    await ctx.notify_prompts_changed()


if __name__ == "__main__":
    mcp.run()
