from random import randint

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations
from pydantic import BaseModel

# Initialize MCP server
mcp = MCPServer("full-tool-server")


class Course(BaseModel):
    title: str
    grade: int
    instructor: str
    credits: int


class ReportCard(BaseModel):
    name: str
    grades: list[Course]
    weighted_gpa: float | None = None
    unweighted_gpa: float | None = None


def _generate_courses() -> list[Course]:
    return [
        Course(
            title="Math",
            grade=randint(0, 100),
            instructor="Mr. Smith",
            credits=randint(1, 4),
        ),
        Course(
            title="Science",
            grade=randint(0, 100),
            instructor="Mrs. Johnson",
            credits=randint(1, 4),
        ),
        Course(
            title="History",
            grade=randint(0, 100),
            instructor="Mr. Brown",
            credits=randint(1, 4),
        ),
    ]


@mcp.tool(title="Generate Report Card")
def grader_generate_report_card(
    name: str, courses: list[Course] | None = None
) -> ReportCard:
    """
    Generates a full report card for a student and a list of courses.
    Can leave out the list of courses to use a randomly generated list.

    Args:
        name: The name of the student
        courses: An optional list of Course objects to add to the report card
    """
    if not courses:
        courses = _generate_courses()

    weighted_gpa = grader_calculate_gpa(courses)
    unweighted_gpa = grader_calculate_gpa(courses, weighted=False)
    return ReportCard(
        name=name,
        grades=courses,
        weighted_gpa=weighted_gpa,
        unweighted_gpa=unweighted_gpa,
    )


@mcp.tool(
    title="Calculate GPA",
    annotations=ToolAnnotations(read_only_hint=True),
    structured_output=False,
)
def grader_calculate_gpa(courses: list[Course], weighted: bool = True) -> float:
    """
    Calculate the GPA for a list of courses. Calculates the weighted
    GPA by default, but can optionally calculate the unweighted GPA.

    Args:
        courses: A list of courses
        weighted: Whether to use weighted GPA
    """
    if weighted:
        return sum(course.grade * course.credits for course in courses) / sum(
            course.credits for course in courses
        )
    return sum(course.grade for course in courses) / len(courses)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run()
