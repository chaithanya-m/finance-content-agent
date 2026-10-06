from dataclasses import dataclass, field


@dataclass
class InstagramPost:
    topic: str
    hook: str
    slides: list[str] = field(default_factory=list)
    caption: str = ""
    call_to_action: str = ""
    sources: list[str] = field(default_factory=list)
