from time import sleep

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

mcp = FastMCP("progress-notification-fastmcp-server")


@mcp.tool()
async def slow_operation(
    ctx: Context[ServerSession, None], length: int = 100
) -> None:
    """A tool that performs a long-running operation and reports its progress.
    Args:
        length: The length of the operation in steps.
    """
    report_frequency = 10 if length > 10 else length // 4
    for i in range(1, length + 1):
        sleep(0.1)
        if i % report_frequency == 0:
            await ctx.report_progress(
                progress=i,
                total=length,
                message=f"Step {i}/{length}",
            )


if __name__ == "__main__":
    mcp.run()
