from src.research.local_research_agent import (
    LocalResearchAgent,
    _PageTextParser,
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
    statement = (
        "A home loan interest rate change affects the monthly EMI amount."
    )
    monkeypatch.setattr(agent.discovery, "discover", lambda request: [candidate])
    monkeypatch.setattr(
        agent,
        "_fetch_page",
        lambda source: f"Opening text.\n{statement}\nClosing text.",
    )

    report = agent.research(make_request())

    assert len(report.verified_facts) == 1
    fact = report.verified_facts[0]
    assert fact["fact"] == statement
    assert fact["evidence"][0]["evidence_text"] == statement
    assert fact["evidence"][0]["source_url"] == candidate.source_url
    assert report.sources[0]["source_url"] == candidate.source_url


def test_research_keeps_table_label_and_rate_together(monkeypatch):
    agent = LocalResearchAgent()
    candidate = make_candidate()
    monkeypatch.setattr(agent.discovery, "discover", lambda request: [candidate])
    monkeypatch.setattr(
        agent,
        "_fetch_page",
        lambda source: "Policy Repo Rate\n:\n5.50%",
    )
    request = ResearchRequest(
        topic="What is the RBI repo rate?",
        research_question="What is the current repo rate?",
    )

    report = agent.research(request)

    assert [fact["fact"] for fact in report.verified_facts] == [
        "Policy Repo Rate : 5.50%"
    ]
    assert report.important_numbers == [{"number": "5.50%"}]


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
