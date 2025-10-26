from mcp.server.fastmcp import Context, FastMCP
from mcp.shared.context import RequestContext
from mcp.types import CancelledNotification, CancelledNotificationParams

mcp = FastMCP("cancel-request-notifications-server")


@mcp.tool()
async def test_cancel_request(ctx: Context[RequestContext, None]) -> None:
    """A tool that tests the notifications."""
    await ctx.request_context.session.send_notification(
        notification=CancelledNotification(
            params=CancelledNotificationParams(
                requestId=ctx.request_context.request_id,
                reason="This is a test cancellation notification",
            ),
        ),
        related_request_id=ctx.request_context.request_id,
    )


if __name__ == "__main__":
    mcp.run()
