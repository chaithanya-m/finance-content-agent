from .claim import Claim, Evidence
from .evidence import EvidenceRecord
from .evidence_adapter import add_source_authority
from .evidence_resolution import (
    is_verifiable_authority,
    resolve_evidence,
)
from .claim_verifier import evidence_relation

def resolve_claim(
    claim: Claim,
    evidence_records: list[EvidenceRecord],
) -> Claim:
    if not evidence_records:
        claim.status = "unverified"
        claim.notes = "No evidence was supplied."
        return claim

    # Only evidence that actually supports the claim
    # participates in authority-based resolution.
# Classify every evidence record before resolution.
    evidence_relations = [
        (record, evidence_relation(claim, record))
        for record in evidence_records
    ]

    supporting_records = [
        record
        for record, relation in evidence_relations
        if relation == "supporting"
    ]

    contradicting_records = [
        record
        for record, relation in evidence_relations
        if relation == "contradicting"
    ]

    # Preserve all supplied evidence for auditability.
    claim.evidence = [
        Evidence(
            source_name=record.source.source_name,
            source_url=record.source.source_url,
            evidence_text=record.supporting_text,
            support=relation,
            published_at=record.source.published_at,
            as_of_date=record.source.as_of_date,
        )
        for record, relation in evidence_relations
    ]

    if not supporting_records:
        claim.status = "unverified"
        claim.notes = "No supplied evidence supports the claim."
        return claim

    if contradicting_records and supporting_records:
        claim.notes = (
            f"Found {len(supporting_records)} supporting "
            f"and {len(contradicting_records)} contradicting evidence records."
        )

    evidence_with_authority = [
        add_source_authority(record, relation)
        for record, relation in evidence_relations
        if relation in {"supporting", "contradicting"}
    ]

    resolved = resolve_evidence(evidence_with_authority)

    if resolved is None:
        claim.status = "conflicting"
        claim.notes = (
            "Supporting evidence from equally authoritative sources "
            "conflicts or cannot be uniquely resolved."
        )
        return claim

    if not is_verifiable_authority(resolved.source.authority_level):
        claim.status = "unverified"
        claim.notes = (
            f"Supporting evidence comes only from "
            f"{resolved.source.source_name} "
            f"({resolved.source.authority_level} authority)."
        )
        return claim

    claim.status = "verified"
    claim.notes = (
        f"Claim resolved using "
        f"{resolved.source.source_name} "
        f"({resolved.source.authority_level} authority)."
    )

    return claim
