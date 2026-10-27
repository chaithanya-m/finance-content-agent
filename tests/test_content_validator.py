from src.content_post import InstagramPost
from src.content_validator import ContentValidator
from src.research.research_report import ResearchReport


VERIFIED_FACT = "RBI repo rate is 5.25%."


def make_report() -> ResearchReport:
    return ResearchReport(
        topic="RBI repo rate",
        research_question="What is the policy repo rate?",
        verified_facts=[
            {
                "fact": VERIFIED_FACT,
                "status": "verified",
                "evidence": [
                    {
                        "source_name": "Reserve Bank of India",
                        "source_url": "https://rbi.org.in",
                        "evidence_text": VERIFIED_FACT,
                        "support": "supporting",
                        "published_at": "2026-10-07",
                        "as_of_date": "2026-10-26",
                    }
                ],
                "notes": "Supported by an official source.",
            }
        ],
        sources=[
            {
                "source_name": "Reserve Bank of India",
                "source_url": "https://rbi.org.in",
                "published_at": "2026-10-07",
                "as_of_date": "2026-10-26",
            }
        ],
    )


def make_post(
    slides: list[str] | None = None,
    claims: list[str] | None = None,
    sources: list[str] | None = None,
) -> InstagramPost:
    return InstagramPost(
        topic="RBI repo rate",
        hook="What should you know about RBI repo rate?",
        slides=slides if slides is not None else [VERIFIED_FACT],
        caption=ContentValidator.SAFE_CAPTION,
        call_to_action=ContentValidator.SAFE_CALL_TO_ACTION,
        sources=sources if sources is not None else ["https://rbi.org.in"],
        claims=claims if claims is not None else [VERIFIED_FACT],
    )


def test_accepts_content_supported_by_verified_fact():
    validator = ContentValidator()

    assert validator.validate(make_post(), make_report()) is True


def test_rejects_claim_not_in_verified_facts():
    post = make_post(
        slides=["The RBI changed its rate this week."],
        claims=["The RBI changed its rate this week."],
    )

    assert ContentValidator().validate(post, make_report()) is False


def test_rejects_unsupported_number_in_post_text():
    post = make_post(
        slides=["The policy repo rate is 6.00%."],
        claims=[VERIFIED_FACT],
    )

    assert ContentValidator().validate(post, make_report()) is False


def test_rejects_invalid_source_url():
    post = make_post(sources=["not-a-valid-url"])

    assert ContentValidator().validate(post, make_report()) is False


def test_rejects_generated_prose_that_adds_a_financial_claim():
    post = make_post()
    post.caption = "Interest rate changes can increase your EMI."

    assert ContentValidator().validate(post, make_report()) is False


def test_requires_verified_claims_to_be_the_slide_text():
    post = make_post(slides=["Policy rates"])

    assert ContentValidator().validate(post, make_report()) is False


def test_rejects_source_url_not_present_in_research_report():
    post = make_post(sources=["https://example.com/source"])

    assert ContentValidator().validate(post, make_report()) is False


def test_rejects_verified_but_off_topic_home_loan_claim():
    report = make_report()
    irrelevant_claim = "Lenders must explain how loan rates affect borrowers."
    report.verified_facts[0]["fact"] = irrelevant_claim
    report.verified_facts[0]["evidence"][0]["evidence_text"] = irrelevant_claim
    post = make_post(slides=[irrelevant_claim], claims=[irrelevant_claim])

    assert ContentValidator().validate(post, report) is False


def test_rejects_draft_for_a_different_requested_topic():
    post = make_post()
    post.topic = "Home loan EMI"

    assert ContentValidator().validate(post, make_report()) is False


def test_requires_all_verified_claims_in_the_carousel():
    report = make_report()
    second_fact = {
        "fact": "The rate is set by the RBI.",
        "status": "verified",
        "evidence": [
            {
                "source_name": "Reserve Bank of India",
                "source_url": "https://rbi.org.in",
                "evidence_text": "The rate is set by the RBI.",
                "support": "supporting",
            }
        ],
        "notes": "Quoted and verified.",
    }
    report.verified_facts.append(second_fact)

    assert ContentValidator().validate(make_post(), report) is False


def test_requires_sources_for_each_verified_claim_in_the_output():
    report = make_report()
    report.sources.append(
        {
            "source_name": "Reserve Bank of India",
            "source_url": "https://www.rbi.org.in/decision",
            "published_at": "2026-10-07",
            "as_of_date": None,
        }
    )
    report.verified_facts[0]["evidence"].append(
        {
            "source_name": "Reserve Bank of India",
            "source_url": "https://www.rbi.org.in/decision",
            "evidence_text": VERIFIED_FACT,
            "support": "supporting",
            "published_at": "2026-10-07",
            "as_of_date": None,
        }
    )
    post = make_post(sources=["https://rbi.org.in"])

    assert ContentValidator().validate(post, report) is False
