from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.resources import FileResource

# Initialize MCP server
mcp = MCPServer("resource-object-server")


@mcp.resource("file:///{filename}")
async def resource_template(filename: str) -> FileResource:
    """A resource that loads one of two files based on the filename parameter."""
    # Get the absolute path to the file relative to this script
    file_to_load = Path(__file__).parent / filename
    # Decode .txt files as text; serve anything else as a binary blob.
    encoding = "utf-8" if file_to_load.suffix.lower() == ".txt" else None
    return FileResource(
        uri=f"file:///{filename}", path=file_to_load, encoding=encoding
    )


filename = "1.txt"
file_resource = FileResource(
    uri=f"file:///{filename}", path=Path(__file__).parent / filename
)
mcp.add_resource(file_resource)

if __name__ == "__main__":
    mcp.run()
