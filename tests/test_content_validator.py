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
                "evidence": [],
                "notes": "Supported by an official source.",
            }
        ],
        sources=[
            {
                "source_name": "Reserve Bank of India",
                "source_url": "https://rbi.org.in",
                "published_at": None,
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
