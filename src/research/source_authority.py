from dataclasses import dataclass
from typing import Literal


AuthorityLevel = Literal[
    "high",
    "medium",
    "low",
    "unknown",
]


@dataclass
class SourceAuthority:
    source_name: str
    authority_level: AuthorityLevel
    source_type: str
    reason: str