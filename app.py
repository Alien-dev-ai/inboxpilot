"""Streamlit UI for the InboxPilot Day 1 baseline."""
from __future__ import annotations

import hashlib
import html
import io
import re
import pandas as pd
import streamlit as st

from classifier import classify_message
from csv_loader import load_messages_csv, protect_for_spreadsheet
from reply_generator import draft_reply

REQUIRED_COLUMNS = {"message_id", "message"}
GENERATED_COLUMNS = ["intent", "priority", "reason", "draft_reply"]

# Presentation only: CSS for the dashboard. Colours come from .streamlit/config.toml where possible.
STYLES = """
<style>
:root {
  --ip-navy: #111827; --ip-indigo: #6366F1; --ip-violet: #8B5CF6; --ip-teal: #14B8A6;
  --ip-amber: #F59E0B; --ip-rose: #F43F5E; --ip-bg: #F5F7FF; --ip-slate: #64748B; --ip-line: #E2E8F0;
}
.block-container { padding-top: 4.25rem; max-width: 1280px; }
.ip-header { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.25rem; }
.ip-mark {
  width: 48px; height: 48px; border-radius: 14px; flex: none;
  background: linear-gradient(135deg, var(--ip-indigo), var(--ip-violet));
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.25);
}
.ip-title { font-size: 1.85rem; font-weight: 750; color: var(--ip-navy); line-height: 1.1; margin: 0; }
.ip-subtitle { color: var(--ip-slate); font-size: 0.98rem; margin-top: 0.15rem; }
.ip-badge {
  display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.2rem 0.6rem; border-radius: 999px;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; white-space: nowrap;
}
.ip-badge-ai { background: #EEF2FF; color: #4338CA; border: 1px solid #C7D2FE; }
.ip-badge-review { background: #F0FDFA; color: #0F766E; border: 1px solid #99F6E4; }
.ip-lede { color: #334155; font-size: 0.95rem; margin: 0.6rem 0 1.25rem; max-width: 820px; }
.ip-section-title { font-size: 1.05rem; font-weight: 700; color: var(--ip-navy); margin: 0 0 0.15rem; }
.ip-section-hint { color: var(--ip-slate); font-size: 0.86rem; margin: 0 0 0.6rem; }
.ip-meta { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin-bottom: 0.5rem; }
.ip-pill { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.78rem; font-weight: 600; }
.ip-intent { background: #EEF2FF; color: #4338CA; }
.ip-prio-high { background: #FFE4E6; color: #BE123C; }
.ip-prio-normal { background: #F1F5F9; color: #334155; }
.ip-prio-low { background: #CCFBF1; color: #0F766E; }
.ip-reason { color: var(--ip-slate); font-size: 0.84rem; margin: 0 0 0.75rem; }
.ip-panel-label {
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--ip-slate); margin: 0 0 0.35rem;
}
.ip-panel-label-ai { color: #4F46E5; }
.ip-count { color: var(--ip-slate); font-size: 0.86rem; margin: 0.1rem 0 0.75rem; }

/* Metric cards */
[data-testid="stMetric"] { background: #FFFFFF; box-shadow: 0 1px 2px rgba(17, 24, 39, 0.04); }
[data-testid="stColumn"]:nth-of-type(1) [data-testid="stMetric"] { border-top: 3px solid var(--ip-indigo); }
[data-testid="stColumn"]:nth-of-type(2) [data-testid="stMetric"] { border-top: 3px solid var(--ip-violet); }
[data-testid="stColumn"]:nth-of-type(3) [data-testid="stMetric"] { border-top: 3px solid var(--ip-rose); }
[data-testid="stMetricLabel"] p { color: var(--ip-slate); font-weight: 600; }

/* Upload surface */
[data-testid="stFileUploaderDropzone"] { background: #F8F9FF; border: 1.5px dashed #A5B4FC; }

/* Message cards: open card is the active workspace; high priority gets a rose edge */
[data-testid="stExpander"] details { background: #FFFFFF; box-shadow: 0 1px 2px rgba(17, 24, 39, 0.04); }
[data-testid="stExpander"] details[open] { border-color: #A5B4FC; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.12); }
[data-testid="stExpander"] summary { font-weight: 600; }
[class*="st-key-ip-card-high"] [data-testid="stExpander"] details { border-left: 4px solid var(--ip-rose); }
[class*="st-key-ip-card-low"] [data-testid="stExpander"] details { border-left: 4px solid var(--ip-teal); }

/* Candidate message: literal text in a calm panel; long lines wrap instead of overflowing */
[data-testid="stExpander"] [data-testid="stText"] {
  background: #F8FAFC; border: 1px solid var(--ip-line); border-radius: 0.75rem; padding: 0.85rem 1rem;
}
[data-testid="stText"], [data-testid="stText"] * { white-space: pre-wrap; overflow-wrap: anywhere; font-family: inherit; }

/* Suggested reply editor: indigo accent */
[data-testid="stExpander"] [data-testid="stTextArea"] textarea {
  background: #FAFAFF; border-left: 3px solid var(--ip-indigo); line-height: 1.5;
}
</style>
"""

HEADER = """
<div class="ip-header">
  <div class="ip-mark" aria-hidden="true">
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/>
      <path d="m3 7 9 6 9-6"/></svg>
  </div>
  <div>
    <div class="ip-title">InboxPilot</div>
    <div class="ip-subtitle">AI-powered candidate inbox triage</div>
  </div>
  <div style="display:flex; gap:0.4rem; flex-wrap:wrap;">
    <span class="ip-badge ip-badge-ai">AI WORKSPACE</span>
    <span class="ip-badge ip-badge-review">&#10003; HUMAN REVIEW ENABLED</span>
  </div>
</div>
<div class="ip-lede">Organizes candidate messages, identifies their intent with transparent rules, and prepares
editable reply suggestions. Nothing is sent: every draft is reviewed by a person.</div>
"""

PRIORITY_LABELS = {"high": "High priority", "normal": "Normal priority", "low": "Low priority"}
PRIORITY_ICONS = {"high": ":material/priority_high:", "normal": ":material/mail:", "low": ":material/drafts:"}

def escape_markdown(text: str) -> str:
    """Backslash-escape ASCII punctuation so untrusted text in a Markdown label stays literal."""
    return re.sub(r"([!-/:-@\[-`{-~])", r"\\\1", " ".join(text.split()))

def intent_label(intent: str) -> str:
    return "All intents" if intent == "all" else intent.replace("_", " ").capitalize()

def section(title: str, hint: str = "") -> None:
    """Fixed, app-authored section heading (never untrusted text)."""
    hint_html = f'<div class="ip-section-hint">{html.escape(hint)}</div>' if hint else ""
    st.markdown(f'<div class="ip-section-title">{html.escape(title)}</div>{hint_html}', unsafe_allow_html=True)

st.set_page_config(page_title="InboxPilot", page_icon="📨", layout="wide")
st.markdown(STYLES, unsafe_allow_html=True)
st.markdown(HEADER, unsafe_allow_html=True)

with st.container(border=True):
    section(
        "Data source",
        "Upload a CSV with message_id and message columns (received_at, candidate_name and subject are optional), "
        "or keep working with the built-in synthetic sample.",
    )
    uploaded = st.file_uploader("Upload candidate messages (CSV)", type=["csv"])
    if not uploaded:
        st.info("Showing synthetic sample data. Upload your own CSV to replace it.", icon=":material/dataset:")
try:
    df = load_messages_csv(uploaded or "data/sample_messages.csv")
except Exception as exc:
    st.error("Could not read the CSV. Fix the problems below and try again.")
    # Details can quote header names and IDs from the file: show them literally, never as Markdown.
    st.text(str(exc))
    st.stop()

missing = REQUIRED_COLUMNS - set(df.columns)
if missing:
    st.error(f"Missing required column(s): {', '.join(sorted(missing))}")
    st.caption("Required: message_id and message. Optional: received_at, candidate_name, subject.")
    st.stop()

for optional in ("received_at", "candidate_name", "subject"):
    if optional not in df.columns:
        df[optional] = ""

if df.empty:
    st.warning("No messages found in this CSV.")
    st.stop()

existing_generated = [column for column in GENERATED_COLUMNS if column in df.columns]
if existing_generated:
    st.info(
        f"This CSV already contains generated column(s): {', '.join(existing_generated)}. "
        "They have been refreshed: previous generated results and any human edits to "
        "draft_reply are replaced by the new results below and in the export."
    )
    df = df.drop(columns=existing_generated)

# Reviewer edits are kept per message_id for this dataset only, so rows hidden by the
# intent filter keep their edits, and a different upload never inherits them.
source_id = getattr(uploaded, "file_id", uploaded.name) if uploaded else "sample"
dataset_key = hashlib.sha256(f"{source_id}\n{df.to_csv(index=False)}".encode("utf-8")).hexdigest()[:12]
if st.session_state.get("draft_edits_dataset") != dataset_key:
    st.session_state["draft_edits_dataset"] = dataset_key
    st.session_state["draft_edits"] = {}
draft_edits = st.session_state["draft_edits"]

results = []
for _, row in df.iterrows():
    result = classify_message(row["message"], row["subject"])
    results.append({
        "intent": result.intent,
        "priority": result.priority,
        "reason": result.reason,
        "draft_reply": draft_reply(result.intent, row["candidate_name"]),
    })

out = pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)
high_count = int((out["priority"] == "high").sum())
c1, c2, c3 = st.columns(3)
c1.metric("Messages", len(out), border=True, icon=":material/inbox:")
c2.metric("Intent groups", out["intent"].nunique(), border=True, icon=":material/category:")
c3.metric("High-priority flags", high_count, border=True, icon=":material/priority_high:")

filter_col, export_col = st.columns([3, 2], vertical_alignment="bottom")
with filter_col:
    chosen_intent = st.selectbox(
        "Filter by intent", ["all"] + sorted(out["intent"].unique().tolist()), format_func=intent_label
    )
# Filled after the editors run, so the export always includes the latest edits.
export_slot = export_col.empty()
view = out if chosen_intent == "all" else out[out["intent"] == chosen_intent]

section("Inbox")
st.markdown(
    f'<div class="ip-count">Showing {len(view)} of {len(out)} messages · '
    f"{html.escape(intent_label(chosen_intent))} · open a card to review its suggested reply</div>",
    unsafe_allow_html=True,
)
for position, (_, row) in enumerate(view.iterrows()):
    name = escape_markdown(row["candidate_name"]) or "Unknown candidate"
    subject = escape_markdown(row["subject"]) or "No subject"
    label = f"{name} · {subject} · {row['intent']}"
    priority = row["priority"]
    with st.container(key=f"ip-card-{priority}-{position}"):
        with st.expander(label, expanded=(priority == "high"), icon=PRIORITY_ICONS.get(priority)):
            st.markdown(
                '<div class="ip-meta">'
                f'<span class="ip-pill ip-intent">{html.escape(intent_label(row["intent"]))}</span>'
                f'<span class="ip-pill ip-prio-{html.escape(priority)}">'
                f"{html.escape(PRIORITY_LABELS.get(priority, priority))}</span></div>"
                f'<div class="ip-reason">{html.escape(row["reason"])}</div>',
                unsafe_allow_html=True,
            )
            message_col, reply_col = st.columns(2, gap="medium")
            with message_col:
                st.markdown('<div class="ip-panel-label">Candidate message</div>', unsafe_allow_html=True)
                # Untrusted text: render literally, never as Markdown, links or images.
                if row["message"]:
                    st.text(row["message"])
                else:
                    st.write("_Empty message_")
            with reply_col:
                st.markdown(
                    '<div class="ip-panel-label ip-panel-label-ai">Suggested reply · template draft, edit before use</div>',
                    unsafe_allow_html=True,
                )
                message_id = row["message_id"]
                draft_edits[message_id] = st.text_area(
                    "Suggested reply — review and edit before using",
                    value=draft_edits.get(message_id, row["draft_reply"]),
                    key=f"draft_{dataset_key}_{message_id}",
                    height=170,
                    label_visibility="collapsed",
                )

out["draft_reply"] = [draft_edits.get(mid, draft) for mid, draft in zip(out["message_id"], out["draft_reply"])]

csv_bytes = protect_for_spreadsheet(out).to_csv(index=False).encode("utf-8")
with export_slot.container():
    st.download_button(
        "Export triage results as CSV",
        data=csv_bytes,
        file_name="inboxpilot_results.csv",
        mime="text/csv",
        type="primary",
        icon=":material/download:",
        width="stretch",
    )
st.warning("InboxPilot does not send messages. A human must review every draft.", icon=":material/person_check:")
