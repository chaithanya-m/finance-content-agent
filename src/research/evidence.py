from dataclasses import dataclass
from typing import Literal


@dataclass
class SourceDocument:
    source_name: str
    source_url: str
    title: str
    content: str
    source_type: str
    published_at: str | None = None
    as_of_date: str | None = None


@dataclass
class EvidenceRecord:
    claim: str
    source: SourceDocument
    supporting_text: str
    confidence: str = "high"
    verification_status: Literal[
        "supported",
        "contradicting",
        "insufficient",
    ] | None = None