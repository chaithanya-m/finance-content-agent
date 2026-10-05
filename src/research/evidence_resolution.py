from dataclasses import dataclass

from .source_authority import SourceAuthority
from .source_rules import authority_rank


@dataclass
class EvidenceWithAuthority:
    value: str
    source: SourceAuthority
    relation: str


def resolve_evidence(
    evidence: list[EvidenceWithAuthority],
) -> EvidenceWithAuthority | None:
    if not evidence:
        return None

    highest_rank = max(
        authority_rank(item.source.authority_level)
        for item in evidence
    )

    highest = [
        item
        for item in evidence
        if authority_rank(item.source.authority_level) == highest_rank
    ]

    supporting = [
        item
        for item in highest
        if item.relation == "supporting"
    ]

    contradicting = [
        item
        for item in highest
        if item.relation == "contradicting"
    ]

    # Equal-authority sources disagree.
    if supporting and contradicting:
        return None

    if not supporting:
        return None

    return supporting[0]


def is_verifiable_authority(level: str) -> bool:
    return level in {"high", "medium"}