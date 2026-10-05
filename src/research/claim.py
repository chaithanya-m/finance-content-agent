from dataclasses import dataclass, field
from typing import Literal


VerificationStatus = Literal[
    "verified",
    "unverified",
    "conflicting",
]


@dataclass
class Evidence:
    source_name: str
    source_url: str
    evidence_text: str
    published_at: str | None = None


@dataclass
class Claim:
    claim: str
    status: VerificationStatus
    evidence: list[Evidence] = field(default_factory=list)
    notes: str | None = None
