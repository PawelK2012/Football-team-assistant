# Quickstart — Validate Football Admin Panel

Run from the repository root after implementation. Use the project's locked Python
environment and a local PostgreSQL 18 server. Admin verification does not require Ollama
or MCP.

## Prepare isolated data and launch

Configure the local PostgreSQL client for the test server. Create a new disposable
database and initialize it with fictional records. The commands stop if the database
already exists.

```sh
createdb football_admin_browser_test &&
  psql -X -v ON_ERROR_STOP=1 -d football_admin_browser_test \
    -f src/football_team_assistant/db/init.sql &&
  psql -X -v ON_ERROR_STOP=1 -d football_admin_browser_test <<'SQL'
BEGIN;
INSERT INTO fixtures (fixture_date, opponent, home)
VALUES (CURRENT_DATE - 7, 'North Test FC', TRUE),
       (CURRENT_DATE + 7, 'South Test FC', FALSE);

INSERT INTO players (name, rating, can_play_goalkeeper)
SELECT 'Test Player ' || lpad(n::text, 2, '0'), 3.5, n <= 4
FROM generate_series(1, 25) AS n;

INSERT INTO availability (fixture_id, player_id, available)
SELECT f.id, p.id, p.name = 'Test Player 01'
FROM fixtures f CROSS JOIN players p
WHERE p.name IN ('Test Player 01', 'Test Player 02');

INSERT INTO goalkeeper_history (fixture_id, player_id)
SELECT f.id, p.id
FROM fixtures f CROSS JOIN players p
WHERE f.opponent = 'North Test FC' AND p.name = 'Test Player 01';
COMMIT;
SQL
```

Set the application's `DATABASE_URL` to this disposable database. If the repository
discovers an `.env` file, its value must point at the same database because the
database module loads it with override enabled. Check the effective connection
before launching.

```sh
uv --config-file ./uv.toml run --locked python -c '
from football_team_assistant.db.database import get_connection

with get_connection() as connection:
    if connection.info.dbname != "football_admin_browser_test":
        raise SystemExit("Point the app at football_admin_browser_test before continuing.")
' && make admin
```

Open `http://127.0.0.1:8002/admin` on the host computer. From another device on the
same private network, opening the page or reaching the admin HTTP routes via the
host's LAN address must fail. HTTP tests verify Host, Origin, and peer checks at the
app boundary.

## Browser scenarios

1. In Players, create a player with rating 3.5 and goalkeeper eligibility enabled.
   View the saved record, edit it, and reload to verify the update. Try invalid names
   and ratings and check that the form retains the inputs.
2. In Fixtures, create and view a fixture, then edit its date, opponent, and Home or
   Away designation. Reload and verify the edited fixture also appears in Availability.
   Verify invalid inputs keep the form populated and leave saved data intact.
3. Select South Test FC. Verify the full roster includes Available, Unavailable, and
   Not recorded. Set Test Player 01 to Unavailable and Test Players 02 and 03 to
   Available. Select Save once. Reload and verify all three changes, all 25 original
   roster entries, and the saved values for North Test FC. Compare the available
   players with the existing `get_available_players()` integration path.
4. Change a status without saving and select the other fixture. Cancel the prompt
   and verify selection and edits are preserved. Repeat and confirm that the other
   fixture opens and the discarded edit never appears in saved data. Make another
   pending edit, select Players, and cancel. Verify the current fixture and edit are
   preserved. Select Fixtures and confirm. Reopen Availability and verify the discarded
   edit is absent from saved data.
5. Check both conflict and failure behavior in the automated suite. In the browser,
   interrupt a save response with DevTools or stop the test service during a request.
   Verify pending values stay visible, saved status is not assumed, and the panel reloads
   saved data before offering a manual retry after recovery.
6. Verify player and fixture deletion with records you created for this browser test.
   Add availability for them first. Confirm that cancel preserves the parent and
   availability, then confirm each delete and check that both are removed. Attempt to
   delete Test Player 01 and North Test FC. Both are protected by goalkeeper history.
7. At 360 and 1280 pixels, complete a player edit, a fixture edit, and an availability
   save with the keyboard. Verify visible focus, readable status text, and no
   horizontal page scrolling. Ask a first-time user to find all three pages and
   explain Unavailable and Not recorded.

## Performance verification

Run scenario 3 with the initial 25 players and two fixtures on a local workstation,
with local PostgreSQL and browser throttling disabled. Measure from selecting the
fixture to verifying the three edits after one Save action and a reload. The run must
finish within 60 seconds. Record workstation, OS, browser, viewport, elapsed time,
row count, and fixture isolation. Run before adding extra fixture or player records
and before deleting seeded records.

## Automated verification

Initialize the separate `football_assistant_test` database using the CI setup in
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), then run:

```sh
uv --config-file ./uv.toml run --locked pytest -v \
  tests/test_admin_service.py tests/api tests/integration/test_admin_operations.py
uv --config-file ./uv.toml run --locked pytest -v
uv --config-file ./uv.toml run --locked ruff check .
uv --config-file ./uv.toml run --locked ruff format --check .
```

Verify that malformed inputs, stale IDs and forced mid-batch failures leave saved
statuses intact. Check two saves for the same player and fixture and verify that the
final status comes from the last commit. Exercise both orderings of a save racing
with deletion. When deletion takes effect first, verify that the entire save is
rejected. When the save commits first, verify that the subsequent deletion removes
the linked availability. Check repeated saves, concurrent history insertion versus
deletion, and existing HTTP and lookup behavior. Verify the built wheel contains all three
admin assets and the installed app serves them outside the checkout. The
[browser contract](contracts/browser-admin.md) defines the expected requests and responses.

## Validation results · 2026-11-28

- The full suite passed 151 tests against disposable PostgreSQL 18.6. The
  integration suite covered batch rollback, repeated saves, fixture isolation,
  both orderings of concurrent deletion and save, and a lost commit acknowledgment.
- Headless Chrome 158 on macOS 26.7.3 (arm64) passed scripted player and fixture
  CRUD, keyboard submission with visible focus, and availability saves at 360 and
  1280 pixels without horizontal scrolling. Confirm and cancel were exercised for
  fixture and page changes. The recovery checks covered retained overlong input,
  explicit review before retrying a create with a lost response, and stale roster
  protection after consecutive fixture read failures.
- With 25 players and two fixtures, the scripted three-player save and reload
  took 134 ms at 1280 × 740 in an unthrottled local browser. All 25 players were
  present after reload and the other fixture retained its original statuses.
- Ruff lint and formatting, targeted Python type checking, and JavaScript syntax
  checking passed. The built wheel contained the three admin assets and the
  unpacked app served them outside the source checkout.
- Host, Origin, and remote peer rejection are covered by HTTP tests. A separate
  physical-device attempt and a first-use walkthrough with a coach remain
  unverified.
