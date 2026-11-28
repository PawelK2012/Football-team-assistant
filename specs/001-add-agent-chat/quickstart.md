# Quickstart — Validate Football Agent Web Chat

Run this guide after implementation, from the repository root.

## Prerequisites and launch

Use the repository's locked Python environment and local Ollama with `qwen3:8b`.
For the live checks, create an empty PostgreSQL database named `football_chat_test`.
Configure the local PostgreSQL client credentials and set the application's `DATABASE_URL`
to the same test database. The repository loads `.env` with override enabled, so any
`.env` the subprocess discovers must also target this test database.

```sh
createdb football_chat_test &&
  psql -X -v ON_ERROR_STOP=1 -d football_chat_test \
    -f src/football_team_assistant/db/init.sql &&
  psql -X -v ON_ERROR_STOP=1 -d football_chat_test <<'SQL'
BEGIN;
INSERT INTO fixtures (fixture_date, opponent, home) VALUES
    (CURRENT_DATE + 1, 'North Test FC', TRUE),
    (CURRENT_DATE + 2, 'South Test FC', FALSE),
    (CURRENT_DATE - 7, 'Past Test FC', TRUE);
INSERT INTO players (name, rating, can_play_goalkeeper)
SELECT 'Test Player ' || n, 2 + (n % 7) * 0.5, n <= 4
FROM generate_series(1, 16) AS n;
INSERT INTO availability (fixture_id, player_id, available)
SELECT f.id, p.id, TRUE
FROM fixtures f CROSS JOIN players p
WHERE f.opponent = 'North Test FC'
   OR (f.opponent = 'South Test FC' AND p.id <= 10);
INSERT INTO goalkeeper_history (fixture_id, player_id)
SELECT f.id, p.id FROM fixtures f CROSS JOIN players p
WHERE f.opponent = 'Past Test FC' AND p.name IN ('Test Player 1', 'Test Player 2');
COMMIT;
SQL
```

From the repository root, check the effective application configuration before starting the app.

```sh
uv run --locked python -c '
from football_team_assistant.db.database import get_connection

with get_connection() as connection:
    if connection.info.dbname != "football_chat_test":
        raise SystemExit("Point the application at football_chat_test before continuing.")
'
```

Once that check succeeds, start the app.

```sh
make webapp
```

Open `http://127.0.0.1:8001/chat` on the same computer. From a different device on the same
private network, try the host computer's LAN address on port 8001. Both page and chat
requests should be unreachable. Check separately that the existing HTTP app still works
through its own entry point. For the chat boundary, a local `GET /chat` returns the page,
and a `POST /chat/conversations` with `Origin: http://127.0.0.1:8001` returns 201.
Requests sent to the host's LAN address from the other device should fail to connect.

## Acceptance checks

1. Ask “Which fixtures are upcoming?”, then “Who is available for North Test FC?” and
   “Create squads for that game.” The availability reply should list 16 players. Verify
   that the squads use that fixture, include each of its 16 players once, and include an
   eligible goalkeeper per squad.
2. In a second tab, ask about availability for South Test FC. Verify that squad follow-ups
   use the intended fixture in each tab, with 16 players for North and 10 for South. With
   both fixtures upcoming, ask “Who is available?” from a fresh tab and verify the agent
   displays a clarification question. In the North tab, ask “Who is available for North
   Test FC or South Test FC?” and check that the clarification lists the matches. Ask for
   squads “for that game” again and verify the prior North selection is still in use.
3. At browser widths of 360 and 1280 pixels, send a message and read the reply without
   horizontal scrolling. Use only the keyboard for a complete send-and-read flow. Check
   visible focus, the role label on each message, and readable wrapped output. Use a screen
   reader to confirm the pending notice is announced when a reply is outstanding.
4. Stop the live chat process and launch the test app below. Start with a successful
   exchange, then send `Simulate unavailable` and `Simulate timeout`, retrying each after
   its first failure. Confirm pending clears, an actionable message appears, and retry
   succeeds without retyping or duplicating the coach message. Earlier messages and their
   context remain available. Verify blank and duplicate sends are ignored and markup-like
   replies remain visible as text. Repeat the recovery at both viewport widths using only
   the keyboard. Check visible focus on the retry control and confirm the screen reader
   announces each error and the return to pending on retry.
5. With a delayed test reply pending, reload and verify that the new page starts empty and
   the old reply never appears. Navigate away and use Back to check that a restored page
   starts fresh as well. Switching tabs without navigating away should preserve each
   tab's transcript.
6. After a failed reply, stop the test app and rerun the same launch command below with
   the tab still open. At both viewport
   widths, use the keyboard to recover and check that the earlier transcript and failed
   question remain visible. Confirm the screen reader announces the context loss before
   resending. Tab to the control for starting fresh and verify its focus indicator is
   visible. Resend and confirm the reply uses only the new agent context.

```sh
uv run --locked uvicorn tests.api.test_web_chat:browser_test_app --factory \
  --host 127.0.0.1 --port 8001 --workers 1 --no-proxy-headers --no-access-log
```

## Performance checks

Use a representative local workstation with no CPU or network throttling. Record OS, CPU,
browser version, viewport, and the elapsed time in milliseconds for each prompt. In Chrome
DevTools Performance, enable screenshots and measure from the submit interaction to the
first captured frame showing pending feedback.

Run the three prompts in check 1 in a fresh test-app tab six times, then run the first two
prompts once more for 20 samples. Wait for each reply before submitting the next prompt.
The test app delays ordinary replies by at least 500 ms. At least 19 submissions must show
pending feedback within 250 ms.

Record end-to-end times separately against the live app for a cold first fixture turn and
warm fixture lookup, availability, and 16-player squad generation. Verify the server timeout
with `Simulate timeout` and the browser fallback with `Simulate missing response`, which
delays the HTTP response beyond the shortened client deadline on its first attempt.
Cross-check the production defaults of 90 seconds on the server and 95 in the browser.

## Regression checks

```sh
uv run --locked pytest -v tests/api tests/test_football_agent.py tests/test_squad_optimizer.py
uv run --locked ruff check .
uv run --locked ruff format --check .
```

Run `uv run --locked pytest -v` with the repository's isolated
`football_assistant_test` database initialized, as in `.github/workflows/ci.yml`.
The chat HTTP tests should cover access guards, input validation, retry and replay,
concurrent turns within and across tabs, release during a pending turn, and shutdown cleanup.
Check exact MCP tool arguments across the fixture follow-up. See the
[browser contract](contracts/browser-chat.md) for response and payload expectations.

## Validation results · 2026-11-28

- Headless Chrome 158.0.8127.89 on macOS 26.7.3, Apple M4 Max, passed keyboard and
  overflow checks at 360 and 1280 pixels. Verified tab isolation, literal markup,
  retry after unavailable and timed-out replies, the browser response deadline, restart
  recovery, and fresh context after reload or Back. Chrome's accessibility tree exposed
  pending feedback as a polite live region and errors and restart notices as assertive.
- On the same workstation at 1280 × 740, without throttling, all 20 submissions showed
  pending feedback within 250 ms. Chrome's captured frames were measured from submission
  to the first frame containing the pending text.

| Prompt | First visible pending frame in ms |
| --- | --- |
| Which fixtures are upcoming? | 30, 4, 16, 6, 30, 5, 27 |
| Who is available for North Test FC? | 21, 2, 27, 5, 29, 4, 26 |
| Create squads for that game | 1, 4, 26, 3, 27, 14 |

- Live HTTP checks used the installed wheel, local `qwen3:8b`, and an isolated,
  seeded PostgreSQL instance through the existing MCP server. The cold first lookup
  took 9.69 s and returned the earliest upcoming fixture. Warm fixture lookups took
  17.92 s and 11.68 s. North and South availability took 6.50 s and 10.96 s, respectively.
  The 16-player North squad reply took 3.55 s, and the 10-player South squad reply took
  6.01 s. Both included the expected fixture, every available player once, and two
  eligible goalkeepers. The North selection was preserved after a multiple-match
  clarification. The next North squad reply took 5.39 s.
- The HTTP boundary tests rejected a non-loopback peer. A live connection attempt via
  the workstation's non-loopback IPv4 address failed for both routes. A separate physical
  device and audible announcements in a native screen reader remain unverified.
- The complete pytest suite passed 108 tests against a disposable PostgreSQL instance.
  Ruff lint and format checks passed. The built wheel contained all three assets and the
  installed app located them outside the source checkout.
