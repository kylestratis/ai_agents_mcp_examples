"""
Calculator MCP server using MCPServer.
Provides mathematical operations as tools for calculation tasks.

Run with:
uv run ...
or
uvicorn ch7.05_starlette_mount.server:app --reload

Initiate a connection with a client or curl:

curl -X POST http://localhost:3333/mcp \
     -H "Accept: application/json, text/event-stream" \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "initialize",
       "params": {
         "protocolVersion": "2024-11-05",
         "capabilities": {},
         "clientInfo": {
           "name": "curl-client",
           "version": "1.0.0"
         }
       }
     }'
"""

import math
from contextlib import AsyncExitStack, asynccontextmanager

import uvicorn
from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.routing import Mount

# Initialize MCP server
mcp = MCPServer("calculator")


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


@asynccontextmanager
async def lifespan(app: Starlette):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = Starlette(
    routes=[
        Mount(
            "/",
            mcp.streamable_http_app(stateless_http=True, json_response=True),
        )
    ],
    lifespan=lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3333)
