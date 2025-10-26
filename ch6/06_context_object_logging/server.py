from datetime import datetime

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

mcp = FastMCP("context-object-logging-server")


@mcp.tool()
async def add(
    a: float, b: float, ctx: Context[ServerSession, None]
) -> dict[str, float]:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    await ctx.info(f"{datetime.now()}: add called")
    try:
        result = {"augend": a, "addend": b, "sum": a + b}
    except Exception as e:
        await ctx.error(f"{datetime.now()}: error: {e}")
        raise e
    await ctx.debug(f"{datetime.now()}: add result: {result}")
    if result["sum"] < 0:
        await ctx.warning(
            f"{datetime.now()}: add result is negative: {result['sum']}"
        )
    return result


if __name__ == "__main__":
    mcp.run()
