import random

from .topic import Topic


class TopicSelector:
    def select(self, candidates: list[Topic], random_pick: bool = False) -> Topic | None:
        if not candidates:
            return None

        if random_pick:
            return random.choice(candidates)

        priority_rank = {
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        return max(
            candidates,
            key=lambda topic: priority_rank.get(topic.priority, 0),
        )
