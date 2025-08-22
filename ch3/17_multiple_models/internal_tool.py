from typing import Any


class InternalTool:
    def __init__(
        self, name: str, input_schema: dict[str, Any], description: str | None = None
    ) -> None:
        self.name = name
        self.input_schema = input_schema
        self.description = description

    def translate_to_openai(self) -> dict[str, Any]:
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
        }

    def translate_to_anthropic(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
