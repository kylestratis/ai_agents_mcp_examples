import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)

# Initialize FastMCP server
mcp = FastMCP("completion-server")


@mcp.resource("file:///{filename}")
async def resource_template(filename: str) -> str | bytes:
    """A resource that loads one of two files based on the filename parameter."""
    # Get the absolute path to the file relative to this script
    file_to_load = Path(__file__).parent / filename

    # Determine if file is binary based on extension
    if file_to_load.suffix.lower() == ".txt":
        with open(file_to_load, "r", encoding="utf-8") as f:
            return f.read()
    else:
        with open(file_to_load, "rb") as f:
            return f.read()


@mcp.prompt()
async def simple_prompt_input(username: str) -> str:
    """A simple prompt that greets the user with their name."""
    return f"Say hello to the user using their name: {username}"


@mcp.completion()
async def simple_completion(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion:
    """Returns potential completions for a given reference and argument."""
    completion = Completion(values=[], total=0, hasMore=False)
    prompt_default_suggestions = ["user"]
    resource_template_default_suggestions = ["1.txt", "2.png"]
    print(context, file=sys.stderr)
    if isinstance(ref, PromptReference):
        if ref.name == "simple_prompt_input":
            suggested = [
                suggestion
                for suggestion in prompt_default_suggestions
                if argument.value.lower() in suggestion.lower()
            ]
            if previous := context.arguments.get("username"):
                suggested.extend(
                    [
                        prev
                        for prev in previous
                        if argument.value.lower() in prev.lower()
                    ]
                )
            completion = Completion(
                values=suggested, total=len(suggested), hasMore=False
            )
    else:
        if ref.uri == "file:///{filename}":
            suggested = [
                suggestion
                for suggestion in resource_template_default_suggestions
                if argument.value.lower() in suggestion.lower()
            ]
            if previous := context.arguments.get("filename"):
                suggested.extend(
                    [
                        prev
                        for prev in previous
                        if argument.value.lower() in prev.lower()
                    ]
                )
            completion = Completion(values=suggested, total=2, hasMore=False)
    return completion


if __name__ == "__main__":
    mcp.run()
