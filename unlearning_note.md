# What I Unlearned

## A habit or assumption I stopped relying on
I learned that a useful project does not need an LLM or extra complexity when the requirements do not call for one. InboxPilot stayed a small, deterministic, rule-based app; the work went into making it correct and testable rather than more complex.

## Evidence that it was not working
Recorded during the build session:
- `pytest -q`, the README's own test command, failed with `ModuleNotFoundError` while `python -m pytest` passed (B4).
- pandas silently shifted columns for rows with extra fields (B1), treated short rows like empty values (B8), and renamed duplicate headers (R4); none of this was visible without checking the raw CSV.
- Re-uploading an export crashed the app (B3); edits to rows hidden by the intent filter were lost on export (R1); untrusted message text was rendered as Markdown (R2). No existing test covered any of these.
- With "documentation" forced to `general_question`, all 32 earlier classifier tests still passed (found during R8).

## What I tried instead
- One audit finding per change, with regression tests for each code fix.
- Testing through the real app with Streamlit `AppTest` instead of only testing functions.
- Comparing intent, priority, and reason across a fixed message corpus before and after every classifier change, and choosing the option with the fewest side effects.
- Recording decisions explicitly (e.g. past deadlines stay `high`) and pinning them with tests.

## What improved, and how I measured it
- The automated suite grew from 9 to 103 passing tests. After the initial test-runner fix (B4), code fixes were paired with regression tests where applicable; most were seen failing before the fix, while some tests documented existing behavior rather than failing before a change.
- Classifier changes were measured against the corpus, e.g. B5 changed 3 messages instead of 6–7 for the alternatives; the last offer-wording change altered exactly 3 of 139 messages.
- The tightened R8 tests catch the forced misclassification that the earlier tests missed.
- My manual check on 2026-10-15 complemented the automated tests: I edited multiple reply drafts, changed the intent filter and saw the edits persist; the downloaded CSV contained my edited drafts; re-uploading the export did not create duplicate rows. Re-uploading does regenerate the generated columns, so human edits saved in those columns can be overwritten.
- Passing tests do not prove that every workflow is correct.

## What still did not work
- Automated tests do not cover every browser or upload workflow, and spreadsheet behavior was not checked in Excel or LibreOffice.
- A withdrawal question receives the withdrawal reply template ("We acknowledge your request…").
- Keyword rules remain blind to sarcasm, mixed intent, and unusual wording.

## What I would do differently next time
Define requirements first, build small, and test incrementally.

## Where AI helped
- Claude Code (Claude Opus 5.5) ran the audit, reproduced each finding, wrote tests alongside fixes, implemented narrow changes, and reported command output after each step.
- It surfaced problems outside the request, e.g. that the original app already carried draft edits into unrelated data (R1), and that the sample row M009 conflicted with rejecting empty messages (B8).

## Where AI output was wrong, incomplete, or unsafe
AI-generated changes needed manual checking or fixing. Examples recorded during the build session:
- B8: the first version rejected whitespace-only lines that pandas skips; corrected after a probe.
- B6: the first "resume" pattern missed "my CV and resume"; its later "and/or" fix made "pause and resume" a false positive, corrected in a follow-up pass.
- B3 and R7/R8: two verification runs initially failed for the AI's own setup reasons (wrong pytest config; a shell quoting error that ran no tests) and had to be re-run.
- Two new tests contained wrong expectations (`classify_message(None)` treated as empty; "negotiable" assumed to match "negotiate") and were corrected.
