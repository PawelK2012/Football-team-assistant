from copy import deepcopy

import pytest

from football_team_assistant.formatters import validate_squads


def test_valid_squads(sample_squads):
    validate_squads(sample_squads)


def test_duplicate_player_in_same_squad(sample_squads):
    data = deepcopy(sample_squads)

    data["squad_a"][1] = deepcopy(data["squad_a"][0])

    with pytest.raises(ValueError, match="Duplicate player"):
        validate_squads(data)


def test_duplicate_player_across_squads(sample_squads):
    data = deepcopy(sample_squads)

    data["squad_b"][1] = deepcopy(data["squad_a"][0])

    with pytest.raises(ValueError, match="Duplicate player"):
        validate_squads(data)


def test_goalkeeper_missing_from_squad(sample_squads):
    data = deepcopy(sample_squads)

    data["goalkeeper_a"]["id"] = 999

    with pytest.raises(ValueError, match="Goalkeeper missing"):
        validate_squads(data)


def test_ineligible_goalkeeper(sample_squads):
    data = deepcopy(sample_squads)

    data["goalkeeper_a"]["can_play_goalkeeper"] = False

    with pytest.raises(ValueError, match="Ineligible goalkeeper"):
        validate_squads(data)


def test_unbalanced_squad_sizes(sample_squads):
    data = deepcopy(sample_squads)

    data["squad_a"].append(
        {
            "id": 20,
            "name": "Extra Player",
            "rating": 3.0,
            "can_play_goalkeeper": True,
        }
    )

    with pytest.raises(ValueError, match="Squad sizes"):
        validate_squads(data)
