"""Tests for the SQLite script database."""

import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

from src.db import ScriptDatabase
from src.dialogue_script import (
    CarouselSlideScript,
    DialogueLine,
    DialogueScript,
    VideoSceneScript,
)
from src.dialogue_script_generator import DialogueScriptGenerator
from src.research.research_report import ResearchReport


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_script() -> DialogueScript:
    return DialogueScript(
        topic="How does inflation affect household budgets in India?",
        format_hint="both",
        language="conversational Indian English",
        dialogue=[
            DialogueLine(speaker="LEARNER", text="Riya didi, what is inflation?", arc_stage="hook"),
            DialogueLine(speaker="GUIDE", text="Inflation is when prices rise over time.", arc_stage="scenario"),
            DialogueLine(speaker="GUIDE", text="When RBI raises rates to control inflation, borrowing costs go up.", arc_stage="explanation"),
            DialogueLine(speaker="GUIDE", text="If inflation is 6%, a ₹100 grocery basket costs ₹106 next year.", arc_stage="example"),
            DialogueLine(speaker="GUIDE", text="If your salary doesn't rise with inflation, you lose purchasing power.", arc_stage="consequences"),
            DialogueLine(speaker="GUIDE", text="Track your monthly expenses and notice which items rise fastest.", arc_stage="takeaway"),
        ],
        carousel_slides=[
            CarouselSlideScript(
                slide_number=1, arc_stage="hook",
                title="Have you noticed prices rising?",
                guide_line="", learner_line="Riya didi, what is inflation?",
                visual_prompt="Arjun at a grocery store looking at prices",
                key_fact="", on_screen_text='"Riya didi, what is inflation?"',
            )
        ],
        video_scenes=[
            VideoSceneScript(
                scene_number=1, arc_stage="hook", duration_seconds=4,
                visual_direction="Arjun at a grocery store",
                guide_voiceover="", learner_voiceover="What is inflation?",
                on_screen_text="What is inflation?",
                visual_prompt="Grocery store scene",
            )
        ],
        estimated_duration_seconds=33,
        verified_facts=["Inflation was 6.2% in September 2024 per MOSPI."],
        sources=["https://mospi.gov.in/"],
    )


@pytest.fixture
def tmp_db(tmp_path: Path) -> ScriptDatabase:
    return ScriptDatabase(db_path=tmp_path / "test_scripts.db")


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestScriptDatabaseSchema:
    def test_creates_db_file(self, tmp_path: Path):
        db_path = tmp_path / "new.db"
        assert not db_path.exists()
        ScriptDatabase(db_path=db_path)
        assert db_path.exists()

    def test_creates_tables(self, tmp_db: ScriptDatabase):
        import sqlite3
        conn = sqlite3.connect(tmp_db.db_path)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "scripts" in tables
        assert "topics_history" in tables
        conn.close()


class TestSave:
    def test_save_returns_integer_id(self, tmp_db: ScriptDatabase):
        script = _make_script()
        script_id = tmp_db.save(script)
        assert isinstance(script_id, int)
        assert script_id > 0

    def test_save_roundtrip(self, tmp_db: ScriptDatabase):
        script = _make_script()
        script_id = tmp_db.save(script)
        row = tmp_db.get_by_id(script_id)
        assert row is not None
        assert row["topic"] == script.topic
        assert row["status"] == "ready"

    def test_save_stores_verified_facts(self, tmp_db: ScriptDatabase):
        script = _make_script()
        script_id = tmp_db.save(script)
        row = tmp_db.get_by_id(script_id)
        facts = json.loads(row["verified_facts"])
        assert facts == script.verified_facts

    def test_save_stores_sources(self, tmp_db: ScriptDatabase):
        script = _make_script()
        script_id = tmp_db.save(script)
        row = tmp_db.get_by_id(script_id)
        sources = json.loads(row["sources"])
        assert sources == script.sources

    def test_save_with_output_dir(self, tmp_db: ScriptDatabase):
        script = _make_script()
        script_id = tmp_db.save(script, output_dir="/some/path")
        row = tmp_db.get_by_id(script_id)
        assert row["output_dir"] == "/some/path"

    def test_carousel_json_is_full_script(self, tmp_db: ScriptDatabase):
        script = _make_script()
        script_id = tmp_db.save(script)
        data = tmp_db.get_carousel_json(script_id)
        assert data is not None
        assert data["topic"] == script.topic
        assert "dialogue" in data
        assert "carousel_slides" in data

    def test_video_json_is_full_script(self, tmp_db: ScriptDatabase):
        script = _make_script()
        script_id = tmp_db.save(script)
        data = tmp_db.get_video_json(script_id)
        assert data is not None
        assert data["topic"] == script.topic
        assert "video_scenes" in data

    def test_get_by_id_missing_returns_none(self, tmp_db: ScriptDatabase):
        assert tmp_db.get_by_id(99999) is None
        assert tmp_db.get_carousel_json(99999) is None
        assert tmp_db.get_video_json(99999) is None

    def test_save_error_sets_failed_status(self, tmp_db: ScriptDatabase):
        error_id = tmp_db.save_error("Bad topic", "Research failed: no sources")
        row = tmp_db.get_by_id(error_id)
        assert row["status"] == "failed"
        assert "Research failed" in row["error"]

    def test_failed_carousel_json_returns_none(self, tmp_db: ScriptDatabase):
        error_id = tmp_db.save_error("Bad topic", "error!")
        assert tmp_db.get_carousel_json(error_id) is None
        assert tmp_db.get_video_json(error_id) is None

    def test_topics_history_table_records_entries(self, tmp_db: ScriptDatabase):
        import sqlite3
        script = _make_script()
        script_id = tmp_db.save(script)

        conn = sqlite3.connect(tmp_db.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM topics_history WHERE script_id=?", (script_id,)).fetchall()
        assert len(rows) == 1
        assert rows[0]["topic"] == script.topic
        conn.close()

    def test_multiple_saves_get_unique_ids(self, tmp_db: ScriptDatabase):
        s1 = _make_script()
        s2 = _make_script()
        s2.topic = "A different topic"
        id1 = tmp_db.save(s1)
        id2 = tmp_db.save(s2)
        assert id1 != id2


class TestMarkPublished:
    def test_mark_published(self, tmp_db: ScriptDatabase):
        script = _make_script()
        script_id = tmp_db.save(script)
        tmp_db.mark_published(script_id)
        row = tmp_db.get_by_id(script_id)
        assert row["status"] == "published"


class TestListAll:
    def test_list_all_empty(self, tmp_db: ScriptDatabase):
        assert tmp_db.list_all() == []

    def test_list_all_returns_rows(self, tmp_db: ScriptDatabase):
        script = _make_script()
        tmp_db.save(script)
        rows = tmp_db.list_all()
        assert len(rows) == 1
        assert rows[0]["topic"] == script.topic

    def test_list_all_newest_first(self, tmp_db: ScriptDatabase):
        s = _make_script()
        tmp_db.save(s)
        s2 = _make_script()
        s2.topic = "Second topic"
        tmp_db.save(s2)
        rows = tmp_db.list_all()
        assert rows[0]["topic"] == "Second topic"


class TestTopicsGenerated:
    def test_topics_generated_empty(self, tmp_db: ScriptDatabase):
        assert tmp_db.topics_generated() == set()

    def test_topics_generated_excludes_failed(self, tmp_db: ScriptDatabase):
        tmp_db.save_error("Failed topic", "error!")
        assert "Failed topic" not in tmp_db.topics_generated()

    def test_topics_generated_includes_ready(self, tmp_db: ScriptDatabase):
        script = _make_script()
        tmp_db.save(script)
        assert script.topic in tmp_db.topics_generated()

    def test_topics_generated_includes_published(self, tmp_db: ScriptDatabase):
        script = _make_script()
        script_id = tmp_db.save(script)
        tmp_db.mark_published(script_id)
        assert script.topic in tmp_db.topics_generated()

