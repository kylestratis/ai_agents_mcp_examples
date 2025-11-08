import sys
from time import sleep

from mcp.server.fastmcp import Context, FastMCP
from mcp.shared.context import RequestContext

mcp = FastMCP("pings-server")


@mcp.tool()
async def long_running_pinger(ctx: Context[RequestContext, None]) -> None:
    """A tool that tests the notifications."""
    ctx.session.send_
    for i in range(25):
        sleep(0.1)
        if i % 5 == 0:
            response = await ctx.request_context.session.send_ping()
            print(
                f"Ping {i} response: {response}, type: {type(response)}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    mcp.run()
