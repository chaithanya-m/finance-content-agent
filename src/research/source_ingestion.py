from .evidence import SourceDocument
from .evidence import EvidenceRecord, SourceDocument


def create_source_document(
    source_name: str,
    source_url: str,
    title: str,
    content: str,
    source_type: str,
    published_at: str | None = None,
    as_of_date: str | None = None,
) -> SourceDocument:
    return SourceDocument(
        source_name=source_name,
        source_url=source_url,
        title=title,
        content=content,
        source_type=source_type,
        published_at=published_at,
        as_of_date=as_of_date,
    )

def create_evidence_record(
    claim: str,
    source: SourceDocument,
    supporting_text: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        claim=claim,
        source=source,
        supporting_text=supporting_text,
    )