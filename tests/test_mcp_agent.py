
import json
from types import SimpleNamespace

import pytest

from football_team_assistant.mcp_agent import extract_tool_result


def make_result(
    structured_content=None,
    content=None,
    is_error=False,
):
    return SimpleNamespace(
        structured_content=structured_content,
        content=content or [],
        is_error=is_error,
    )


def text_block(value):
    return SimpleNamespace(type="text", text=value)


def test_extract_structured_content():
    players = [{"id": 1, "name": "Henry"}]

    result = make_result(
        structured_content={"result": players}
    )

    assert extract_tool_result(result) == players


def test_extract_json_text_content():
    squads = {
        "squad_a": [{"id": 1, "name": "Henry"}],
        "squad_b": [{"id": 2, "name": "Sam"}],
    }

    result = make_result(
        content=[text_block(json.dumps(squads))]
    )

    assert extract_tool_result(result) == squads


def test_extract_plain_text():
    result = make_result(
        content=[text_block("No fixtures found")]
    )

    assert extract_tool_result(result) == "No fixtures found"


def test_extract_mcp_error():
    result = make_result(
        is_error=True,
        content=[text_block("Database connection failed")],
    )

    with pytest.raises(
        RuntimeError,
        match="Database connection failed",
    ):
        extract_tool_result(result)


def test_extract_empty_result():
    result = make_result()

    assert extract_tool_result(result) == []
