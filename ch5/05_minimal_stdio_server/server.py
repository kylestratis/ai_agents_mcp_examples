from mcp.server.mcpserver import MCPServer

# Initialize MCP server
mcp = MCPServer("minimal-stdio-server")

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run()
    # mcp.run("streamable-http")
