# Contract — Browser Admin Panel

Canonical origin is `http://127.0.0.1:8002`. The admin listener accepts loopback peers
with exactly one Host value of `127.0.0.1:8002`. Writes require exactly one matching
Origin and an `application/json` body. Admin responses use `Cache-Control: no-store`.
The listener does not trust forwarded headers or serve cross-origin requests.

## Browser pages

| URL | Expected view |
| --- | --- |
| `/admin` | Redirects to `/admin/players`. |
| `/admin/players` | Full player list, create and edit forms, and delete confirmation. |
| `/admin/fixtures` | Past and upcoming fixture list, create and edit forms, and delete confirmation. |
| `/admin/availability` | Fixture selector, full roster, status controls, and one Save action for the selected fixture. |

Provide direct links, visible keyboard focus, and clear loading, empty, saved, and failed
states. Render record text literally. Use the reference's charcoal panels, thin borders,
and light primary buttons. At narrow widths, keep controls and reading order usable
without horizontal page scrolling.

Availability shows the roster before selection and disables editing until a fixture is
selected. The selector includes opponent, date, and Home or Away. Add the fixture ID
where these labels collide. Show saved statuses separately from pending edits. Allow
the coach to undo a pending row edit. Ask for confirmation before switching fixtures or
opening Players or Fixtures from Availability while edits are pending. Cancel keeps the
current page, fixture, and pending edits. Confirm discards the edits before opening the
chosen fixture or page. Ignore outdated responses when the fixture selection changes.

## Admin JSON endpoints

All paths in this table are under `/admin/api` and belong to the separate admin app.

| Method and path | Request | Success |
| --- | --- | --- |
| `GET /players` | — | 200, array of player records |
| `POST /players` | Player fields | 201, saved player |
| `PUT /players/{player_id}` | Player fields, including goalkeeper eligibility | 200, saved player |
| `POST /players/{player_id}/delete` | `{"confirmed": true}` | 204, empty body |
| `GET /fixtures` | — | 200, array of fixture records |
| `POST /fixtures` | Fixture fields | 201, saved fixture |
| `PUT /fixtures/{fixture_id}` | Fixture fields | 200, saved fixture |
| `POST /fixtures/{fixture_id}/delete` | `{"confirmed": true}` | 204, empty body |
| `GET /fixtures/{fixture_id}/availability` | — | 200, `{"fixture_id": 8, "players": [...]}` |
| `PUT /fixtures/{fixture_id}/availability` | A nonempty array in `changes` | 200, `{"fixture_id": 8, "changes": [...]}` with committed rows |

Player fields are `name`, numeric `rating`, and boolean `can_play_goalkeeper`
(optional only for creation). Fixture fields are `date`, `opponent`, and boolean
`home`. Saved records add their generated `id`. Lists include the fields required for
viewing and editing, and empty lists return `[]`. Use name then ID order for players,
and date then ID order for fixtures.

An availability roster item contains `player_id`, `name`, and `available` as
`true`, `false`, or `null`. An availability save accepts and returns changes in the
following shape, with boolean values only. The fixture ID in the URL scopes the batch.

```json
{
  "changes": [
    {"player_id": 2, "available": true},
    {"player_id": 5, "available": false}
  ]
}
```

Validate the whole request before writing. Reject repeated player IDs. A batch with a
missing fixture or referenced player returns `record_missing` without applying any of
its changes. A complete batch commits together. When two successful batches affect
the same player and fixture, the last batch to commit determines that status. A
permitted deletion that takes effect after a save removes the corresponding linked
availability. The save response confirms the rows written by that batch and leaves
unsubmitted statuses intact. The browser asks the coach to confirm
deletion by record, naming it and stating what happens to linked availability before
sending the delete action.

## Failures and recovery

Failures return `{"error":{"code":"...","message":"..."}}`. Field validation can include
`error.fields`, a mapping from field names or indexed change paths to messages.

| Status | Code | Browser behavior |
| --- | --- | --- |
| 403 | `access_denied` | Explain that the panel is available at the canonical address on the host computer. |
| 404 | `record_missing` | Identify the missing player or fixture, keep pending inputs, and offer to reload the affected list. |
| 409 | `goalkeeper_history_exists` | Explain that the record is protected and retain it in the list. |
| 415 | `unsupported_content_type` | Explain that the request format was rejected. |
| 422 | `invalid_request` | Show validation feedback and keep the entered values. |
| 503 | `storage_unavailable` | Keep pending changes and show a retryable storage failure when rollback or lack of execution is known. |
| 503 | `outcome_unknown` | Keep the entered values and reload saved data before offering a manual retry. |

Treat a lost response or a write request that times out in the browser as an unknown
outcome. Avoid automatic mutation retries. Disable repeated submission while a save
is pending. Reload saved values before offering retry of an unknown outcome. For an
unknown create, show the current list and let the coach check whether the record exists
before allowing a new submission.

The existing football HTTP app and the MCP server keep their endpoints, input and
output shapes, and error behavior. Their read results reflect the records the coach
saves to the shared database.
