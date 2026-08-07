"""
Resolve MCP Registry entries into connection settings by server name.

Run me directly to resolve a few real registry entries and print the
settings they produce. Set RUN_REGISTRY_CONNECT=1 to also connect the
MCPClient to the stdio entry that gets resolved (this downloads and
executes the resolved server package with uvx, so it is opt-in).
"""

import asyncio
import logging
import os
from typing import Literal
from urllib.parse import quote

import httpx2
from anthropic import Anthropic
from client import MCPClient
from dotenv import load_dotenv

load_dotenv()

LLM_API_KEY = os.environ["LLM_API_KEY"]
anthropic_client = Anthropic(api_key=LLM_API_KEY)
logger = logging.getLogger(__name__)

REGISTRY_URL = "https://registry.modelcontextprotocol.io"
RUNTIMES = {"pypi": "uvx", "npm": "npx"}
Transport = Literal["streamable-http", "stdio"]


async def resolve_server(name: str, transport: Transport) -> dict:
    """
    Getting server connection settings from the MCP Registry using
    only the server's name.
    """
    async with httpx2.AsyncClient(base_url=REGISTRY_URL) as http:
        response = await http.get(
            f"/v0.1/servers/{quote(name, safe='')}/versions/latest"
        )
        response.raise_for_status()
        server = response.json()["server"]

    match transport:
        case "streamable-http":
            for remote in server.get("remotes", []):
                if remote["type"] == "streamable-http":
                    return {"server_url": remote["url"]}

        case "stdio":
            for package in server.get("packages", []):
                if package["transport"]["type"] != "stdio":
                    continue
                runtime = package.get("runtimeHint") or RUNTIMES.get(
                    package["registryType"]
                )
                if runtime not in ("uvx", "npx"):
                    continue
                args = [
                    argument["value"]
                    for argument in package.get("runtimeArguments", [])
                ]
                return {
                    "command": runtime,
                    "server_args": [*args, package["identifier"]],
                }

    raise ValueError(f"{name} has no {transport} connection method")


async def main() -> None:
    for name, transport in [
        ("ai.anomalyarmor/armor-mcp", "streamable-http"),
        ("ai.anomalyarmor/armor-mcp", "stdio"),
        ("com.mcparmory/github", "stdio"),
    ]:
        try:
            settings = await resolve_server(name, transport)
            print(f"{name} ({transport}): {settings}")
        except (ValueError, httpx2.HTTPError) as e:
            print(f"{name} ({transport}): could not resolve — {e}")

    if not os.environ.get("RUN_REGISTRY_CONNECT"):
        print(
            "\nSet RUN_REGISTRY_CONNECT=1 to also connect to the resolved "
            "stdio server (downloads and runs the package with uvx)."
        )
        return

    settings = await resolve_server("ai.anomalyarmor/armor-mcp", "stdio")
    mcp_client = MCPClient(
        name="armor_connection",
        llm_client=anthropic_client,
        **settings,
    )
    await mcp_client.connect()
    available_tools = await mcp_client.get_available_tools()
    print(f"Connected; server offers {len(available_tools)} tools")
    await mcp_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
