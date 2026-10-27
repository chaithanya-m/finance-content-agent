import json

import pytest

from src.research.research_report import ResearchReport
from src.research_content_generator import ResearchContentGenerator


def make_report() -> ResearchReport:
    return ResearchReport(
        topic="Home loan interest rates",
        research_question="How do home loan interest rates work?",
        verified_facts=[
            {
                "fact": "A home loan interest rate change affects the monthly EMI amount.",
                "status": "verified",
                "evidence": [],
                "notes": "Quoted verbatim from an official source.",
            }
        ],
    )


def test_ollama_timeout_is_reported_without_fallback(monkeypatch):
    def timeout(*args, **kwargs):
        raise TimeoutError("request timed out")

    monkeypatch.setattr(
        "src.research_content_generator.urllib.request.urlopen",
        timeout,
    )

    with pytest.raises(RuntimeError, match="timed out"):
        ResearchContentGenerator().generate(make_report())


def test_malformed_ollama_response_is_rejected(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"response": []}).encode()

    monkeypatch.setattr(
        "src.research_content_generator.urllib.request.urlopen",
        lambda *args, **kwargs: Response(),
    )

    with pytest.raises(ValueError, match="missing generated text"):
        ResearchContentGenerator().generate(make_report())


def test_non_object_generated_json_is_rejected(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"response": "[]"}).encode()

    monkeypatch.setattr(
        "src.research_content_generator.urllib.request.urlopen",
        lambda *args, **kwargs: Response(),
    )

    with pytest.raises(ValueError, match="JSON object"):
        ResearchContentGenerator().generate(make_report())


def test_carousel_contains_every_verified_fact_even_if_model_omits_one(monkeypatch):
    report = make_report()
    second_fact = {
        "fact": "A benchmark rate can affect loan tenure.",
        "status": "verified",
        "evidence": [],
        "notes": "Verified.",
    }
    report.verified_facts.append(second_fact)
    model_output = {
        "topic": report.topic,
        "hook": "What should you know about Home loan interest rates?",
        "slides": ["model omitted the second verified fact"],
        "caption": "Educational content only; this is not personalized financial advice.",
        "call_to_action": "Review the cited sources before sharing.",
        "sources": ["https://rbi.org.in"],
        "claims": ["model omitted the second verified fact"],
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"response": json.dumps(model_output)}).encode()

    monkeypatch.setattr(
        "src.research_content_generator.urllib.request.urlopen",
        lambda *args, **kwargs: Response(),
    )

    post = ResearchContentGenerator().generate(report)

    assert post.slides == [fact["fact"] for fact in report.verified_facts]
    assert post.claims == post.slides
