"""Tests for DraftContentWorkflow including topic selection and dialogue draft generation."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.content_post import InstagramPost
from src.dialogue_script import (
    CarouselSlideScript,
    DialogueLine,
    DialogueScript,
    VideoSceneScript,
)
from src.draft_content_workflow import DraftContentWorkflow, slugify
from src.research.research_report import ResearchReport
from src.research.topic import Topic


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_topics_file(tmp_path: Path) -> Path:
    topics = [
        {
            "title": "Topic Alpha",
            "reason": "Explain topic alpha",
            "content_type": "carousel",
            "priority": "high",
        },
        {
            "title": "Topic Beta",
            "reason": "Explain topic beta",
            "content_type": "carousel",
            "priority": "medium",
        },
        {
            "title": "Topic Gamma",
            "reason": "Explain topic gamma",
            "content_type": "carousel",
            "priority": "low",
        },
    ]
    file_path = tmp_path / "topics.json"
    file_path.write_text(json.dumps(topics), encoding="utf-8")
    return file_path


@pytest.fixture
def workflow(mock_topics_file: Path, tmp_path: Path) -> DraftContentWorkflow:
    output_dir = tmp_path / "output_drafts"
    return DraftContentWorkflow(
        topics_file=mock_topics_file,
        output_dir=output_dir,
    )


def _make_report(topic_title: str = "Topic Alpha") -> ResearchReport:
    return ResearchReport(
        topic=topic_title,
        research_question=f"What is {topic_title}?",
        verified_facts=[
            {
                "fact": f"{topic_title} is verified by RBI.",
                "status": "verified",
                "evidence": [
                    {
                        "source_name": "RBI",
                        "source_url": "https://rbi.org.in/test",
                        "evidence_text": f"{topic_title} is verified by RBI.",
                        "support": "supporting",
                    }
                ],
            }
        ],
        sources=[{"source_name": "RBI", "source_url": "https://rbi.org.in/test"}],
    )


def _make_post(topic_title: str = "Topic Alpha") -> InstagramPost:
    fact = f"{topic_title} is verified by RBI."
    return InstagramPost(
        topic=topic_title,
        hook=f"What should you know about {topic_title}?",
        slides=[fact],
        caption="Educational content only; this is not personalized financial advice.",
        call_to_action="Review the cited sources before sharing.",
        sources=["https://rbi.org.in/test"],
        claims=[fact],
    )


def _make_dialogue_script(topic_title: str = "Topic Alpha") -> DialogueScript:
    return DialogueScript(
        topic=topic_title,
        format_hint="both",
        language="conversational Indian English",
        dialogue=[
            DialogueLine(speaker="LEARNER", text="What is this?", arc_stage="hook"),
            DialogueLine(speaker="GUIDE", text="Let me explain.", arc_stage="scenario"),
        ],
        carousel_slides=[
            CarouselSlideScript(
                slide_number=1,
                arc_stage="hook",
                title="Hook slide",
                guide_line="",
                learner_line="What is this?",
                visual_prompt="Arjun asking",
                key_fact="",
                on_screen_text="What is this?",
            )
        ],
        video_scenes=[
            VideoSceneScript(
                scene_number=1,
                arc_stage="hook",
                duration_seconds=5,
                visual_direction="Arjun on phone",
                guide_voiceover="",
                learner_voiceover="What is this?",
                on_screen_text="What is this?",
                visual_prompt="Arjun on phone",
            )
        ],
        estimated_duration_seconds=25,
        verified_facts=[f"{topic_title} is verified by RBI."],
        sources=["https://rbi.org.in/test"],
    )


# ── Tests for slugify ─────────────────────────────────────────────────────────

def test_slugify():
    assert slugify("What is RBI Repo Rate?") == "what-is-rbi-repo-rate"
    assert slugify("Special @#$% Characters! 123") == "special-characters-123"
    assert slugify("   ") == "finance-topic"


# ── Tests for topic loading and selection ─────────────────────────────────────

def test_load_topics_missing_file(tmp_path: Path):
    wf = DraftContentWorkflow(topics_file=tmp_path / "nonexistent.json")
    with pytest.raises(FileNotFoundError):
        wf._load_topics()


def test_load_topics_invalid_json(tmp_path: Path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text('{"not": "a list"}', encoding="utf-8")
    wf = DraftContentWorkflow(topics_file=bad_file)
    with pytest.raises(ValueError, match="JSON list"):
        wf._load_topics()


def test_select_topic_by_explicit_title(workflow: DraftContentWorkflow):
    selected = workflow.select_topic(requested_title="Topic Beta")
    assert selected.title == "Topic Beta"
    assert selected.priority == "medium"


def test_select_topic_by_unconfigured_title(workflow: DraftContentWorkflow):
    selected = workflow.select_topic(requested_title="Completely New Topic")
    assert selected.title == "Completely New Topic"
    assert selected.priority == "high"


def test_select_topic_highest_priority_default(workflow: DraftContentWorkflow):
    selected = workflow.select_topic()
    # High priority topic is Topic Alpha
    assert selected.title == "Topic Alpha"


def test_select_topic_skips_history(workflow: DraftContentWorkflow):
    workflow.output_dir.mkdir(parents=True, exist_ok=True)
    workflow.history_file.write_text(
        json.dumps([{"title": "Topic Alpha"}]), encoding="utf-8"
    )

    selected = workflow.select_topic()
    # Topic Alpha is done, next highest is Topic Beta
    assert selected.title == "Topic Beta"


def test_select_topic_skips_externally_provided_titles(workflow: DraftContentWorkflow):
    # E.g. topics already stored in SQLite DB
    selected = workflow.select_topic(skip_titles={"Topic Alpha", "Topic Beta"})
    assert selected.title == "Topic Gamma"


def test_select_topic_resets_when_all_topics_completed(workflow: DraftContentWorkflow):
    # When all 3 topics are completed, workflow resets so any topic is selectable
    selected = workflow.select_topic(skip_titles={"Topic Alpha", "Topic Beta", "Topic Gamma"})
    assert selected is not None
    assert selected.title in {"Topic Alpha", "Topic Beta", "Topic Gamma"}


def test_select_topic_random(workflow: DraftContentWorkflow):
    selected = workflow.select_topic(random_pick=True)
    assert selected.title in {"Topic Alpha", "Topic Beta", "Topic Gamma"}


# ── Tests for generate_drafts ─────────────────────────────────────────────────

@patch("src.draft_content_workflow.LocalResearchAgent")
@patch("src.draft_content_workflow.ResearchContentGenerator")
@patch("src.draft_content_workflow.ContentValidator")
@patch("src.draft_content_workflow.DialogueScriptGenerator")
def test_generate_drafts_success(
    mock_dialogue_gen_cls,
    mock_validator_cls,
    mock_content_gen_cls,
    mock_research_cls,
    workflow: DraftContentWorkflow,
):
    topic = Topic(title="Topic Alpha", reason="Explain Alpha")
    report = _make_report("Topic Alpha")
    post = _make_post("Topic Alpha")
    dialogue_script = _make_dialogue_script("Topic Alpha")

    mock_research_cls.return_value.research.return_value = report
    mock_content_gen_cls.return_value.generate.return_value = post
    mock_validator_cls.return_value.validate.return_value = True
    mock_dialogue_gen_cls.return_value.generate.return_value = dialogue_script

    out_path = workflow.generate_drafts(topic)
    assert out_path.exists()

    # Core drafts exist
    assert (out_path / "research_report.json").exists()
    assert (out_path / "carousel.json").exists()
    assert (out_path / "carousel.md").exists()
    assert (out_path / "video_script.json").exists()
    assert (out_path / "video_script.md").exists()

    # Dialogue teaching scripts exist
    assert (out_path / "dialogue_carousel.json").exists()
    assert (out_path / "dialogue_carousel.md").exists()
    assert (out_path / "dialogue_video.json").exists()
    assert (out_path / "dialogue_video.md").exists()

    # History updated
    history = workflow._load_history()
    assert len(history) == 1
    assert history[0]["title"] == "Topic Alpha"


@patch("src.draft_content_workflow.LocalResearchAgent")
def test_generate_drafts_fails_when_no_verified_facts(
    mock_research_cls,
    workflow: DraftContentWorkflow,
):
    topic = Topic(title="Unverified Topic", reason="No facts")
    empty_report = ResearchReport(
        topic="Unverified Topic",
        research_question="Question?",
        verified_facts=[],
        unverified_claims=[{"fact": "Unverified fact"}],
    )
    mock_research_cls.return_value.research.return_value = empty_report

    with pytest.raises(ValueError, match="no verified claims"):
        workflow.generate_drafts(topic)


@patch("src.draft_content_workflow.LocalResearchAgent")
@patch("src.draft_content_workflow.ResearchContentGenerator")
@patch("src.draft_content_workflow.ContentValidator")
@patch("src.draft_content_workflow.DialogueScriptGenerator")
def test_generate_drafts_gracefully_handles_dialogue_error(
    mock_dialogue_gen_cls,
    mock_validator_cls,
    mock_content_gen_cls,
    mock_research_cls,
    workflow: DraftContentWorkflow,
):
    topic = Topic(title="Topic Alpha", reason="Explain Alpha")
    report = _make_report("Topic Alpha")
    post = _make_post("Topic Alpha")

    mock_research_cls.return_value.research.return_value = report
    mock_content_gen_cls.return_value.generate.return_value = post
    mock_validator_cls.return_value.validate.return_value = True
    # Dialogue generator raises an error (e.g. Ollama unreachable)
    mock_dialogue_gen_cls.return_value.generate.side_effect = RuntimeError("Ollama connection failed")

    out_path = workflow.generate_drafts(topic)
    assert out_path.exists()

    # Core drafts are still successfully written
    assert (out_path / "carousel.json").exists()
    assert (out_path / "video_script.json").exists()

    # Dialogue error was logged rather than aborting the workflow
    assert (out_path / "dialogue_error.txt").exists()
    assert "Ollama connection failed" in (out_path / "dialogue_error.txt").read_text()

