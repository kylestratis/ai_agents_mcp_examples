from random import randint

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel

# Initialize FastMCP server
mcp = FastMCP("full-tool-server")


class Class(BaseModel):
    title: str
    grade: int
    instructor: str
    credits: int


class ReportCard(BaseModel):
    name: str
    grades: list[Class]
    weighted_gpa: float | None = None
    unweighted_gpa: float | None = None


def _generate_classes() -> list[Class]:
    return [
        Class(
            title="Math",
            grade=randint(0, 100),
            instructor="Mr. Smith",
            credits=randint(1, 4),
        ),
        Class(
            title="Science",
            grade=randint(0, 100),
            instructor="Mrs. Johnson",
            credits=randint(1, 4),
        ),
        Class(
            title="History",
            grade=randint(0, 100),
            instructor="Mr. Brown",
            credits=randint(1, 4),
        ),
    ]


@mcp.tool(title="Generate Report Card")
def grader_generate_report_card(
    name: str, classes: list[Class] | None = None
) -> ReportCard:
    """
    Generates a full report card for a student and a list of classes.
    Can leave out the list of classes to use a randomly generated list.

    Args:
        name: The name of the student
        classes: An optional list of Class objects to add to the report card
    """
    if not classes:
        classes = _generate_classes()

    weighted_gpa = grader_calculate_gpa(classes)
    unweighted_gpa = grader_calculate_gpa(classes, weighted=False)
    return ReportCard(
        name=name,
        grades=classes,
        weighted_gpa=weighted_gpa,
        unweighted_gpa=unweighted_gpa,
    )


@mcp.tool(
    title="Calculate GPA",
    annotations=ToolAnnotations(readOnlyHint=True),
    structured_output=False,
)
def grader_calculate_gpa(classes: list[Class], weighted: bool = True) -> float:
    """
    Calculate the GPA for a list of classes. Calculates the weighted
    GPA by default, but can optionally calculate the unweighted GPA.

    Args:
        classes: A list of classes
        weighted: Whether to use weighted GPA
    """
    if weighted:
        return sum(_class.grade * _class.credits for _class in classes) / sum(
            _class.credits for _class in classes
        )
    return sum(_class.grade for _class in classes) / len(classes)


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run()
