# InboxPilot — Final Directive

This directive describes InboxPilot as it was built during the Quest. It supersedes the initial directive (`directive.md`), which is kept unchanged as the starting point. Product intent and boundaries remain as stated in `intent.md`; differences from `intent.md` are noted below.

## Purpose
A small, local, deterministic Python app that helps a recruiter triage candidate messages from a CSV. It assigns an intent, a priority with an explainable reason, and a conservative reply draft, then exports the reviewed results. It is not an LLM system.

**Human review:** every draft requires human review. The app never sends messages and does not connect to a mailbox or ATS.

## Required behavior
1. **Input.** Accept a CSV with required `message_id` and `message`, and optional `received_at`, `candidate_name`, `subject`. Known column names (input and generated) are matched ignoring case and surrounding spaces; other headers are kept unchanged.
2. **Validation.** A file with a detected problem is rejected as a whole; error details are shown as plain text.
   - Row problems (short rows, blank `message_id` values, duplicate `message_id` values with surrounding spaces ignored) are reported together in one list.
   - Structural problems (rows with more fields than the header, exact duplicate headers, headers that resolve to the same known column) stop loading at the first one detected, so other problems may only appear after it is fixed.
   - Missing required columns are reported separately, after the file has loaded.
   - Empty messages are allowed and go to human review.
   - *Differs from `intent.md`, which describes processing valid rows and reporting malformed ones; whole-file rejection was chosen so invalid records are never silently skipped.*
3. **Intent.** Assign exactly one of: `interview_scheduling`, `application_status`, `offer_discussion`, `withdrawal`, `general_question`, `document_request`, `other`. Fixed keyword rules, first match wins; the reason names the matched phrases. Unmatched or empty messages are `other` with "human review required".
4. **Priority.** `high` for time-limit or urgent wording ("urgent", "deadline", "by today", "end of today", "within an hour", "in 1 hour", "offer expires", "need to reschedule", "cannot attend"); `low` only for clear courtesy-only messages (see `directive.md` item 4); `normal` otherwise, including empty and unclear messages.
5. **Drafts.** One fixed template per intent, using only the candidate's name. Drafts never invent dates, decisions, or salary terms and never assume an offer exists.
6. **Review.** Show each message as plain text with its intent, priority, reason, and an editable draft. Draft edits are kept per `message_id` while filtering and cleared when the loaded data changes.
7. **Export.** Export all input columns plus `intent`, `priority`, `reason`, and the current `draft_reply` for every row. Cells starting with `=`, `+`, `-`, or `@` (or a tab or carriage return) are prefixed with `'` for spreadsheet safety, and known column names are written in lowercase, so the export is not always byte-for-byte identical to the input. *(Differs from `intent.md`'s "Export preserves the original message" for those cells and headers.)*
8. **Re-upload.** Uploading an exported CSV again regenerates `intent`, `priority`, `reason`, and `draft_reply`, with a visible notice. Previous generated values, including any edits saved in `draft_reply`, are overwritten.
9. **Tests.** Automated tests for classification, priority precedence, draft safety, CSV validation, re-upload, filtering edits, rendering, and export protection.

## Decisions recorded during the build
- Classification edge cases: negated withdrawal phrases are ignored; "next steps" yields to explicit question phrases; "document", "resume" (noun only), "salary" (not "salary range" or "salary expectations"), and "compensation" (not "compensation range") use precise patterns.
- Kept by decision: withdrawal questions ("Should I withdraw my application or not?") stay `withdrawal`; "deadline" stays urgent even for past deadlines.
- Formula protection keeps a visible `'`; re-uploads preserve it.
- Blank header cells are accepted and exported as `Unnamed: N`.

## Constraints (unchanged from the initial directive)
Python 3.10+; lightweight dependencies (`pandas`, `streamlit`, `pytest`); no paid APIs or API keys; no sending or inbox connection; no candidate ranking or hiring recommendations; inspectable rules with documented limitations; complexity added only when tests and observed failures justify it.

## Working method
Inspect before editing; one finding per change; regression tests with each code fix, written to fail first where applicable; focused and full test runs after each change; before/after comparison over a fixed message corpus for classifier changes; honest reporting of commands, results, failures, and risks; daily log kept in `daily_log.md`.

## Verification
- The automated suite reported 103 passing tests.
- Manual check (2026-10-15): several reply drafts were edited, the intent filter was changed and the edits persisted; the downloaded CSV contained the edited drafts; re-uploading the export did not create duplicate rows.
- Automated tests do not cover every browser or upload workflow (Streamlit `AppTest` cannot simulate file uploads).
- Spreadsheet behavior has not been independently verified in Excel or LibreOffice.
- Passing tests do not prove that every possible workflow is correct.
- Demo video (Loom): [InboxPilot Demo](https://www.loom.com/share/2d189862e2d045b5b31cbb25ceec05f4), 2 minutes 57 seconds. Whether it satisfies the Quest's five-minute demo item has not been confirmed against the official Quest instructions.

## Known limitations
- Keyword rules miss sarcasm, mixed intent, and unusual wording.
- A withdrawal-related question can receive the withdrawal-request template ("We acknowledge your request…"); human review must catch this.
- Draft edits last only for the browser session and are overwritten by a re-upload.
- See `README.md` for further details.
