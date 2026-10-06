from dataclasses import dataclass, field


@dataclass
class ResearchReport:
    topic: str
    research_question: str

    verified_facts: list[str] = field(default_factory=list)
    important_numbers: list[str] = field(default_factory=list)
    analysis: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
