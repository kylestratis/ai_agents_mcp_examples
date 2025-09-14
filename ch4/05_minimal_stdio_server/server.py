from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("minimal-stdio-server")

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run()
    # mcp.run(t"streamable-http")
