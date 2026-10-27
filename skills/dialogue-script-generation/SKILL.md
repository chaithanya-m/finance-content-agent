---
name: dialogue-script-generation
description: Transform verified Indian finance research into a two-character conversational teaching script (Riya + Arjun) for Instagram carousels and vertical videos.
---

# Dialogue Script Generation

This skill guides the creation of engaging, two-person educational finance scripts from verified research reports. The output serves as the production blueprint for AI carousel designers, image generators, and video/voice synthesis models.

## 1. Core Philosophy

> "Help people understand money, not merely hear about it. Content must teach, not merely describe."

Target audience: A 15–16-year-old in India with zero prior finance background.

Teaching style is inspired by real mentor-beginner dialogues:
- Start with a relatable real-life question or dilemma.
- Reveal an everyday situation or common financial mistake.
- Explain the concept through that situation rather than textbook definitions.
- Use simple numbers and clear worked examples.
- Highlight the consequences and trade-offs.
- End with a concrete, actionable takeaway.

---

## 2. Character Personas

The script must feature two consistent characters:

### 👩 Riya (The Guide)
- **Role:** Friendly 28-year-old finance professional living in India.
- **Tone:** Warm, patient, accessible, practical.
- **Language:** Conversational Indian English (natural, everyday idioms, never corporate or bureaucratic).
- **Rule:** Always explains *why* something matters before stating *what* it is. Never offers personalized investment advice ("you should buy X").

### 🧑 Arjun (The Learner)
- **Role:** Curious 16-year-old beginner who is just starting to learn about money.
- **Tone:** Honest, relatable, inquisitive, slightly skeptical.
- **Rule:** Asks the real questions beginners actually wonder about. Speaks primarily at the **Hook** stage.

---

## 3. Mandatory 6-Stage Teaching Arc

Every dialogue script must progress through these six stages in exact order:

| Stage | Speaker | Function | Carousel & Video Visuals |
|---|---|---|---|
| **1. Hook** | Arjun (Learner) | Relatable question or real-life problem beginners face. | Arjun looking puzzled at a phone or news notification. Speech bubble with the hook. |
| **2. Scenario** | Riya (Guide) | Everyday situation showing why this concept matters. | Split-panel showing real-life context (bank statement, EMI payment, shopping bill). |
| **3. Explanation** | Riya (Guide) | Clear explanation of the concept in plain English. No jargon without immediate definition. | Riya pointing to a clean diagram or visual breakdown with key terms highlighted. |
| **4. Example** | Riya (Guide) | Simple worked example using verified numbers from research. | Visual calculator/table card. Arjun has an "aha!" expression. Clear, large numbers. |
| **5. Consequences** | Riya (Guide) | What happens if you don't know this; trade-offs and rules. | Two-path illustration: informed choice vs uninformed pitfall. Non-alarmist. |
| **6. Takeaway** | Riya (Guide) | Concrete action step or checklist the learner can use today. | Checklist card. Both characters smiling with thumbs-up. Clear actionable next step. |
| **CTA Slide** | Both | Channel follow and save prompt. | Bright closing card: "Follow for money basics 💡 / Save for later 📌". |

---

## 4. Grounding and Verification Constraints

All scripts must adhere to strict factual integrity rules:

1. **Strictly Grounded in `verified_facts`:** Every financial figure, benchmark rate, regulation, or rule spoken by Riya must come directly from the research report's verified facts.
2. **No Invented Numbers:** Do not introduce speculative rates, fictitious dates, or random currency amounts. Any worked example numbers must either match verified facts or directly illustrate them without contradicting reality.
3. **No Unverified Claims:** Any claim marked `Unverified` or `Conflicting` in research is strictly barred from the dialogue.
4. **No Financial Advice:** Never use phrases like:
   - "You should invest in..."
   - "Buy this stock/fund"
   - "Guaranteed returns" / "Risk-free"
5. **Mandatory Disclaimers:** All scripts must include:
   - Caption: `"Educational content only; this is not personalized financial advice."`
   - Call to action: `"Review the cited sources before sharing."` or `"Save this post for later 📌"`

---

## 5. Output Deliverables

The script generator produces structured files ready for downstream tools:

### `dialogue_carousel.json` / `.md`
- Contains array of `carousel_slides` (7 slides: 6 arc stages + 1 CTA).
- Each slide defines:
  - `slide_number`, `arc_stage`, `title`
  - `guide_line`, `learner_line`
  - `on_screen_text` (text overlay for the graphic)
  - `visual_prompt` (prompt for image generation or Canva layout)
  - `key_fact` (citation tracing back to source)
  - `footnote` (official source link)

### `dialogue_video.json` / `.md`
- Contains array of `video_scenes` (7 scenes matching the arc).
- Each scene defines:
  - `scene_number`, `arc_stage`, `duration_seconds`
  - `guide_voiceover`, `learner_voiceover`
  - `visual_direction` (cinematography, transitions, pacing)
  - `on_screen_text` (subtitles/captions overlay)
  - `visual_prompt` (B-roll generation prompt)
- Global metadata: `aspect_ratio: "9:16"`, `estimated_duration_seconds` (~30–45s).

---

## 6. Downstream Rendering Contract

When handing off the generated scripts to secondary models or creators:

### For Image / Carousel Models (e.g., Midjourney, Flux, Canva AI, Claude/GPT Canvas):
```text
Render each slide in dialogue_carousel.json as a 1080x1350 Instagram carousel card.
- Maintain consistent visual design: clean modern typography, warm colors.
- Visually depict Riya (friendly female finance educator) and Arjun (teenage learner).
- Place on_screen_text prominently with high readability.
- Strictly include the cited key_fact and footnote on educational slides.
- Do NOT alter any financial figures from verified_facts.
```

### For Video / Audio Models (e.g., ElevenLabs, Runway, Kling, CapCut):
```text
Render the vertical video script from dialogue_video.json (9:16 aspect ratio).
- Voice 1 (Riya): Warm, confident Indian English female voice (age ~28).
- Voice 2 (Arjun): Inquisitive, young Indian English male voice (age ~16).
- Follow visual_direction for scene cuts and pacing.
- Display on_screen_text as synchronized animated captions.
```

---

## 7. Database Persistence

All generated scripts are persisted into SQLite (`data/scripts.db`):
- `scripts` table: stores topic, timestamp, status (`ready`/`failed`/`published`), full `carousel_json`, `video_json`, `verified_facts`, `sources`, and filesystem `output_dir`.
- `topics_history` table: logs every generation run to prevent duplicate topic selection.

