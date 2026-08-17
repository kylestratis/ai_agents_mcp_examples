from typing import Annotated

from mcp.server.mcpserver import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
    Elicit,
    ElicitationResult,
    MCPServer,
    Resolve,
)
from pydantic import BaseModel, Field

# Initialize MCP server
mcp = MCPServer("elicitations-server")


class SignupInfo(BaseModel):
    """Form schema for the signup elicitation request."""

    name: str = Field(title="Full Name", description="Your full name", min_length=1)
    email: str = Field(title="Email Address", description="Your email address")
    age: int | None = Field(
        default=None,
        title="Age",
        description="Your age in years",
        ge=0,
        le=150,
    )


async def request_signup_info() -> Elicit[SignupInfo]:
    """Resolver: ask the user for their signup information."""
    return Elicit(
        "Please provide your information to sign up for daily math facts!",
        SignupInfo,
    )


@mcp.tool()
async def signup_math_facts(
    signup: Annotated[ElicitationResult[SignupInfo], Resolve(request_signup_info)],
) -> str:
    """Sign up to receive daily math facts (demonstration of elicitation)."""
    # Handle the different response actions
    match signup:
        case AcceptedElicitation(data=user_data):
            response = (
                f"Welcome {user_data.name}! You've successfully signed up "
                "for daily math facts.\n"
            )
            response += (
                f"We'll send interesting mathematical tidbits to "
                f"{user_data.email}.\n"
            )

            if user_data.age:
                response += (
                    f"Thanks for sharing that you're {user_data.age} years "
                    "old - we'll tailor the content accordingly!\n"
                )

            response += "\nYou'll receive your first math fact soon!"
            response += (
                "\n(Note: This is just a demonstration - "
                "no actual signup occurred!)"
            )

            return response

        case DeclinedElicitation():
            return (
                "No problem! You've chosen not to sign up for math facts. "
                "You can always use our calculation tools anytime!"
            )

        case CancelledElicitation():
            return (
                "Signup cancelled. Feel free to try again later or "
                "use our other mathematical tools!"
            )


if __name__ == "__main__":
    mcp.run()
