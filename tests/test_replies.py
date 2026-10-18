from classifier import classify_message
from reply_generator import draft_reply

OFFER_ASSERTIONS = ("the offer", "your offer", "an offer", "offer has", "offer is",
                    "approved", "congratulations", "pleased to")

def assert_no_offer_assertion(draft):
    lowered = draft.lower()
    for phrase in OFFER_ASSERTIONS:
        assert phrase not in lowered, phrase

def test_reply_includes_candidate_name():
    draft = draft_reply("application_status", "Ada")
    assert draft.startswith("Hello Ada,")

def test_reply_never_claims_a_specific_outcome():
    for intent in ("interview_scheduling", "application_status", "offer_discussion",
                   "withdrawal", "document_request", "general_question", "other"):
        draft = draft_reply(intent, "Taylor")
        assert "you got the job" not in draft.lower()
        assert "your offer is approved" not in draft.lower()

def test_unknown_intent_uses_safe_fallback():
    assert "review your message" in draft_reply("unknown").lower()

def test_salary_range_question_without_offer_gets_neutral_reply():
    result = classify_message("What is the salary range for this role?")
    assert result.intent == "other"
    draft = draft_reply(result.intent, "Ada")
    assert draft == draft_reply("other", "Ada")
    assert_no_offer_assertion(draft)

def test_offer_details_question_does_not_confirm_an_offer_exists():
    result = classify_message("Could you share the offer details for this position?")
    assert result.intent == "offer_discussion"
    assert_no_offer_assertion(draft_reply(result.intent, "Ada"))

def test_offer_discussion_reply_keeps_greeting_and_structure():
    greeting, body, sign_off = draft_reply("offer_discussion", "Ada").split("\n\n")
    assert greeting == "Hello Ada,"
    assert body.startswith("Thank you for your message.")
    assert sign_off == "Best regards,\nRecruiting Team"
    assert draft_reply("offer_discussion").startswith("Hello,\n\n")

def test_offer_discussion_reply_never_asserts_an_offer():
    for name in ("Ada", ""):
        assert_no_offer_assertion(draft_reply("offer_discussion", name))
