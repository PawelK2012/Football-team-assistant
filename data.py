PLAYERS = [
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


FIXTURES = [
    {
        "id": 1,
        "date": "2026-10-11",
        "opponent": "Dunboyne AFC",
        "home": False,
    },
    {
        "id": 2,
        "date": "2026-10-18",
        "opponent": "Raheny United",
        "home": True,
    },
]


AVAILABILITY = [
    # Dunboyne
    {"fixture_id": 1, "player_id": 1, "available": True},
    {"fixture_id": 1, "player_id": 2, "available": True},
    {"fixture_id": 1, "player_id": 3, "available": True},
    {"fixture_id": 1, "player_id": 4, "available": True},
    {"fixture_id": 1, "player_id": 5, "available": True},
    {"fixture_id": 1, "player_id": 6, "available": True},
    {"fixture_id": 1, "player_id": 7, "available": True},
    {"fixture_id": 1, "player_id": 8, "available": True},
    {"fixture_id": 1, "player_id": 9, "available": True},
    {"fixture_id": 1, "player_id": 10, "available": True},
    {"fixture_id": 1, "player_id": 11, "available": True},
    {"fixture_id": 1, "player_id": 12, "available": True},
    {"fixture_id": 1, "player_id": 13, "available": True},

    # Raheny
    {"fixture_id": 2, "player_id": 1, "available": True},
    {"fixture_id": 2, "player_id": 2, "available": False},
    {"fixture_id": 2, "player_id": 3, "available": True},
    {"fixture_id": 2, "player_id": 4, "available": True},
    {"fixture_id": 2, "player_id": 5, "available": False},
    {"fixture_id": 2, "player_id": 6, "available": True},
    {"fixture_id": 2, "player_id": 7, "available": True},
    {"fixture_id": 2, "player_id": 8, "available": True},
    {"fixture_id": 2, "player_id": 9, "available": True},
    {"fixture_id": 2, "player_id": 10, "available": True},
    {"fixture_id": 2, "player_id": 11, "available": True},
    {"fixture_id": 2, "player_id": 12, "available": True},
    {"fixture_id": 2, "player_id": 13, "available": True},
]


GOALKEEPER_HISTORY = [
    {
        "fixture_id": 101,
        "date": "2026-09-20",
        "player_id": 1,
    },
    {
        "fixture_id": 101,
        "date": "2026-09-20",
        "player_id": 4,
    },
    {
        "fixture_id": 102,
        "date": "2026-09-27",
        "player_id": 2,
    },
    {
        "fixture_id": 102,
        "date": "2026-09-27",
        "player_id": 5,
    },
]