"""Tests for generate_dialogue.py CLI commands and options."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import generate_dialogue
from src.db import ScriptDatabase
from src.dialogue_script import (
    CarouselSlideScript,
    DialogueLine,
    DialogueScript,
    VideoSceneScript,
)
from src.research.research_report import ResearchReport
from src.research.topic import Topic


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path: Path) -> ScriptDatabase:
    return ScriptDatabase(db_path=tmp_path / "cli_test.db")


@pytest.fixture
def sample_topics_file(tmp_path: Path) -> Path:
    topics = [
        {
            "title": "Repo Rate Impact",
            "reason": "Explain repo rate changes",
            "content_type": "carousel",
            "priority": "high",
        }
    ]
    path = tmp_path / "topics.json"
    path.write_text(json.dumps(topics), encoding="utf-8")
    return path


def _sample_script(topic: str = "Repo Rate Impact") -> DialogueScript:
    return DialogueScript(
        topic=topic,
        format_hint="both",
        language="conversational Indian English",
        dialogue=[
            DialogueLine(speaker="LEARNER", text="What is repo rate?", arc_stage="hook"),
            DialogueLine(speaker="GUIDE", text="It is the RBI lending rate.", arc_stage="scenario"),
        ],
        carousel_slides=[
            CarouselSlideScript(
                slide_number=1,
                arc_stage="hook",
                title="Hook",
                guide_line="",
                learner_line="What is repo rate?",
                visual_prompt="Arjun on phone",
                key_fact="",
                on_screen_text="What is repo rate?",
            )
        ],
        video_scenes=[
            VideoSceneScript(
                scene_number=1,
                arc_stage="hook",
                duration_seconds=4,
                visual_direction="Arjun reading news",
                guide_voiceover="",
                learner_voiceover="What is repo rate?",
                on_screen_text="What is repo rate?",
                visual_prompt="Arjun reading news",
            )
        ],
        estimated_duration_seconds=20,
        verified_facts=["The repo rate is 5.50%."],
        sources=["https://rbi.org.in/"],
    )


def _sample_report(topic: str = "Repo Rate Impact") -> ResearchReport:
    return ResearchReport(
        topic=topic,
        research_question=f"What is {topic}?",
        verified_facts=[
            {
                "fact": "The repo rate is 5.50%.",
                "status": "verified",
                "evidence": [
                    {
                        "source_name": "RBI",
                        "source_url": "https://rbi.org.in/",
                        "evidence_text": "The repo rate is 5.50%.",
                        "support": "supporting",
                    }
                ],
            }
        ],
        sources=[{"source_name": "RBI", "source_url": "https://rbi.org.in/"}],
    )


# ── Parser Tests ──────────────────────────────────────────────────────────────

def test_parser_defaults():
    parser = generate_dialogue._build_parser()
    args = parser.parse_args([])
    assert args.topic is None
    assert args.no_random is False
    assert args.no_files is False
    assert args.list is False
    assert args.show is None
    assert args.db == "data/scripts.db"


def test_parser_custom_flags():
    parser = generate_dialogue._build_parser()
    args = parser.parse_args([
        "--topic", "Custom Topic",
        "--no-random",
        "--no-files",
        "--db", "custom.db",
    ])
    assert args.topic == "Custom Topic"
    assert args.no_random is True
    assert args.no_files is True
    assert args.db == "custom.db"


# ── Query Command Tests ───────────────────────────────────────────────────────

def test_cmd_list_empty(tmp_db: ScriptDatabase, capsys):
    generate_dialogue.cmd_list(tmp_db)
    captured = capsys.readouterr().out
    assert "No scripts in the database yet" in captured


def test_cmd_list_with_records(tmp_db: ScriptDatabase, capsys):
    script = _sample_script("Inflation 101")
    tmp_db.save(script)

    generate_dialogue.cmd_list(tmp_db)
    captured = capsys.readouterr().out
    assert "Inflation 101" in captured
    assert "Total: 1 records" in captured


def test_cmd_show_valid(tmp_db: ScriptDatabase, capsys):
    script = _sample_script("Inflation 101")
    script_id = tmp_db.save(script)

    generate_dialogue.cmd_show(tmp_db, script_id)
    captured = capsys.readouterr().out
    data = json.loads(captured)
    assert data["topic"] == "Inflation 101"
    assert "carousel_slides" in data


def test_cmd_show_invalid(tmp_db: ScriptDatabase):
    with pytest.raises(SystemExit) as exc:
        generate_dialogue.cmd_show(tmp_db, 9999)
    assert exc.value.code == 1


# ── Generation Command Tests ──────────────────────────────────────────────────

@patch("generate_dialogue.LocalResearchAgent")
@patch("generate_dialogue.DialogueScriptGenerator")
def test_cmd_generate_success_with_files(
    mock_dialogue_cls,
    mock_research_cls,
    tmp_db: ScriptDatabase,
    sample_topics_file: Path,
    tmp_path: Path,
    capsys,
):
    output_dir = tmp_path / "drafts"
    mock_research_cls.return_value.research.return_value = _sample_report("Repo Rate Impact")
    mock_dialogue_cls.return_value.generate.return_value = _sample_script("Repo Rate Impact")

    generate_dialogue.cmd_generate(
        topic_title="Repo Rate Impact",
        random_pick=False,
        topics_file=sample_topics_file,
        output_dir=output_dir,
        db=tmp_db,
        save_files=True,
    )

    captured = capsys.readouterr().out
    assert "Script ready" in captured
    assert "Stored in DB as script id=" in captured

    # Database has record
    rows = tmp_db.list_all()
    assert len(rows) == 1
    assert rows[0]["topic"] == "Repo Rate Impact"
    assert rows[0]["status"] == "ready"

    # Disk has files
    saved_dirs = list(output_dir.glob("*_repo-rate-impact"))
    assert len(saved_dirs) == 1
    draft_dir = saved_dirs[0]
    assert (draft_dir / "dialogue_carousel.json").exists()
    assert (draft_dir / "dialogue_carousel.md").exists()
    assert (draft_dir / "dialogue_video.json").exists()
    assert (draft_dir / "dialogue_video.md").exists()


@patch("generate_dialogue.LocalResearchAgent")
@patch("generate_dialogue.DialogueScriptGenerator")
def test_cmd_generate_no_files_flag(
    mock_dialogue_cls,
    mock_research_cls,
    tmp_db: ScriptDatabase,
    sample_topics_file: Path,
    tmp_path: Path,
):
    output_dir = tmp_path / "drafts"
    mock_research_cls.return_value.research.return_value = _sample_report("Repo Rate Impact")
    mock_dialogue_cls.return_value.generate.return_value = _sample_script("Repo Rate Impact")

    generate_dialogue.cmd_generate(
        topic_title="Repo Rate Impact",
        random_pick=False,
        topics_file=sample_topics_file,
        output_dir=output_dir,
        db=tmp_db,
        save_files=False,
    )

    # Database has record
    rows = tmp_db.list_all()
    assert len(rows) == 1
    # Output dir was not created on disk
    assert not output_dir.exists()


@patch("generate_dialogue.LocalResearchAgent")
def test_cmd_generate_research_failure(
    mock_research_cls,
    tmp_db: ScriptDatabase,
    sample_topics_file: Path,
    tmp_path: Path,
):
    mock_research_cls.return_value.research.side_effect = RuntimeError("Network error")

    with pytest.raises(SystemExit) as exc:
        generate_dialogue.cmd_generate(
            topic_title="Repo Rate Impact",
            random_pick=False,
            topics_file=sample_topics_file,
            output_dir=tmp_path / "drafts",
            db=tmp_db,
            save_files=True,
        )
    assert exc.value.code == 1

    # Error recorded in DB
    rows = tmp_db.list_all()
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert "Network error" in rows[0]["error"]


@patch("generate_dialogue.LocalResearchAgent")
def test_cmd_generate_no_verified_facts(
    mock_research_cls,
    tmp_db: ScriptDatabase,
    sample_topics_file: Path,
    tmp_path: Path,
):
    empty_report = ResearchReport(
        topic="Repo Rate Impact",
        research_question="Question?",
        verified_facts=[],
        unverified_claims=[{"fact": "unverified"}],
        sources=[],
    )
    mock_research_cls.return_value.research.return_value = empty_report

    with pytest.raises(SystemExit) as exc:
        generate_dialogue.cmd_generate(
            topic_title="Repo Rate Impact",
            random_pick=False,
            topics_file=sample_topics_file,
            output_dir=tmp_path / "drafts",
            db=tmp_db,
            save_files=True,
        )
    assert exc.value.code == 1

    rows = tmp_db.list_all()
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert "no verified claims" in rows[0]["error"]


# ── Main Entrypoint Routing Tests ─────────────────────────────────────────────

def test_main_list_routing(tmp_path: Path):
    db_file = tmp_path / "test.db"
    with patch("sys.argv", ["generate_dialogue.py", "--db", str(db_file), "--list"]):
        with patch("generate_dialogue.cmd_list") as mock_list:
            generate_dialogue.main()
            mock_list.assert_called_once()


def test_main_show_routing(tmp_path: Path):
    db_file = tmp_path / "test.db"
    with patch("sys.argv", ["generate_dialogue.py", "--db", str(db_file), "--show", "42"]):
        with patch("generate_dialogue.cmd_show") as mock_show:
            generate_dialogue.main()
            mock_show.assert_called_once()

