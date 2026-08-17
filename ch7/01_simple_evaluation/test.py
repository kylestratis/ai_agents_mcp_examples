""" """

import os

from anthropic import Anthropic
from dotenv import load_dotenv
from server import add, divide, multiply, subtract

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]


def _create_tool_dictionary(tool_func):
    return {
        "name": tool_func.__name__,
        "description": tool_func.__doc__,
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
    }


TOOLS = [
    _create_tool_dictionary(add),
    _create_tool_dictionary(subtract),
    _create_tool_dictionary(multiply),
    _create_tool_dictionary(divide),
]

TEST_PROMPT_TOOL_CHOICE_PAIRS = [
    ("What is 2 + 2?", "add"),
    ("What is 2 - 2?", "subtract"),
    ("What is 2 * 2?", "multiply"),
    ("What is 2 / 2?", "divide"),
]


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable not set. "
            "Please create a .env file with your API key."
        )

    client = Anthropic(api_key=api_key)

    tool_choice_score = 0
    for prompt, expected_tool_choice in TEST_PROMPT_TOOL_CHOICE_PAIRS:
        conversation_messages = [
            {"role": "user", "content": prompt},
        ]
        # Call Claude API with available tools
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            messages=conversation_messages,
            tools=TOOLS,
            tool_choice={"type": "auto"},  # Let Claude decide when to use tools
        )

        # Check if Claude wants to use tools
        if response.stop_reason == "tool_use":
            # Extract all tool use blocks from the response
            tool_use_blocks = [
                block for block in response.content if block.type == "tool_use"
            ]

            if (
                len(tool_use_blocks) == 1
                and tool_use_blocks[0].name == expected_tool_choice
            ):
                tool_choice_score += 1

    print(f"Tool choice score: {tool_choice_score}")
    print(
        f"Tool choice accuracy: {tool_choice_score / len(TEST_PROMPT_TOOL_CHOICE_PAIRS) * 100}%"
    )


if __name__ == "__main__":
    main()
