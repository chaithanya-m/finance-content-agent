from .claim import Claim
from .claim_resolution import resolve_claim
from .evidence import EvidenceRecord


def research_claim(
    claim_text: str,
    evidence_records: list[EvidenceRecord],
) -> Claim:
    claim = Claim(claim_text)

    return resolve_claim(
        claim,
        evidence_records,
    )
