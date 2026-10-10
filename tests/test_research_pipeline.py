from src.research.claim import Claim, Evidence
from src.research.evidence import EvidenceRecord, SourceDocument
from src.research import research_pipeline


def make_evidence(claim_text: str, url: str) -> EvidenceRecord:
    source = SourceDocument(
        source_name="Reserve Bank of India",
        source_url=url,
        title="Test source",
        content="Test content",
        source_type="official",
        published_at="2026-10-01",
    )
    return EvidenceRecord(
        claim=claim_text,
        source=source,
        supporting_text="Policy repo rate is 5.25 per cent.",
    )


def test_build_report_preserves_claim_status_evidence_and_sources(monkeypatch):
    verified = Claim(
        claim="RBI repo rate is 5.25%.",
        status="verified",
        evidence=[
            Evidence(
                source_name="Reserve Bank of India",
                source_url="https://rbi.org.in",
                evidence_text="Policy repo rate is 5.25 per cent.",
                support="supporting",
                published_at="2026-10-01",
            )
        ],
        notes="Resolved using an official source.",
    )
    unverified = Claim(
        claim="An unsupported finance claim.",
        status="unverified",
        notes="No supporting evidence.",
    )
    conflicting = Claim(
        claim="A conflicting finance claim.",
        status="conflicting",
        notes="Evidence could not be resolved.",
    )

    results = {
        "verified claim": verified,
        "unverified claim": unverified,
        "conflicting claim": conflicting,
    }

    monkeypatch.setattr(
        research_pipeline,
        "research_claim",
        lambda claim_text, evidence_records: results[claim_text],
    )

    evidence_by_claim = {
        "verified claim": [
            make_evidence("verified claim", "https://rbi.org.in")
        ],
        "unverified claim": [
            make_evidence("unverified claim", "https://rbi.org.in")
        ],
        "conflicting claim": [
            make_evidence("conflicting claim", "https://example.com")
        ],
    }

    report = research_pipeline.build_research_report(
        topic="Indian interest rates",
        research_question="What is the repo rate?",
        claims=list(results),
        evidence_by_claim=evidence_by_claim,
    )

    assert report.verified_facts == [
        {
            "fact": verified.claim,
            "status": "verified",
            "evidence": [
                {
                    "source_name": "Reserve Bank of India",
                    "source_url": "https://rbi.org.in",
                    "evidence_text": "Policy repo rate is 5.25 per cent.",
                    "support": "supporting",
                    "published_at": "2026-10-01",
                }
            ],
            "notes": "Resolved using an official source.",
        }
    ]

    assert report.unverified_claims == [
        {
            "fact": unverified.claim,
            "status": "unverified",
            "evidence": [],
            "notes": "No supporting evidence.",
        },
        {
            "fact": conflicting.claim,
            "status": "conflicting",
            "evidence": [],
            "notes": "Evidence could not be resolved.",
        },
    ]

    assert report.sources == [
        {
            "source_name": "Reserve Bank of India",
            "source_url": "https://rbi.org.in",
            "published_at": "2026-10-01",
        },
        {
            "source_name": "Reserve Bank of India",
            "source_url": "https://example.com",
            "published_at": "2026-10-01",
        },
    ]
