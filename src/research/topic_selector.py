from .topic import Topic


class TopicSelector:
    def select(self, candidates: list[Topic]) -> Topic | None:
        if not candidates:
            return None

        priority_rank = {
            "high": 3,
            "medium": 2,
            "low": 1,
        }

        return max(
            candidates,
            key=lambda topic: priority_rank.get(topic.priority, 0),
        )
