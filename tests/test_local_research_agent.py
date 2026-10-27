from src.research.local_research_agent import (
    LocalResearchAgent,
    _PageTextParser,
    _repo_rate_observation,
    _source_dates,
    _relevant_statements,
)
from src.research.research_request import ResearchRequest
from src.research.source_discovery import SourceCandidate


def make_request() -> ResearchRequest:
    return ResearchRequest(
        topic="How do interest rates affect home loan EMIs in India?",
        research_question="Explain the effect of home loan interest rates.",
    )


def make_candidate() -> SourceCandidate:
    return SourceCandidate(
        source_name="Reserve Bank of India",
        source_url="https://www.rbi.org.in/example",
        title="Home loan directions",
        source_type="official",
        category="home_loan",
    )


def test_page_parser_skips_navigation_and_recovers_at_main_content():
    parser = _PageTextParser()
    parser.feed(
        "<header><nav>Navigation text"
        "<main><p>Official source statement about home loan rates.</p></main>"
    )
    text = "".join(parser.parts)

    assert "Navigation text" not in text
    assert "Official source statement" in text


def test_research_verifies_verbatim_source_statement_and_preserves_url(
    monkeypatch,
):
    agent = LocalResearchAgent()
    candidate = make_candidate()
    quote = (
        "At loan sanction, regulated lenders must tell borrowers that "
        "benchmark changes may affect their home loan EMI or tenure."
    )
    claim = (
        "At sanction, lenders must explain how benchmark changes can affect "
        "a home loan's EMI or term."
    )
    monkeypatch.setattr(agent.discovery, "discover", lambda request: [candidate])
    monkeypatch.setattr(
        agent,
        "_fetch_page",
        lambda source: f"Opening text.\n{quote}\nClosing text.",
    )
    monkeypatch.setattr(
        agent,
        "_make_claims",
        lambda request, items: [
            {"id": "C1", "claim": claim, "evidence_ids": ["Q1"]}
        ],
    )
    monkeypatch.setattr(
        agent,
        "_verify_claims",
        lambda claims, quote_map: {"C1": "supported"},
    )

    report = agent.research(make_request())

    assert len(report.verified_facts) == 1
    fact = report.verified_facts[0]
    assert fact["fact"] == claim
    assert fact["fact"] != quote
    assert fact["evidence"][0]["evidence_text"] == quote
    assert fact["evidence"][0]["source_url"] == candidate.source_url
    assert report.sources[0]["source_url"] == candidate.source_url


def test_paraphrase_stays_unverified_when_independent_check_is_insufficient(
    monkeypatch,
):
    agent = LocalResearchAgent()
    candidate = make_candidate()
    quote = (
        "At the time of sanction of EMI based floating rate housing loans, "
        "UCBs must assess the repayment capacity of borrowers."
    )
    claim = "UCBs must assess repayment capacity for floating-rate housing loans."
    monkeypatch.setattr(agent.discovery, "discover", lambda request: [candidate])
    monkeypatch.setattr(
        agent,
        "_fetch_page",
        lambda source: f"Opening text.\n{quote}\nClosing text.",
    )
    monkeypatch.setattr(
        agent,
        "_make_claims",
        lambda request, items: [
            {"id": "C1", "claim": claim, "evidence_ids": ["Q1"]}
        ],
    )
    monkeypatch.setattr(
        agent,
        "_verify_claims",
        lambda claims, quote_map: {"C1": "insufficient"},
    )

    report = agent.research(make_request())

    assert report.verified_facts == []
    assert report.unverified_claims[0]["fact"] == claim
    assert report.unverified_claims[0]["evidence"][0]["evidence_text"] == quote
    assert report.unverified_claims[0]["evidence"][0]["support"] == "not_relevant"


def test_repo_rate_discovery_does_not_include_home_loan_clauses():
    from src.research.source_discovery import ResearchSourceDiscovery

    request = ResearchRequest(
        "What is the RBI repo rate and how does it affect borrowers?",
        "Explain the repo rate.",
    )
    candidates = ResearchSourceDiscovery().discover(request)
    urls = {candidate.source_url for candidate in candidates}

    assert all(candidate.category == "repo_rate" for candidate in candidates)
    assert "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12529" not in urls
    assert any("PressReleaseDisplay" in url for url in urls)

    home_request = ResearchRequest(
        "How do interest rates affect home loan EMIs in India?",
        "Explain home-loan EMI changes.",
    )
    home_sources = ResearchSourceDiscovery().discover(home_request)
    assert all(candidate.category == "home_loan" for candidate in home_sources)
    assert all("PressReleaseDisplay" not in candidate.source_url for candidate in home_sources)
    assert all(
        "BS_ViewMasDirections.aspx?id=12529" not in candidate.source_url
        for candidate in home_sources
    )


def test_repo_rate_relevance_filter_excludes_loan_reset_clauses():
    content = (
        "The policy repo rate was raised by 25 basis points to 5.50 per cent.\n"
        "At the time of reset, lenders may offer borrowers a fixed rate."
    )

    statements = _relevant_statements(content, "RBI repo rate", "repo_rate")

    assert len(statements) == 1
    assert "repo rate" in statements[0].casefold()
    assert "borrowers" not in statements[0].casefold()


def test_repo_rate_parser_keeps_metric_label_and_value_together():
    assert _repo_rate_observation("Policy Repo Rate\n:\n5.50%") == (
        "Policy Repo Rate is 5.50%.",
        "Policy Repo Rate : 5.50%",
    )


def test_claim_paraphrase_must_be_grounded_beyond_model_verdict(monkeypatch):
    agent = LocalResearchAgent()
    quote_items = [
        {
            "id": "Q1",
            "text": (
                "UCBs can decide margins and grant housing loans depending "
                "on the borrower's repayment capacity."
            ),
            "category": "home_loan",
        }
    ]
    monkeypatch.setattr(
        agent,
        "_ask_ollama",
        lambda prompt, num_predict: {
            "claims": [
                {
                    "claim": (
                        "Interest rates change a home loan's monthly EMI."
                    ),
                    "evidence_ids": ["Q1"],
                }
            ]
        },
    )

    claims = agent._make_claims(make_request(), quote_items)

    assert claims == []


def test_home_loan_claims_are_short_scoped_paraphrases_of_each_quote():
    agent = LocalResearchAgent()
    quotes = [
        {
            "id": "Q1",
            "text": (
                "At the time of sanction of EMI based floating rate housing loans, "
                "UCBs are required to take into account the repayment capacity of "
                "borrowers to ensure that adequate headroom/margin is available "
                "for elongation of tenor and/or increase in EMI, in the scenario "
                "of possible increase in the benchmark rate during the tenor "
                "of the loan."
            ),
            "category": "home_loan",
        },
        {
            "id": "Q2",
            "text": (
                "Further, UCBs are advised to put in place an appropriate policy "
                "framework for reset of floating interest rates on EMI based "
                "housing loans."
            ),
            "category": "home_loan",
        },
        {
            "id": "Q3",
            "text": (
                "UCBs are not permitted to charge foreclosure penalties on "
                "floating-rate home loans."
            ),
            "category": "home_loan",
        },
    ]

    claims = agent._make_claims(make_request(), quotes)

    assert [claim["evidence_ids"] for claim in claims] == [["Q1"], ["Q2"]]
    assert all(len(claim["claim"]) <= 180 for claim in claims)
    assert all(claim["claim"] != quotes[index]["text"] for index, claim in enumerate(claims))


def test_source_as_of_and_update_dates_are_preserved():
    assert _source_dates("(As at 1.00pm of October 26, 2026)") == (
        None,
        "2026-10-26",
    )
    assert _source_dates("Updated as on October 1, 2025") == (
        "2025-10-01",
        None,
    )


def test_current_repo_rate_requires_matching_dated_authoritative_sources():
    agent = LocalResearchAgent()
    decision = SourceCandidate(
        "Reserve Bank of India",
        "https://www.rbi.org.in/decision",
        "MPC decision",
        "official",
        published_at="2026-10-07",
        category="repo_rate",
    )
    current_rates = SourceCandidate(
        "Reserve Bank of India",
        "https://www.rbi.org.in/current-rates",
        "Current RBI rates",
        "official",
        category="repo_rate",
        as_of_date="2026-10-26",
    )
    pages = [
        {
            "candidate": decision,
            "content": (
                "The MPC voted to increase the policy repo rate to "
                "5.50 per cent."
            ),
        },
        {
            "candidate": current_rates,
            "content": "Policy Repo Rate : 5.50%",
        },
    ]

    report = agent._research_repo_rate(
        ResearchRequest("What is the RBI repo rate?", "Current repo rate?"),
        pages,
    )

    assert len(report.verified_facts) == 1
    fact = report.verified_facts[0]
    assert fact["fact"] == (
        "The RBI policy repo rate is 5.50% as of October 26, 2026."
    )
    assert {item["source_url"] for item in fact["evidence"]} == {
        decision.source_url,
        current_rates.source_url,
    }
    assert {item["published_at"] for item in fact["evidence"]} == {
        "2026-10-07",
        None,
    }
    assert {item["as_of_date"] for item in fact["evidence"]} == {
        None,
        "2026-10-26",
    }


def test_conflicting_current_repo_rate_values_are_not_verified():
    agent = LocalResearchAgent()
    decision = SourceCandidate(
        "Reserve Bank of India",
        "https://www.rbi.org.in/decision",
        "MPC decision",
        "official",
        published_at="2026-10-07",
        category="repo_rate",
    )
    current_rates = SourceCandidate(
        "Reserve Bank of India",
        "https://www.rbi.org.in/current-rates",
        "Current RBI rates",
        "official",
        category="repo_rate",
        as_of_date="2026-10-26",
    )
    pages = [
        {
            "candidate": decision,
            "content": (
                "The MPC voted to increase the policy repo rate to "
                "5.50 per cent."
            ),
        },
        {
            "candidate": current_rates,
            "content": "Policy Repo Rate : 5.25%",
        },
    ]

    report = agent._research_repo_rate(
        ResearchRequest("What is the RBI repo rate?", "Current repo rate?"),
        pages,
    )

    assert report.verified_facts == []
    assert len(report.unverified_claims) == 1
    assert report.unverified_claims[0]["status"] == "conflicting"
    assert {
        item["support"]
        for item in report.unverified_claims[0]["evidence"]
    } == {"supporting", "contradicting"}


def test_repo_rate_values_with_different_decimal_format_are_equal():
    agent = LocalResearchAgent()
    decision = SourceCandidate(
        "Reserve Bank of India",
        "https://www.rbi.org.in/decision",
        "MPC decision",
        "official",
        published_at="2026-10-07",
        category="repo_rate",
    )
    current_rates = SourceCandidate(
        "Reserve Bank of India",
        "https://www.rbi.org.in/current-rates",
        "Current RBI rates",
        "official",
        category="repo_rate",
        as_of_date="2026-10-26",
    )
    pages = [
        {
            "candidate": decision,
            "content": "The MPC set the policy repo rate to 5.5 per cent.",
        },
        {
            "candidate": current_rates,
            "content": "Policy Repo Rate : 5.50%",
        },
    ]

    report = agent._research_repo_rate(
        ResearchRequest("What is the RBI repo rate?", "Current repo rate?"),
        pages,
    )

    assert len(report.verified_facts) == 1
    assert report.unverified_claims == []


def test_unavailable_sources_return_unverified_research(monkeypatch):
    agent = LocalResearchAgent()
    monkeypatch.setattr(
        agent.discovery,
        "discover",
        lambda request: [make_candidate()],
    )
    monkeypatch.setattr(agent, "_fetch_page", lambda source: None)

    report = agent.research(make_request())

    assert report.verified_facts == []
    assert report.unverified_claims[0]["status"] == "unverified"
    assert "unavailable" in report.unverified_claims[0]["notes"]


def test_unmapped_topic_reports_missing_source_mapping(monkeypatch):
    agent = LocalResearchAgent()
    monkeypatch.setattr(agent.discovery, "discover", lambda request: [])

    report = agent.research(
        ResearchRequest("Unmapped subject", "Research an unmapped subject.")
    )

    assert report.verified_facts == []
    assert "No curated sources" in report.unverified_claims[0]["fact"]
