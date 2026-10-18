import io
import re
from pathlib import Path

import pandas as pd
import streamlit
from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = str(PROJECT_ROOT / "app.py")
SAMPLE_BYTES = (PROJECT_ROOT / "data" / "sample_messages.csv").read_bytes()
INPUT_COLUMNS = ["message_id", "received_at", "candidate_name", "subject", "message"]
GENERATED_COLUMNS = ["intent", "priority", "reason", "draft_reply"]

def start_app(csv_bytes, tmp_path, monkeypatch):
    """Run app.py once on csv_bytes; return the app and a dict whose "data" is the latest export."""
    # AppTest cannot simulate file uploads, so the CSV is served as data/sample_messages.csv.
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "sample_messages.csv").write_bytes(csv_bytes)
    monkeypatch.chdir(tmp_path)

    exported = {}
    original_download_button = streamlit.download_button

    def capturing_download_button(label, data, *args, **kwargs):
        exported["data"] = data
        return original_download_button(label, data, *args, **kwargs)

    monkeypatch.setattr(streamlit, "download_button", capturing_download_button)
    at = AppTest.from_file(APP_PATH, default_timeout=30).run()
    return at, exported

def run_app(csv_bytes, tmp_path, monkeypatch):
    """Run app.py on csv_bytes via its default sample path; return the app and exported CSV bytes."""
    at, exported = start_app(csv_bytes, tmp_path, monkeypatch)
    return at, exported.get("data")

def metrics(at):
    return {metric.label: metric.value for metric in at.metric}

def refresh_notices(at):
    return [info.value for info in at.info if "already contains generated column" in info.value]

def test_original_sample_runs_with_expected_metrics(tmp_path, monkeypatch):
    at, export = run_app(SAMPLE_BYTES, tmp_path, monkeypatch)
    assert not at.exception
    assert metrics(at) == {"Messages": "10", "Intent groups": "7", "High-priority flags": "1"}
    assert refresh_notices(at) == []
    exported = pd.read_csv(io.BytesIO(export), dtype=str)
    assert list(exported.columns) == INPUT_COLUMNS + GENERATED_COLUMNS

def test_reuploaded_export_runs_and_matches_original_results(tmp_path, monkeypatch):
    first_at, first_export = run_app(SAMPLE_BYTES, tmp_path, monkeypatch)
    at, second_export = run_app(first_export, tmp_path, monkeypatch)

    assert not at.exception
    assert metrics(at) == metrics(first_at)
    assert at.selectbox[0].options == first_at.selectbox[0].options

    notices = refresh_notices(at)
    assert len(notices) == 1
    assert "intent, priority, reason, draft_reply" in notices[0]
    assert "human edits to draft_reply" in notices[0]

    first = pd.read_csv(io.BytesIO(first_export), dtype=str, keep_default_na=False)
    second = pd.read_csv(io.BytesIO(second_export), dtype=str, keep_default_na=False)
    assert list(second.columns) == INPUT_COLUMNS + GENERATED_COLUMNS
    assert second.columns.is_unique
    pd.testing.assert_frame_equal(second, first)

def test_reuploaded_export_replaces_edited_drafts(tmp_path, monkeypatch):
    _, export = run_app(SAMPLE_BYTES, tmp_path, monkeypatch)
    edited = pd.read_csv(io.BytesIO(export), dtype=str, keep_default_na=False)
    original_draft = edited.loc[0, "draft_reply"]
    edited.loc[0, "draft_reply"] = "Reviewer-edited draft"

    at, second_export = run_app(edited.to_csv(index=False).encode("utf-8"), tmp_path, monkeypatch)
    assert not at.exception
    second = pd.read_csv(io.BytesIO(second_export), dtype=str, keep_default_na=False)
    assert second.loc[0, "draft_reply"] == original_draft

def test_single_generated_column_is_refreshed_and_other_columns_kept(tmp_path, monkeypatch):
    sample = pd.read_csv(io.BytesIO(SAMPLE_BYTES), dtype=str, keep_default_na=False)
    sample["priority"] = "high"
    sample["notes"] = "keep me"

    at, export = run_app(sample.to_csv(index=False).encode("utf-8"), tmp_path, monkeypatch)
    assert not at.exception
    assert metrics(at)["High-priority flags"] == "1"
    notices = refresh_notices(at)
    assert len(notices) == 1
    assert "column(s): priority." in notices[0]

    exported = pd.read_csv(io.BytesIO(export), dtype=str, keep_default_na=False)
    assert exported.columns.is_unique
    assert list(exported.columns) == INPUT_COLUMNS + ["notes"] + GENERATED_COLUMNS
    assert (exported["notes"] == "keep me").all()
    assert exported["message_id"].tolist() == [f"M{i:03d}" for i in range(1, 11)]

def test_non_canonical_optional_headers_are_used_not_blanked(tmp_path, monkeypatch):
    csv = (
        "message_id,message,Subject, Candidate_Name \n"
        'M1,Thanks for everything.,Urgent - withdraw my application,Ada\n'
    ).encode("utf-8")

    at, export = run_app(csv, tmp_path, monkeypatch)
    assert not at.exception
    assert not at.error
    exported = pd.read_csv(io.BytesIO(export), dtype=str, keep_default_na=False)
    assert exported.columns.is_unique
    assert list(exported.columns) == ["message_id", "message", "subject", "candidate_name",
                                      "received_at"] + GENERATED_COLUMNS
    # Both signals live only in the Subject header's column.
    assert exported.loc[0, "intent"] == "withdrawal"
    assert exported.loc[0, "priority"] == "high"
    assert exported.loc[0, "draft_reply"].startswith("Hello Ada,")

def test_export_neutralizes_formula_cells_but_app_shows_original_text(tmp_path, monkeypatch):
    csv = (
        "message_id,candidate_name,subject,message\n"
        'M1,=1+1,+SUM(A1),"=HYPERLINK(""https://evil.example"",""click"")"\n'
        "M2,Ada,-5,Any update on my application?\n"
    ).encode("utf-8")

    at, export = run_app(csv, tmp_path, monkeypatch)
    assert not at.exception
    exported = pd.read_csv(io.BytesIO(export), dtype=str, keep_default_na=False)
    assert list(exported.columns) == ["message_id", "candidate_name", "subject", "message",
                                      "received_at"] + GENERATED_COLUMNS
    assert len(exported) == 2
    assert exported.loc[0, "candidate_name"] == "'=1+1"
    assert exported.loc[0, "subject"] == "'+SUM(A1)"
    assert exported.loc[0, "message"] == "'=HYPERLINK(\"https://evil.example\",\"click\")"
    assert exported.loc[1].tolist()[:4] == ["M2", "Ada", "-5", "Any update on my application?"]
    assert exported.loc[1, "intent"] == "application_status"
    # Classification and on-screen text use the original values, not the export copy.
    assert exported.loc[0, "draft_reply"].startswith("Hello =1+1,")
    assert any(text.value == '=HYPERLINK("https://evil.example","click")' for text in at.text)

def exported_drafts(exported):
    frame = pd.read_csv(io.BytesIO(exported["data"]), dtype=str, keep_default_na=False)
    return dict(zip(frame["message_id"], frame["draft_reply"]))

def draft_editor(at, message_id):
    matches = [area for area in at.text_area if area.key.endswith(f"_{message_id}")]
    assert len(matches) == 1, f"expected one visible editor for {message_id}, found {len(matches)}"
    return matches[0]

def visible_editor_ids(at):
    return {area.key.rsplit("_", 1)[1] for area in at.text_area}

def test_draft_edit_survives_hiding_the_row_with_the_intent_filter(tmp_path, monkeypatch):
    at, exported = start_app(SAMPLE_BYTES, tmp_path, monkeypatch)
    original = exported_drafts(exported)["M001"]

    draft_editor(at, "M001").set_value("Edited reply for M001").run()
    assert exported_drafts(exported)["M001"] == "Edited reply for M001"

    at.selectbox[0].set_value("withdrawal").run()
    assert "M001" not in visible_editor_ids(at)
    assert exported_drafts(exported)["M001"] == "Edited reply for M001"

    at.selectbox[0].set_value("all").run()
    assert draft_editor(at, "M001").value == "Edited reply for M001"
    drafts = exported_drafts(exported)
    assert drafts["M001"] == "Edited reply for M001"
    assert drafts["M001"] != original

def test_edits_to_several_rows_stay_with_their_message_ids(tmp_path, monkeypatch):
    at, exported = start_app(SAMPLE_BYTES, tmp_path, monkeypatch)
    original = exported_drafts(exported)

    draft_editor(at, "M001").set_value("Edit for M001")
    draft_editor(at, "M004").set_value("Edit for M004")
    at.run()
    at.selectbox[0].set_value("withdrawal").run()
    draft_editor(at, "M004").set_value("Second edit for M004").run()
    at.selectbox[0].set_value("interview_scheduling").run()

    drafts = exported_drafts(exported)
    assert drafts["M001"] == "Edit for M001"
    assert drafts["M004"] == "Second edit for M004"
    assert {mid: d for mid, d in drafts.items() if mid not in ("M001", "M004")} == {
        mid: d for mid, d in original.items() if mid not in ("M001", "M004")
    }

def test_saved_edits_do_not_carry_into_different_data(tmp_path, monkeypatch):
    at, exported = start_app(SAMPLE_BYTES, tmp_path, monkeypatch)
    draft_editor(at, "M001").set_value("Edit for the original M001").run()
    assert exported_drafts(exported)["M001"] == "Edit for the original M001"

    # Same message IDs, different content: stands in for uploading another file.
    (tmp_path / "data" / "sample_messages.csv").write_bytes(SAMPLE_BYTES.replace(b"Ada Okafor", b"Zed Example"))
    at.run()
    assert exported_drafts(exported)["M001"].startswith("Hello Zed Example,")
    assert draft_editor(at, "M001").value.startswith("Hello Zed Example,")

MARKDOWN_PAYLOAD = "**bold** _it_ [click](https://evil.example) ![img](https://evil.example/p.png) <b>html</b> # Heading"

def test_message_body_is_rendered_as_literal_text_not_markdown(tmp_path, monkeypatch):
    csv = (
        "message_id,candidate_name,subject,message\n"
        f'M1,Ada,Hello,"{MARKDOWN_PAYLOAD}"\n'
    ).encode("utf-8")

    at, export = run_app(csv, tmp_path, monkeypatch)
    assert not at.exception
    assert [element.value for element in at.text] == [MARKDOWN_PAYLOAD]
    assert not any("evil.example" in element.value for element in at.markdown)
    exported = pd.read_csv(io.BytesIO(export), dtype=str, keep_default_na=False)
    assert exported.loc[0, "message"] == MARKDOWN_PAYLOAD

def test_expander_label_escapes_markdown_from_untrusted_fields(tmp_path, monkeypatch):
    name = "**Eve** [x](https://evil.example)"
    subject = "![s](https://evil.example/s.png) :red[alert] $x^2$ <b>hi</b>"
    csv = (
        "message_id,candidate_name,subject,message\n"
        f'M1,"{name}","{subject}",Thanks.\n'
    ).encode("utf-8")

    at, export = run_app(csv, tmp_path, monkeypatch)
    assert not at.exception
    [label] = [expander.label for expander in at.expander]
    untrusted_part, intent_part = label.rsplit(" · ", 1)
    assert intent_part == "other"
    # Every Markdown-significant character from the CSV is backslash-escaped...
    assert re.search(r"(?<!\\)[*_\[\]()!`<>:$^~#|]", untrusted_part.replace("\\\\", "")) is None
    # ...and removing the escapes gives back exactly the original text.
    assert re.sub(r"\\(.)", r"\1", untrusted_part) == f"{name} · {subject}"
    exported = pd.read_csv(io.BytesIO(export), dtype=str, keep_default_na=False)
    assert exported.loc[0, "candidate_name"] == name
    assert exported.loc[0, "subject"] == subject

def test_plain_labels_and_empty_message_placeholder_still_render(tmp_path, monkeypatch):
    at, _ = run_app(SAMPLE_BYTES, tmp_path, monkeypatch)
    labels = [expander.label for expander in at.expander]
    assert re.sub(r"\\(.)", r"\1", labels[0]) == "Ada Okafor · Interview availability · interview_scheduling"
    assert any(md.value == "_Empty message_" for md in at.markdown)
    assert len(at.text) == 9

EVIL = "[click](https://evil.example)"

def assert_error_details_are_literal(at, *expected_fragments):
    assert not at.exception
    assert [error.value for error in at.error] == ["Could not read the CSV. Fix the problems below and try again."]
    [details] = [text.value for text in at.text]
    for fragment in expected_fragments:
        assert fragment in details
    assert not any("evil.example" in md.value for md in at.markdown)
    assert not at.expander and not at.metric

def test_malicious_duplicate_header_error_is_shown_as_literal_text(tmp_path, monkeypatch):
    header = f"**{EVIL}**"
    at, _ = run_app(f"message_id,message,{header},{header}\nM1,hi,a,b\n".encode("utf-8"), tmp_path, monkeypatch)
    assert_error_details_are_literal(at, "Duplicate CSV header(s)", f"'{header}' (columns 3, 4)")

def test_malicious_message_id_error_is_shown_as_literal_text(tmp_path, monkeypatch):
    csv = f"message_id,message\n{EVIL},a\n{EVIL},b\n<b>x</b>,c\n,d\n".encode("utf-8")
    at, _ = run_app(csv, tmp_path, monkeypatch)
    assert_error_details_are_literal(
        at,
        "Invalid CSV rows; fix these and upload again:",
        f"duplicate message_id '{EVIL}' on lines 2, 3",
        "line 5: message_id is blank",
    )

def test_malicious_conflicting_header_error_is_shown_as_literal_text(tmp_path, monkeypatch):
    at, _ = run_app(b"message_id,message, MESSAGE \nM1,a,b\n", tmp_path, monkeypatch)
    assert_error_details_are_literal(at, "Conflicting CSV headers", "' MESSAGE ' both map to 'message'")

def test_malformed_row_error_keeps_actionable_hint(tmp_path, monkeypatch):
    at, _ = run_app(b"message_id,message\nM1,hi,extra\n", tmp_path, monkeypatch)
    assert_error_details_are_literal(at, "more fields than the header", "wrap such values in double quotes")
