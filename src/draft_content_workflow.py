import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .content_validator import ContentValidator
from .dialogue_script import DialogueScript
from .dialogue_script_generator import DialogueScriptGenerator
from .research.local_research_agent import LocalResearchAgent
from .research.research_request import ResearchRequest
from .research.topic import Topic
from .research.topic_generator import AITopicGenerator
from .research.topic_selector import TopicSelector
from .research_content_generator import ResearchContentGenerator


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:70].strip("-") or "finance-topic"


def slide_text(slide: Any) -> str:
    if isinstance(slide, dict):
        parts = [
            str(slide[key]).strip()
            for key in ("title", "content", "text")
            if slide.get(key)
        ]
        return " — ".join(parts) if parts else json.dumps(slide, ensure_ascii=False)
    return str(slide).strip()


class DraftContentWorkflow:
    """Generate and save finance content drafts without publishing."""

    def __init__(
        self,
        topics_file: Path = Path("config/topics.json"),
        output_dir: Path = Path("output/drafts"),
    ) -> None:
        self.topics_file = topics_file
        self.output_dir = output_dir
        self.history_file = output_dir / ".topic_history.json"

    def _load_topics(self) -> list[Topic]:
        if not self.topics_file.exists():
            raise FileNotFoundError(
                f"Topic configuration not found: {self.topics_file}"
            )

        data = json.loads(self.topics_file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Topic configuration must be a JSON list.")

        topics = []
        for item in data:
            if not isinstance(item, dict) or not item.get("title") or not item.get("reason"):
                raise ValueError("Each topic must have a title and a reason.")

            topics.append(
                Topic(
                    title=str(item["title"]),
                    reason=str(item["reason"]),
                    content_type=str(item.get("content_type", "carousel")),
                    priority=str(item.get("priority", "medium")),
                )
            )

        if not topics:
            raise ValueError("No topics are configured.")

        return topics

    def _load_history(self) -> list[dict[str, Any]]:
        if not self.history_file.exists():
            return []

        history = json.loads(self.history_file.read_text(encoding="utf-8"))
        if not isinstance(history, list):
            raise ValueError(f"Invalid topic history: {self.history_file}")

        return [item for item in history if isinstance(item, dict)]

    def select_topic(
        self,
        requested_title: str | None = None,
        random_pick: bool = False,
        skip_titles: set[str] | None = None,
        use_ai: bool = False,
    ) -> Topic:
        if requested_title:
            topics = self._load_topics()
            match = next(
                (topic for topic in topics
                 if topic.title.casefold() == requested_title.strip().casefold()),
                None,
            )
            if match:
                return match

            return Topic(
                title=requested_title.strip(),
                reason="Create educational finance content using current, reliable sources for an Indian audience.",
                content_type="carousel",
                priority="high",
            )

        # Build the set of already-completed titles
        history = self._load_history()
        completed = {
            item.get("title")
            for item in history
            if isinstance(item.get("title"), str)
        }
        # Also exclude any titles provided externally (e.g. from the DB)
        if skip_titles:
            completed |= skip_titles

        if use_ai:
            return AITopicGenerator().generate(exclude_titles=completed)

        topics = self._load_topics()
        available = [topic for topic in topics if topic.title not in completed]

        if not available:
            # If all topics are done, reset and allow any topic
            available = topics

        selected = TopicSelector().select(available, random_pick=random_pick)
        if selected is None:
            raise RuntimeError("No topic could be selected.")

        return selected

    @staticmethod
    def _build_video_script(post: Any) -> dict[str, Any]:
        """Create a video shot list from the validated carousel, without adding facts."""
        scenes = [
            {
                "scene": 1,
                "duration_seconds": 3,
                "visual_direction": (
                    "Vertical 9:16 opening card with readable typography "
                    "and a simple finance-themed visual."
                ),
                "on_screen_text": post.hook,
                "voiceover": post.hook,
            }
        ]

        for index, slide in enumerate(post.slides, start=2):
            text = slide_text(slide)
            scenes.append(
                {
                    "scene": index,
                    "duration_seconds": 5,
                    "visual_direction": (
                        "Show the supplied text with clean typography and "
                        "simple supporting visuals. Do not add statistics "
                        "or facts that are not in the supplied text."
                    ),
                    "on_screen_text": text,
                    "voiceover": text,
                }
            )

        scenes.append(
            {
                "scene": len(scenes) + 1,
                "duration_seconds": 3,
                "visual_direction": "Show a simple closing card and call to action.",
                "on_screen_text": post.call_to_action,
                "voiceover": post.call_to_action,
            }
        )

        return {
            "topic": post.topic,
            "format": "short-form vertical video script",
            "aspect_ratio": "9:16",
            "estimated_duration_seconds": sum(
                scene["duration_seconds"] for scene in scenes
            ),
            "scenes": scenes,
            "caption": post.caption,
            "sources": post.sources,
            "claims": post.claims,
        }

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _carousel_markdown(post: Any) -> str:
        lines = [
            f"# {post.topic}",
            "",
            "## Hook",
            "",
            post.hook,
            "",
            "## Slides",
            "",
        ]

        for index, slide in enumerate(post.slides, start=1):
            lines.extend([f"### Slide {index}", "", slide_text(slide), ""])

        lines.extend(
            [
                "## Caption",
                "",
                post.caption,
                "",
                "## Call to action",
                "",
                post.call_to_action,
                "",
                "## Verified claims supplied to the generator",
                "",
            ]
        )
        lines.extend(f"- {claim}" for claim in post.claims)
        lines.extend(["", "## Sources", ""])
        lines.extend(f"- {url}" for url in post.sources)

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _video_markdown(video: dict[str, Any]) -> str:
        lines = [
            f"# Video script: {video['topic']}",
            "",
            f"**Format:** Vertical video ({video['aspect_ratio']})",
            f"**Estimated duration:** {video['estimated_duration_seconds']} seconds",
            "",
        ]

        for scene in video["scenes"]:
            lines.extend(
                [
                    f"## Scene {scene['scene']} — {scene['duration_seconds']} seconds",
                    "",
                    f"**Visual direction:** {scene['visual_direction']}",
                    "",
                    f"**On-screen text:** {scene['on_screen_text']}",
                    "",
                    f"**Voiceover:** {scene['voiceover']}",
                    "",
                ]
            )

        lines.extend(["## Caption", "", video["caption"], "", "## Sources", ""])
        lines.extend(f"- {url}" for url in video["sources"])

        return "\n".join(lines).rstrip() + "\n"

    # ── Dialogue script renderers ─────────────────────────────────────────────

    @staticmethod
    def _dialogue_carousel_markdown(script: DialogueScript) -> str:
        """
        Human-readable markdown for the dialogue-format carousel.

        Pass the JSON version (dialogue_carousel.json) to another LLM with:

            "You will receive a CarouselScript JSON. Render each slide as an
             Instagram carousel image. Keep the two-character conversation.
             Use only the facts listed in verified_facts."
        """
        lines = [
            f"# Carousel script: {script.topic}",
            "",
            "> **Rendering contract** — pass `dialogue_carousel.json` to your",
            "> image-generation or carousel-creation LLM with this instruction:",
            "> *\"Render each slide as described. Keep the GUIDE / LEARNER",
            "> conversation. Use only the facts listed in verified_facts.\"*",
            "",
            f"**Characters:** {script.guide_persona}  |  {script.learner_persona}",
            f"**Language:** {script.language}",
            f"**Format:** Instagram carousel ({len(script.carousel_slides)} slides)",
            "",
            "---",
            "",
        ]

        for slide in script.carousel_slides:
            lines.extend([
                f"## Slide {slide.slide_number} — {slide.arc_stage.upper()}",
                "",
                f"**Title:** {slide.title}",
                "",
            ])
            if slide.learner_line:
                lines.extend([
                    f"**🧑 Arjun (Learner):** {slide.learner_line}",
                    "",
                ])
            if slide.guide_line:
                lines.extend([
                    f"**👩 Riya (Guide):** {slide.guide_line}",
                    "",
                ])
            lines.extend([
                f"**📱 On-screen text:** {slide.on_screen_text}",
                "",
                f"**🎨 Visual prompt:** {slide.visual_prompt}",
                "",
            ])
            if slide.key_fact:
                lines.extend([
                    f"**📌 Verified fact used:** {slide.key_fact}",
                    "",
                ])
            if slide.footnote:
                lines.extend([
                    f"**📎 Footnote:** {slide.footnote}",
                    "",
                ])
            lines.append("---")
            lines.append("")

        lines.extend([
            "## Caption",
            "",
            script.caption,
            "",
            "## Call to action",
            "",
            script.call_to_action,
            "",
            "## Hashtags",
            "",
            " ".join(script.hashtags),
            "",
            "## Verified facts (do not change or add to these)",
            "",
        ])
        lines.extend(f"- {fact}" for fact in script.verified_facts)
        lines.extend(["", "## Sources", ""])
        lines.extend(f"- {url}" for url in script.sources)

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _dialogue_video_markdown(script: DialogueScript) -> str:
        """
        Human-readable markdown for the dialogue-format video script.

        Pass the JSON version (dialogue_video.json) to a video generation
        LLM or tool with:

            "You will receive a VideoScript JSON. Render each scene as a
             short vertical video segment. Keep the GUIDE / LEARNER dialogue.
             Use only the facts in verified_facts. Do not add numbers or
             claims that are not in verified_facts."
        """
        lines = [
            f"# Video script: {script.topic}",
            "",
            "> **Rendering contract** — pass `dialogue_video.json` to your",
            "> video-generation LLM or tool with this instruction:",
            "> *\"Render each scene as described. Keep the GUIDE / LEARNER",
            "> dialogue. Use only facts in verified_facts.\"*",
            "",
            f"**Characters:** {script.guide_persona}  |  {script.learner_persona}",
            f"**Format:** Vertical video ({script.aspect_ratio})",
            f"**Estimated duration:** {script.estimated_duration_seconds} seconds",
            f"**Language:** {script.language}",
            "",
            "---",
            "",
            "## Full Teaching Dialogue",
            "",
            "*(Use this to understand the conversational flow before rendering scenes.)*",
            "",
        ]

        for line in script.dialogue:
            emoji = "👩" if line.speaker == "GUIDE" else "🧑"
            name = "Riya" if line.speaker == "GUIDE" else "Arjun"
            lines.extend([
                f"**{emoji} {name} [{line.arc_stage.upper()}]:** {line.text}",
                "",
            ])

        lines.extend(["---", "", "## Scenes", ""])

        for scene in script.video_scenes:
            lines.extend([
                f"## Scene {scene.scene_number} — {scene.arc_stage.upper()} "
                f"({scene.duration_seconds}s)",
                "",
                f"**🎬 Visual direction:** {scene.visual_direction}",
                "",
                f"**📱 On-screen text:** {scene.on_screen_text}",
                "",
            ])
            if scene.learner_voiceover:
                lines.extend([
                    f"**🧑 Arjun (voiceover):** {scene.learner_voiceover}",
                    "",
                ])
            if scene.guide_voiceover:
                lines.extend([
                    f"**👩 Riya (voiceover):** {scene.guide_voiceover}",
                    "",
                ])
            lines.extend([
                f"**🎨 Visual prompt:** {scene.visual_prompt}",
                "",
                "---",
                "",
            ])

        lines.extend([
            "## Caption",
            "",
            script.caption,
            "",
            "## Verified facts (do not change or add to these)",
            "",
        ])
        lines.extend(f"- {fact}" for fact in script.verified_facts)
        lines.extend(["", "## Sources", ""])
        lines.extend(f"- {url}" for url in script.sources)

        return "\n".join(lines).rstrip() + "\n"

    def generate_drafts(self, topic: Topic) -> Path:
        request = ResearchRequest(
            topic=topic.title,
            research_question=(
                f"{topic.reason} Research current information using authoritative "
                "Indian sources. Preserve source URLs and supporting evidence. "
                "Do not mark a claim verified unless the finance-research "
                "verification tool returns status 'verified'."
            ),
        )

        print("Researching topic and verifying claims...")
        report = LocalResearchAgent().research(request)

        verified_facts = [
            fact
            for fact in report.verified_facts
            if isinstance(fact, dict)
            and fact.get("status") == "verified"
            and isinstance(fact.get("fact"), str)
        ]
        if not verified_facts:
            research_notes = [
                item.get("notes", item.get("fact", ""))
                for item in report.unverified_claims[:3]
                if isinstance(item, dict)
            ]
            raise ValueError(
                "Research produced no verified claims; no drafts were generated. "
                f"Research notes={research_notes}, "
                f"unverified_claims={len(report.unverified_claims)}, "
                f"sources={len(report.sources)}."
            )

        print("Generating carousel...")
        post = ResearchContentGenerator().generate(report)

        if not ContentValidator().validate(post, report):
            raise ValueError(
                "Generated carousel failed validation. No drafts were saved."
            )

        video = self._build_video_script(post)

        # ── Dialogue scripts (new two-character teaching format) ──────────────
        print("Generating dialogue teaching scripts...")
        dialogue_script: DialogueScript | None = None
        dialogue_error: str | None = None
        try:
            dialogue_script = DialogueScriptGenerator().generate(report)
        except (ValueError, RuntimeError) as exc:
            dialogue_error = str(exc)
            print(
                f"  Warning: dialogue script generation failed — {exc}\n"
                "  Continuing without dialogue scripts."
            )

        now = datetime.now().astimezone()
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        output_path = self.output_dir / f"{timestamp}_{slugify(topic.title)}"
        output_path.mkdir(parents=True, exist_ok=False)

        self._write_json(output_path / "research_report.json", asdict(report))
        self._write_json(output_path / "carousel.json", asdict(post))
        (output_path / "carousel.md").write_text(
            self._carousel_markdown(post), encoding="utf-8"
        )
        self._write_json(output_path / "video_script.json", video)
        (output_path / "video_script.md").write_text(
            self._video_markdown(video), encoding="utf-8"
        )

        # Write dialogue scripts (best-effort — do not fail the entire workflow)
        if dialogue_script is not None:
            self._write_json(
                output_path / "dialogue_carousel.json",
                asdict(dialogue_script),
            )
            (output_path / "dialogue_carousel.md").write_text(
                self._dialogue_carousel_markdown(dialogue_script),
                encoding="utf-8",
            )
            self._write_json(
                output_path / "dialogue_video.json",
                asdict(dialogue_script),
            )
            (output_path / "dialogue_video.md").write_text(
                self._dialogue_video_markdown(dialogue_script),
                encoding="utf-8",
            )
        elif dialogue_error:
            (output_path / "dialogue_error.txt").write_text(
                dialogue_error, encoding="utf-8"
            )

        history = self._load_history()
        history.append(
            {
                "title": topic.title,
                "generated_at": now.isoformat(),
                "output_directory": str(output_path),
            }
        )
        temporary_history = self.history_file.with_suffix(".tmp")
        temporary_history.write_text(
            json.dumps(history, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary_history.replace(self.history_file)

        return output_path
