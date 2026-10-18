# InboxPilot — Initial Directive (Day 1)

Build a small local Python application that processes candidate messages from a CSV and helps a recruiter triage them.

## Required behavior
1. Accept a CSV containing `message_id`, `received_at`, `candidate_name`, `subject`, and `message`.
2. Validate required columns and handle blank values without crashing.
3. Assign one intent from the documented category list.
4. Assign a priority (`high`, `normal`, or `low`) with an explainable reason.
   - `low` is only for clear courtesy-only messages: the text contains "thank you for your time", "just wanted to say thank you", or "thanks for your time"; no intent matched; no urgent wording; and no "?" or "please". Urgent wording (`high`) and any matched request take precedence. Empty, unclear, and unmatched messages stay `normal`, and every `low` message still requires human review. (Approved Day 1 rule, R5.)
5. Draft a concise reply that does not invent missing facts or claim a hiring decision.
6. Present each draft for human review and editing.
7. Export the reviewed data to CSV.
8. Include automated tests for classification, draft safety, CSV validation, and edge cases.

## Constraints
- Python 3.10+.
- Keep dependencies lightweight.
- No paid APIs or API keys required for the baseline.
- Do not send emails or connect to a real inbox.
- Do not rank candidates or recommend hiring decisions.
- Keep classification logic inspectable and document its limitations.
- Do not claim the baseline is an LLM; describe it accurately as a deterministic starting point.
- Add complexity only after tests and observed failures justify it.

## Working method
- Inspect the repository before editing.
- Make one small change at a time.
- Run tests after each meaningful change.
- Report commands run, results, failures, and unresolved risks honestly.
- Do not silently remove tests to make a build pass.
- Keep a short daily log of assumptions, prompts, iterations, and lessons.
