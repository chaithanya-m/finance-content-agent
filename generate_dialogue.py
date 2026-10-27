#!/usr/bin/env python3
"""
generate_dialogue.py — Finance Content Agent: Dialogue Script Generator
=======================================================================

Run this script to autonomously:
  1. Select a topic (random from configured pool, or a specific one you name)
  2. Research and verify claims using authoritative Indian finance sources
  3. Generate a two-character dialogue teaching script (Riya + Arjun)
  4. Save the dialogue_carousel and dialogue_video scripts to disk
  5. Store everything in a local SQLite database (data/scripts.db)

Usage examples
--------------
  # Pick a random uncompleted topic and generate
  python generate_dialogue.py

  # Pick the highest-priority uncompleted topic (not random)
  python generate_dialogue.py --no-random

  # Generate on a specific topic
  python generate_dialogue.py --topic "How does inflation affect household budgets in India?"

  # List all generated scripts stored in the DB
  python generate_dialogue.py --list

  # Show the full carousel JSON for a specific DB record
  python generate_dialogue.py --show 3

  # Change where the DB and drafts are stored
  python generate_dialogue.py --db data/mydb.db --output-dir output/drafts

Database
--------
  SQLite file: data/scripts.db  (created automatically)

  Tables:
    scripts         — one row per generated DialogueScript
    topics_history  — log of every generation attempt
"""

import argparse
import json
import sys
import textwrap
from dataclasses import asdict
from pathlib import Path

# ── project imports ───────────────────────────────────────────────────────────
from src.content_validator import ContentValidator
from src.db import ScriptDatabase
from src.dialogue_script_generator import DialogueScriptGenerator
from src.draft_content_workflow import DraftContentWorkflow
from src.research.local_research_agent import LocalResearchAgent
from src.research.research_request import ResearchRequest
from src.research.topic import Topic
from src.research_content_generator import ResearchContentGenerator


# ── helpers ───────────────────────────────────────────────────────────────────

def _hr(char: str = "─", width: int = 60) -> str:
    return char * width


def _print_step(step: int, total: int, message: str) -> None:
    print(f"\n[{step}/{total}] {message}")


def _print_success(message: str) -> None:
    print(f"  ✅ {message}")


def _print_warn(message: str) -> None:
    print(f"  ⚠️  {message}")


def _print_error(message: str) -> None:
    print(f"  ❌ {message}", file=sys.stderr)


# ── sub-commands ──────────────────────────────────────────────────────────────

def cmd_list(db: ScriptDatabase) -> None:
    """Print a summary table of all stored scripts."""
    rows = db.list_all(limit=100)
    if not rows:
        print("No scripts in the database yet. Run `python generate_dialogue.py` to generate one.")
        return

    print(_hr())
    print(f"{'ID':>4}  {'STATUS':<12}  {'GENERATED AT':<22}  TOPIC")
    print(_hr())
    for row in rows:
        topic_short = row["topic"][:60] + ("…" if len(row["topic"]) > 60 else "")
        ts = row["generated_at"][:19].replace("T", " ")
        status = row["status"]
        rid = row["id"]
        print(f"{rid:>4}  {status:<12}  {ts:<22}  {topic_short}")
    print(_hr())
    print(f"Total: {len(rows)} records  •  DB: {db.db_path}")


def cmd_show(db: ScriptDatabase, script_id: int) -> None:
    """Pretty-print the carousel JSON for a stored script."""
    data = db.get_carousel_json(script_id)
    if data is None:
        _print_error(f"No script with id={script_id} found (or it failed).")
        sys.exit(1)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_generate(
    *,
    topic_title: str | None,
    random_pick: bool,
    topics_file: Path,
    output_dir: Path,
    db: ScriptDatabase,
    save_files: bool,
) -> None:
    """Full pipeline: research → verify → dialogue script → save."""
    TOTAL_STEPS = 5

    print(_hr("═"))
    print("  Finance Content Agent — Dialogue Script Generator")
    print(_hr("═"))

    # ── Step 1: Topic selection ───────────────────────────────────────────────
    _print_step(1, TOTAL_STEPS, "Selecting topic…")

    workflow = DraftContentWorkflow(
        topics_file=topics_file,
        output_dir=output_dir,
    )

    already_in_db = db.topics_generated()

    topic: Topic = workflow.select_topic(
        requested_title=topic_title,
        random_pick=random_pick,
        skip_titles=already_in_db,
    )

    print(f"\n  📚 Topic: {topic.title}")
    print(f"     Priority: {topic.priority}  |  Type: {topic.content_type}")

    # ── Step 2: Research ──────────────────────────────────────────────────────
    _print_step(2, TOTAL_STEPS, "Researching and verifying claims…")
    print("     (Fetching authoritative Indian finance sources)")

    request = ResearchRequest(
        topic=topic.title,
        research_question=(
            f"{topic.reason} Research current information using authoritative "
            "Indian sources. Preserve source URLs and supporting evidence. "
            "Do not mark a claim verified unless the finance-research "
            "verification tool returns status 'verified'."
        ),
    )

    try:
        report = LocalResearchAgent().research(request)
    except (RuntimeError, ValueError) as exc:
        _print_error(f"Research failed: {exc}")
        db.save_error(topic.title, str(exc))
        sys.exit(1)

    verified = [
        f for f in report.verified_facts
        if isinstance(f, dict)
        and f.get("status") == "verified"
        and isinstance(f.get("fact"), str)
        and f["fact"].strip()
    ]

    if not verified:
        msg = (
            f"Research produced no verified claims. "
            f"Unverified: {len(report.unverified_claims)}, "
            f"Sources checked: {len(report.sources)}."
        )
        _print_error(msg)
        db.save_error(topic.title, msg)
        sys.exit(1)

    _print_success(f"{len(verified)} verified claim(s) from {len(report.sources)} source(s)")
    for i, fact in enumerate(verified, 1):
        text = fact["fact"]
        short = textwrap.shorten(text, width=90, placeholder="…")
        print(f"     {i}. {short}")

    # ── Step 3: Generate dialogue script ──────────────────────────────────────
    _print_step(3, TOTAL_STEPS, "Generating two-character dialogue script…")
    print("     Riya (Guide) + Arjun (Learner) — teaching arc: hook→scenario→")
    print("     explanation→example→consequences→takeaway")

    try:
        script = DialogueScriptGenerator().generate(report)
    except (ValueError, RuntimeError) as exc:
        _print_error(f"Dialogue generation failed: {exc}")
        db.save_error(topic.title, str(exc))
        sys.exit(1)

    _print_success(
        f"Script ready: {len(script.carousel_slides)} carousel slides, "
        f"{len(script.video_scenes)} video scenes, "
        f"~{script.estimated_duration_seconds}s video"
    )

    # Preview the dialogue
    print()
    print("  Preview of teaching dialogue:")
    print("  " + _hr("-", 58))
    for line in script.dialogue:
        name = "👩 Riya " if line.speaker == "GUIDE" else "🧑 Arjun"
        stage = f"[{line.arc_stage.upper():<13}]"
        text = textwrap.shorten(line.text, width=72, placeholder="…")
        print(f"  {name} {stage}  {text}")
    print("  " + _hr("-", 58))

    # ── Step 4: Save to DB ────────────────────────────────────────────────────
    _print_step(4, TOTAL_STEPS, "Saving to database…")

    output_path_str: str | None = None

    # Optionally write files to disk as well
    if save_files:
        from datetime import datetime
        import re

        def slugify(val: str) -> str:
            val = re.sub(r"[^a-zA-Z0-9]+", "-", val.lower()).strip("-")
            return val[:70].strip("-") or "finance-topic"

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_dir = output_dir / f"{ts}_{slugify(topic.title)}"
        draft_dir.mkdir(parents=True, exist_ok=True)

        carousel_md = DraftContentWorkflow._dialogue_carousel_markdown(script)
        video_md = DraftContentWorkflow._dialogue_video_markdown(script)

        (draft_dir / "dialogue_carousel.md").write_text(carousel_md, encoding="utf-8")
        (draft_dir / "dialogue_video.md").write_text(video_md, encoding="utf-8")

        script_dict = asdict(script)
        (draft_dir / "dialogue_carousel.json").write_text(
            json.dumps(script_dict, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (draft_dir / "dialogue_video.json").write_text(
            json.dumps(script_dict, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        output_path_str = str(draft_dir.resolve())
        _print_success(f"Files saved to: {output_path_str}")

    script_id = db.save(script, output_dir=output_path_str)
    _print_success(f"Stored in DB as script id={script_id}  ({db.db_path})")

    # ── Step 5: Summary ───────────────────────────────────────────────────────
    _print_step(5, TOTAL_STEPS, "Done!")
    print()
    print(_hr("═"))
    print(f"  Topic    : {script.topic}")
    print(f"  DB id    : {script_id}")
    print(f"  Slides   : {len(script.carousel_slides)} carousel + {len(script.video_scenes)} video scenes")
    print(f"  Duration : ~{script.estimated_duration_seconds}s")
    if output_path_str:
        print(f"  Files    : {output_path_str}")
    print(_hr("═"))
    print()
    print("  Next steps:")
    print("    • View in DB     : python generate_dialogue.py --list")
    print(f"    • Show JSON      : python generate_dialogue.py --show {script_id}")
    print("    • Pass to AI     : Feed dialogue_carousel.json to your image/video LLM")
    print("      with the instruction in the JSON's rendering_contract field.")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_dialogue",
        description=textwrap.dedent("""\
            Finance Content Agent — Dialogue Script Generator

            Autonomously picks a finance topic, researches it using
            authoritative Indian sources, and generates a two-character
            teaching script (Riya + Arjun) for carousel and video formats.
            Stores everything in a local SQLite database.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Generation options
    gen = parser.add_argument_group("Generation")
    gen.add_argument(
        "--topic", "-t",
        metavar="TITLE",
        help="Use a specific topic title instead of selecting from the pool.",
    )
    gen.add_argument(
        "--no-random",
        action="store_true",
        default=False,
        help="Pick highest-priority uncompleted topic instead of a random one.",
    )
    gen.add_argument(
        "--no-files",
        action="store_true",
        default=False,
        help="Store in DB only; do not write markdown/JSON files to disk.",
    )
    gen.add_argument(
        "--topics-file",
        default="config/topics.json",
        metavar="PATH",
        help="Path to the topic pool JSON (default: config/topics.json).",
    )
    gen.add_argument(
        "--output-dir",
        default="output/drafts",
        metavar="PATH",
        help="Directory for saved draft files (default: output/drafts).",
    )

    # DB options
    db_grp = parser.add_argument_group("Database")
    db_grp.add_argument(
        "--db",
        default="data/scripts.db",
        metavar="PATH",
        help="SQLite database file (default: data/scripts.db).",
    )

    # Query commands
    query = parser.add_argument_group("Query (skips generation)")
    query.add_argument(
        "--list", "-l",
        action="store_true",
        default=False,
        help="List all scripts stored in the database and exit.",
    )
    query.add_argument(
        "--show", "-s",
        metavar="ID",
        type=int,
        default=None,
        help="Print the carousel JSON for the given script id and exit.",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    db = ScriptDatabase(db_path=Path(args.db))

    if args.list:
        cmd_list(db)
        return

    if args.show is not None:
        cmd_show(db, args.show)
        return

    cmd_generate(
        topic_title=args.topic,
        random_pick=not args.no_random,
        topics_file=Path(args.topics_file),
        output_dir=Path(args.output_dir),
        db=db,
        save_files=not args.no_files,
    )


if __name__ == "__main__":
    main()

