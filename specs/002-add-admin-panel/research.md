# Research — Football Admin Panel

## Browser entry point and dependencies

**Decision** — Use a separate FastAPI app at `127.0.0.1:8002`, plain browser assets, and an
additive `make admin` command. Package the assets with setuptools using the browser chat
as the local example.

**Rationale** — `web_chat/app.py` starts the local Ollama and MCP runtime in its lifespan.
Admin writes only need PostgreSQL. An independent loopback listener also avoids altering
the existing HTTP API application's routes or the chat's host and origin behavior.

**Alternatives considered** — A route group on the existing football API would couple
admin access to its listener configuration. Adding the routes to the chat service would
couple roster management to agent startup. A frontend framework would add dependencies and
a build step for three forms and lists.

## Local browser boundary

**Decision** — Bind IPv4 loopback with proxy-header handling disabled. Require an actual
loopback peer and canonical Host on every request. Require the same Origin and JSON on
requests that write, including an explicit confirmation body for deletes.

**Rationale** — The current chat already uses a comparable loopback, Host, and Origin
guard. Direct access from the host browser meets the first-release access requirement.
Serve the UI and calls from the same origin. Use text APIs for record data in the UI.

**Alternatives considered** — Network access with accounts expands the first-release
scope. Doing only a network bind would omit the existing project's browser request checks.

## Roster and availability save

**Decision** — Query all players with a left join restricted to the selected fixture.
Represent a missing row as `null` and retain both boolean values. Submit only edited
player IDs and desired booleans. Validate the fixture and unique player IDs, then upsert
the batch by its existing composite key in a single Psycopg transaction.

**Rationale** — `db/init.sql` already enforces one row per fixture and player and requires
a boolean. The existing `get_available_players()` query filters for true. An upsert can
insert a missing status or set an existing one, including when repeating the same desired
values. [PostgreSQL INSERT and conflict handling](https://www.postgresql.org/docs/18/sql-insert.html#SQL-ON-CONFLICT)

**Alternatives considered** — Per-row browser writes can leave a partial save. Replacing
the complete fixture roster risks overwriting rows the coach left untouched. A persisted
draft or a third stored status is unnecessary for this feature.

## Deletes and integrity

**Decision** — In a read-committed transaction, lock the player or fixture row with
`FOR UPDATE`, then query for goalkeeper history in a separate statement. Reject records
with history. Otherwise delete the parent and let the existing foreign key cascade remove
availability. For an availability save, lock the fixture and the referenced players in
stable ID order with `FOR KEY SHARE` before upserting changes in player ID order.

**Rationale** — The existing schema cascades deletes to both availability and goalkeeper
history. The separate history check after acquiring the lock can see history committed
while the deletion was waiting. The row lock conflicts with the key-share lock used by
referencing inserts. Verify this ordering with two connections. This design protects
history on the admin deletion path using the existing schema. [PostgreSQL row locks](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-ROWS),
[PostgreSQL read-committed snapshots](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED)

**Alternatives considered** — Checking history and deleting through separate repository
connections leaves a race. A single conditional delete can use a snapshot taken before
waiting on the parent. Changing the foreign key would require a migration and alter
other database operations.

## Database request limits

**Decision** — Apply connection, statement, and transaction limits only to admin
connections. Use the PostgreSQL 18 baseline already used by Compose and CI.

**Rationale** — The transaction limit bounds a batch across its individual statements.
The statement limit also bounds waits on a lock. [PostgreSQL client timeouts](https://www.postgresql.org/docs/18/runtime-config-client.html#GUC-TRANSACTION-TIMEOUT)

**Alternatives considered** — A browser deadline alone leaves database work running.
Global database defaults would affect existing callers.

## Recovery and verification

**Decision** — Keep pending edits in the page. Confirm before switching fixtures with
pending edits or opening Players or Fixtures from Availability with pending edits.
Preserve inputs on failures and block duplicate submissions while a
request is outstanding. If the client loses the response, fetch the current saved state
before offering a manual retry. For availability, disjoint batches preserve each other's
changes. When two tabs edit the same row, the last committed explicit value wins.

**Rationale** — The host-only, one-coach workflow can use a single transaction and
plain request state. A lost response can occur after a commit. Reading current state
helps the coach distinguish confirmed values and pending edits.

**Alternatives considered** — Automatic retry can duplicate player or fixture creates.
Version columns and client-side draft persistence add state beyond the initial
single-coach workflow. Verification combines deterministic tests and the representative
browser check from the specification.
