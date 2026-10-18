import io

import pytest

import pandas as pd

from csv_loader import load_messages_csv, protect_for_spreadsheet

HEADER = "message_id,received_at,candidate_name,subject,message\n"

def test_valid_row_parses_into_correct_columns():
    df = load_messages_csv(io.StringIO(HEADER + "M1,2026-10-12 09:10,Ada,Hello,Any update?\n"))
    assert df.to_dict("records") == [{
        "message_id": "M1",
        "received_at": "2026-10-12 09:10",
        "candidate_name": "Ada",
        "subject": "Hello",
        "message": "Any update?",
    }]

def test_quoted_field_with_comma_parses_correctly():
    df = load_messages_csv(io.StringIO(HEADER + 'M1,,Ada,Hi,"Hello, any update, please?"\n'))
    assert df.loc[0, "message_id"] == "M1"
    assert df.loc[0, "message"] == "Hello, any update, please?"
    assert df.loc[0, "received_at"] == ""

def test_extra_field_in_every_row_is_rejected_not_shifted():
    with pytest.raises(ValueError, match="more fields than the header"):
        load_messages_csv(io.StringIO(HEADER + "M1,t,Ada,S,hi,extra\nM2,t,Bo,S,hey,more\n"))

def test_extra_field_in_minimal_two_column_csv_is_rejected():
    with pytest.raises(ValueError, match="more fields than the header"):
        load_messages_csv(io.StringIO("message_id,message\nM1,hi,extra\n"))

def test_extra_field_in_one_row_is_rejected_with_line_number():
    csv = HEADER + "M1,t,Ada,S,hi\nM2,t,Bo,S,hi,extra\n"
    with pytest.raises(ValueError, match="line 3"):
        load_messages_csv(io.StringIO(csv))

def test_sample_dataset_still_loads_unchanged():
    df = load_messages_csv("data/sample_messages.csv")
    assert list(df.columns) == ["message_id", "received_at", "candidate_name", "subject", "message"]
    assert len(df) == 10
    assert df["message_id"].tolist() == [f"M{i:03d}" for i in range(1, 11)]
    assert df.loc[8, "message"] == ""
    assert df.loc[8, "candidate_name"] == ""

def test_blank_message_id_is_rejected_with_line_number():
    csv = HEADER + "M1,t,Ada,S,hi\n,t,Bo,S,hey\n"
    with pytest.raises(ValueError, match=r"line 3: message_id is blank"):
        load_messages_csv(io.StringIO(csv))

def test_whitespace_only_message_id_is_rejected():
    with pytest.raises(ValueError, match=r"line 2: message_id is blank"):
        load_messages_csv(io.StringIO(HEADER + "   ,t,Ada,S,hi\n"))

def test_duplicate_message_ids_are_rejected():
    csv = HEADER + "M1,t,Ada,S,hi\nM2,t,Bo,S,hey\nM1,t,Cy,S,yo\n"
    with pytest.raises(ValueError, match=r"duplicate message_id 'M1' on lines 2, 4"):
        load_messages_csv(io.StringIO(csv))

def test_ids_differing_only_by_surrounding_whitespace_are_duplicates():
    csv = HEADER + "M1,t,Ada,S,hi\n M1 ,t,Bo,S,hey\n"
    with pytest.raises(ValueError, match=r"duplicate message_id 'M1' on lines 2, 3"):
        load_messages_csv(io.StringIO(csv))

def test_unique_id_with_surrounding_whitespace_is_not_rewritten():
    df = load_messages_csv(io.StringIO(HEADER + " M1 ,t,Ada,S,hi\n"))
    assert df.loc[0, "message_id"] == " M1 "

def test_short_row_is_rejected_not_padded():
    csv = HEADER + "M1,t,Ada,S,hi\nM2,t,Bo\n"
    with pytest.raises(ValueError, match=r"line 3: has 3 field\(s\) but the header has 5"):
        load_messages_csv(io.StringIO(csv))

def test_row_missing_only_the_message_field_is_rejected():
    with pytest.raises(ValueError, match=r"line 2: has 4 field\(s\) but the header has 5"):
        load_messages_csv(io.StringIO(HEADER + "M1,t,Ada,S\n"))

def test_explicitly_empty_message_is_accepted():
    df = load_messages_csv(io.StringIO(HEADER + 'M9,t,,No subject,""\nM10,t,,S,\n'))
    assert df["message_id"].tolist() == ["M9", "M10"]
    assert df["message"].tolist() == ["", ""]

def test_multiple_invalid_rows_are_reported_together():
    csv = HEADER + "M1,t,Ada,S,hi\n,t,Bo,S,hey\nM3,t\nM1,t,Cy,S,yo\n"
    with pytest.raises(ValueError) as excinfo:
        load_messages_csv(io.StringIO(csv))
    message = str(excinfo.value)
    assert "line 3: message_id is blank" in message
    assert "line 4: has 2 field(s) but the header has 5" in message
    assert "duplicate message_id 'M1' on lines 2, 5" in message

def test_line_numbers_account_for_multiline_quoted_messages():
    csv = HEADER + 'M1,t,Ada,S,"line one\nline two"\n,t,Bo,S,hey\n'
    with pytest.raises(ValueError, match=r"line 4: message_id is blank"):
        load_messages_csv(io.StringIO(csv))

def test_valid_multiline_quoted_message_still_loads():
    df = load_messages_csv(io.StringIO(HEADER + 'M1,t,Ada,S,"Hello,\nany update?"\n'))
    assert df.loc[0, "message"] == "Hello,\nany update?"

def test_missing_message_id_column_is_left_to_the_app_check():
    df = load_messages_csv(io.StringIO("message\nhello\n"))
    assert list(df.columns) == ["message"]

def test_sample_dataset_keeps_intentionally_empty_m009_message():
    df = load_messages_csv("data/sample_messages.csv")
    m009 = df[df["message_id"] == "M009"].iloc[0]
    assert m009["message"] == ""
    assert m009["subject"] == "No subject"

def test_case_and_whitespace_variant_headers_normalize_with_data_in_place():
    csv = (' Message_ID ,RECEIVED_AT,Candidate_Name,\tSubject,"  Message"\n'
           'M1,2026-10-12 09:10,Ada,Hello,"Any update, please?"\n')
    df = load_messages_csv(io.StringIO(csv))
    assert df.to_dict("records") == [{
        "message_id": "M1",
        "received_at": "2026-10-12 09:10",
        "candidate_name": "Ada",
        "subject": "Hello",
        "message": "Any update, please?",
    }]

def test_generated_column_headers_normalize_to_canonical_names():
    df = load_messages_csv(io.StringIO("message_id,message,Intent, PRIORITY ,Reason,Draft_Reply\nM1,hi,a,b,c,d\n"))
    assert list(df.columns) == ["message_id", "message", "intent", "priority", "reason", "draft_reply"]
    assert df.loc[0, "priority"] == "b"

def test_unknown_headers_keep_exact_original_spelling():
    csv = "message_id,message, Notes ,Message ID,message-id,messageId,Sender\nM1,hi,n,x,y,z,s\n"
    df = load_messages_csv(io.StringIO(csv))
    assert list(df.columns) == ["message_id", "message", " Notes ", "Message ID", "message-id", "messageId", "Sender"]

def test_conflicting_message_headers_are_rejected():
    with pytest.raises(ValueError, match=r"'message' and ' Message' both map to 'message'"):
        load_messages_csv(io.StringIO("message_id,message, Message\nM1,a,b\n"))

def test_conflicting_message_id_headers_are_rejected():
    with pytest.raises(ValueError, match=r"'message_id' and 'Message_ID' both map to 'message_id'"):
        load_messages_csv(io.StringIO("message_id,Message_ID,message\nM1,M2,hi\n"))

def test_blank_id_rejected_under_non_canonical_id_header():
    with pytest.raises(ValueError, match=r"line 2: message_id is blank"):
        load_messages_csv(io.StringIO("Message_ID,Message\n ,hi\n"))

def test_duplicate_ids_rejected_under_non_canonical_id_header():
    with pytest.raises(ValueError, match=r"duplicate message_id 'M1' on lines 2, 3"):
        load_messages_csv(io.StringIO(" MESSAGE_ID ,message\nM1,a\nM1 ,b\n"))

def test_extra_fields_still_rejected_with_non_canonical_headers():
    with pytest.raises(ValueError, match="more fields than the header"):
        load_messages_csv(io.StringIO("Message_ID, Message\nM1,hi,extra\n"))
    with pytest.raises(ValueError, match="line 3"):
        load_messages_csv(io.StringIO("Message_ID, Message\nM1,hi\nM2,hi,extra\n"))

def test_bom_prefixed_non_canonical_header_normalizes():
    df = load_messages_csv(io.BytesIO("﻿Message_ID,Message\nM1,hi\n".encode("utf-8")))
    assert list(df.columns) == ["message_id", "message"]
    assert df.loc[0, "message_id"] == "M1"

def test_formula_like_values_are_neutralized_for_spreadsheets():
    df = pd.DataFrame({"message": [
        "=1+1", "+SUM(A1)", "-2+3", "@cmd", "\t=1+1", "\r=1+1", "  =HYPERLINK(\"https://evil.example\")", "\n@x",
    ]})
    protected = protect_for_spreadsheet(df)
    assert protected["message"].tolist() == [
        "'=1+1", "'+SUM(A1)", "'-2+3", "'@cmd", "'\t=1+1", "'\r=1+1", "'  =HYPERLINK(\"https://evil.example\")", "'\n@x",
    ]

def test_ordinary_text_and_negative_numbers_are_unchanged():
    values = ["Hello, any update?", "", "M001", "2026-10-12 09:10", "-5", "-12.50", "a=b", "email@example.com", "Hello =1+1,"]
    protected = protect_for_spreadsheet(pd.DataFrame({"message": values}))
    assert protected["message"].tolist() == values

def test_already_protected_values_are_not_double_protected():
    once = protect_for_spreadsheet(pd.DataFrame({"message": ["=1+1", "+44 20 7946 0000"]}))
    twice = protect_for_spreadsheet(once)
    assert twice["message"].tolist() == ["'=1+1", "'+44 20 7946 0000"]

def test_protection_preserves_shape_and_leaves_source_unchanged():
    source = pd.DataFrame({"message_id": ["M1", "M2"], "message": ["=1+1", "hi"], "notes": ["@x", "ok"]})
    snapshot = source.copy()
    protected = protect_for_spreadsheet(source)
    pd.testing.assert_frame_equal(source, snapshot)
    assert list(protected.columns) == list(source.columns)
    assert len(protected) == len(source)
    assert protected.loc[1, "message"] == "hi"

def test_exact_duplicate_known_header_is_rejected():
    with pytest.raises(ValueError, match=r"Duplicate CSV header\(s\): 'message' \(columns 2, 3\)"):
        load_messages_csv(io.StringIO("message_id,message,message\nM1,first,second\n"))

def test_exact_duplicate_unknown_header_is_rejected():
    with pytest.raises(ValueError, match=r"'Notes' \(columns 3, 4\)"):
        load_messages_csv(io.StringIO("message_id,message,Notes,Notes\nM1,hi,a,b\n"))

def test_quoted_duplicate_header_is_rejected():
    with pytest.raises(ValueError, match="Duplicate CSV header"):
        load_messages_csv(io.StringIO('"message",message_id,message\nhi,M1,x\n'))

def test_literal_dotted_header_is_not_a_duplicate():
    df = load_messages_csv(io.StringIO("message_id,message,message.1\nM1,a,b\n"))
    assert list(df.columns) == ["message_id", "message", "message.1"]
    assert df.loc[0].tolist() == ["M1", "a", "b"]

def test_case_only_header_differences_follow_existing_rules():
    with pytest.raises(ValueError, match=r"'message' and 'Message' both map to 'message'"):
        load_messages_csv(io.StringIO("message_id,message,Message\nM1,a,b\n"))
    df = load_messages_csv(io.StringIO("message_id,message,Notes,notes\nM1,hi,a,b\n"))
    assert list(df.columns) == ["message_id", "message", "Notes", "notes"]

def test_blank_header_cells_keep_existing_positional_names():
    df = load_messages_csv(io.StringIO("message_id,message,,\nM1,hi,,\n"))
    assert list(df.columns) == ["message_id", "message", "Unnamed: 2", "Unnamed: 3"]
