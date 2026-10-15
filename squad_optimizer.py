from datetime import date
from itertools import combinations


def average_rating(players: list[dict]) -> float:
    if not players:
        return 0.0

    return sum(
        player["rating"]
        for player in players
    ) / len(players)


def validate_players(players: list[dict]) -> None:
    if len(players) < 10:
        raise ValueError(
            f"At least 10 available players are required. "
            f"Got {len(players)}."
        )

    if len(players) > 16:
        raise ValueError(
            f"Maximum supported squad size is 16. "
            f"Got {len(players)}."
        )

    for player in players:
        rating = player["rating"]

        if not 1.0 <= rating <= 6.0:
            raise ValueError(
                f"Invalid rating for {player['name']}: {rating}"
            )

        if rating * 2 != int(rating * 2):
            raise ValueError(
                f"Rating must use 0.5 increments: "
                f"{player['name']} has {rating}"
            )


def has_goalkeeper(squad: list[dict]) -> bool:
    return any(
        player["can_play_goalkeeper"]
        for player in squad
    )


def calculate_balance_score(
    squad_a: list[dict],
    squad_b: list[dict],
) -> float:

    return abs(
        average_rating(squad_a)
        - average_rating(squad_b)
    )


def select_goalkeeper(
    squad: list[dict],
    goalkeeper_history: list[dict],
) -> dict:

    eligible_players = [
        player
        for player in squad
        if player["can_play_goalkeeper"]
    ]

    if not eligible_players:
        raise ValueError(
            "Squad does not contain an eligible goalkeeper."
        )

    stats = {}

    for player in eligible_players:

        player_history = [
            entry
            for entry in goalkeeper_history
            if entry["player_id"] == player["id"]
        ]

        appearances = len(player_history)

        if player_history:
            last_played = max(
                date.fromisoformat(entry["date"])
                for entry in player_history
            )
        else:
            last_played = date.min

        stats[player["id"]] = {
            "appearances": appearances,
            "last_played": last_played,
        }

    return min(
        eligible_players,
        key=lambda player: (
            stats[player["id"]]["appearances"],
            stats[player["id"]]["last_played"],
        ),
    )


def create_balanced_squads(
    available_players: list[dict],
    goalkeeper_history: list[dict],
) -> dict:

    validate_players(available_players)

    player_count = len(available_players)

    squad_a_size = (player_count + 1) // 2

    best_result = None
    best_score = float("inf")

    for squad_a_tuple in combinations(
        available_players,
        squad_a_size,
    ):

        squad_a = list(squad_a_tuple)

        squad_a_ids = {
            player["id"]
            for player in squad_a
        }

        squad_b = [
            player
            for player in available_players
            if player["id"] not in squad_a_ids
        ]

        # Hard constraint:
        # both squads need a potential goalkeeper.
        if not has_goalkeeper(squad_a):
            continue

        if not has_goalkeeper(squad_b):
            continue

        score = calculate_balance_score(
            squad_a,
            squad_b,
        )

        if score < best_score:

            best_score = score

            best_result = {
                "squad_a": squad_a,
                "squad_b": squad_b,
                "average_rating_a": round(
                    average_rating(squad_a),
                    2,
                ),
                "average_rating_b": round(
                    average_rating(squad_b),
                    2,
                ),
                "balance_difference": round(
                    score,
                    2,
                ),
            }

    if best_result is None:
        raise ValueError(
            "Unable to create two squads with eligible goalkeepers."
        )

    best_result["goalkeeper_a"] = select_goalkeeper(
        best_result["squad_a"],
        goalkeeper_history,
    )

    best_result["goalkeeper_b"] = select_goalkeeper(
        best_result["squad_b"],
        goalkeeper_history,
    )

    return best_result