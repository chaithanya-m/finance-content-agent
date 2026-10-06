from dataclasses import dataclass

from .research_request import ResearchRequest


@dataclass
class SourceCandidate:
    source_name: str
    source_url: str
    title: str
    source_type: str
    published_at: str | None = None


class ResearchSourceDiscovery:
    def discover(
        self,
        request: ResearchRequest,
    ) -> list[SourceCandidate]:
        raise NotImplementedError
