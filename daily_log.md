# Quest Work Log

> Add dated entries as work happens. Do not backdate entries or claim tests were run unless they were.

## Day 1 — Baseline
_Work dates: 2026-10-13 (audit, B4, B2) and 2026-10-14 (B1 onward, final audit, R1–R5). Evidence: file modification times and the session clock; the folder is not a git repository, so there is no commit history. Entry written 2026-10-14._

- Goal: Audit the deterministic baseline, fix confirmed bugs one at a time with regression tests, and leave a tested end-to-end workflow (CSV → intent/priority/reason/draft → human review → CSV export).
- Initial assumptions:
  - The keyword baseline is a reasonable starting point if its failures are made visible by tests (intent.md "Assumptions to verify").
  - Message text and every uploaded CSV value are untrusted (intent.md safety rules).
  - Unclear, empty, or unmatched messages should go to human review, not be guessed (intent.md: "classify conservatively").
  - Malformed CSV input must be rejected clearly instead of being loaded silently or wrongly.
- AI prompts / tools used: Claude Code (Claude Opus 5.5) in the terminal. One prompt per step: read-only audit first, then one finding per prompt, each with "inspect before editing, add regression tests, run focused and full suites, report, stop and wait for approval". Streamlit `AppTest` (already installed) was used to drive the real `app.py`. No new dependencies or external APIs.
- Changes made (in order; files: `pytest.ini`, `csv_loader.py`, `app.py`, `classifier.py`, `reply_generator.py`, `tests/`):
  - B4: added `pytest.ini` (`pythonpath = .`) so the README command `pytest -q` works.
  - B2: urgency is checked independently of intent, so unmatched urgent messages are `high`.
  - B1: new `csv_loader.load_messages_csv`; rows with more fields than the header are rejected instead of shifting columns.
  - B8: blank or whitespace-only IDs, duplicate IDs (ignoring surrounding spaces) and short rows are rejected, all errors listed together. Empty messages are still allowed (sample row M009).
  - B3: re-uploading an export no longer crashes; old generated columns are refreshed, with a visible notice.
  - B10: known headers are matched ignoring case and surrounding whitespace; conflicting headers are rejected.
  - B9: the offer reply template no longer assumes an offer exists.
  - B5: "next steps" is checked after explicit question phrases (M006 → `general_question`).
  - B6: precise patterns for "document", "resume" (noun only) and "salary" (not "salary range").
  - B7: negated withdrawal phrases ("I'm not going to withdraw…") are not treated as withdrawals.
  - B11: a bare "today" no longer means `high`; "by today" / "end of today" still do.
  - R3: CSV export prefixes formula-like cells (`= + - @`, tab, CR) with `'`; plain negative numbers are left alone.
  - R1: draft edits are kept per `message_id` in session state, survive intent filtering, and reset when the data changes.
  - R2: the message body is rendered with `st.text`; candidate name and subject are Markdown-escaped in expander labels.
  - R4: exact duplicate CSV headers are rejected using the raw header row (pandas renames them silently).
  - R5: `low` priority for clear courtesy-only messages (three thank-you phrases, no intent, no urgency, no "?" or "please"). M008 is now `low`.
- Commands run and results:
  - Before fixes: `.venv/bin/python -m pytest -q` → 9 passed; `pytest -q` (README command) → 2 collection errors (`ModuleNotFoundError`).
  - Each fix: new tests run first and seen failing, then `.venv/bin/pytest -q` on the focused file and the full suite. Full-suite totals after each step: 9 → 12 → 18 → 31 → 35 → 45 → 49 → 53 → 58 → 63 → 67 → 72 → 75 → 78 → 84 → 89.
  - Latest: `.venv/bin/pytest -q` → 89 passed; compile check of `app.py`, `classifier.py`, `csv_loader.py`, `reply_generator.py` and `tests/*.py` → OK (re-run 2026-10-14 when writing this entry).
- What failed or surprised me:
  - The README test command did not work at all until B4.
  - pandas silently turned extra fields into an index (B1), gives padded short rows the same value as empty fields (B8), and renames duplicate headers (R4); each needed a check on the raw CSV text.
  - The obvious `index_col=False` fix for B1 silently dropped data instead.
  - Two earlier tests had expected values that encoded bugs: the app's "6 intent groups" (wrong after the M006 fix, now 7) and a B10 fixture that relied on bare "today" being urgent (changed to "Urgent - …").
  - The original app already carried draft edits into different data by row position (found while fixing R1).
  - Reviewer edits in rows hidden by the filter were lost on export, and message text was rendered as Markdown — neither was covered by any test.
- What I changed after checking the output:
  - B8: the first version rejected whitespace-only lines that pandas skips; fixed to match pandas.
  - B6: the first "resume" pattern missed "my CV and resume"; added "and"/"or".
  - B5, B6, B7, B11: compared intent/priority/reason across a fixed message corpus before and after each change, and chose the narrowest fix (B5 option with 3 changes instead of 6–7).
  - B3: my first check of the new tests against the old code failed for a setup reason (wrong pytest config); re-ran correctly before relying on it.
- What I learned / unlearned (observed this day):
  - "Tests pass" was not evidence of correctness: the suite passed while the documented test command, the export round-trip, filtered edits and Markdown rendering were all broken or untested.
  - Library defaults (pandas parsing, Streamlit widget state) caused most data-integrity bugs; checking raw input and testing through the real app (`AppTest`) found them.
  - Measuring every classification change against a fixed corpus kept rule fixes narrow and made side effects visible.
- Remaining risks:
  - Not yet fixed: R7 (README does not describe CSV validation, header normalization, re-upload, formula protection or the `low` rule) and R8 (permissive assertion in `test_urgent_language_flags_high_priority`).
  - Upload error messages can quote IDs and header names from the file through `st.error`, which renders Markdown.
  - The upload path (`if uploaded:`) is not covered by tests (`AppTest` cannot simulate uploads); no browser-level check of rendering was done.
  - Known classifier limits: comma-separated or trailing negation (B7), "pause and resume", "salary expectations"/"compensation range" (B6), other plain-substring priority terms such as "deadline" (B11).
  - The `low` criteria exist only in code; `directive.md` still does not define them.
  - Exported protected cells show a visible `'`; duplicate blank headers are still accepted.
  - No git repository, so changes are not versioned.

### Day 1 follow-up — 2026-10-14 (after R6)
_Covers three later passes on 2026-10-14: R7/R8, residual issues, and three classifier decisions. The "Remaining risks" list above is superseded by the one below. Entry written 2026-10-14._

- Goal: Close the remaining audit items (R7, R8), fix confirmed residual defects, and record explicit decisions for the classifier edge cases.
- AI prompts / tools used: Claude Code (Claude Opus 5.5), one prompt per pass, each with inspect-first, test-first, before/after corpus comparison for classifier changes, and full verification. No new dependencies.
- Changes made:
  - R7: `README.md` rewritten section by section to match the implementation (CSV validation, header matching, re-upload, priorities including `low`, filtered edits, export, formula protection, limitations, full file list).
  - R8: permissive classifier tests replaced with exact intent/priority/reason expectations; added precedence-boundary and priority-reachability tests. 89 → 91 tests.
  - Residual pass: upload/load errors now show a fixed headline via `st.error` and the file-derived details via `st.text` (no Markdown); the sample path uses the same error handling. B7: a comma-enclosed aside ("I do not, under any circumstances, want to …") no longer hides negation. B6: "pause and resume" is no longer a résumé mention ("and/or resume" counts only after "CV", "cover letter", or "portfolio"). `directive.md` now records the approved `low` rule. 91 → 99 tests.
  - Decisions pass (`classifier.py`, `tests/test_classifier.py`):
    - Decision 1: withdrawal questions ("Should I withdraw my application or not?") stay `withdrawal`; reason text unchanged because it only names the matched phrase.
    - Decision 2: "salary expectations" and "compensation range" alone no longer imply `offer_discussion` (same exclusion style as "salary range"); messages with an offer term ("offer letter", "offer details", "employment offer", "negotiate") still match.
    - Decision 3: "deadline" stays an urgency signal, including past deadlines; no date interpretation.
    - Four new tests: withdrawal question with neutral reason; compensation range / salary expectations unmatched; genuine offer messages with compensation wording still `offer_discussion`; past-deadline wording stays `high`. 99 → 103 tests.
  - This entry and the README "Known gaps" correction (documentation only).
- Commands run and results:
  - Decisions pass: 139-message corpus compared before and after; exactly 3 messages changed, all from `offer_discussion` to `other / normal` ("salary expectations?", "Compensation range for this role?", "What is the compensation range for this role?"); no priority changed.
  - `.venv/bin/pytest -q tests/test_classifier.py` → 42 passed.
  - `.venv/bin/pytest -q` → 103 passed.
  - `.venv/bin/python -m py_compile app.py classifier.py csv_loader.py tests/test_app.py tests/test_classifier.py tests/test_csv_loader.py` → exit 0.
  - Re-run before writing this entry (2026-10-14): `.venv/bin/pytest -q` → 103 passed; the same `py_compile` command → exit 0.
- What failed or surprised me:
  - Loosely written tests let a real regression through: with "documentation" forced to `general_question`, all 32 old classifier tests passed; the R8 tests catch it.
  - `classify_message(None)` is treated as the text "none", not as empty (the app never passes `None`; left unchanged).
  - In the decisions pass, one new test expected "negotiable" to match the term "negotiate"; the expectation was corrected to what the rule actually matches.
- Remaining risks (current):
  - Withdrawal questions get the withdrawal reply template, which reads as if a request was received ("We acknowledge your request…"); relies on human review. Changing it is a reply-template decision.
  - The file-upload path is not covered by automated tests (`AppTest` cannot simulate uploads) and has not been run in a real browser; label escaping and plain-text error display are verified only at the element level.
  - Formula protection is verified on the exported CSV text only, not by opening exports in Excel or LibreOffice; protected cells show a visible `'`, which re-uploads preserve.
  - Kept by decision: past deadlines are `high`; withdrawal questions are `withdrawal`.
  - Duplicate blank header cells are accepted (exported as `Unnamed: N`).
  - No git repository, so changes are not versioned.
- Status:
  - Audit findings: all audit items (B1–B11, R1–R8) are closed.
  - Known limitations (not open audit items): the withdrawal-question reply template and the other risks listed above.
  - Pending manual checks: browser behaviour not covered by the 2026-10-15 check below (such as error display and label escaping) and opening exports in Excel or LibreOffice.

### Manual verification — 2026-10-15
_Manual checks performed by me in the running app; these are separate from, and complement, the automated test suite (103 passing tests). Date confirmed by me._

- Edited multiple generated reply drafts, changed the intent filter, and confirmed the edits persisted.
- Downloaded the exported CSV and confirmed my edited drafts appeared in it.
- Re-uploaded the exported CSV; it did not create duplicate rows.
- Re-uploading regenerates the generated columns (the app shows a notice), so previous generated values and human edits saved in `draft_reply` can be overwritten.
- Updates the "has not been run in a real browser" note above for these workflows only. Not checked: other browser behaviour (such as error display and label escaping) and opening the export in Excel or LibreOffice. Passing tests and these checks do not prove that every workflow is correct.
- Documentation on 2026-10-15: `final_directive.md` renamed to `Final directive.md` and corrected; `unlearning_note.md` completed from confirmed reflections; `README.md` validation description corrected and video deliverables marked pending.
- Loom video and five-minute demo video: pending, not yet recorded.

### UI review, documentation, and Loom demo — 2026-10-17
_Covers the dashboard UI redesign (2026-10-16, per the session clock) and the review and documentation pass on 2026-10-17. Entry written 2026-10-17._

- UI redesign (2026-10-16): presentation-only changes to `app.py` plus a new `.streamlit/config.toml` theme (header, data-source card, metric cards, filter and export toolbar, message cards with candidate-message and suggested-reply panels). Classification, reply, validation, draft-persistence, and export logic were not changed.
- UI review (2026-10-17): no blocking issues found. Optional items noted: card titles show raw intent names; the header says "AI-powered" although classification is rule-based; narrow-screen layout not checked.
- Documentation: `README.md` updated with the Loom link, corrected launch instructions, the new card layout, two added limitations, and an updated file list; `Final directive.md` video line updated.
- Loom demo: [InboxPilot Demo](https://www.loom.com/share/33c6e8d6b24b4502a695623dd734cf74), about 1 minute 41 seconds (length as reported by me). The separate five-minute demo video is still pending unless the Quest confirms the Loom video satisfies that item.
- Verification: `.venv/bin/pytest -q` → 103 passed (re-run 2026-10-17); the app launched with `.venv/bin/streamlit run app.py` and its health check returned `ok`.

### Demo video edit — 2026-10-17
_Entry written 2026-10-17. Duration as reported by me; no new link was supplied._

- Finished editing the InboxPilot demo video; its current duration is 2 minutes 57 seconds.
- Not yet confirmed whether the edited video replaces the Loom link recorded above (listed there as about 1 minute 41 seconds) or will have a new link. `README.md` and `Final directive.md` still reference that Loom link and its earlier duration.
- Not yet verified against the Quest instructions whether a 2:57 video satisfies the separate five-minute demo requirement.
- Remaining submission tasks: confirm the final demo video link and update `README.md` and `Final directive.md` with it and its duration; check the required demo duration in the Quest instructions; complete the GitHub phase (the project folder is not yet a Git repository; nothing has been committed or pushed); submit.

### Submission preparation — 2026-10-17
_Entry written 2026-10-17._

- Final demo link confirmed by me: [InboxPilot Demo](https://www.loom.com/share/2d189862e2d045b5b31cbb25ceec05f4), 2 minutes 57 seconds. It supersedes the earlier Loom link recorded above. `README.md` and `Final directive.md` now reference only the final link.
- Not yet confirmed: whether the 2:57 video satisfies the Quest's five-minute demo item. The official Quest instructions are not in the project folder.
- `requirements.txt`: Streamlit lower bound raised from 1.35 to 1.65, the version the app was built and tested with (the dashboard uses features newer than 1.35). No dependency was added.
- Added `.gitignore` (virtual environment, bytecode, test cache, secrets files, logs, exports, recordings, OS metadata).
- File audit before Git: no secrets, credentials, `.env` files, or OS metadata found in the project files; `.venv`, `__pycache__`, and `.pytest_cache` excluded.
- Verification: `.venv/bin/pytest -q` → 103 passed; `py_compile` of the app, modules, and tests → exit 0; the app launched with `.venv/bin/streamlit run app.py` and its health check returned `ok`.
- Git: initialised the repository in the project folder on branch `main`; staged 19 reviewed files by name; initial commit `3294e93` ("Prepare InboxPilot Quest submission").
- GitHub: with my confirmation, created the public repository `Alien-dev-ai/inboxpilot` under my account (empty, no extra files) and pushed `main` without force. Verified on GitHub: the latest commit matches `3294e93`; the same 19 files are present; no `.venv`, cache, or secrets files; the README contains the final Loom link; the only collaborator is my account and there are no invitations.
- Not done: Quest submission itself.

_The project was completed ahead of the five-day Quest window. No Day 2–5 entries are recorded because no further confirmed work is assigned to those days._
