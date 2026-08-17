from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from pydantic import AnyHttpUrl


# Auth settings - these will come from your authorization server's documentation
AUTHORIZATION_SERVER_SETTINGS = AuthSettings(
    issuer_url=AnyHttpUrl("https://authorization-server.com"),
    resource_server_url=AnyHttpUrl("https://localhost:3001"),
    required_scopes=["read", "write"],
)


class MyTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        # YOUR VALIDATION LOGIC HERE
        pass


# Initialize MCP server
mcp = MCPServer(
    "resource-server",
    token_verifier=MyTokenVerifier(),
    auth=AUTHORIZATION_SERVER_SETTINGS,
)


@mcp.tool()
async def example_tool(request: str) -> str:
    """Uppercase the request."""
    return request.upper()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
