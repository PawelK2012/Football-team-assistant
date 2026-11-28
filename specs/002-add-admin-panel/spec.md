# Feature Specification — Football Admin Panel

**Feature Branch** — `add-admin-panel`

**Created** — 2026-11-28

**Status** — Draft

**Input** — A simple browser admin panel for creating, viewing, editing, and deleting
players and fixtures, with a dedicated page to record each player's availability for a
selected fixture. Use the attached dark UI reference as visual direction.

## Clarifications

### Session 2026-11-28

- Q: When marking availability for several players in one fixture, how should the coach save those changes? → A: Edit several players’ statuses and save the changes together for the selected fixture.
- Q: If the coach leaves Availability for Players or Fixtures with unsaved changes, should the panel ask before discarding them? → A: Ask before discarding. Cancel keeps the coach on Availability with their edits.
- Q: If the coach edits the same player’s availability for the same fixture in two browser tabs, and the tabs save different statuses, what should the panel do? → A: Keep the status from the last successful save.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record availability for a fixture (Priority: P1)

A coach opens Availability, chooses a fixture, and sees the entire player roster and
each player's saved status for that match. The coach records who can play so the
football agent has an accurate list for squad selection.

**Why this priority** — Fixture availability is the coach's recurring match preparation task.

**Independent Test** — Using two existing fixtures and a seeded roster, change two
players' statuses for one fixture, save once, reload, then switch fixtures and check
the saved statuses.

**Acceptance Scenarios**

1. **Given** a fixture and a roster containing players with available, unavailable,
   and unrecorded statuses, **when** the coach selects that fixture, **then** every
   player is listed and each row shows the correct status in text.
2. **Given** a selected fixture, **when** the coach sets one player to Available,
   another to Unavailable, and selects Save once, **then** both statuses persist on
   reload and the agent's availability lookup includes only the player marked Available
   among those two. Both players remain visible on the Availability page.
3. **Given** two identifiable fixtures, **when** the coach saves changes for the first
   and selects the second, **then** the second shows its own saved statuses and any
   players left untouched in the first retain their saved statuses.
4. **Given** unsaved changes for one fixture, **when** the coach tries to select another,
   **then** the panel asks whether to discard those changes. Cancel keeps the current
   fixture and its pending edits. Confirm discards the edits and opens the other fixture.
5. **Given** pending edits for several players, **when** one edit cannot be saved,
   **then** none of the submitted changes take effect, the panel explains the failure,
   and the pending edits remain visible so the coach can correct them or retry.
6. **Given** unsaved changes on Availability, **when** the coach selects Players or
   Fixtures in the panel, **then** the panel asks whether to discard the changes.
   Cancel keeps the coach on Availability with the same fixture and edits. Confirm
   discards the edits and opens the chosen page.
7. **Given** two tabs with different pending statuses for the same player and fixture,
   **when** both saves succeed, **then** a fresh view shows the status from the save
   that took effect last.

### User Story 2 - Manage players (Priority: P1)

A coach uses the Players page to maintain the roster, including ratings and goalkeeper
eligibility.

**Why this priority** — The roster supplies the players shown in Availability and used
by the football agent.

**Independent Test** — Create, view, edit, and delete a player from the Players page,
including an edit to a half-point rating.

**Acceptance Scenarios**

1. **Given** the Players page is open, **when** the coach creates a player with a name,
   a rating of 3.5, and goalkeeper eligibility selected, **then** the saved values appear
   in the roster and persist on reload. **When** the coach edits those values, **then**
   the same player record shows the updates.
2. **Given** a player form, **when** the coach submits a blank name, a name over 100
   characters, or a rating outside the valid range or half-point increments, **then**
   the form explains the invalid field, retains the entered values, and saves no changes.
3. **Given** a player with availability records and no goalkeeper history, **when** the
   coach initiates deletion, **then** the panel identifies the player and explains that
   associated availability will be removed. Cancel keeps the data. Confirm removes the
   player from Players and Availability and removes that player's availability records.
4. **Given** a player with recorded goalkeeper history, **when** the coach attempts to
   delete the player, **then** the panel explains why deletion is blocked and retains
   both the player and linked records.

### User Story 3 - Manage fixtures (Priority: P1)

A coach uses the Fixtures page to maintain the match schedule, including past and
upcoming fixtures.

**Why this priority** — The fixture schedule determines which matches the coach can
choose when recording availability.

**Independent Test** — Create, view, edit, and delete a fixture from the Fixtures page,
then check the fixture selector.

**Acceptance Scenarios**

1. **Given** the Fixtures page is open, **when** the coach creates a fixture with a
   date, opponent, and home or away designation, **then** the saved values appear in
   the schedule and the fixture is selectable on the Availability page. **When** the
   coach edits the fixture, **then** the updated details appear on both pages and the
   fixture retains its existing availability records.
2. **Given** the fixture form, **when** the coach submits an invalid date, a blank or
   overlong opponent name, or omits the home or away designation, **then** the form
   identifies the invalid field, retains the entered values, and saves no changes.
3. **Given** a fixture with availability records and no goalkeeper history, **when** the
   coach initiates deletion, **then** the panel identifies the fixture and explains that
   associated availability will be removed. Cancel keeps the data. Confirm removes the
   fixture from the schedule and selector and removes its availability records.
4. **Given** a fixture with recorded goalkeeper history, **when** the coach attempts to
   delete it, **then** the panel explains why deletion is blocked and retains both the
   fixture and linked records.

### Edge Cases

- Empty player and fixture lists explain how to create the first record. With no fixtures,
  Availability directs the coach to Fixtures. With a selected fixture and no players,
  Availability directs the coach to Players.
- Before fixture selection, Availability shows the roster with fixture-specific editing
  disabled and prompts the coach to choose a fixture.
- Fixtures against the same opponent are identifiable by date and home or away designation.
  If those details also match, the selector identifies the records separately.
- If a player in an availability batch or its fixture is deleted before the save
  takes effect, the entire batch is rejected. The panel explains which record is
  missing, keeps the pending edits, and lets the coach reload the list. If the save
  takes effect first and the record is subsequently deleted, that deletion removes
  its linked availability.
- If a player or fixture record is removed while its edit form is open, the failed
  edit explains what happened and lets the coach reload the list.
- If a save fails, the panel reports the failure, keeps the coach's inputs available to
  retry, and continues to distinguish them from the last confirmed values.
- On the host computer, a device on the same network cannot open the admin pages or
  submit an admin action. Keyboard users can navigate, edit, save, and cancel with
  visible focus.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** — The panel MUST provide direct navigation to Players, Fixtures, and Availability.
- **FR-002** — Players MUST list all players and support creating, viewing, editing, and
  deleting individual records. A player requires a nonblank name of at most 100 characters,
  a rating from 1.0 to 6.0 in half-point increments, and a goalkeeper eligibility setting
  that defaults to off on creation. Editing MUST preserve the player's fixture availability.
- **FR-003** — Fixtures MUST list past and upcoming fixtures and support creating, viewing,
  editing, and deleting individual records. A fixture requires a valid date, a nonblank
  opponent name of at most 150 characters, and a home or away designation. Editing MUST
  preserve the fixture's availability records.
- **FR-004** — Availability MUST show the full roster and let the coach select one fixture
  at a time. The selector MUST identify fixtures by opponent, date, and home or away
  designation and distinguish otherwise identical entries. Each row MUST show its saved
  status for the selected fixture as Available, Unavailable, or Not recorded. Not recorded
  represents an absence of a saved status.
- **FR-005** — The coach MUST be able to change one or more players' statuses to
  Available or Unavailable and save all pending changes for the selected fixture in one
  action. The panel MUST distinguish pending edits from saved statuses. The save MUST
  apply all submitted changes together, affect only the edited players in the selected
  fixture, persist across reloads, and feed the agent's existing availability lookup.
  Only players recorded as Available are eligible through that lookup. Switching fixtures
  or opening Players or Fixtures from Availability with pending edits MUST require
  confirmation to discard them. Canceling MUST retain the current fixture and pending edits.
  If two successful saves change the same player and fixture, the last save to take
  effect MUST determine the saved status. If a referenced player or fixture is already
  deleted when the batch is processed, the panel MUST reject the entire batch.
- **FR-006** — Deletion MUST require confirmation that identifies the player or fixture
  and explains the removal of linked availability. Deletion MUST be blocked when the
  record has linked goalkeeper history. A confirmed, permitted deletion MUST remove the
  record and its availability together. Canceling MUST leave the data intact.
- **FR-007** — The panel MUST identify invalid fields before committing a change, retain
  submitted values after a validation or save failure, and show clear saved, failed,
  empty, and missing-record states. A failed save MUST never be shown as successful.
- **FR-008** — The panel MUST apply the reference image's dark palette, layered charcoal
  panels, subtle borders, and light primary buttons to compact football lists and labeled
  forms. On desktop and narrow viewports, the navigation and editing controls MUST be
  usable without horizontal page scrolling. All controls MUST be keyboard operable
  with visible focus, and availability and feedback MUST be readable without relying on color.
- **FR-009** — The panel and its admin actions MUST be accessible only from the computer
  running it in the first release.

### Scope and Compatibility Constraints

- The first release covers one team's player roster, fixture schedule, and per-fixture
  availability. Accounts, permissions management, bulk player and fixture record editing,
  and reporting are out of scope.
- Existing API contracts and behavior MUST be preserved. If planning identifies a
  necessary change to an existing API, the maintainer MUST be asked for approval
  before the change is made. Planning may propose separate admin entry points.
- Planning MUST favor the project's existing capabilities and justify any new framework
  as necessary for the requested workflows.

### Key Entities *(include if feature involves data)*

- **Player** — A roster entry with a name, rating, and goalkeeper eligibility.
- **Fixture** — A match identified by its date, opponent, and home or away designation.
- **Availability** — One recorded available or unavailable status for a player and fixture.
- **Goalkeeper history** — A record of goalkeeper assignments tied to players and fixtures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** — A scripted browser check completes all eight player and fixture actions
  (create, view, edit, and delete for each). The saved results are visible after reload.
- **SC-002** — With 25 players and two fixtures, the coach can select a fixture,
  locate three named players, update their availability, and verify the changes after
  one Save action within 60 seconds on a local workstation. The selected fixture still
  shows all 25 players, untouched statuses match their previous values, and the second
  fixture's statuses are unchanged.
- **SC-003** — In all three deletion checks (cancel, confirm an eligible deletion, and
  attempt to delete a record with goalkeeper history), the roster or schedule and linked
  records reflect the specified outcome.
- **SC-004** — At viewport widths of 360 and 1280 pixels, a coach can navigate all three
  pages and complete a player edit, fixture edit, and availability update with a
  keyboard, visible focus, and no horizontal page scrolling.
- **SC-005** — In a first-use walkthrough, a coach can identify all three destinations
  by their labels and explain the difference between Unavailable and Not recorded after
  viewing the roster for one fixture.

## Assumptions

- The first user is a coach operating from the computer running the football agent,
  consistent with the existing browser chat. The panel manages the same football data
  the agent uses.
- An unrecorded availability status keeps its current meaning for the agent and is
  shown distinctly in the panel.
- The deletion policy defaults to preserving goalkeeper history. Records with availability
  only can be deleted with confirmation, including their linked availability.
