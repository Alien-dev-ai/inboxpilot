from classifier import INTENTS, classify_message

UNMATCHED_REASON = "No confident keyword match; human review required."

def assert_unmatched_for_review(result, message=""):
    """Unmatched, non-urgent text goes to human review as other/normal with no matched terms."""
    assert (result.intent, result.priority, result.reason, result.matched_terms) == (
        "other", "normal", UNMATCHED_REASON, ()
    ), message

def test_interview_message_is_classified():
    result = classify_message("Can we reschedule the interview time?")
    assert result.intent == "interview_scheduling"
    assert result.priority == "normal"
    assert result.matched_terms == ("reschedule", "interview time")

def test_application_status_message_is_classified():
    result = classify_message("Any update on my application?")
    assert result.intent == "application_status"
    assert result.priority == "normal"
    assert result.reason == "Matched application status phrase(s): any update, update on my application."

def test_withdrawal_takes_precedence_over_general_followup():
    result = classify_message("I am following up, but I want to withdraw my application.")
    assert result.intent == "withdrawal"

def test_urgent_language_flags_high_priority():
    result = classify_message("I cannot attend the interview today and need to reschedule urgently.")
    assert result.intent == "interview_scheduling"
    assert result.priority == "high"
    assert result.reason == (
        "Matched interview scheduling phrase(s): reschedule. "
        "Time-sensitive wording detected; verify urgency manually."
    )

def test_empty_message_is_reviewed_not_crashed():
    for empty in ("", "   ", "\n\t"):
        result = classify_message(empty)
        assert (result.intent, result.priority, result.reason, result.matched_terms) == (
            "other", "normal", "Message is empty; human review required.", ()
        )

def test_unknown_message_defaults_to_other():
    result = classify_message("Greetings, I hope your week is going well.")
    assert_unmatched_for_review(result)
    assert result.intent in INTENTS

def test_urgent_message_with_matched_intent_is_high_priority():
    result = classify_message("I need to reschedule the interview, it is urgent.")
    assert result.intent == "interview_scheduling"
    assert result.priority == "high"
    assert "time-sensitive" in result.reason.lower()

def test_urgent_message_without_matched_intent_is_high_priority():
    result = classify_message("I can't make it to the call today, urgent")
    assert result.intent == "other"
    assert result.priority == "high"
    assert "review" in result.reason.lower()
    assert "time-sensitive" in result.reason.lower()

def test_non_urgent_unmatched_message_stays_normal_priority():
    result = classify_message("Greetings, I hope your week is going well.")
    assert result.intent == "other"
    assert result.priority == "normal"

def test_question_about_next_steps_is_general_question():
    result = classify_message(
        "I have a question about the next steps and would appreciate more information.", "Question"
    )
    assert result.intent == "general_question"
    assert result.priority == "normal"

def test_application_update_request_remains_application_status():
    result = classify_message("I am following up to ask if there is any update on my application.")
    assert result.intent == "application_status"

def test_strong_status_phrase_still_beats_question_phrase():
    result = classify_message("Any update on my application? I have a question about the role.")
    assert result.intent == "application_status"

def test_next_steps_without_question_phrase_remains_application_status():
    result = classify_message("What are the next steps for my application?")
    assert result.intent == "application_status"

def test_documentation_is_not_a_document_request():
    assert_unmatched_for_review(classify_message("Is there documentation on the benefits?"))

def test_resume_as_a_verb_is_not_a_resume_request():
    assert_unmatched_for_review(classify_message("Can we resume our conversation?"))

def test_genuine_document_and_resume_requests_still_match():
    for message, term in [
        ("I have attached my resume for the role.", "resume"),
        ("Should I send an updated resume?", "resume"),
        ("Please find my résumé attached.", "résumé"),
        ("Which document should I include with my application?", "document"),
        ("Which documents do you need from me?", "document"),
    ]:
        result = classify_message(message)
        assert result.intent == "document_request", message
        assert term in result.matched_terms, message

def test_salary_range_question_is_not_offer_discussion():
    assert_unmatched_for_review(classify_message("What is the salary range for this role?"))

def test_genuine_offer_questions_still_match_offer_discussion():
    for message in [
        "Thank you for the offer. Could you clarify the salary and compensation details?",
        "Is the salary in the offer letter negotiable?",
        "I'd like to discuss the salary you offered.",
    ]:
        result = classify_message(message)
        assert result.intent == "offer_discussion", message

def test_negated_withdrawal_is_not_classified_as_withdrawal():
    assert_unmatched_for_review(classify_message("I'm not going to withdraw my application."))

def test_other_negated_withdrawal_phrasings_are_not_withdrawals():
    for message in [
        "I don't want to withdraw my application.",
        "I do not wish to withdraw my candidacy.",
        "I will never withdraw my application.",
        "Please do not remove my application.",
        "I have no plans to withdraw my application.",
        "I did not accept another offer.",
    ]:
        assert_unmatched_for_review(classify_message(message), message)

def test_genuine_withdrawals_still_match():
    for message in [
        "I would like to withdraw my application because I have accepted another offer.",
        "Please withdraw my application.",
        "I'm no longer interested in this role.",
        "I can't continue with the process, so please withdraw my application.",
        "I cannot attend any more interviews and want to withdraw my application.",
        "Not an easy decision, but I want to withdraw my application.",
        "I'm not going to withdraw my application. Actually, on reflection, please withdraw my application.",
    ]:
        result = classify_message(message)
        assert result.intent == "withdrawal", message

def test_negation_handling_does_not_affect_other_intents():
    result = classify_message("I cannot attend the interview today and need to reschedule urgently.")
    assert result.intent == "interview_scheduling"
    result = classify_message("I have not heard back about my application status.")
    assert result.intent == "application_status"

def test_negated_withdrawal_falls_through_to_other_matching_intent():
    result = classify_message("I don't want to withdraw my application; any update on my application?")
    assert result.intent == "application_status"

def test_plain_mention_of_today_is_not_high_priority():
    result = classify_message("I submitted my documents today.")
    assert result.intent == "document_request"
    assert result.priority == "normal"
    assert "time-sensitive" not in result.reason.lower()

def test_genuine_urgent_wording_is_still_high_priority():
    for message in [
        "I cannot attend the interview today and need to reschedule urgently.",
        "This is urgent: please call me.",
        "I need this within an hour, please.",
        "Please reply by today.",
        "I need an answer by end of today.",
    ]:
        assert classify_message(message).priority == "high", message

def test_deadline_wording_keeps_high_priority():
    for message in [
        "The deadline to accept is tomorrow; could you clarify the offer letter?",
        "My offer expires on Friday and I have questions about compensation.",
    ]:
        result = classify_message(message)
        assert result.priority == "high", message
        assert "time-sensitive" in result.reason.lower()

def test_sample_rows_keep_expected_intents_and_priorities():
    import pandas as pd
    df = pd.read_csv("data/sample_messages.csv", dtype=str).fillna("")
    expected = {
        "M001": ("interview_scheduling", "normal"), "M002": ("application_status", "normal"),
        "M003": ("offer_discussion", "normal"), "M004": ("withdrawal", "normal"),
        "M005": ("document_request", "normal"), "M006": ("general_question", "normal"),
        "M007": ("interview_scheduling", "high"), "M008": ("other", "low"),
        "M009": ("other", "normal"), "M010": ("document_request", "normal"),
    }
    actual = {
        row["message_id"]: (lambda r: (r.intent, r.priority))(classify_message(row["message"], row["subject"]))
        for _, row in df.iterrows()
    }
    assert actual == expected

def test_courtesy_only_message_is_low_priority():
    for message in [
        "Hello, just wanted to say thank you for your time.",
        "Thanks for your time.",
        "Thank you for your time.",
    ]:
        result = classify_message(message)
        assert result.intent == "other", message
        assert result.priority == "low", message
        assert "courtesy" in result.reason.lower()
        assert "review" in result.reason.lower()

def test_urgent_wording_beats_courtesy_phrase():
    for message in ["Thank you for your time. This is urgent.", "Thank you for your time, the deadline is Friday."]:
        assert classify_message(message).priority == "high", message

def test_matched_request_beats_courtesy_phrase():
    result = classify_message("Thank you for your time. Any update on my application?")
    assert (result.intent, result.priority) == ("application_status", "normal")
    result = classify_message("Just wanted to say thank you for the interview; I'd like to withdraw my application.")
    assert (result.intent, result.priority) == ("withdrawal", "normal")

def test_courtesy_phrase_with_unmatched_request_stays_normal():
    for message in ["Thank you for your time. Can you call me back?", "Thanks for your time, please keep me posted."]:
        result = classify_message(message)
        assert (result.intent, result.priority) == ("other", "normal"), message

def test_empty_and_unclear_messages_stay_normal():
    assert classify_message("").priority == "normal"
    assert classify_message("Thank you!").priority == "normal"
    assert classify_message("Greetings, I hope your week is going well.").priority == "normal"

def test_priority_and_intent_precedence_boundaries():
    cases = [
        # (message, intent, priority, reason)
        ("Thank you for your time.", "other", "low",
         "Courtesy phrase(s) only: thank you for your time. No request detected; human review still required."),
        ("Thank you for your time. This is urgent.", "other", "high",
         UNMATCHED_REASON + " Time-sensitive wording detected; verify urgency manually."),
        ("Thank you for your time. Any update on my application?", "application_status", "normal",
         "Matched application status phrase(s): any update, update on my application."),
        ("Please withdraw my application, it is urgent.", "withdrawal", "high",
         "Matched withdrawal phrase(s): withdraw my application. "
         "Time-sensitive wording detected; verify urgency manually."),
        ("Greetings, I hope your week is going well.", "other", "normal", UNMATCHED_REASON),
    ]
    for message, intent, priority, reason in cases:
        result = classify_message(message)
        assert (result.intent, result.priority, result.reason) == (intent, priority, reason), message

def test_every_priority_label_is_reachable_and_valid():
    priorities = {classify_message(m).priority for m in (
        "This is urgent.", "Any update on my application?", "Thanks for your time.",
    )}
    assert priorities == {"high", "normal", "low"}

def test_negation_separated_by_a_comma_enclosed_aside_is_still_negation():
    for message in [
        "I do not, under any circumstances, want to withdraw my application.",
        "I will not, after all, withdraw my application.",
    ]:
        assert_unmatched_for_review(classify_message(message), message)

def test_single_comma_still_ends_the_negated_clause():
    for message in [
        "No, I want to withdraw my application.",
        "Yes, no problem, I want to withdraw my application.",
        "I cannot continue, sadly, and want to withdraw my application.",
        "I cannot continue, unfortunately, so withdraw my application.",
        "I can't come, but anyway, I want to withdraw my application.",
    ]:
        result = classify_message(message)
        assert (result.intent, result.matched_terms) == ("withdrawal", ("withdraw my application",)), message

def test_resume_as_a_verb_after_and_is_not_a_resume_request():
    for message in ["Can we pause and resume later?", "Stop and resume the interview?"]:
        assert_unmatched_for_review(classify_message(message), message)

def test_resume_listed_with_other_application_documents_still_matches():
    for message in [
        "Here is my CV and resume.",
        "My CV or resume?",
        "Here is my cover letter and resume.",
        "Attached are my portfolio and resume.",
    ]:
        result = classify_message(message)
        assert result.intent == "document_request", message
        assert "resume" in result.matched_terms, message

def test_withdrawal_question_stays_withdrawal_with_neutral_reason():
    # Decision: questions about withdrawing stay "withdrawal"; the reason only names the matched phrase.
    result = classify_message("Should I withdraw my application or not?")
    assert (result.intent, result.priority, result.reason) == (
        "withdrawal", "normal", "Matched withdrawal phrase(s): withdraw my application."
    )

def test_compensation_range_and_salary_expectations_do_not_imply_an_offer():
    for message in [
        "What is the compensation range for this role?",
        "What are the salary expectations for this role?",
        "What are your salary expectations?",
        "Compensation-range question: what is it?",
    ]:
        assert_unmatched_for_review(classify_message(message), message)

def test_genuine_offer_messages_with_compensation_wording_still_match():
    cases = [
        ("Is the compensation range in my offer letter negotiable?", ("offer letter",)),
        ("My salary expectations are above the employment offer; can we negotiate?",
         ("negotiate", "employment offer")),
        ("Could you explain the compensation package in the offer details?", ("compensation", "offer details")),
    ]
    for message, terms in cases:
        result = classify_message(message)
        assert result.intent == "offer_discussion", message
        assert result.matched_terms == terms, message

def test_past_deadline_wording_stays_high_priority():
    # Decision: "deadline" stays an urgency signal; no date interpretation.
    result = classify_message("The deadline passed last month.")
    assert (result.intent, result.priority, result.reason) == (
        "other", "high", UNMATCHED_REASON + " Time-sensitive wording detected; verify urgency manually."
    )
