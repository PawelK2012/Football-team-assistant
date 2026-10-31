from mcp.server import MCPServer

from football_team_assistant.repositories.fixture_repository import (
    get_fixtures,
)
from football_team_assistant.repositories.player_repository import (
    get_available_players,
)

mcp = MCPServer("Football Team Assistant")


@mcp.tool()
def fixtures() -> list[dict]:
    """Get football fixtures."""

    return get_fixtures()


@mcp.tool()
def available_players(
    fixture_id: int,
) -> list[dict]:
    """
    Get available players for a football fixture.

    Args:
        fixture_id: ID of the fixture.
    """

    return get_available_players(fixture_id)


if __name__ == "__main__":
    mcp.run()
