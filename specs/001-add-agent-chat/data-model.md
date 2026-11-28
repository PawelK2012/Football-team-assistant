# Data Model — Football Agent Web Chat

## Conversation

One loaded chat page owns one browser conversation. The page obtains an unpredictable,
opaque server-issued ID at startup and keeps it in memory. Server state consists of the ID, one `FootballAgent`
instance, the current in-flight request if any, and the most recent successful request and
reply for replay after an interrupted response.

- The browser transcript holds visible messages. The agent owns its model and tool history
  and selected fixture. Tool records and selected fixture IDs are never accepted as conversation
  state from the browser.
- A conversation moves from ready to pending when a valid turn is admitted. Only one turn can
  enter pending. Admission and the rollback or commit of the turn are exclusive.
- On success, keep the updated agent state and response. On error, empty reply, or cancellation,
  truncate the agent history to its previous length and restore the selected fixture before
  releasing the pending turn. The page keeps the failed text and previously completed messages.
- On reload, restore from the back-forward cache, or in a separate tab, create a new ID with
  empty context. Invalidate stale callbacks on page exit. A delivered release removes the
  registry entry and cancels any pending turn. A late completion cannot recreate the entry
  or publish a reply. An undelivered release can leave unreachable state in process memory
  until shutdown, when the application clears all conversations.
- If process restart invalidates an open page's ID, report that context was lost. Keep the old
  transcript visible and require the coach to start fresh context before resending. The new
  agent starts with empty context.

## Turn and visible messages

A turn contains a browser-generated UUID, the coach's trimmed nonblank text, and either
a nonblank assistant reply or a failure. The browser renders each message as plain text, with
line breaks and distinct coach and assistant labels. Failed turns can be retried without
retyping. The retry of the current failed or unconfirmed turn keeps its UUID, while a new
turn uses a fresh UUID. The successful replay record holds only the most recent successful
UUID, normalized input, and reply. An identical retry of that ID returns its cached reply.

The browser does not persist transcripts in cookies, browser storage, or the database.
Football fixtures, availability, ratings, and goalkeeper history continue to come from the
agent's existing MCP tools.
