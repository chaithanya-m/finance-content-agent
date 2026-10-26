from .evidence import EvidenceRecord
from .evidence_resolution import EvidenceWithAuthority
from .source_rules import classify_source


def add_source_authority(
    record: EvidenceRecord,
    relation: str,
) -> EvidenceWithAuthority:
    authority = classify_source(
        record.source.source_name,
        record.source.source_type,
        record.source.source_url,
    )

    return EvidenceWithAuthority(
        value=record.supporting_text,
        source=authority,
        relation=relation,
    )