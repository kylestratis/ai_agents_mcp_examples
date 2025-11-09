from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage
from PIL import ImageDraw
from pydantic import BaseModel

# Initialize FastMCP server
mcp = FastMCP("structured-output-server")


class ReportCard(BaseModel):
    name: str
    grades: list[tuple[str, int]]  # class name and grade


@mcp.tool()
async def generate_report_card(
    name: str, grades: list[tuple[str, int]]
) -> ReportCard:
    """
    Generate a report card for a student.

    Args:
        name: The name of the student
        grades: A list of tuples containing the class name and grade
    """
    return ReportCard(name=name, grades=grades)


@mcp.tool()
async def generate_report_card_image(report_card: ReportCard) -> Image:
    """
    Generate a report card image for a student.

    Args:
        report_card: The report card to generate an image for
    """
    image = PILImage.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.text((100, 100), report_card.name, fill=(0, 0, 0))
    return Image(data=image.tobytes())


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run()
