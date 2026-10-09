from .research_report import ResearchReport
from .research_request import ResearchRequest


class ResearchAgent:
    def research(self, request: ResearchRequest) -> ResearchReport:
        raise NotImplementedError
