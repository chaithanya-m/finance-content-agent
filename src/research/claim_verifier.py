import re

from .claim import Claim, Evidence
from .evidence import EvidenceRecord
from .evidence_resolution import (
    EvidenceWithAuthority,
    is_verifiable_authority,
    resolve_evidence,
)
from .source_rules import classify_source


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _resolve_assessed_evidence(
    claim: Claim,
    evidence_records: list[EvidenceRecord],
) -> bool:
    matching = []
    for record in evidence_records:
        relation = evidence_relation(claim, record)
        if relation not in {"supporting", "contradicting"}:
            continue
        source = classify_source(
            record.source.source_name,
            record.source.source_type,
            record.source.source_url,
        )
        matching.append(
            EvidenceWithAuthority(
                value=record.supporting_text,
                source=source,
                relation=relation,
            )
        )

    resolved = resolve_evidence(matching)
    return bool(
        resolved and is_verifiable_authority(resolved.source.authority_level)
    )


def verify_claim(claim: Claim, evidence: EvidenceRecord) -> Claim:
    relation = evidence_relation(claim, evidence)
    claim.evidence.append(
        Evidence(
            source_name=evidence.source.source_name,
            source_url=evidence.source.source_url,
            evidence_text=evidence.supporting_text,
            support=relation,
            published_at=evidence.source.published_at,
            as_of_date=evidence.source.as_of_date,
        )
    )

    if relation == "supporting" and _resolve_assessed_evidence(claim, [evidence]):
        claim.status = "verified"
        claim.notes = "Claim was independently assessed as supported by an authoritative source."
    else:
        claim.status = "unverified"
        claim.notes = "No independent supporting assessment was supplied for authoritative evidence."

    return claim


def detect_conflict(
    claim: Claim,
    evidence_records: list[EvidenceRecord],
) -> Claim:
    relations = [
        (record, evidence_relation(claim, record))
        for record in evidence_records
    ]
    if not any(relation == "supporting" for _, relation in relations):
        claim.status = "unverified"
        claim.notes = "No independent supporting assessment was supplied."
        return claim

    evidence = [
        Evidence(
            source_name=record.source.source_name,
            source_url=record.source.source_url,
            evidence_text=record.supporting_text,
            support=relation,
            published_at=record.source.published_at,
            as_of_date=record.source.as_of_date,
        )
        for record, relation in relations
    ]
    claim.evidence = evidence
    if not _resolve_assessed_evidence(
        claim,
        [record for record, relation in relations if relation in {"supporting", "contradicting"}],
    ):
        claim.status = "conflicting"
        claim.notes = "Verified assessments from equally authoritative sources conflict."
        return claim

    claim.status = "verified"
    claim.notes = "Claim was independently assessed against authoritative evidence."

    return claim


def evidence_supports_claim(
    claim: Claim,
    evidence: EvidenceRecord,
) -> bool:
    return evidence_relation(claim, evidence) == "supporting"


def evidence_relation(
    claim: Claim,
    evidence: EvidenceRecord,
) -> str:
    if evidence.verification_status == "supported":
        return "supporting"
    if evidence.verification_status == "contradicting":
        return "contradicting"
    if evidence.verification_status == "insufficient":
        return "not_relevant"

    if evidence.verification_status is None:
        return "not_relevant"

    claim_text = _normalize(claim.claim)
    evidence_text = _normalize(evidence.supporting_text)
    claim_numbers = re.findall(r"\d+(?:\.\d+)?%?", claim_text)
    evidence_numbers = re.findall(r"\d+(?:\.\d+)?%?", evidence_text)
    claim_without_numbers = re.sub(r"\d+(?:\.\d+)?%?", "<number>", claim_text)
    evidence_without_numbers = re.sub(
        r"\d+(?:\.\d+)?%?",
        "<number>",
        evidence_text,
    )

    if (
        claim_numbers
        and evidence_numbers
        and claim_numbers != evidence_numbers
        and claim_without_numbers == evidence_without_numbers
    ):
        return "contradicting"

    return "not_relevant"
