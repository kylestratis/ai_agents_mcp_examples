import asyncio
import logging

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.types import (
    CancelledNotification,
    CancelledNotificationParams,
    ModelPreferences,
    SamplingMessage,
    ServerNotification,
    TextContent,
)

logger = logging.getLogger(__name__)
mcp = FastMCP("cancel-request-notification-server")


async def handle_cancelled_notification(
    notification: CancelledNotification,
) -> None:
    """Handle cancellation notifications from the client."""
    logger.info(
        (
            f"Cancelled notification received for request ID "
            f"{notification.params.requestId}: {notification.params.reason}"
        )
    )


@mcp.tool()
async def sampling_with_timeout(ctx: Context[ServerSession, None]) -> str:
    """
    Perform a sampling request with a timeout, sending cancellation if it expires.
    """
    if not ctx.session.client_params.capabilities.sampling:
        return "Error: Sampling is not supported by this client"

    # Capture the request ID that will be used by the next send_request call
    request_id = ctx.session._request_id
    await ctx.info(f"Starting sampling request with ID: {request_id}")

    try:
        # Use asyncio.timeout to limit how long we wait for the response
        async with asyncio.timeout(5.0):  # 5 second timeout
            result = await ctx.session.create_message(
                messages=[
                    SamplingMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=(
                                "Write a very long, detailed essay about "
                                "the history of mathematics."
                            ),
                        ),
                    )
                ],
                max_tokens=10000,
                model_preferences=ModelPreferences(
                    intelligencePriority=1.0,
                ),
            )
            await ctx.info("Sampling completed successfully")
            if result.content:
                return f"Result: {result.content.text[:200]}..."
            else:
                return "No content in result"

    except TimeoutError:
        await ctx.warning(f"Sampling request {request_id} timed out after 5 seconds")

        await ctx.session.send_notification(
            ServerNotification(
                CancelledNotification(
                    params=CancelledNotificationParams(
                        requestId=request_id,
                        reason="Server timeout: Sampling request took too long (>5s)",
                    )
                )
            )
        )

        await ctx.info(f"Sent cancellation notification for request {request_id}")
        return f"Request timed out and cancellation sent to client (request ID: {request_id})"

    except Exception as e:
        await ctx.error(f"Sampling request failed: {e}")
        return f"Error: {e}"


if __name__ == "__main__":
    mcp._mcp_server.notification_handlers[CancelledNotification] = (
        handle_cancelled_notification
    )
    mcp.run()
