from dataclasses import dataclass, field
from typing import Literal


VerificationStatus = Literal[
    "verified",
    "unverified",
    "conflicting",
]

EvidenceSupport = Literal[
    "supporting",
    "contradicting",
    "not_relevant",
]


@dataclass
class Evidence:
    source_name: str
    source_url: str
    evidence_text: str
    support: EvidenceSupport
    published_at: str | None = None


@dataclass
class Claim:
    claim: str
    status: VerificationStatus = "unverified"
    evidence: list[Evidence] = field(default_factory=list)
    notes: str | None = None