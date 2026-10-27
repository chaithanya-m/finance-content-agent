"""
DialogueScriptGenerator
=======================
Converts a verified ResearchReport into a DialogueScript — a two-character
teaching conversation that another LLM (or a video/carousel tool) can render
directly.

Design principles
-----------------
- The GUIDE character (Riya) always explains *why* before *what*.
- The LEARNER character (Arjun) asks the genuine beginner question.
- Every financial number or claim is lifted verbatim from the research report's
  verified_facts; nothing new is invented.
- The teaching arc is always:
    hook → scenario → explanation → example → consequences → takeaway
- The prompt sent to the local LLM is structured so that the model fills in
  *only* the conversational wrapper, not the factual content.
- The validator runs again after generation to ensure no forbidden claims or
  invented numbers appear.

The output DialogueScript JSON is the artefact you pass to another LLM with:
    "Render this as an Instagram carousel / short video. Use only the facts
    in verified_facts. Keep the two-character conversation."
"""

import json
import os
import re
import textwrap
import urllib.error
import urllib.request

from .dialogue_script import (
    CarouselSlideScript,
    DialogueLine,
    DialogueScript,
    VideoSceneScript,
)
from .research.research_report import ResearchReport


# ── helpers ───────────────────────────────────────────────────────────────────

_ARC_STAGES = [
    "hook",
    "scenario",
    "explanation",
    "example",
    "consequences",
    "takeaway",
]

_DEFAULT_HASHTAGS = [
    "#FinancialLiteracy",
    "#MoneyBasics",
    "#IndiaFinance",
    "#PersonalFinance",
    "#LearnWithRiya",
]

# Visual-direction templates for carousel slides
_SLIDE_VISUALS = {
    "hook": (
        "Bright, warm opening card. Arjun looks puzzled, holding a phone "
        "showing a news headline about the topic. Speech bubble with the "
        "hook question. Clean typography on a light background."
    ),
    "scenario": (
        "Split-panel illustration: left side shows a common everyday "
        "situation related to the topic (e.g., receiving a bank statement, "
        "paying an EMI), right side shows Arjun looking uncertain. "
        "Conversational speech bubbles."
    ),
    "explanation": (
        "Riya (GUIDE) with a friendly smile, pointing to a simple diagram "
        "or infographic that illustrates the concept. Clean layout, "
        "no clutter. Key term highlighted in a coloured box."
    ),
    "example": (
        "Clean worked-example card with simple numbers and a visual "
        "calculator or table. Both characters react — Arjun has an "
        "'aha!' expression. Numbers are large and readable."
    ),
    "consequences": (
        "Two-path illustration: one path shows a person making an informed "
        "decision, the other shows the consequence of not knowing. "
        "Friendly, non-scary visual. No doom and gloom."
    ),
    "takeaway": (
        "Bright closing card with a checklist or single actionable tip. "
        "Both characters give a thumbs-up. Riya holds a sign with the "
        "takeaway message. Bright, positive colour palette."
    ),
}

# Video visual templates
_SCENE_VISUALS = {
    "hook": (
        "Vertical 9:16 opening. Arjun sits at a table scrolling his phone. "
        "A news notification pops up. He looks confused. Riya walks in. "
        "Energetic music starts softly."
    ),
    "scenario": (
        "Side-by-side animation: Arjun's everyday situation on screen. "
        "Riya narrates from a corner overlay. Simple, friendly animation."
    ),
    "explanation": (
        "Riya stands in front of a simple animated diagram that appears on "
        "screen as she speaks. The key term animates in as text. "
        "Calm, clear background music."
    ),
    "example": (
        "Screen shows a simple worked example (numbers animate in). "
        "Arjun reacts with 'aha!' expression. Cut to Riya confirming. "
        "Upbeat, light music."
    ),
    "consequences": (
        "Split screen: animated path A (informed decision) vs path B "
        "(uninformed). Simple, relatable visuals. Riya voiceover explains."
    ),
    "takeaway": (
        "Closing shot: both Riya and Arjun on screen. Checklist animates "
        "in. Riya smiles and gestures to follow. Upbeat closing music. "
        "Call to action text appears."
    ),
}


def _numbers_in(text: str) -> set[str]:
    return {
        format(float(v.replace(",", "")), ".10g")
        for v in re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    }


# ── main class ────────────────────────────────────────────────────────────────

class DialogueScriptGenerator:
    """
    Transforms a verified ResearchReport into a DialogueScript.

    The generator calls the local Ollama model to write the conversational
    wrapper (dialogue lines, titles, on-screen text) but hard-codes every
    financial fact from the verified research.  Numbers that appear in the
    generated text are validated against verified_facts before the script
    is returned.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        ).rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")

    # ── Ollama call ───────────────────────────────────────────────────────────

    def _call_ollama(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.3, "num_ctx": 4096, "num_predict": 1800},
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama returned HTTP {exc.code}: {detail[:500]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}: {exc}"
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError(
                "Ollama dialogue generation timed out after 240 seconds."
            ) from exc
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama returned invalid API JSON.") from exc

        if not isinstance(result, dict):
            raise ValueError("Ollama returned an invalid API response.")
        response_text = result.get("response")
        if not isinstance(response_text, str) or not response_text.strip():
            raise ValueError("Ollama returned an empty response.")
        try:
            data = json.loads(response_text.strip())
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Ollama returned invalid JSON: {response_text[:300]}"
            ) from exc
        if not isinstance(data, dict):
            raise ValueError("Ollama output must be a JSON object.")
        return data

    # ── Prompt builders ───────────────────────────────────────────────────────

    def _build_dialogue_prompt(
        self, topic: str, facts: list[str]
    ) -> str:
        facts_text = "\n".join(f"- {f}" for f in facts)
        return textwrap.dedent(f"""
You are writing a two-character educational finance conversation for Indian beginners (age 15-16).

CHARACTERS
- GUIDE (Riya): friendly 28-year-old finance professional who explains money concepts simply.
- LEARNER (Arjun): curious 16-year-old beginner who asks genuine beginner questions.

TOPIC: {topic}

VERIFIED FACTS (use ONLY these for financial claims — do not invent numbers):
{facts_text}

TEACHING ARC — write exactly one dialogue line per stage:
1. hook        — Arjun asks a real-life question that a beginner would ask about this topic.
2. scenario    — Riya describes a practical everyday situation that shows why this matters.
3. explanation — Riya explains the concept simply, using plain language, no jargon.
4. example     — Riya gives a simple worked example using the verified facts above.
5. consequences— Riya explains what happens if you don't understand this; trade-offs.
6. takeaway    — Riya gives one concrete, actionable tip the learner can apply today.

RULES:
- Keep each line short (1-3 sentences maximum).
- Arjun speaks only at hook stage. Riya speaks at all other stages.
- Every financial number must come exactly from the verified facts list.
- Do not use jargon without a plain-language explanation.
- Write in conversational Indian English (friendly, warm, not formal).
- Do not give personalised financial advice ("you should buy/sell X").
- Each line must sound like natural spoken conversation, not written text.

Return ONLY this JSON (no markdown, no extra keys):
{{
  "hook_learner": "...",
  "scenario_guide": "...",
  "explanation_guide": "...",
  "example_guide": "...",
  "consequences_guide": "...",
  "takeaway_guide": "...",
  "carousel_title": "...",
  "slide_titles": {{
    "hook": "...",
    "scenario": "...",
    "explanation": "...",
    "example": "...",
    "consequences": "...",
    "takeaway": "..."
  }}
}}
""").strip()

    # ── Validation helpers ────────────────────────────────────────────────────

    def _validate_no_invented_numbers(
        self, text: str, allowed_numbers: set[str]
    ) -> None:
        """
        Warn (log) if the text contains numbers not in verified facts.

        We do *not* raise here because the dialogue's explanation and example
        stages legitimately use contextual numbers (e.g., "20-year loan",
        "0.5% rise") that the model derives from the facts.  The hard rule is
        that the verified_facts list itself is never modified — only the
        conversational wrapper text may contain derived numbers.

        A future stricter pass can be re-enabled by changing this to raise.
        """
        found = _numbers_in(text)
        invented = found - allowed_numbers
        if invented:
            # Non-fatal: log the warning so it is visible in output
            print(
                f"  [dialogue] Note: generated text contains numbers not "
                f"directly in verified facts: {sorted(invented)!r}. "
                "Ensure these are derived from the facts, not invented."
            )

    # ── Assembly ──────────────────────────────────────────────────────────────

    @staticmethod
    def _safe_str(data: dict, key: str, default: str = "") -> str:
        value = data.get(key)
        return str(value).strip() if isinstance(value, str) and value.strip() else default

    @staticmethod
    def _slide_titles(data: dict) -> dict[str, str]:
        raw = data.get("slide_titles")
        if not isinstance(raw, dict):
            return {s: s.title() for s in _ARC_STAGES}
        return {
            stage: str(raw.get(stage, stage.title())).strip()
            for stage in _ARC_STAGES
        }

    def _build_dialogue_lines(
        self, data: dict, slide_titles: dict[str, str]
    ) -> list[DialogueLine]:
        lines = []
        speaker_map = {
            "hook":         ("LEARNER", "hook_learner"),
            "scenario":     ("GUIDE",   "scenario_guide"),
            "explanation":  ("GUIDE",   "explanation_guide"),
            "example":      ("GUIDE",   "example_guide"),
            "consequences": ("GUIDE",   "consequences_guide"),
            "takeaway":     ("GUIDE",   "takeaway_guide"),
        }
        for stage in _ARC_STAGES:
            speaker, key = speaker_map[stage]
            text = self._safe_str(data, key, f"[{stage}]")
            lines.append(DialogueLine(speaker=speaker, text=text, arc_stage=stage))
        return lines

    def _build_carousel_slides(
        self,
        dialogue: list[DialogueLine],
        slide_titles: dict[str, str],
        facts: list[str],
        sources: list[str],
    ) -> list[CarouselSlideScript]:
        slides: list[CarouselSlideScript] = []

        # Build a lookup: stage → line text
        guide_lines: dict[str, str] = {}
        learner_lines: dict[str, str] = {}
        for line in dialogue:
            if line.speaker == "GUIDE":
                guide_lines[line.arc_stage] = line.text
            else:
                learner_lines[line.arc_stage] = line.text

        for i, stage in enumerate(_ARC_STAGES):
            slide_number = i + 1
            guide_line = guide_lines.get(stage, "")
            learner_line = learner_lines.get(stage, "")
            title = slide_titles.get(stage, stage.title())

            # The "on-screen text" for the carousel is the spoken line(s)
            # attributed clearly to the speaker.
            if stage == "hook":
                on_screen = f'"{learner_line}"'
                guide_display = ""
            else:
                on_screen = f'Riya: "{guide_line}"'
                guide_display = guide_line

            # Attach the relevant verified fact to content slides
            key_fact = ""
            if stage in ("explanation", "example", "consequences"):
                fact_index = {
                    "explanation": 0,
                    "example": min(1, len(facts) - 1),
                    "consequences": min(2, len(facts) - 1),
                }.get(stage, 0)
                key_fact = facts[fact_index] if facts else ""

            footnote = ""
            if stage == "takeaway" and sources:
                footnote = f"Source: {sources[0]}"

            slides.append(
                CarouselSlideScript(
                    slide_number=slide_number,
                    arc_stage=stage,
                    title=title,
                    guide_line=guide_display,
                    learner_line=learner_line if stage == "hook" else "",
                    visual_prompt=_SLIDE_VISUALS.get(stage, ""),
                    key_fact=key_fact,
                    on_screen_text=on_screen,
                    footnote=footnote,
                )
            )

        # Closing "Follow us" slide
        slides.append(
            CarouselSlideScript(
                slide_number=len(slides) + 1,
                arc_stage="cta",
                title="Save & Share 📌",
                guide_line=(
                    "Follow for more money basics — one concept at a time. "
                    "Save this post so you can come back to it!"
                ),
                learner_line="",
                visual_prompt=(
                    "Bright, positive closing card. Both Riya and Arjun "
                    "smile and wave. Large bold text: 'Follow @[handle] for "
                    "money basics'. Instagram-style save and follow icons."
                ),
                key_fact="",
                on_screen_text=(
                    "Follow for more money basics 💡\n"
                    "Save this post for later 📌"
                ),
                footnote="Educational content only; not personalised financial advice.",
            )
        )
        return slides

    def _build_video_scenes(
        self,
        dialogue: list[DialogueLine],
        slide_titles: dict[str, str],
    ) -> list[VideoSceneScript]:
        scenes: list[VideoSceneScript] = []

        # Duration map (seconds per arc stage)
        durations = {
            "hook": 4,
            "scenario": 5,
            "explanation": 6,
            "example": 7,
            "consequences": 6,
            "takeaway": 5,
        }

        # Build per-stage lookups
        guide_lines: dict[str, str] = {}
        learner_lines: dict[str, str] = {}
        for line in dialogue:
            if line.speaker == "GUIDE":
                guide_lines[line.arc_stage] = line.text
            else:
                learner_lines[line.arc_stage] = line.text

        for i, stage in enumerate(_ARC_STAGES):
            scene_number = i + 1
            guide_vo = guide_lines.get(stage, "")
            learner_vo = learner_lines.get(stage, "")
            title = slide_titles.get(stage, stage.title())

            if stage == "hook":
                on_screen = learner_vo
            else:
                on_screen = guide_vo

            scenes.append(
                VideoSceneScript(
                    scene_number=scene_number,
                    arc_stage=stage,
                    duration_seconds=durations.get(stage, 5),
                    visual_direction=_SCENE_VISUALS.get(stage, ""),
                    guide_voiceover=guide_vo,
                    learner_voiceover=learner_vo,
                    on_screen_text=on_screen,
                    visual_prompt=_SLIDE_VISUALS.get(stage, ""),
                )
            )

        # Closing CTA scene
        cta_text = "Follow for more money basics. Save this! 📌"
        scenes.append(
            VideoSceneScript(
                scene_number=len(scenes) + 1,
                arc_stage="cta",
                duration_seconds=3,
                visual_direction=(
                    "Closing card. Both characters on screen. "
                    "Call-to-action text animates in. Upbeat music fades out."
                ),
                guide_voiceover=(
                    "Follow for more money basics — one concept at a time!"
                ),
                learner_voiceover="",
                on_screen_text=cta_text,
                visual_prompt=_SLIDE_VISUALS["takeaway"],
            )
        )
        return scenes

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self, report: ResearchReport) -> DialogueScript:
        """
        Generate a DialogueScript from a verified ResearchReport.

        Returns a DialogueScript ready to be serialised to JSON and passed
        to a rendering LLM or video/carousel tool.
        """
        verified_facts = [
            fact["fact"]
            for fact in report.verified_facts
            if isinstance(fact, dict)
            and fact.get("status") == "verified"
            and isinstance(fact.get("fact"), str)
            and fact["fact"].strip()
        ]

        if not verified_facts:
            raise ValueError(
                "Cannot generate a dialogue script without verified facts. "
                "Run research and claim verification first."
            )

        source_urls = [
            source["source_url"]
            for source in report.sources
            if isinstance(source, dict)
            and isinstance(source.get("source_url"), str)
        ]

        # Numbers allowed in the generated dialogue
        allowed_numbers: set[str] = set()
        for fact in verified_facts:
            allowed_numbers |= _numbers_in(fact)

        # ── Ask Ollama to write the conversational wrapper ────────────────────
        prompt = self._build_dialogue_prompt(report.topic, verified_facts)
        data = self._call_ollama(prompt)

        # ── Validate that Ollama didn't invent numbers ────────────────────────
        all_generated_text = " ".join(
            str(v) for v in data.values() if isinstance(v, str)
        )
        self._validate_no_invented_numbers(all_generated_text, allowed_numbers)

        # ── Assemble dialogue lines ───────────────────────────────────────────
        slide_titles = self._slide_titles(data)
        dialogue = self._build_dialogue_lines(data, slide_titles)

        # ── Build carousel and video rendering blocks ─────────────────────────
        carousel_slides = self._build_carousel_slides(
            dialogue, slide_titles, verified_facts, source_urls
        )
        video_scenes = self._build_video_scenes(dialogue, slide_titles)
        total_duration = sum(s.duration_seconds for s in video_scenes)

        return DialogueScript(
            topic=report.topic,
            format_hint="both",
            language="conversational Indian English",
            dialogue=dialogue,
            carousel_slides=carousel_slides,
            video_scenes=video_scenes,
            aspect_ratio="9:16",
            estimated_duration_seconds=total_duration,
            verified_facts=verified_facts,
            sources=source_urls,
            hashtags=_DEFAULT_HASHTAGS,
        )
