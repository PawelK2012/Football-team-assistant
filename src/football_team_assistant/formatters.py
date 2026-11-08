# The classic reliability issue with LLMs is that,
# even though the tools return accurate data, the model still introduces errors
# when translating that data into a human‑readable response.
# To fix this, I added formatters.py


def format_available_players(players: list[dict]) -> str:
    lines = [f"Available players ({len(players)}):", ""]

    for index, player in enumerate(players, start=1):
        lines.append(f"{index}. {player['name']} ({player['rating']})")

    return "\n".join(lines)


def format_squads(data: dict) -> str:
    lines = [
        f"Fixture: {data['fixture']['opponent']}",
        f"Date: {data['fixture']['date']}",
        "",
    ]

    for label in ("a", "b"):
        players = data[f"squad_{label}"]
        goalkeeper = data[f"goalkeeper_{label}"]
        average = data[f"average_rating_{label}"]

        lines.append(f"Squad {label.upper()} ({len(players)} players)")
        lines.append(f"Goalkeeper: {goalkeeper['name']}")
        lines.append("")

        for index, player in enumerate(players, start=1):
            suffix = " (GK)" if player["id"] == goalkeeper["id"] else ""
            lines.append(f"{index}. {player['name']} ({player['rating']}){suffix}")

        lines.append(f"Average rating: {average:.2f}")
        lines.append("")

    lines.append(f"Balance difference: {data['balance_difference']:.2f}")

    return "\n".join(lines)


def validate_squads(data: dict) -> None:
    squad_a = data["squad_a"]
    squad_b = data["squad_b"]

    all_players = squad_a + squad_b
    player_ids = [player["id"] for player in all_players]

    if len(player_ids) != len(set(player_ids)):
        raise ValueError("Duplicate player detected in squads")

    if abs(len(squad_a) - len(squad_b)) > 1:
        raise ValueError("Squad sizes are unbalanced")

    for label, squad in (("a", squad_a), ("b", squad_b)):
        goalkeeper = data[f"goalkeeper_{label}"]

        if goalkeeper["id"] not in {player["id"] for player in squad}:
            raise ValueError(f"Goalkeeper missing from Squad {label.upper()}")

        if not goalkeeper["can_play_goalkeeper"]:
            raise ValueError(f"Ineligible goalkeeper in Squad {label.upper()}")
