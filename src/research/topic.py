from dataclasses import dataclass


@dataclass
class Topic:
    title: str
    reason: str
    content_type: str = "carousel"
    priority: str = "medium"
