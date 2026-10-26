from src.research.claim import Claim
from src.research.evidence import EvidenceRecord, SourceDocument
from src.research.claim_verifier import evidence_relation
from src.research.research_service import research_claim


def make_evidence(
    text: str,
    url: str = "https://rbi.org.in",
) -> EvidenceRecord:
    source = SourceDocument(
        source_name="Reserve Bank of India",
        source_url=url,
        title="Test",
        content=text,
        source_type="official",
    )

    return EvidenceRecord(
        claim="RBI repo rate is 5.25%",
        source=source,
        supporting_text=text,
    )


def test_direct_support():
    statement = "Policy repo rate is 5.25 per cent."
    claim = Claim(statement)
    evidence = make_evidence(statement)

    assert evidence_relation(claim, evidence) == "supporting"


def test_keyword_overlap_does_not_verify_a_paraphrase():
    claim = Claim("RBI repo rate is 5.25%")
    evidence = make_evidence(
        "Policy Repo Rate 5.50 5.25 5.25 5.25 5.25 5.25"
    )

    assert evidence_relation(claim, evidence) == "not_relevant"


def test_explicit_different_value_is_not_supporting():
    claim = Claim("RBI repo rate is 5.25%")
    evidence = make_evidence("Policy repo rate is 6.00 per cent.")

    assert evidence_relation(claim, evidence) != "supporting"


def test_same_statement_with_a_different_value_is_contradicting():
    claim = Claim("Policy Repo Rate : 5.50%")
    evidence = make_evidence("Policy Repo Rate : 5.25%")

    assert evidence_relation(claim, evidence) == "contradicting"


def test_equal_authority_sources_with_different_values_conflict():
    claim_text = "Policy Repo Rate : 5.50%"
    result = research_claim(
        claim_text,
        [
            make_evidence(claim_text, "https://rbi.org.in"),
            make_evidence("Policy Repo Rate : 5.25%", "https://rbi.org.in"),
        ],
    )

    assert result.status == "conflicting"
    assert [evidence.support for evidence in result.evidence] == [
        "supporting",
        "contradicting",
    ]


def test_unrelated_numbers_are_not_relevant():
    claim = Claim("RBI repo rate is 5.25%")
    evidence = make_evidence(
        "SDF is 5.00 per cent and MSF is 5.50 per cent."
    )

    assert evidence_relation(claim, evidence) == "not_relevant"
