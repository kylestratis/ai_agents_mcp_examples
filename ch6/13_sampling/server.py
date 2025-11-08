import sys

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.types import ModelHint, ModelPreferences, SamplingMessage, TextContent

# Initialize FastMCP server
mcp = FastMCP("sampling-server")

MODEL_PREFERENCES = ModelPreferences(
    hints=[
        ModelHint(name="claude-4-5-haiku"),
        ModelHint(name="claude-haiku"),
        ModelHint(name="gpt-4o-mini"),
    ],
    costPriority=1.0,
    speedPriority=0.8,
    intelligencePriority=0.3,
)


@mcp.tool()
async def explain_math(operation: str, ctx: Context[ServerSession, None]) -> str:
    """Use sampling to explain how a mathematical operation works."""
    prompt = f"""
    Explain how the following mathematical operation works. Break it down into 
    discrete steps and explain any relevant concepts. The operation is: {operation}.
    Use the voice of a patient but eccentric math professor explaining to a curious
    but inexperienced student.
    """
    if not ctx.session.client_params.capabilities.sampling:
        return "Sampling is not supported by this server"

    try:
        result = await ctx.session.create_message(
            messages=[
                SamplingMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt),
                )
            ],
            max_tokens=100,
            model_preferences=MODEL_PREFERENCES,
        )
    except Exception as e:
        await ctx.error(f"Error: {e}")
        return f"Error: {e}"

    print(f"result: {result}", file=sys.stderr)
    await ctx.info("Sending math explanation to LLM")
    if not result.content:
        await ctx.warning("No content in result")
        return "No content in result"

    match result.content.type:
        case "text":
            return result.content.text
        case "image" | "audio":
            return str(result.content.data)


if __name__ == "__main__":
    mcp.run()
