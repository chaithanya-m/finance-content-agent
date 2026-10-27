"""Tests for AITopicGenerator (autonomous AI topic brainstorming)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.research.topic import Topic
from src.research.topic_generator import AITopicGenerator, VERIFIED_DOMAINS


def test_fallback_topic_selection():
    generator = AITopicGenerator()
    domain = VERIFIED_DOMAINS[0]  # home_loan
    topic = generator._fallback_topic(domain, exclude_titles=[])

    assert isinstance(topic, Topic)
    assert topic.content_type == "carousel"
    assert topic.priority == "high"
    assert any(kw in topic.title.casefold() or kw in topic.reason.casefold() for kw in domain["keywords"])


def test_fallback_topic_respects_exclusions():
    generator = AITopicGenerator()
    domain = VERIFIED_DOMAINS[0]
    all_angles = domain["angles"]
    # Exclude all except one
    exclude = all_angles[:-1]
    topic = generator._fallback_topic(domain, exclude_titles=exclude)

    assert topic.title == all_angles[-1]


@patch.object(AITopicGenerator, "_call_ollama")
def test_generate_success_with_ollama(mock_ollama):
    mock_ollama.return_value = {
        "title": "Why does my home loan tenure increase when interest rates go up?",
        "reason": "Explain how floating-rate loan resets affect borrowers in India.",
    }

    generator = AITopicGenerator()
    topic = generator.generate()

    assert isinstance(topic, Topic)
    assert "home loan" in topic.title.casefold()
    assert topic.reason == "Explain how floating-rate loan resets affect borrowers in India."


@patch.object(AITopicGenerator, "_call_ollama")
def test_generate_guarantees_keyword_if_model_omits_it(mock_ollama):
    # LLM returns a title without the domain keyword
    mock_ollama.return_value = {
        "title": "Why is borrowing money getting more expensive?",
        "reason": "Explain rate changes.",
    }

    generator = AITopicGenerator()
    topic = generator.generate()

    assert isinstance(topic, Topic)
    # The generator appends theme/keyword so source_discovery matches the domain
    assert any(d["theme"] in topic.title for d in VERIFIED_DOMAINS) or any(
        kw in topic.title.casefold() for d in VERIFIED_DOMAINS for kw in d["keywords"]
    )


@patch.object(AITopicGenerator, "_call_ollama")
def test_generate_falls_back_gracefully_on_ollama_failure(mock_ollama):
    mock_ollama.side_effect = RuntimeError("Ollama connection refused")

    generator = AITopicGenerator()
    topic = generator.generate()

    assert isinstance(topic, Topic)
    assert topic.priority == "high"
    assert topic.title != ""

