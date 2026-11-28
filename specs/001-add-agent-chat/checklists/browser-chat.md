# Browser Chat Requirements Checklist

**Purpose** — Review the browser experience and conversation lifecycle requirements before implementation.

**Created** — 2026-11-28

**Feature** — [Football Agent Web Chat](../spec.md)

This custom checklist was generated with `$speckit-checklist`. The reviewer marks an item
`[x]` when the written requirements satisfy its criterion.

## Requirement Completeness

- [ ] CHK001 Are the required chat controls and the empty, pending, successful, and failed conversation states defined? [Completeness, Spec §FR-001, §FR-004]
- [ ] CHK002 Do the requirements specify the order of coach and assistant messages and how the coach can distinguish their roles? [Completeness, Spec §FR-002]
- [ ] CHK003 Are the transcript and fixture context that carry over between successful turns both specified? [Completeness, Spec §FR-003, User Story 2]

## Requirement Clarity

- [ ] CHK004 Do the requirements define when an ambiguous fixture question needs clarification and identify a clarification as an ordinary assistant reply? [Clarity, Spec §FR-002, Edge Cases]
- [ ] CHK005 Are the upper bounds for a pending reply and initial conversation creation clearly distinguished across the spec, plan, and browser contract? [Clarity, Spec §FR-004, Plan §Technical Context, Browser Chat Contract]
- [ ] CHK006 Do the requirements define the information and next action an unavailable or timeout message must communicate? [Clarity, Spec §FR-004, §SC-004]

## Requirement Consistency

- [ ] CHK007 Is host-only access defined consistently for both the chat page and conversation requests, while narrow viewport support remains in scope on the host? [Consistency, Spec §Clarifications, User Story 1, Scope and Compatibility Constraints]
- [ ] CHK008 Is the new browser entry point distinguished from the existing API surface, with the approval trigger for existing contract or behavior changes stated explicitly? [Consistency, Spec §Scope and Compatibility Constraints, Plan §Constitution Check]
- [ ] CHK009 Are the meanings of a fresh page, a restored page, and an independent tab consistent across the spec and browser contract? [Consistency, Spec §FR-003, Edge Cases, Browser Chat Contract]

## Scenario Coverage

- [ ] CHK010 Are separate requirements defined for a delivered page-exit notification and a missed notification, including which context may remain in memory and who can access it? [Coverage, Spec §FR-003, Clarifications]
- [ ] CHK011 Is recovery defined for both an agent failure and a timeout, including preservation of the earlier transcript, fixture context, and failed message text? [Recovery, Spec §FR-003, §FR-004, User Story 3, Data Model §Conversation]
- [ ] CHK012 Does the contract specify what the coach can recover when the chat service restarts and the open page still has an earlier transcript? [Recovery, Spec §FR-003, §FR-004, Browser Chat Contract, Data Model §Conversation]
- [ ] CHK013 Do the requirements distinguish retrying a request whose result was lost from retrying a request that failed before completion? [Recovery, Spec §FR-004, Browser Chat Contract]

## Edge Case Coverage

- [ ] CHK014 Are the input and concurrency boundaries explicit for whitespace-only text and repeated submissions during a pending reply? [Edge Case, Spec §FR-001, Edge Cases]
- [ ] CHK015 Is the treatment of a reply that finishes after its page exits or refreshes defined consistently? [Edge Case, Spec §FR-003, Edge Cases, Browser Chat Contract]
- [ ] CHK016 Are wrapping and inert treatment of long and markup-like messages specified for both coach and assistant messages? [Edge Case, Spec §FR-002, §FR-005, Edge Cases]

## Non-Functional Requirements

- [ ] CHK017 Are keyboard operation, visible focus, and accessible pending and error notices defined for the complete send and retry flows? [Accessibility, Gap, Spec §FR-004, §FR-005, §SC-002, Plan §Design and verification]
- [ ] CHK018 Does the plan state what chat content and conversation identifiers must stay out of logs and error responses? [Completeness, Plan §Constitution Check, Browser Chat Contract, Constitution §Technical Constraints]

## Acceptance Criteria Quality

- [ ] CHK019 Can a reviewer determine whether the squad follow-up used the same fixture as the preceding availability question from the stated acceptance criteria? [Measurability, Spec §SC-001, User Story 2]
- [ ] CHK020 Does the responsive-layout criterion specify viewport widths, horizontal overflow, and the complete keyboard-only flow? [Measurability, Spec §SC-002, §FR-005]
- [ ] CHK021 Are the timing start and end, sample count, passing threshold, environment, and prompt workload defined for the pending feedback target? [Measurability, Spec §SC-003, Quickstart §Performance checks]

## Dependencies and Assumptions

- [ ] CHK022 Does the plan distinguish the assumptions required to run the local agent today from the deferred sign-in, administration, and saved-history capabilities? [Assumption, Spec §Scope and Compatibility Constraints, Plan §Technical Context]

## Notes

- Leave items unchecked while they need reviewer evaluation, clarification, or correction.
- Add findings inline and link to the relevant part of the spec, plan, or contract.
- `$speckit-implement` reads checklist state as a gate. Reviewers own the markers.
- [The built-in specification checklist](requirements.md) follows the `$speckit-specify` and `$speckit-clarify` workflow.
