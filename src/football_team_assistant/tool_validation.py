from jsonschema import Draft202012Validator, ValidationError


def validate_tool_arguments(
    name: str,
    arguments: dict,
    tools: list[dict],
) -> None:
    tool = next(
        (
            tool
            for tool in tools
            if tool["function"]["name"] == name
        ),
        None,
    )

    if tool is None:
        raise ValueError(f"Unknown tool: {name}")

    schema = tool["function"]["parameters"].copy()

    # Reject arguments not explicitly defined in the MCP schema.
    schema["additionalProperties"] = False

    Draft202012Validator.check_schema(schema)

    try:
        Draft202012Validator(schema).validate(arguments)
    except ValidationError as error:
        raise ValueError(
            f"Invalid arguments for {name}: {error.message}"
        ) from error