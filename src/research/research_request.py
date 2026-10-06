from dataclasses import dataclass


@dataclass
class ResearchRequest:
    topic: str
    research_question: str
