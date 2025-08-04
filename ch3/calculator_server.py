"""
Calculator MCP server using FastMCP.
Provides mathematical operations as tools for calculation tasks.
"""

import math

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("calculator")


@mcp.tool()
async def add(a: float, b: float) -> str:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a + b
    return f"{a} + {b} = {result}"


@mcp.tool()
async def subtract(a: float, b: float) -> str:
    """Subtract the second number from the first.

    Args:
        a: Number to subtract from
        b: Number to subtract
    """
    result = a - b
    return f"{a} - {b} = {result}"


@mcp.tool()
async def multiply(a: float, b: float) -> str:
    """Multiply two numbers together.

    Args:
        a: First number
        b: Second number
    """
    result = a * b
    return f"{a} × {b} = {result}"


@mcp.tool()
async def divide(a: float, b: float) -> str:
    """Divide the first number by the second.

    Args:
        a: Dividend (number to be divided)
        b: Divisor (number to divide by)
    """
    if b == 0:
        return "Error: Division by zero is not allowed"

    result = a / b
    return f"{a} ÷ {b} = {result}"


@mcp.tool()
async def power(base: float, exponent: float) -> str:
    """Raise a number to a power.

    Args:
        base: The base number
        exponent: The power to raise the base to
    """
    try:
        result = base**exponent
        return f"{base}^{exponent} = {result}"
    except Exception as e:
        return f"Error calculating power: {str(e)}"


@mcp.tool()
async def square_root(number: float) -> str:
    """Calculate the square root of a number.

    Args:
        number: The number to find the square root of
    """
    if number < 0:
        return "Error: Cannot calculate square root of negative number"

    result = math.sqrt(number)
    return f"√{number} = {result}"


@mcp.tool()
async def count_rs(text: str) -> str:
    """Count all occurrences of the letter 'R' (case-insensitive) in the input string.

    Args:
        text: The input string to search for the letter 'R'
    """
    count = text.upper().count("R")
    return f"The letter 'R' appears {count} times in: '{text}'"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")
