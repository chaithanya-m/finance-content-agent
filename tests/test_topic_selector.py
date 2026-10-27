"""Tests for TopicSelector including priority and random selection."""

from src.research.topic import Topic
from src.research.topic_selector import TopicSelector


def test_select_empty_list_returns_none():
    selector = TopicSelector()
    assert selector.select([]) is None
    assert selector.select([], random_pick=True) is None


def test_select_highest_priority():
    selector = TopicSelector()
    topics = [
        Topic(title="Low priority topic", reason="Reason", priority="low"),
        Topic(title="High priority topic", reason="Reason", priority="high"),
        Topic(title="Medium priority topic", reason="Reason", priority="medium"),
    ]

    selected = selector.select(topics, random_pick=False)
    assert selected is not None
    assert selected.title == "High priority topic"


def test_select_priority_fallback_defaults():
    selector = TopicSelector()
    topics = [
        Topic(title="Unknown priority", reason="Reason", priority="unknown"),
        Topic(title="Medium priority", reason="Reason", priority="medium"),
    ]

    selected = selector.select(topics, random_pick=False)
    assert selected is not None
    assert selected.title == "Medium priority"


def test_select_random_pick():
    selector = TopicSelector()
    topics = [
        Topic(title=f"Topic {i}", reason="Reason", priority="medium")
        for i in range(10)
    ]

    selected = selector.select(topics, random_pick=True)
    assert selected is not None
    assert selected in topics


def test_select_random_pick_distribution():
    selector = TopicSelector()
    topics = [
        Topic(title="A", reason="Reason", priority="high"),
        Topic(title="B", reason="Reason", priority="medium"),
        Topic(title="C", reason="Reason", priority="low"),
    ]

    picked_titles = {
        selector.select(topics, random_pick=True).title
        for _ in range(50)
    }

    # Over 50 random trials with 3 items, all items should be chosen at least once
    assert len(picked_titles) > 1

