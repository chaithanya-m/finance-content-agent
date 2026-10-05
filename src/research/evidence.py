from dataclasses import dataclass


@dataclass
class SourceDocument:
    source_name: str
    source_url: str
    title: str
    content: str
    published_at: str | None = None


@dataclass
class EvidenceRecord:
    claim: str
    source: SourceDocument
    supporting_text: str
    confidence: str = "high"
