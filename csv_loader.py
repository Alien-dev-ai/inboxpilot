"""CSV loading for candidate messages, rejecting rows that would shift columns."""
from __future__ import annotations

import csv
import io
import re

import pandas as pd

MALFORMED_HINT = (
    "This usually means a value contains an unquoted comma; "
    'wrap such values in double quotes (e.g. "Hello, any update?") and try again.'
)
# Input and generated columns used by app.py; matched ignoring case and surrounding whitespace.
KNOWN_COLUMNS = (
    "message_id", "received_at", "candidate_name", "subject", "message",
    "intent", "priority", "reason", "draft_reply",
)
SHORT_ROW_HINT = (
    'Keep a comma for every column, even when a value is empty (e.g. M009,2026-10-12 12:00,,No subject,"").'
)

def load_messages_csv(source) -> pd.DataFrame:
    """Read a messages CSV as text, raising ValueError instead of misaligning columns."""
    try:
        df = pd.read_csv(source, dtype=str)
    except pd.errors.ParserError as exc:
        raise ValueError(f"Malformed CSV: {str(exc).strip()}. {MALFORMED_HINT}") from exc
    # When every data row has more fields than the header, pandas silently uses
    # the leading fields as an index, shifting all values one or more columns left.
    if not isinstance(df.index, pd.RangeIndex):
        raise ValueError(f"Malformed CSV: data rows have more fields than the header. {MALFORMED_HINT}")
    records = _read_records(source)
    # pandas silently renames repeated headers ("message" -> "message.1"), so check the raw header row.
    if records:
        _reject_duplicate_headers(records[0][1])
    df = _normalise_headers(df).fillna("")

    errors = _validate_rows(df, records)
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Invalid CSV rows; fix these and upload again:\n{details}")
    return df

def _reject_duplicate_headers(header: list[str]) -> None:
    """Raise ValueError if a non-blank header name appears more than once exactly as written."""
    positions: dict[str, list[int]] = {}
    for position, name in enumerate(header, start=1):
        if name.strip():
            positions.setdefault(name, []).append(position)
    duplicates = [
        f"{name!r} (columns {', '.join(map(str, cols))})" for name, cols in positions.items() if len(cols) > 1
    ]
    if duplicates:
        raise ValueError(
            f"Duplicate CSV header(s): {'; '.join(duplicates)}. "
            "Rename or remove the extra column(s) so each header appears once, and try again."
        )

def _normalise_headers(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known columns to their canonical spelling; leave other headers untouched."""
    originals_by_name: dict[str, list[str]] = {}
    for column in df.columns:
        name = str(column).strip().lower()
        if name in KNOWN_COLUMNS:
            originals_by_name.setdefault(name, []).append(column)

    conflicts = [
        f"{', '.join(map(repr, originals[:-1]))} and {originals[-1]!r} "
        f"{'both' if len(originals) == 2 else 'all'} map to '{name}'"
        for name, originals in originals_by_name.items()
        if len(originals) > 1
    ]
    if conflicts:
        raise ValueError(
            f"Conflicting CSV headers: {'; '.join(conflicts)}. Keep only one column for each and try again."
        )
    return df.rename(columns={originals[0]: name for name, originals in originals_by_name.items()})

def _read_records(source) -> list[tuple[int, list[str]]]:
    """Return (starting line number, raw fields) for each non-blank CSV record.

    pandas pads short rows with the same value as a genuinely empty field, so
    field counts must come from the raw text.
    """
    if hasattr(source, "seek"):
        source.seek(0)
        text = source.read()
        source.seek(0)
    else:
        with open(source, "rb") as handle:
            text = handle.read()
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig")
    text = text.removeprefix("﻿")

    records = []
    reader = csv.reader(io.StringIO(text, newline=""))
    previous_line = 0
    for fields in reader:
        # Skip blank and whitespace-only lines, as pandas does.
        if fields and not (len(fields) == 1 and not fields[0].strip()):
            records.append((previous_line + 1, fields))
        previous_line = reader.line_num
    return records

def _validate_rows(df: pd.DataFrame, records: list[tuple[int, list[str]]]) -> list[str]:
    """Collect every row-level problem so the user can fix them in one pass."""
    if not records:
        return []
    header_width = len(records[0][1])
    data_records = records[1:]
    errors = [
        f"line {line}: has {len(fields)} field(s) but the header has {header_width}. {SHORT_ROW_HINT}"
        for line, fields in data_records
        if len(fields) < header_width
    ]

    if len(data_records) != len(df):
        errors.append(
            f"found {len(data_records)} data row(s) but parsed {len(df)}; "
            "check the file for stray quotes or malformed lines."
        )
    elif "message_id" in df.columns:
        lines_by_id: dict[str, list[int]] = {}
        for (line, _), message_id in zip(data_records, df["message_id"]):
            key = message_id.strip()
            if not key:
                errors.append(f"line {line}: message_id is blank; every message needs a unique ID.")
            else:
                lines_by_id.setdefault(key, []).append(line)
        for key, lines in lines_by_id.items():
            if len(lines) > 1:
                errors.append(
                    f"duplicate message_id '{key}' on lines {', '.join(map(str, lines))}; "
                    "IDs must be unique (surrounding spaces are ignored when comparing)."
                )
    return errors

# Spreadsheet apps may run a cell starting with these as a formula (CSV/formula injection).
FORMULA_TRIGGERS = ("=", "+", "-", "@")
PLAIN_NEGATIVE_NUMBER = re.compile(r"-\d+(?:\.\d+)?")

def _protect_cell(value):
    if not isinstance(value, str) or not value:
        return value
    if value[0] in "\t\r":
        return "'" + value
    stripped = value.lstrip()
    if stripped.startswith(FORMULA_TRIGGERS) and not PLAIN_NEGATIVE_NUMBER.fullmatch(stripped):
        return "'" + value
    return value

def protect_for_spreadsheet(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy for CSV export with formula-like cells prefixed by an apostrophe."""
    return df.apply(lambda column: column.map(_protect_cell))
