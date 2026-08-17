from typing import Annotated

from mcp.server.mcpserver import MCPServer, Resolve, Sample
from mcp_types import (
    CreateMessageResult,
    ModelHint,
    ModelPreferences,
    SamplingMessage,
    TextContent,
)

# Initialize MCP server
mcp = MCPServer("sampling-server")

MODEL_PREFERENCES = ModelPreferences(
    hints=[
        ModelHint(name="claude-4-5-haiku"),
        ModelHint(name="claude-haiku"),
        ModelHint(name="gpt-4o-mini"),
    ],
    cost_priority=1.0,
    speed_priority=0.8,
    intelligence_priority=0.3,
)


def request_math_explanation(operation: str) -> Sample:
    """Resolver: sample the client's language model for an explanation."""
    prompt = f"""
    Explain how the following mathematical operation works. Break it down into
    discrete steps and explain any relevant concepts. The operation is:
    {operation}. Use the voice of a patient but eccentric math professor
    explaining to a curious but inexperienced student.
    """
    return Sample(
        [
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt),
            )
        ],
        max_tokens=100,
        model_preferences=MODEL_PREFERENCES,
    )


@mcp.tool()
async def explain_math(
    operation: str,
    explanation: Annotated[CreateMessageResult, Resolve(request_math_explanation)],
) -> str:
    """Use sampling to explain how a mathematical operation works."""
    match explanation.content.type:
        case "text":
            return explanation.content.text
        case "image" | "audio":
            return str(explanation.content.data)


if __name__ == "__main__":
    mcp.run()
