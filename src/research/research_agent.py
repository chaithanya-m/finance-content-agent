from .research_report import ResearchReport


class ResearchAgent:
    def research(self, topic: str) -> ResearchReport:
        raise NotImplementedError
