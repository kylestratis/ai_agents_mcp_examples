import logging

import anyio
from mcp.server import ServerRequestContext
from mcp.server.mcpserver import Context, MCPServer
from mcp_types import CancelledNotificationParams

logger = logging.getLogger(__name__)
mcp = MCPServer("cancel-request-notification-server")


async def handle_cancelled_notification(
    ctx: ServerRequestContext,
    params: CancelledNotificationParams,
) -> None:
    """Handle cancellation notifications from the client."""
    logger.info(
        (
            f"Cancelled notification received for request ID "
            f"{params.request_id}: {params.reason}"
        )
    )


@mcp.tool()
async def slow_operation(ctx: Context, length: int = 100) -> str:
    """A long-running tool the user may want to cancel.
    Args:
        length: The length of the operation in steps.
    """
    try:
        for i in range(1, length + 1):
            await anyio.sleep(0.1)
            await ctx.report_progress(progress=i, total=length)
    except anyio.get_cancelled_exc_class():
        logger.info("slow_operation cancelled mid-run, cleaning up")
        raise
    return f"Completed all {length} steps"


if __name__ == "__main__":
    mcp._lowlevel_server.add_notification_handler(
        "notifications/cancelled",
        CancelledNotificationParams,
        handle_cancelled_notification,
    )
    mcp.run()
