from mcp import MCPError
from mcp.server.mcpserver import MCPServer
from mcp_types import INVALID_REQUEST

# Initialize MCP server
mcp = MCPServer("error-handling-server")

GRADES_POSTED = True
GRADEBOOK = {"Ada Lovelace": 98, "Alan Turing": 94, "Grace Hopper": 97}


@mcp.tool()
def grader_get_grade(student: str) -> int:
    """
    Look up a student's posted grade.

    Args:
        student: The full name of the student
    """
    if not GRADES_POSTED:
        raise MCPError(
            INVALID_REQUEST,
            "Grades have not been posted yet. No results are available.",
        )
    if student not in GRADEBOOK:
        raise ValueError(f"No student named {student!r} in the gradebook.")
    return GRADEBOOK[student]


if __name__ == "__main__":
    mcp.run()
