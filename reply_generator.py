"""Conservative, non-sending reply templates for human review."""
from __future__ import annotations

def draft_reply(intent: str, candidate_name: object = "") -> str:
    name = str(candidate_name or "").strip()
    greeting = f"Hello {name}," if name else "Hello,"
    templates = {
        "interview_scheduling": "Thank you for your message. We’ll review the scheduling details and follow up with the next steps. Please share any relevant availability if you have not already done so.",
        "application_status": "Thank you for following up and for your continued interest. Your message has been received. We’ll share an update when one is available.",
        "offer_discussion": "Thank you for your message. We’ve noted your question about compensation or related details. The relevant team will need to review it before we can provide a confirmed response.",
        "withdrawal": "Thank you for letting us know. We acknowledge your request and will route it to the relevant team for processing.",
        "document_request": "Thank you for your message. Please refer to the instructions provided for the role and let us know which document or submission detail needs clarification.",
        "general_question": "Thank you for reaching out. We’ve noted your question and will review it before providing a confirmed response.",
        "other": "Thank you for reaching out. We need to review your message to make sure we provide an accurate response.",
    }
    body = templates.get(intent, templates["other"])
    return f"{greeting}\n\n{body}\n\nBest regards,\nRecruiting Team"
