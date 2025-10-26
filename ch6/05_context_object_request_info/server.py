import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncGenerator[dict[str, list[str]]]:
    logs = []
    logs.append(f"{datetime.now()}: Server started")
    print(logs[-1], file=sys.stderr)
    try:
        logs.append(f"{datetime.now()}: logs yielded")
        yield {"logs": logs}
    finally:
        logs.append(f"{datetime.now()}: Server stopped, printing all logs")
        print(logs, file=sys.stderr)


mcp = FastMCP("context-object-request-info-server", lifespan=lifespan)


@mcp.tool()
async def add(
    a: float, b: float, ctx: Context[ServerSession, dict[str, list[str]]]
) -> dict[str, float]:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = {"augend": a, "addend": b, "sum": a + b}
    logs = ctx.request_context.lifespan_context["logs"]
    logs.append(f"{datetime.now()}: add called")
    print(logs[-1], file=sys.stderr)
    return result


if __name__ == "__main__":
    mcp.run()
