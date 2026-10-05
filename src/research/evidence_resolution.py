from dataclasses import dataclass

from .source_authority import SourceAuthority
from .source_rules import authority_rank


@dataclass
class EvidenceWithAuthority:
    value: str
    source: SourceAuthority


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

    if len(highest) > 1:
        values = {item.value for item in highest}

        if len(values) > 1:
            return None

    return highest[0]