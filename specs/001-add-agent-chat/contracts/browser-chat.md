# Browser Chat Contract

All routes below belong to the new loopback app. The canonical origin is
`http://127.0.0.1:8001`. Require a loopback peer and the canonical Host for the page, assets,
and requests. For conversation writes, require the canonical Origin as well. Accept
`application/json` on the turn endpoint and send chat responses with `Cache-Control: no-store`.
No CORS access is enabled. Conversation IDs stay in page memory and are omitted from logs.

| Method and path | Successful response |
| --- | --- |
| `GET /chat` | `200` chat page with same-origin CSS and JavaScript. |
| `POST /chat/conversations` | Send an empty body. A `201` with `{"conversation_id":"<server-issued ID>"}` creates an independent conversation. |
| `POST /chat/conversations/{conversation_id}/turns` | `200` with `{"request_id":"<request ID>","reply":"<assistant text>"}`. |
| `DELETE /chat/conversations/{conversation_id}` | Send an empty body. A `204` releases the conversation and cancels any pending turn. Unknown or released IDs return the same status. |

A turn request has the form `{"request_id":"<UUID>","message":"Who is available for Example FC?"}`.
Trim surrounding whitespace before dispatch and comparison. Reject blank text and malformed
fields. Reject overlapping turns while one is pending. Once a turn succeeds, an identical
retry of that last successful request returns the same reply. Reusing the retained ID with
different text returns `invalid_request`. Failed turns release their request ID for retry.

Errors from the chat endpoints have the form
`{"error":{"code":"agent_unavailable","message":"The football agent is unavailable. Try again."}}`.

| HTTP status | Error code | Browser behavior |
| --- | --- | --- |
| `400` | `invalid_request` | Explain that a valid message is required. |
| `403` | `access_denied` | Deny access before dispatching any turn. |
| `404` | `conversation_missing` | Keep the displayed transcript and failed question in the open tab. Explain that the agent lost the previous fixture context and offer to start fresh before resending. |
| `409` | `turn_pending` | Keep the message available to retry. |
| `415` | `unsupported_content_type` | Report a request error without dispatching a turn. |
| `503` | `agent_unavailable` | Clear pending feedback and keep the message available to retry. An unavailable MCP runtime may require restarting the chat service. |
| `504` | `turn_timeout` | Clear pending feedback and keep the message available to retry. |

Return the stated error envelope for request validation and application failures. Keep
conversation IDs, internal exception details, request text, and transcript content out
of error response bodies, including the human-readable message.

The client shows the coach's message and announces pending feedback before sending. During
the turn it disables further sends. On a transport error or an absent turn response after
95 seconds, it clears pending feedback and offers manual retry of the same request ID without
adding a duplicate coach message. The server enforces a 90-second deadline for the agent
turn. Conversation creation has a separate 10-second browser deadline. Chat output is
displayed as text, including agent clarification questions and markup-like strings.
If a question matches multiple fixtures, return the agent's clarification in the regular
`200` turn response and preserve the prior fixture context.

The page sends a same-origin keepalive DELETE on `pagehide` if it has a conversation ID.
It ignores outstanding callbacks after page exit and starts fresh on a back-forward cache
restore. A release notification is best effort.
