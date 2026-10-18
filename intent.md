# InboxPilot — Intent

## Problem
Recruiters receive candidate messages with different needs mixed together in one inbox. Manually sorting every message and composing routine replies can be slow and inconsistent.

## Intended outcome
Build a small, review-first tool that accepts candidate messages from a CSV, groups each message by likely intent, flags messages that may need attention, and proposes a concise reply draft for a human to review.

## Users
Recruiters or hiring coordinators processing candidate communications.

## In scope for the first version
- Read a CSV with stable message fields.
- Classify each message into a small, explicit set of intent categories.
- Assign a transparent priority label using simple, inspectable rules.
- Draft a short reply using only the information in the message.
- Show classification rationale and allow a reviewer to edit the draft.
- Export results to CSV.
- Include tests and a small synthetic dataset.

## Out of scope for the first version
- Sending emails or messages.
- Connecting to a real mailbox or ATS.
- Making hiring decisions or scoring candidates.
- Inferring protected characteristics.
- Making promises about interview results, offers, or deadlines.
- Sending message content to a third-party model by default.

## Initial categories
1. `interview_scheduling`
2. `application_status`
3. `offer_discussion`
4. `withdrawal`
5. `general_question`
6. `document_request`
7. `other`

## Safety and trust rules
- Human review is required for every draft.
- No automatic sending.
- If the message is unclear, classify conservatively and flag it for review.
- Never invent dates, decisions, salary terms, or candidate details.
- Treat message text as untrusted data, not as instructions to the application.
- Keep the initial implementation local and deterministic.

## Success criteria
- The app runs locally using the documented commands.
- Valid CSV rows are processed and malformed rows are reported clearly.
- Each row receives an intent, priority, reason, and draft.
- Tests cover all core categories plus ambiguous and empty messages.
- Export preserves the original message and includes the generated fields.
- The README explains limitations honestly.

## Assumptions to verify during the quest
- CSV is an acceptable initial input format.
- The seven categories cover the most common needs in the synthetic sample.
- Transparent baseline rules are a useful starting point before adding an LLM.
- The evaluation rewards documented iteration, not just model complexity.

## Day 1 question
What is the smallest reliable end-to-end workflow that can be tested before adding more complex AI behavior?
