from .research_agent import ResearchAgent
from .research_report import ResearchReport


class SimpleResearchAgent(ResearchAgent):
    def research(self, topic: str) -> ResearchReport:
        return ResearchReport(
            topic=topic,
            research_question=f"What should we know about {topic}?",
        )
