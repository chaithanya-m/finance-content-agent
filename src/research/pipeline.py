from .claim import Claim, Evidence
from .evidence import EvidenceRecord


def evidence_to_claim(record: EvidenceRecord) -> Claim:
    evidence = Evidence(
        source_name=record.source.source_name,
        source_url=record.source.source_url,
        evidence_text=record.supporting_text,
        published_at=record.source.published_at,
    )

    return Claim(
        claim=record.claim,
        status="verified",
        evidence=[evidence],
    )
