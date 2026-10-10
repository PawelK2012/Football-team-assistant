from itertools import combinations


def has_goalkeeper(squad: list[dict]) -> bool:
    return any(player["can_play_goalkeeper"] for player in squad)


def select_goalkeeper(
    squad: list[dict],
    goalkeeper_history: list[dict],
) -> dict:

    eligible_players = [player for player in squad if player["can_play_goalkeeper"]]

    if not eligible_players:
        raise ValueError("Squad does not contain an eligible goalkeeper.")

    appearances = {player["id"]: 0 for player in eligible_players}

    for entry in goalkeeper_history:
        player_id = entry["player_id"]

        if player_id in appearances:
            appearances[player_id] += 1

    return min(
        eligible_players,
        key=lambda player: appearances[player["id"]],
    )


def average_rating(players: list[dict]) -> float:
    if not players:
        return 0.0

    return sum(player["rating"] for player in players) / len(players)


def validate_players(players: list[dict]) -> None:
    if len(players) < 10:
        raise ValueError(
            f"At least 10 available players are required. Got {len(players)}."
        )

    if len(players) > 16:
        raise ValueError(f"Maximum supported squad size is 16. Got {len(players)}.")

    for player in players:
        rating = player["rating"]

        if not 1.0 <= rating <= 6.0:
            raise ValueError(f"Invalid rating for {player['name']}: {rating}")

        if rating * 2 != int(rating * 2):
            raise ValueError(
                f"Rating must use 0.5 increments: {player['name']} has {rating}"
            )


def calculate_balance_score(
    squad_a: list[dict],
    squad_b: list[dict],
) -> float:
    """
    Lower score = better balance.

    For now we only compare average player rating.
    """

    average_a = average_rating(squad_a)
    average_b = average_rating(squad_b)

    return abs(average_a - average_b)


def create_balanced_squads(
    available_players: list[dict],
    goalkeeper_history: list[dict],
) -> dict:

    validate_players(available_players)

    player_count = len(available_players)

    # Example:
    # 10 -> 5 + 5
    # 11 -> 6 + 5
    # 12 -> 6 + 6
    # 13 -> 7 + 6
    # ...
    squad_a_size = (player_count + 1) // 2

    best_result = None
    best_score = float("inf")

    # Try every possible Squad A.
    #
    # Everyone not selected for A automatically becomes Squad B.
    for squad_a_tuple in combinations(
        available_players,
        squad_a_size,
    ):
        squad_a = list(squad_a_tuple)

        squad_a_ids = {player["id"] for player in squad_a}

        squad_b = [
            player for player in available_players if player["id"] not in squad_a_ids
        ]

        if not has_goalkeeper(squad_a):
            continue

        if not has_goalkeeper(squad_b):
            continue

        score = calculate_balance_score(
            squad_a,
            squad_b,
        )
        print("\nChecking combination:")
        print(f"score: {score} - best_score: {best_score}")
        if score < best_score:
            print("Found new best squad!")
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
        raise ValueError("Unable to create two squads with eligible goalkeepers.")

    best_result["goalkeeper_a"] = select_goalkeeper(
        best_result["squad_a"],
        goalkeeper_history,
    )

    best_result["goalkeeper_b"] = select_goalkeeper(
        best_result["squad_b"],
        goalkeeper_history,
    )

    return best_result


if __name__ == "__main__":
    players = [
        {"id": 1, "name": "Henry", "rating": 4.5, "can_play_goalkeeper": True},
        {"id": 2, "name": "Jack", "rating": 5.5, "can_play_goalkeeper": True},
        {"id": 3, "name": "Ben", "rating": 3.5, "can_play_goalkeeper": False},
        {"id": 4, "name": "Milo", "rating": 5.0, "can_play_goalkeeper": True},
        {"id": 5, "name": "Calum", "rating": 4.0, "can_play_goalkeeper": True},
        {"id": 6, "name": "Aron", "rating": 3.0, "can_play_goalkeeper": False},
        {"id": 7, "name": "Mason", "rating": 4.5, "can_play_goalkeeper": False},
        {"id": 8, "name": "Liam", "rating": 4.0, "can_play_goalkeeper": True},
        {"id": 9, "name": "Mateo", "rating": 3.5, "can_play_goalkeeper": False},
        {"id": 10, "name": "Knox", "rating": 5.0, "can_play_goalkeeper": False},
        {"id": 11, "name": "Leo", "rating": 4.5, "can_play_goalkeeper": False},
        {"id": 12, "name": "Ethan", "rating": 3.0, "can_play_goalkeeper": True},
        {"id": 13, "name": "Sidan", "rating": 5.5, "can_play_goalkeeper": False},
    ]

    goalkeeper_history = [
        {
            "date": "2026-09-20",
            "player_id": 1,
        },
        {
            "date": "2026-09-20",
            "player_id": 4,
        },
        {
            "date": "2026-09-27",
            "player_id": 2,
        },
        {
            "date": "2026-09-27",
            "player_id": 5,
        },
    ]

    result = create_balanced_squads(players, goalkeeper_history)

    print("\nSquad A")
for player in result["squad_a"]:
    marker = ""

    if player["id"] == result["goalkeeper_a"]["id"]:
        marker = " (GK)"

    print(f"  {player['name']}: {player['rating']}{marker}")

print(f"Average: {result['average_rating_a']}")

print("\nSquad B")
for player in result["squad_b"]:
    marker = ""

    if player["id"] == result["goalkeeper_b"]["id"]:
        marker = " (GK)"

    print(f"  {player['name']}: {player['rating']}{marker}")

print(f"Average: {result['average_rating_b']}")

print(f"\nBalance difference: {result['balance_difference']}")
