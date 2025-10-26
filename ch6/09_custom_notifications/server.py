from mcp.server.fastmcp import Context, FastMCP
from mcp.shared.context import RequestContext
from mcp.types import Notification, NotificationParams

mcp = FastMCP("custom-notifications-server")


class CustomNotificationParams(NotificationParams):
    message: str


@mcp.tool()
async def test_notifications(ctx: Context[RequestContext, None]) -> None:
    """A tool that tests the notifications."""
    await ctx.request_context.session.send_notification(
        notification=Notification(
            method="notifications/test_notifications",
            params=CustomNotificationParams(message="This is a test notification"),
        ),
        related_request_id=ctx.request_context.request_id,
    )


if __name__ == "__main__":
    mcp.run()
