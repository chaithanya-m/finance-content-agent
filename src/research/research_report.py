from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchReport:
    topic: str
    research_question: str

    verified_facts: list[dict[str, Any]] = field(default_factory=list)
    important_numbers: list[dict[str, Any]] = field(default_factory=list)
    analysis: list[dict[str, Any]] = field(default_factory=list)
    unverified_claims: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
