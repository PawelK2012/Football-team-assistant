import re


# todo - it's a duplicate of the same function in agent class
def extract_explicit_fixture_id(question: str) -> int | None:
    match = re.search(
        r"\bfixture\s*(?:id\s*)?#?\s*(\d+)\b",
        question,
        flags=re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def resolve_fixture(
    question: str,
    fixtures: list[dict],
    current_fixture_id: int | None = None,
) -> int | None:
    explicit_id = extract_explicit_fixture_id(question)

    if explicit_id is not None:
        if not any(f["id"] == explicit_id for f in fixtures):
            raise ValueError(f"Fixture {explicit_id} does not exist.")
        return explicit_id

    question_lower = question.casefold()

    # Match known opponents, preferring longer names.
    matches = [fixture for fixture in fixtures if fixture["opponent"].casefold() in question_lower]

    # Also allow short names, such as "Verona".
    if not matches:
        for fixture in fixtures:
            opponent = fixture["opponent"].casefold()
            words = opponent.split()

            if not words:
                continue

            first_word = words[0]

            if len(first_word) < 4:
                continue

            pattern = r"(?<!\w)" + re.escape(first_word) + r"(?!\w)"

            if re.search(pattern, question_lower):
                matches.append(fixture)

    if matches:
        unique_ids = {fixture["id"] for fixture in matches}

        if len(unique_ids) > 1:
            descriptions = ", ".join(
                f"{fixture['id']}: {fixture['opponent']} ({fixture['date']})" for fixture in matches
            )
            raise ValueError(
                f"Multiple fixtures match. Please specify a fixture ID: {descriptions}"
            )

        return matches[0]["id"]

    return current_fixture_id
