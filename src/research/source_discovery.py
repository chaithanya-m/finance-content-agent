from dataclasses import dataclass


@dataclass
class SourceCandidate:
    source_name: str
    source_url: str
    title: str
    source_type: str
    published_at: str | None = None


class SourceDiscovery:
    def search(self, research_question: str) -> list[SourceCandidate]:
        raise NotImplementedError
