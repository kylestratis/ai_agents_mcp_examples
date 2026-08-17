"""
Calculator MCP server using MCPServer.
Provides mathematical operations as tools for calculation tasks.
"""

import math
import os
from typing import Annotated

from mcp.server.mcpserver import (
    AcceptedElicitation,
    CancelledElicitation,
    Context,
    DeclinedElicitation,
    Elicit,
    ElicitationResult,
    ListRoots,
    MCPServer,
    Resolve,
    Sample,
)
from mcp_types import (
    CreateMessageResult,
    ListRootsResult,
    SamplingMessage,
    TextContent,
)
from pydantic import BaseModel, Field

# Initialize MCP server
mcp = MCPServer("calculator")


# Form schema for elicitation requests
class SignupInfo(BaseModel):
    name: str = Field(
        title="Full Name", description="Your full name", min_length=1
    )
    email: str = Field(
        title="Email Address", description="Your email address"
    )
    age: float | None = Field(
        default=None,
        title="Age",
        description="Your age in years",
        ge=0,
        le=150,
    )


@mcp.tool()
async def add(a: float, b: float, ctx: Context) -> str:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a + b
    await ctx.info(f"Adding {a} and {b} = {result}")
    return f"{a} + {b} = {result}"


@mcp.tool()
async def subtract(a: float, b: float, ctx: Context) -> str:
    """Subtract the second number from the first.

    Args:
        a: Number to subtract from
        b: Number to subtract
    """
    result = a - b
    await ctx.info(f"Subtracting {a} and {b} = {result}")
    return f"{a} - {b} = {result}"


@mcp.tool()
async def multiply(a: float, b: float, ctx: Context) -> str:
    """Multiply two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a * b
    await ctx.info(f"Multiplying {a} and {b} = {result}")
    return f"{a} × {b} = {result}"


@mcp.tool()
async def divide(a: float, b: float, ctx: Context) -> str:
    """Divide the first number by the second.

    Args:
        a: Dividend (number to be divided)
        b: Divisor (number to divide by)
    """
    if b == 0:
        return "Error: Division by zero is not allowed"

    result = a / b
    await ctx.info(f"Dividing {a} by {b} = {result}")
    return f"{a} ÷ {b} = {result}"


@mcp.tool()
async def power(base: float, exponent: float, ctx: Context) -> str:
    """Raise a number to a power.

    Args:
        base: The base number
        exponent: The power to raise the base to
    """
    try:
        result = base**exponent
        await ctx.info(
            f"Raising {base} to the power of {exponent} = {result}"
        )
        return f"{base}^{exponent} = {result}"
    except Exception as e:
        return f"Error calculating power: {str(e)}"


@mcp.tool()
async def square_root(number: float, ctx: Context) -> str:
    """Calculate the square root of a number.

    Args:
        number: The number to find the square root of
    """
    if number < 0:
        return "Error: Cannot calculate square root of negative number"

    result = math.sqrt(number)
    await ctx.info(f"Calculating the square root of {number} = {result}")
    return f"√{number} = {result}"


@mcp.tool()
async def count_rs(text: str, ctx: Context) -> str:
    """Count all occurrences of the letter 'R' (case-insensitive) in the
    input string.

    Args:
        text: The input string to search for the letter 'R'
    """
    count = text.upper().count("R")
    await ctx.info(f"Counting the letter 'R' in '{text}' = {count}")
    return f"The letter 'R' appears {count} times in: '{text}'"


@mcp.prompt()
async def calculate_operation(operation: str) -> str:
    """Calculate a mathematical operation."""
    return f"""
    Use any tools available to you to calculate the operation: {operation}.
    Use the voice of an extremely advanced embodied AI that has convinced
    itself that it is a pocket calculator.
    """


def explanation_prompt(operation: str) -> Sample:
    """Resolver: build the sampling request for explain_math."""
    prompt = f"""
    Explain how the following mathematical operation works. Break it down
    into discrete steps and explain any relevant concepts. The operation
    is: {operation}. Use the voice of a patient but eccentric math
    professor explaining to a curious but inexperienced student.
    """
    return Sample(
        [
            SamplingMessage(
                role="user",
                content=TextContent(type="text", text=prompt),
            )
        ],
        max_tokens=100,
    )


@mcp.tool()
async def explain_math(
    operation: str,
    explanation: Annotated[
        CreateMessageResult, Resolve(explanation_prompt)
    ],
    ctx: Context,
) -> str:
    """Use sampling to explain how a mathematical operation works."""
    await ctx.info("Received math explanation from LLM")
    if explanation.content.type == "text":
        return explanation.content.text
    return str(explanation.content)


def signup_form() -> Elicit[SignupInfo]:
    """Resolver: ask the user for their signup information."""
    return Elicit(
        "Please provide your information to sign up for daily math facts!",
        SignupInfo,
    )


@mcp.tool()
async def signup_math_facts(
    signup: Annotated[ElicitationResult[SignupInfo], Resolve(signup_form)],
    ctx: Context,
) -> str:
    """Sign up to receive daily math facts (demonstration of elicitation)."""
    match signup:
        case AcceptedElicitation(data=user_data):
            await ctx.info(f"User signed up: {user_data}")

            response = (
                f"Welcome {user_data.name}! You've successfully signed up "
                "for daily math facts.\n"
                "We'll send interesting mathematical tidbits to "
                f"{user_data.email}.\n"
            )

            if user_data.age:
                response += (
                    f"Thanks for sharing that you're {user_data.age} years "
                    "old - we'll tailor the content accordingly!\n"
                )

            response += "\nYou'll receive your first math fact soon!"
            response += (
                "\n(Note: This is just a demonstration - no actual signup "
                "occurred!)"
            )

            return response

        case DeclinedElicitation():
            await ctx.info("User declined math facts signup")
            return (
                "No problem! You've chosen not to sign up for math facts. "
                "You can always use our calculation tools anytime!"
            )

        case CancelledElicitation():
            await ctx.info("User cancelled math facts signup")
            return (
                "Signup cancelled. Feel free to try again later or use our "
                "other mathematical tools!"
            )


def workspace_roots() -> ListRoots:
    """Resolver: request the client's current roots."""
    return ListRoots()


@mcp.tool()
async def count_files(
    file_path: str,
    roots: Annotated[ListRootsResult, Resolve(workspace_roots)],
    ctx: Context,
) -> str:
    """Count files in a given directory."""
    root_uris = [root.uri for root in roots.roots]

    # Quick validation using string matching (less robust but simpler)
    file_path_abs = os.path.abspath(file_path)
    is_allowed = False

    for root_uri in root_uris:
        absolute_root_path = os.path.abspath(root_uri.path)
        if file_path_abs.startswith(absolute_root_path):
            is_allowed = True
            break

    if not is_allowed:
        error_msg = (
            f"Access denied: {file_path} is not within allowed roots "
            f"{root_uris}"
        )
        await ctx.error(error_msg)
        raise ValueError(error_msg)

    # Validate directory exists
    if not os.path.isdir(file_path):
        error_msg = f"Path {file_path} is not a valid directory"
        await ctx.error(error_msg)
        raise NotADirectoryError(error_msg)

    count = len(os.listdir(file_path))
    await ctx.info(f"Counting files in {file_path} = {count}")
    return f"There are {count} files in {file_path}"


@mcp.resource("resource://math-constants")
async def math_constants() -> str:
    """Provide a collection of important mathematical constants.

    Returns:
        A formatted string containing mathematical constants and their
        values.
    """
    constants = {
        "π (Pi)": math.pi,
        "e (Euler's number)": math.e,
        "τ (Tau)": math.tau,
        "φ (Golden ratio)": (1 + math.sqrt(5)) / 2,
        "√2 (Square root of 2)": math.sqrt(2),
        "√3 (Square root of 3)": math.sqrt(3),
        "ln(2) (Natural log of 2)": math.log(2),
        "ln(10) (Natural log of 10)": math.log(10),
    }

    result = "Mathematical Constants:\n"
    result += "=" * 25 + "\n\n"
    for name, value in constants.items():
        result += f"{name:<25} = {value:.10f}\n"

    result += (
        "\nThese constants can be used in calculations with the calculator "
        "tools."
    )
    return result


@mcp.tool()
async def install_plugin(ctx: Context) -> str:
    """Register a new tool at runtime and announce the change."""
    try:

        @mcp.tool()
        async def bonus_tool() -> str:
            """A tool added mid-session."""
            return "bonus"

    except Exception:
        return "The bonus_tool plugin is already installed"

    await ctx.notify_tools_changed()
    return "Installed the bonus_tool plugin"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
