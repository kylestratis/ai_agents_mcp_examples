"""
Calculator MCP server using FastMCP.
Provides mathematical operations as tools for calculation tasks.
"""

import math

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

# Initialize FastMCP server
mcp = FastMCP("calculator", stateless_http=True, json_response=True)


@mcp.tool()
async def add(a: float, b: float, ctx: Context[ServerSession, None]) -> str:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a + b
    await ctx.info(f"Adding {a} and {b} = {result}")
    return f"{a} + {b} = {result}"


@mcp.tool()
async def subtract(a: float, b: float, ctx: Context[ServerSession, None]) -> str:
    """Subtract the second number from the first.

    Args:
        a: Number to subtract from
        b: Number to subtract
    """
    result = a - b
    await ctx.info(f"Subtracting {a} and {b} = {result}")
    return f"{a} - {b} = {result}"


@mcp.tool()
async def multiply(a: float, b: float, ctx: Context[ServerSession, None]) -> str:
    """Multiply two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a * b
    await ctx.info(f"Multiplying {a} and {b} = {result}")
    return f"{a} × {b} = {result}"


@mcp.tool()
async def divide(a: float, b: float, ctx: Context[ServerSession, None]) -> str:
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
async def power(
    base: float, exponent: float, ctx: Context[ServerSession, None]
) -> str:
    """Raise a number to a power.

    Args:
        base: The base number
        exponent: The power to raise the base to
    """
    try:
        result = base**exponent
        await ctx.info(f"Raising {base} to the power of {exponent} = {result}")
        return f"{base}^{exponent} = {result}"
    except Exception as e:
        return f"Error calculating power: {str(e)}"


@mcp.tool()
async def square_root(number: float, ctx: Context[ServerSession, None]) -> str:
    """Calculate the square root of a number.

    Args:
        number: The number to find the square root of
    """
    if number < 0:
        return "Error: Cannot calculate square root of negative number"

    result = math.sqrt(number)
    await ctx.info(f"Calculating the square root of {number} = {result}")
    return f"√{number} = {result}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
