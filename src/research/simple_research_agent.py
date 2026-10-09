from .research_agent import ResearchAgent
from .research_report import ResearchReport
from .research_request import ResearchRequest


class SimpleResearchAgent(ResearchAgent):
    def research(self, request: ResearchRequest) -> ResearchReport:
        return ResearchReport(
            topic=request.topic,
            research_question=request.research_question,
        )
