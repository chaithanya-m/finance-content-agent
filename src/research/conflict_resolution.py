from .source_rules import authority_rank
from .source_authority import SourceAuthority


def choose_preferred_source(
    sources: list[SourceAuthority],
) -> SourceAuthority | None:
    if not sources:
        return None

    highest_rank = max(
        authority_rank(source.authority_level)
        for source in sources
    )

    highest_sources = [
        source
        for source in sources
        if authority_rank(source.authority_level) == highest_rank
    ]

    if len(highest_sources) > 1:
        return None

    return highest_sources[0]