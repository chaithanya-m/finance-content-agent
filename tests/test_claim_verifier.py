from src.research.claim import Claim
from src.research.evidence import EvidenceRecord, SourceDocument
from src.research.claim_verifier import evidence_relation


def make_evidence(text: str) -> EvidenceRecord:
    source = SourceDocument(
        source_name="Reserve Bank of India",
        source_url="https://rbi.org.in",
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
    claim = Claim("RBI repo rate is 5.25%")
    evidence = make_evidence("Policy repo rate is 5.25 per cent.")

    assert evidence_relation(claim, evidence) == "supporting"


def test_rbi_table_support():
    claim = Claim("RBI repo rate is 5.25%")
    evidence = make_evidence(
        "Policy Repo Rate 5.50 5.25 5.25 5.25 5.25 5.25"
    )

    assert evidence_relation(claim, evidence) == "supporting"


def test_explicit_different_value_is_not_supporting():
    claim = Claim("RBI repo rate is 5.25%")
    evidence = make_evidence("Policy repo rate is 6.00 per cent.")

    assert evidence_relation(claim, evidence) != "supporting"


def test_unrelated_numbers_are_not_relevant():
    claim = Claim("RBI repo rate is 5.25%")
    evidence = make_evidence(
        "SDF is 5.00 per cent and MSF is 5.50 per cent."
    )

    assert evidence_relation(claim, evidence) == "not_relevant"
