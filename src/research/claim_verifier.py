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


def _quoted_verbatim(claim: Claim, evidence: EvidenceRecord) -> bool:
    claim_text = _normalize(claim.claim)
    evidence_text = _normalize(evidence.supporting_text)
    return bool(claim_text) and claim_text == evidence_text


def _resolve_exact_evidence(
    claim: Claim,
    evidence_records: list[EvidenceRecord],
) -> bool:
    matching = []
    for record in evidence_records:
        if not _quoted_verbatim(claim, record):
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
                relation="supporting",
            )
        )

    resolved = resolve_evidence(matching)
    return bool(
        resolved and is_verifiable_authority(resolved.source.authority_level)
    )


def verify_claim(claim: Claim, evidence: EvidenceRecord) -> Claim:
    supports = _quoted_verbatim(claim, evidence)
    claim.evidence.append(
        Evidence(
            source_name=evidence.source.source_name,
            source_url=evidence.source.source_url,
            evidence_text=evidence.supporting_text,
            support="supporting" if supports else "not_relevant",
            published_at=evidence.source.published_at,
        )
    )

    if supports and _resolve_exact_evidence(claim, [evidence]):
        claim.status = "verified"
        claim.notes = "Claim appears verbatim in an authoritative source quotation."
    else:
        claim.status = "unverified"
        claim.notes = "No authoritative source quotation contains the claim verbatim."

    return claim


def detect_conflict(
    claim: Claim,
    evidence_records: list[EvidenceRecord],
) -> Claim:
    if _resolve_exact_evidence(claim, evidence_records):
        claim.status = "verified"
        claim.notes = "Claim appears verbatim in an authoritative source quotation."
        return claim

    claim.status = "unverified"
    claim.notes = "No authoritative source quotation contains the claim verbatim."

    return claim


def evidence_supports_claim(
    claim: Claim,
    evidence: EvidenceRecord,
) -> bool:
    return _quoted_verbatim(claim, evidence)


def evidence_relation(
    claim: Claim,
    evidence: EvidenceRecord,
) -> str:
    if _quoted_verbatim(claim, evidence):
        return "supporting"

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
