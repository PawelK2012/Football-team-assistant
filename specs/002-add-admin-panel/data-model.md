# Data Model — Football Admin Panel

The models use the existing tables in
[`db/init.sql`](../../src/football_team_assistant/db/init.sql). Apply the existing schema
to test databases. Existing application databases require no migration.

## Player

| Field | Rules |
| --- | --- |
| `id` | Database-generated positive integer. Stable across edits. |
| `name` | Trim surrounding whitespace. Require 1–100 characters after trimming. Names may repeat. |
| `rating` | Numeric value from 1.0 through 6.0 in increments of 0.5. Validate before writing so the database cannot round an invalid input to a valid value. |
| `can_play_goalkeeper` | Boolean. Defaults to false on creation. |

A player can have availability and goalkeeper history records for many fixtures.
Editing the player preserves both relationships. The roster shows stable IDs where
names would otherwise be ambiguous.

## Fixture

| Field | Rules |
| --- | --- |
| `id` | Database-generated positive integer. Stable across edits. |
| `date` | Calendar date in ISO `YYYY-MM-DD` form, stored as `fixture_date`. |
| `opponent` | Trim surrounding whitespace. Require 1–150 characters after trimming. |
| `home` | Required boolean. True means Home and false means Away. |

Past and upcoming fixtures share the same lifecycle. Opponent, date, and designation
can repeat. Use the fixture ID to distinguish otherwise-identical selector entries.
Editing a fixture preserves its existing availability and goalkeeper history.

## Availability

| Field | Rules |
| --- | --- |
| `fixture_id` | References a fixture. |
| `player_id` | References a player. |
| `available` | Required boolean for an existing record. The pair of IDs forms its unique key. |

| Saved state | Representation | Coach action |
| --- | --- | --- |
| Not recorded | No database row. Admin read returns `null`. | May set Available or Unavailable. |
| Available | Database row with `true`. | May leave it or set Unavailable. |
| Unavailable | Database row with `false`. | May leave it or set Available. |

The coach can undo a pending edit before saving. An explicit status stays recorded
after save. Only `true` feeds the agent's available-player lookup. The browser keeps
pending changes separately from confirmed values. A save submits a nonempty set of
unique player IDs and desired booleans for one fixture. The repository commits
the changed rows together and leaves unsubmitted rows outside the write. When two
batches commit changes for the same pair, the later commit determines the saved
status. If a referenced record is deleted first, the save is rejected in full. If
the save commits first, a subsequent permitted deletion removes its associated
availability.

## Goalkeeper history and deletion

A history row references one fixture and one player. The panel reads whether history
exists when processing a deletion and has no operation for writing history.

A delete requires explicit confirmation for an individual record. In the deletion
transaction, lock that record, check for history, and reject deletion if a linked
history row exists. On permitted deletion, the existing cascade removes associated
availability in the same transaction. A history rejection preserves the parent and
all linked records. A missing parent is reported separately.
