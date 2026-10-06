from .source_authority import SourceAuthority


HIGH_AUTHORITY_SOURCES = {
    "rbi",
    "reserve bank of india",
    "sebi",
    "income tax department",
    "government of india",
    "ministry of finance",
    "official company filing",
}


MEDIUM_AUTHORITY_SOURCES = {
    "reuters",
    "bloomberg",
    "financial times",
    "economic times",
    "moneycontrol",
}


def classify_source(source_name: str, source_type: str) -> SourceAuthority:
    name = source_name.strip().lower()

    if name in HIGH_AUTHORITY_SOURCES:
        return SourceAuthority(
            source_name=source_name,
            authority_level="high",
            source_type=source_type,
            reason="Official or primary source.",
        )

    if name in MEDIUM_AUTHORITY_SOURCES:
        return SourceAuthority(
            source_name=source_name,
            authority_level="medium",
            source_type=source_type,
            reason="Established financial/news source.",
        )

    return SourceAuthority(
        source_name=source_name,
        authority_level="unknown",
        source_type=source_type,
        reason="Source authority has not been established.",
    )

def authority_rank(level: str) -> int:
    return {
        "high": 3,
        "medium": 2,
        "low": 1,
        "unknown": 0,
    }.get(level, 0)