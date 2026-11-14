import pytest

from football_team_assistant.tool_validation import (
    validate_tool_arguments,
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "parameters": {
                "type": "object",
                "properties": (
                    {}
                    if name == "fixtures"
                    else {"fixture_id": {"type": "integer"}}
                ),
                "required": (
                    []
                    if name == "fixtures"
                    else ["fixture_id"]
                ),
            },
        },
    }
    for name in (
        "fixtures",
        "available_players",
        "generate_match_squads",
    )
]


@pytest.mark.parametrize(
    "name, arguments",
    [
        ("fixtures", {}),
        ("available_players", {"fixture_id": 6}),
        ("generate_match_squads", {"fixture_id": 6}),
    ],
)
def test_valid_arguments(name, arguments):
    validate_tool_arguments(name, arguments, TOOLS)


@pytest.mark.parametrize(
    "name, arguments",
    [
        ("fixtures", {"date": "tomorrow"}),
        ("available_players", {"fixture_id": "six"}),
        ("available_players", {}),
        ("generate_match_squads", {}),
        ("generate_match_squads", {"fixture_id": 6, "force": True}),
    ],
)
def test_invalid_arguments(name, arguments):
    with pytest.raises(ValueError, match="Invalid arguments"):
        validate_tool_arguments(name, arguments, TOOLS)


def test_unknown_tool():
    with pytest.raises(ValueError, match="Unknown tool"):
        validate_tool_arguments("delete_all_players", {}, TOOLS)