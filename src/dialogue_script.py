"""
Dialogue script data structures.

A DialogueScript is the rendering-ready output passed to another LLM (or a
video / carousel generator) that must produce content in the two-person
conversational teaching style inspired by the "Money Psychology" teaching
approach.

The two characters are:
  - GUIDE  — a patient, knowledgeable friend who lives in India
  - LEARNER — a curious 15-16-year-old (or any beginner) who asks
               honest, relatable questions

The script follows the mandatory teaching arc:
  1. HOOK         — a relatable real-life question or situation
  2. SCENARIO     — a practical problem or common mistake
  3. EXPLANATION  — the concept explained through the situation
  4. EXAMPLE      — simple numbers and a worked example
  5. CONSEQUENCES — why the concept matters; trade-offs
  6. TAKEAWAY     — a concrete, actionable next step

Both formats (carousel and video) are derived from the *same* DialogueScript.

IMPORTANT: The script carries `verified_facts` and `sources`.  Any LLM that
renders this script MUST NOT invent numbers, claims, or financial details
beyond what is listed in those two fields.  Every financial statement spoken
by the GUIDE must be traceable to one of the verified_facts entries.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DialogueLine:
    """One spoken line in the teaching conversation."""

    speaker: str          # "GUIDE" or "LEARNER"
    text: str             # What the speaker says
    arc_stage: str        # One of: hook, scenario, explanation, example,
    #                       consequences, takeaway


@dataclass
class CarouselSlideScript:
    """
    Instructions for one carousel slide.

    The slide should visualise the dialogue exchange that happens at this
    point in the teaching arc.  The visual_prompt field describes what an
    image-generation model should draw.
    """

    slide_number: int
    arc_stage: str                    # hook | scenario | explanation | example | consequences | takeaway
    title: str                        # Short heading that appears on the slide
    guide_line: str                   # What GUIDE says on this slide
    learner_line: str                 # What LEARNER says / thinks on this slide
    visual_prompt: str                # Text prompt for the slide illustration
    key_fact: str                     # The verified fact this slide is built on (or "" for hook)
    on_screen_text: str               # The readable text that must appear on screen
    footnote: str = ""                # Optional: source or brief footnote text


@dataclass
class VideoSceneScript:
    """
    Instructions for one scene in the short-form vertical video.

    The scene shows a brief exchange between GUIDE and LEARNER.
    The voiceover alternates between their voices.
    """

    scene_number: int
    arc_stage: str
    duration_seconds: int
    visual_direction: str             # Cinematography / animation direction
    guide_voiceover: str              # GUIDE's spoken line for this scene
    learner_voiceover: str           # LEARNER's spoken line for this scene
    on_screen_text: str               # Text overlay visible on screen
    visual_prompt: str                # Image/B-roll generation prompt


@dataclass
class DialogueScript:
    """
    The complete teaching script for one finance topic.

    Pass this object (serialised to JSON) to another LLM with the following
    instruction:

        "You will receive a DialogueScript JSON.  Use ONLY the verified_facts
        and the dialogue lines provided.  Do not add financial numbers, claims,
        or advice that are not in verified_facts.  Render the content in the
        format requested (carousel or video), preserving the two-character
        teaching conversation."

    RENDERING CONTRACT
    ------------------
    - Keep GUIDE as a calm, friendly expert who lives in India.
    - Keep LEARNER as a genuinely curious beginner (15-16 years old).
    - GUIDE never gives personalised financial advice.
    - GUIDE always explains *why* a concept matters before stating the fact.
    - LEARNER asks the question a real beginner would ask.
    - Every financial number or statistic must come from verified_facts.
    - The final slide / scene must always contain the takeaway.
    - Caption and call_to_action are fixed; do not change them.
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    topic: str
    format_hint: str          # "carousel" | "video" | "both"
    language: str             # "conversational Indian English"

    # ── Characters ───────────────────────────────────────────────────────────
    guide_persona: str = (
        "Riya — a friendly, knowledgeable 28-year-old who works in finance "
        "and loves explaining money concepts to beginners."
    )
    learner_persona: str = (
        "Arjun — a curious 16-year-old who has just started paying attention "
        "to money and asks honest, relatable questions."
    )

    # ── Teaching arc (full dialogue) ──────────────────────────────────────────
    dialogue: list[DialogueLine] = field(default_factory=list)

    # ── Carousel rendering instructions ───────────────────────────────────────
    carousel_slides: list[CarouselSlideScript] = field(default_factory=list)

    # ── Video rendering instructions ──────────────────────────────────────────
    video_scenes: list[VideoSceneScript] = field(default_factory=list)
    aspect_ratio: str = "9:16"
    estimated_duration_seconds: int = 0

    # ── Verified grounding (DO NOT change) ───────────────────────────────────
    verified_facts: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    # ── Fixed publishing fields ───────────────────────────────────────────────
    caption: str = (
        "Educational content only; this is not personalised financial advice."
    )
    call_to_action: str = (
        "Follow for more money basics. Save this for later! 📌"
    )
    hashtags: list[str] = field(default_factory=list)

