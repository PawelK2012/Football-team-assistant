# Feature Specification: Football Agent Web Chat

**Feature Branch**: `introduced-chat-ui`

**Created**: 2026-11-28

**Status**: Draft

**Input**: A simple, modern browser chat for the existing football agent. Keep dependencies
minimal, require approval for changes to existing APIs, and leave room for later sign-in and
player and fixture administration.

## Clarifications

### Session 2026-11-28

- Q: Should the first release be accessible only on the computer running the agent, or also from a phone on the same private network? → A: Host computer only. Verify the mobile layout using a narrow browser viewport.
- Q: If the browser closes unexpectedly, how long may the app keep that chat’s context in memory? → A: If the page-exit notification is missed, the app may keep the context in memory until shutdown. A new page cannot access it.
- Q: If the chat service must restart after the football agent fails, what should the coach keep in the tab they already have open? → A: Keep the visible transcript and failed question. Tell the coach that resending starts with fresh fixture context.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask the football agent in a browser (Priority: P1)

A coach opens the chat in a browser on the computer running the agent, asks a football
question, and reads the agent's answer in the conversation.

**Why this priority** — Browser access is the primary feature.

**Independent Test** — Open the chat, ask which fixtures are upcoming, and verify that the
agent's reply appears below the question in a readable conversation.

**Acceptance Scenarios**

1. **Given** the chat is open, **when** the coach types a question and sends it,
   **then** the question appears, the chat shows that a reply is pending, and the agent's
   reply appears under the question when available.
2. **Given** a narrow or desktop viewport on the host computer, **when** the coach uses the chat,
   **then** messages are readable and the message field and send control remain usable
   without horizontal scrolling. On a keyboard, the coach can reach and use both controls.
3. **Given** the chat is running with the first-release configuration, **when** another device
   on the same private network attempts to open the chat or submit a chat request,
   **then** it cannot access the chat.

### User Story 2 - Ask a follow-up in the same conversation (Priority: P2)

A coach can refer to a fixture already discussed in the chat without retyping its name.

**Why this priority** — Follow-ups preserve the existing agent's conversational behavior in
the browser.

**Independent Test** — Ask who is available for a known fixture, then send “Create squads
for that game” and verify the reply refers to the same fixture.

**Acceptance Scenarios**

1. **Given** a completed exchange that identifies a fixture, **when** the coach asks a
   follow-up about that game, **then** the agent can use the earlier fixture context.
2. **Given** two independent chat tabs, **when** the coach discusses different fixtures in
   each, **then** each tab shows and uses only its own conversation.

### User Story 3 - Recover from a failed reply (Priority: P3)

A coach can see when the agent is unavailable or a request times out and can send the failed
message again.

**Why this priority** — A stalled exchange should leave the coach with a clear next action.

**Independent Test** — Simulate a failed reply after a successful exchange, then verify that
the earlier exchange is still visible and the failed text is available to retry.

**Acceptance Scenarios**

1. **Given** the coach has sent a question, **when** the agent is unavailable or the wait
   limit is reached, **then** the pending state clears, a plain-language error appears, and
   the coach can resend the failed text.
2. **Given** a failed exchange after an earlier successful exchange, **when** the coach tries
   again, **then** the earlier messages remain visible and a new reply can be received.
3. **Given** the chat service restarts after a failed reply and the tab stays open,
   **when** the coach returns to the conversation, **then** the transcript and failed
   question are still available. Before resending, the coach is told that the agent
   will start with fresh fixture context.

### Edge Cases

- Empty or whitespace-only text produces no message or request.
- Repeated send attempts while a reply is pending produce one submission.
- An ambiguous fixture question displays the existing agent's clarification as a normal
  reply.
- Long messages wrap within the conversation. Message content appears as inert content,
  including text that resembles markup or code.
- Refreshing the page starts a fresh conversation. A late reply from an earlier conversation
  cannot appear in the new one.
- If the browser closes without notifying the app, reopening the chat starts a fresh
  conversation. The service clears any remaining agent context when it shuts down.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The browser chat MUST provide a conversation view, a labeled message field,
  and a send control. It MUST reject blank submissions and allow one pending reply per
  conversation.
- **FR-002**: The chat MUST send questions through the existing football agent and display
  the agent's replies, including clarification questions. It MUST show messages in order,
  visually distinguish coach and assistant messages, and render message content safely.
- **FR-003**: The chat MUST retain the visible transcript across turns in the current page
  and preserve usable agent context while the conversation remains active. Independent
  tabs and fresh page loads MUST start with separate context.
  The app MUST discard the old conversation when it receives a page-exit notification.
  If the notification is missed, the old context may remain in memory until shutdown.
  A new page MUST be unable to access it.
- **FR-004**: The chat MUST show a pending state immediately after submission. Unavailable
  or timed-out replies MUST clear that state, explain the failure in plain language, and
  leave the failed message available to resend. The wait MUST have a defined upper bound.
  After a service restart, an open tab MUST retain the visible transcript and failed
  question. Before the coach resends it, the chat MUST explain that the agent has lost
  the previous fixture context and that the retry starts with fresh context.
- **FR-005**: The chat MUST use a focused, responsive layout with readable typography,
  distinguishable message roles, and clear pending, error, and keyboard focus states.
  The message field and controls for sending, retrying, and starting fresh after a
  restart MUST be operable by keyboard with visible focus. The chat MUST announce pending
  feedback, errors, and the fresh-context notice to assistive technology.

### Scope and Compatibility Constraints

- The first release is a single chat screen. The chat page and chat request entry point MUST
  be reachable only from the computer running the agent. Sign-in, account management, player
  and fixture administration, and saved chat history are future work.
- Existing API contracts and behavior MUST be preserved. If planning identifies a necessary
  change to an existing API, the maintainer MUST be asked for approval before that change is
  made. A separate browser chat entry point may be proposed in the plan.
- Planning MUST favor existing project capabilities and justify any new framework as necessary
  for this release. The chat MUST avoid dependencies on future sign-in or administration
  features so those capabilities can be added separately.

### Key Entities *(include if feature involves data)*

- **Conversation** — An ordered exchange in one open chat page, with context for follow-ups.
- **Message** — A coach question or assistant reply associated with a conversation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In scripted checks for fixture lookup, player availability, and a follow-up squad
  request, all three requests display an agent reply and the follow-up uses the fixture
  already discussed.
- **SC-002**: In a browser on the host computer at viewport widths of 360 and 1280 pixels,
  a coach can read the transcript, submit a question, and read the reply without horizontal
  scrolling. With the keyboard alone and visible focus, the coach can send a question,
  retry a failed reply, and start fresh after a service restart before resending. In these
  flows, a screen reader announces pending feedback, errors, and the fresh-context notice
  as they appear.
- **SC-003**: On a representative local workstation, at least 19 of 20 valid submissions show
  pending feedback within 250 ms while the reply is outstanding. The plan records the
  browser, workstation, and representative prompts used for verification.
- **SC-004**: In both simulated failure cases, agent unavailable and reply timeout, the coach
  sees a clear error, retains earlier messages, and can resend the failed question without
  retyping it.

## Assumptions

- The initial user is a coach with browser access to the computer running the existing
  football agent. The first release uses a narrow browser viewport to verify the mobile layout.
- A text transcript with one reply at a time is sufficient. The visible transcript starts
  empty on reload or when the chat is reopened.
