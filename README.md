# InboxPilot

InboxPilot is a local, review-first candidate inbox helper. It reads a CSV, groups messages by likely intent, explains priority flags, drafts suggested replies, and lets a human edit/export the results.

**Demo:** [InboxPilot Demo (Loom, 2:57)](https://www.loom.com/share/2d189862e2d045b5b31cbb25ceec05f4)

**Current status:** Quest build. The classifier is deterministic and rule-based; it is not an LLM-powered system. Nothing is sent, no mailbox or ATS is connected, and no external APIs are called.

## Requirements
- Python 3.10 or newer
- macOS Terminal
- Dependencies (`requirements.txt`): `pandas`, `streamlit`, `pytest`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run tests

From the repository root, with the virtual environment active:

```bash
pytest -q
```

Without activating it: `.venv/bin/pytest -q`. `pytest.ini` puts the project root on the import path, so tests can import `classifier`, `csv_loader`, and `reply_generator`.

## Run the app

Run from the project root (the sample file is loaded by a relative path, and the theme in `.streamlit/config.toml` is only picked up from there). With the virtual environment active:

```bash
streamlit run app.py
```

Without activating it: `.venv/bin/streamlit run app.py`. Then open http://localhost:8501 (Streamlit prints a different URL if that port is busy).

With no upload, the app shows the synthetic `data/sample_messages.csv`. Upload a CSV to replace it.

## CSV format

| Column | Required | Meaning |
|---|---|---|
| `message_id` | Yes | Unique message identifier |
| `received_at` | No | Timestamp as text |
| `candidate_name` | No | Candidate's display name |
| `subject` | No | Message subject (also used for classification) |
| `message` | Yes | Message body (may be empty; empty messages are sent to human review) |

- **Header matching:** these column names, and the generated ones below, are recognised ignoring letter case and surrounding spaces (`Message_ID`, ` Subject `). Other spellings such as `Message ID`, `message-id`, or `messageId` are not recognised. Unrecognised columns are kept unchanged and included in the export.
- **Missing optional columns** are added as empty.
- **Validation:** a file with a detected problem is rejected as a whole and nothing is processed. The app shows "Could not read the CSV. Fix the problems below and try again." followed by the details as plain text, because they can quote header names and IDs from the file.
  - **Row problems are listed together:** rows with fewer fields than the header (keep a comma for every column, even when a value is empty); blank or whitespace-only `message_id` values; duplicate `message_id` values (surrounding spaces are ignored when comparing).
  - **Structural problems stop at the first one detected**, so further problems may only appear after it is fixed: rows with more fields than the header (usually an unquoted comma; wrap such values in double quotes); exact duplicate header names (blank header cells are not checked; they are kept and exported with pandas names such as `Unnamed: 2`); two headers that resolve to the same known column (for example `message` and ` Message`).
  - **Missing required columns** (`message_id`, `message`) are reported separately, after the file has loaded.
- Properly quoted values may contain commas and line breaks.

## Re-uploading an export

An exported CSV can be uploaded again. If it already contains `intent`, `priority`, `reason`, or `draft_reply`, those columns are regenerated and a notice says so: **previous results and any edits made to `draft_reply` in the file are replaced**. Cells protected on export (see below) keep their leading `'` after re-upload.

## Classification and priority

- **Intents:** `interview_scheduling`, `application_status`, `offer_discussion`, `withdrawal`, `general_question`, `document_request`, `other`. Keyword rules in `classifier.py` are checked in a fixed order and the first match wins; the reason lists the matched phrases. Unmatched or empty messages are `other` with "human review required".
- Rule details worth knowing: negated withdrawal phrases ("I'm not going to withdraw my application") are ignored; "next steps" counts as a status request only if no explicit question phrase matched; "document", "resume" (noun only), "salary" (not "salary range" or "salary expectations"), and "compensation" (not "compensation range") use precise patterns. A message that mentions a salary range or salary expectations alongside an offer term ("offer letter", "offer details", "employment offer", "negotiate") is still `offer_discussion`.
- **Priority:**
  - `high` when the text contains time-limit or urgent wording: "urgent", "deadline", "by today", "end of today", "within an hour", "in 1 hour", "offer expires", "need to reschedule", "cannot attend". The reason adds "verify urgency manually". A bare "today" is not urgent.
  - `low` only for clear courtesy-only messages: the text contains "thank you for your time", "just wanted to say thank you", or "thanks for your time"; no intent matched; no urgent wording; and no "?" or "please".
  - `normal` for everything else, including empty and unclear messages.
- Priority is a simple heuristic, not a calibrated urgency model.

## Reviewing, editing, and exporting

- Each message is a card in the inbox list; high-priority cards open automatically and have a rose edge, low-priority cards a teal edge. An open card shows intent and priority badges, the classification reason, the **Candidate message** (left) and the editable **Suggested reply** (right). The card titles keep the raw intent name (for example `interview_scheduling`). Drafts are fixed templates per intent; they use only the candidate's name and never invent dates, decisions, or salary terms. Every draft must be reviewed by a person.
- Message bodies are shown as plain text, and candidate names and subjects are escaped in the expander labels, so message content is not rendered as Markdown, links, or images.
- **Filter by intent** to narrow the list (the dropdown shows readable names such as "Interview scheduling"; a line above the list shows how many messages are visible). Draft edits are kept per `message_id` while you filter, so an edit made to a row that is later hidden is still exported and shown again when the row reappears.
- **Edit lifetime:** edits live only in the current browser session. They are cleared when the loaded data changes (including any new upload, even of the same file) and lost on page refresh. Export to keep them.
- **Export:** "Export triage results as CSV" downloads all input columns (known headers in canonical lowercase spelling) plus `intent`, `priority`, `reason`, and the current `draft_reply` for every row, including filtered-out rows.
- **Spreadsheet formula protection:** any exported cell that starts with `=`, `+`, `-`, or `@` (after leading spaces), or with a tab or carriage return, is prefixed with `'` so spreadsheet apps do not run it as a formula. Plain negative numbers such as `-5` are left unchanged. Trade-off: the `'` is usually visible when the CSV is opened in a spreadsheet, and phone numbers starting with `+` are prefixed too.

## Known limitations
- Keyword rules can misclassify sarcasm, mixed-intent messages, and unusual wording. Known gaps, kept by decision: a withdrawal question ("Should I withdraw my application or not?") is classified as `withdrawal`, and its reply template reads as if a withdrawal request was received; "deadline" counts as urgent anywhere in the text, including past deadlines ("The deadline passed last month" is `high`).
- Reply drafts are templates and may sound generic.
- Automated app tests use Streamlit `AppTest` through the sample-data path; `AppTest` cannot simulate file uploads, so automated tests do not cover every browser or upload workflow. A manual check on 2026-10-15 covered editing drafts, filtering, exporting, and re-uploading the export (no duplicate rows); other browser behaviour, such as label escaping and error display, has not been checked manually. Formula protection is tested on the exported CSV text only; it has not been checked by opening exports in Excel or LibreOffice.
- 103 automated tests pass; passing tests do not prove that every possible workflow is correct.
- Synthetic sample data does not establish real-world accuracy.
- The dashboard was checked in a desktop browser at full width; its layout on narrow or mobile screens has not been checked.
- The app header says "AI-powered", but classification uses transparent keyword rules and replies are fixed templates; no LLM is involved.

## Quest deliverables
- `intent.md`, `Final directive.md`, `daily_log.md`, `unlearning_note.md`, and this README are in this project folder.
- Demo video (Loom): [InboxPilot Demo](https://www.loom.com/share/2d189862e2d045b5b31cbb25ceec05f4), 2 minutes 57 seconds (about three minutes), showing the app working.
- Five-minute demo requirement: **not yet confirmed**. Whether a 2:57 video satisfies the Quest's five-minute demo item (for example, a maximum or an approximate length) has not been checked against the official Quest instructions.

## Privacy
Use synthetic or approved data only. The app does not call external APIs or send messages.

## Project files
- `intent.md`: initial product intent and boundaries
- `directive.md`: initial implementation directive
- `Final directive.md`: final directive describing the app as built
- `daily_log.md`: evidence of daily iterations
- `unlearning_note.md`: one-page note on what was unlearned
- `app.py`: Streamlit UI (dashboard layout, filtering, draft editing, export)
- `.streamlit/config.toml`: Streamlit theme (colour palette, corner radius, borders)
- `classifier.py`: deterministic intent and priority rules
- `csv_loader.py`: CSV loading, validation, header normalisation, and export formula protection
- `reply_generator.py`: conservative reply templates
- `data/sample_messages.csv`: synthetic sample data (row M009 has an intentionally empty message)
- `requirements.txt`: dependencies
- `pytest.ini`: test configuration
- `tests/test_classifier.py`: intent, priority, and precedence rules
- `tests/test_replies.py`: reply template safety
- `tests/test_csv_loader.py`: CSV validation, headers, and formula protection
- `tests/test_app.py`: end-to-end app behaviour via Streamlit `AppTest` (export, re-upload, filtering edits, rendering)
