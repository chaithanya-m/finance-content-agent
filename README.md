# Finance Content Agent

An autonomous agent that selects an Indian personal-finance topic, researches
it using authoritative sources (RBI, SEBI, MOSPI, Income Tax, CBIC), verifies
every factual claim, generates a two-character **teaching dialogue** between
*Riya* (a finance guide) and *Arjun* (a curious beginner), produces
carousel and video scripts ready to hand off to a rendering LLM, and stores
everything in a local SQLite database.

> **Core principle:**
> *"Help people understand money, not merely hear about it."*
> Content teaches. It does not just describe.

---

## How the application works — complete flow

```
config/topics.json
       │
       ▼
┌──────────────────────┐
│  1. Topic Selection  │  pick random (or highest-priority) uncompleted topic
│  TopicSelector       │  skips topics already in DB or topic history
└──────────┬───────────┘
           │  Topic{title, reason, priority}
           ▼
┌──────────────────────┐
│  2. Source Discovery │  ResearchSourceDiscovery
│  source_discovery.py │  maps topic → curated list of official URLs
└──────────┬───────────┘  (RBI, SEBI, MOSPI, CBIC, Income Tax, CIBIL)
           │  list[SourceCandidate]
           ▼
┌──────────────────────┐
│  3. Page Fetching    │  LocalResearchAgent._fetch_page()
│  local_research_     │  downloads each URL, strips HTML,
│  agent.py            │  keeps first 80 KB of readable text
└──────────┬───────────┘
           │  page text per source
           ▼
┌──────────────────────────────┐
│  4. Statement Extraction     │  _source_statements() + _relevant_statements()
│  local_research_agent.py     │  pulls verbatim sentences from source text
│                              │  that match topic keywords
└──────────┬───────────────────┘
           │  list of verbatim quotes (Q1, Q2 …)
           ▼
┌──────────────────────────────┐
│  5. Claim Drafting           │  LocalResearchAgent._make_claims()
│  (Ollama LLM call #1)        │  asks Ollama to write ≤4 short plain-language
│                              │  paraphrases grounded in those verbatim quotes
└──────────┬───────────────────┘
           │  list[{id, claim, evidence_ids}]
           ▼
┌──────────────────────────────┐
│  6. Claim Verification       │  LocalResearchAgent._verify_claims()
│  (Ollama LLM call #2)        │  asks Ollama: does the verbatim quote
│  + claim_verifier.py         │  actually entail the drafted claim?
│  + source_rules.py           │  also checks: numbers match, topic terms
│                              │  match, source authority is high/medium
└──────────┬───────────────────┘
           │  verified_facts  (status="verified")
           │  unverified_claims (dropped from content)
           ▼
┌──────────────────────────────┐
│  7. ResearchReport           │  research_pipeline.py
│                              │  structured record: verified_facts,
│                              │  unverified_claims, sources, numbers
└──────────┬───────────────────┘
           │  ResearchReport
     ┌─────┴──────────┐
     │                │
     ▼                ▼
┌──────────┐    ┌────────────────────────────────────┐
│ Legacy   │    │  8. Dialogue Script Generation     │
│ carousel │    │  DialogueScriptGenerator           │
│ + video  │    │  (Ollama LLM call #3)              │
│ script   │    │                                    │
│ (kept    │    │  Asks Ollama to write the          │
│ for      │    │  conversational wrapper ONLY:      │
│ compat.) │    │  hook / scenario / explanation /   │
│          │    │  example / consequences / takeaway │
│          │    │  for two characters: Riya + Arjun  │
└──────────┘    │                                    │
                │  Validated: no invented numbers,   │
                │  verified_facts never rewritten    │
                └──────────┬─────────────────────────┘
                           │  DialogueScript
                           ▼
                ┌──────────────────────┐
                │  9. Rendering Output │
                │  DraftContentWorkflow│
                │                     │
                │  dialogue_carousel   │  ← pass to image LLM
                │    .json / .md       │
                │  dialogue_video      │  ← pass to video LLM
                │    .json / .md       │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │  10. Database Store  │
                │  ScriptDatabase      │
                │  (data/scripts.db)   │
                │                     │
                │  scripts table       │
                │  topics_history table│
                └──────────────────────┘
```

---

## Quick start

### 1. Requirements

| Requirement | Notes |
|---|---|
| Python 3.10+ | Standard library only for the core pipeline |
| Internet access | To fetch RBI, SEBI, MOSPI, and other official pages |
| LLM (Ollama or API) | Used for claim drafting, verification, and dialogue generation |
| `mcp` + `pydantic` packages | Only needed for the optional MCP server |
| `pytest` | Only needed to run tests |

#### Recommended Models & Model Tiers

The pipeline relies heavily on strict JSON adherence, logical entailment checking (determining if a source quotation strictly entails a factual claim), and natural dialogue writing. Here is the tier breakdown:

| Tier / Size | Recommended Models | Best For / Verdict |
|---|---|---|
| **3B Class** *(Lightweight Local)* | `qwen2.5-coder:3b`, `llama3.2:3b` | **Minimum viable local setup.** Runs quickly on low-spec machines and CPU-only setups. Adequate for drafting, but has higher variance on strict JSON formats and logical entailment checks. |
| **7B – 8B Class** *(Sweet Spot Local)* | **`qwen2.5:7b`** (Recommended), `llama3.1:8b`, `qwen2.5-coder:7b` | **Best balance for local use.** Vastly superior JSON formatting reliability, stronger reasoning on claim entailment, and far more natural, engaging conversational dialogue between Riya and Arjun. Needs ~8–12 GB RAM / VRAM. |
| **14B – 32B Class** *(Advanced Local)* | `qwen2.5:14b`, `qwen2.5:32b`, `deepseek-r1:14b` | **Near-cloud quality locally.** Zero hallucinated numbers, highly nuanced financial explanation, robust handling of complex regulatory texts. Needs 16–32 GB RAM or dedicated GPU (12GB+ VRAM). |
| **Cloud / API Models** *(Production SOTA)* | Claude 3.5 / 3.7 Sonnet, GPT-4o / GPT-4o-mini, Gemini 1.5 Pro / Flash | **Best overall quality.** Flawless instruction following, zero JSON drops, and best pedagogical depth for financial concepts. Easily bridged via Ollama OpenAI-compatible proxy or LiteLLM. |

> **Recommendation:**
> - For everyday local development: Use **`qwen2.5:7b`** (`ollama pull qwen2.5:7b`).
> - For fast low-resource testing: Use **`qwen2.5-coder:3b`** (the default).
> - For production quality: Use a **14B+ local model** or a frontier cloud model (Claude 3.5 Sonnet / GPT-4o).

#### Models for Downstream Rendering (Carousel & Video)

When handing off `dialogue_carousel.json` and `dialogue_video.json` to second-stage models:
- **Visuals / Slides:** Midjourney, Flux, Ideogram, or HTML/Canvas generators via GPT-4o / Claude 3.5 Sonnet.
- **Voiceover:** Dual-speaker TTS like ElevenLabs (assigning distinct voice profiles for *Riya* and *Arjun*).
- **Video Generation:** Runway Gen-3, Luma Dream Machine, Kling AI, or HeyGen/Synthesia avatar renderers.

### 2. Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell

# Install test runner (optional)
pip install pytest

# Pull the Ollama model
ollama pull qwen2.5-coder:3b
```

### 3. Run the agent

```bash
# Pick a random topic from topics.json → research → generate dialogue script → save to DB
python generate_dialogue.py

# Autonomously brainstorm a fresh topic using AI (bypasses topics.json)
python generate_dialogue.py --ai-topic

# Use a specific topic
python generate_dialogue.py --topic "How does inflation affect household budgets in India?"

# Highest-priority topic instead of random
python generate_dialogue.py --no-random

# DB only, skip writing files to disk
python generate_dialogue.py --no-files

# List everything stored in the DB
python generate_dialogue.py --list

# Print the full carousel JSON for record id=3
python generate_dialogue.py --show 3
```

### 4. Run tests

```bash
python -m pytest          # all 128 tests
python -m pytest -v       # verbose
```

---

## File and folder map

```
finance-content-agent/
├── generate_dialogue.py          ← THE main command (run this)
├── generate_content.py           ← legacy draft-only command (no DB)
│
├── config/
│   └── topics.json               ← topic pool — edit to add topics
│
├── data/
│   └── scripts.db                ← SQLite database (auto-created)
│
├── output/
│   └── drafts/
│       └── <timestamp>_<topic>/  ← one folder per run
│           ├── research_report.json
│           ├── carousel.json / .md
│           ├── video_script.json / .md
│           ├── dialogue_carousel.json  ← NEW: hand to carousel LLM
│           ├── dialogue_carousel.md
│           ├── dialogue_video.json     ← NEW: hand to video LLM
│           └── dialogue_video.md
│
├── src/
│   ├── db.py                     ← SQLite layer (ScriptDatabase)
│   ├── dialogue_script.py        ← data models (DialogueScript, slides, scenes)
│   ├── dialogue_script_generator.py ← Riya+Arjun teaching script builder
│   ├── draft_content_workflow.py ← orchestrates research → carousel → dialogue
│   ├── research_content_generator.py ← legacy carousel generator (Ollama)
│   ├── content_validator.py      ← post-generation safety checks
│   ├── content_post.py           ← InstagramPost dataclass
│   ├── content_agent.py          ← ContentAgent (wires research + publish)
│   ├── instagram_publisher.py    ← Instagram Graph API publisher (stub)
│   ├── mock_instagram_publisher.py
│   │
│   ├── research/
│   │   ├── topic.py              ← Topic dataclass
│   │   ├── topic_selector.py     ← picks highest-priority or random topic
│   │   ├── topic_generator.py    ← AI topic ideator (bypasses topics.json)
│   │   ├── research_request.py   ← ResearchRequest dataclass
│   │   ├── research_report.py    ← ResearchReport dataclass
│   │   ├── source_discovery.py   ← maps topics → curated source URLs
│   │   ├── source_rules.py       ← domain authority classification
│   │   ├── source_authority.py   ← SourceAuthority dataclass
│   │   ├── local_research_agent.py ← fetch → extract → draft → verify
│   │   ├── claim.py              ← Claim + Evidence dataclasses
│   │   ├── claim_verifier.py     ← verify_claim() logic
│   │   ├── claim_resolution.py
│   │   ├── conflict_resolution.py
│   │   ├── evidence.py           ← EvidenceRecord dataclass
│   │   ├── evidence_adapter.py
│   │   ├── evidence_resolution.py
│   │   ├── research_pipeline.py  ← build_research_report()
│   │   ├── research_service.py   ← research_claim()
│   │   ├── research_agent.py     ← abstract base class
│   │   ├── simple_research_agent.py
│   │   ├── openclaw_research_agent.py
│   │   └── source_ingestion.py
│   │
│   └── mcp/
│       └── server.py             ← optional MCP claim-verification server
│
├── skills/
│   ├── finance-research/
│   │   └── SKILL.md              ← research rules & primary source verification
│   └── dialogue-script-generation/
│       └── SKILL.md              ← Riya & Arjun 6-stage teaching dialogue rules
│
└── tests/
    ├── test_claim_verifier.py             ← claim vs evidence verification logic
    ├── test_content_validator.py          ← safety checks & numbers verification
    ├── test_db.py                         ← 22 SQLite database tests
    ├── test_dialogue_script_generator.py  ← 29 dialogue generation & error handling tests
    ├── test_draft_content_workflow.py     ← 13 workflow & draft generation tests
    ├── test_generate_dialogue_cli.py      ← 12 CLI options & routing tests
    ├── test_local_research_agent.py       ← source parsing & claim drafting tests
    ├── test_research_content_generator.py ← Ollama carousel generator tests
    ├── test_research_pipeline.py          ← report assembly tests
    ├── test_topic_generator.py            ← 5 AI topic generator tests
    └── test_topic_selector.py             ← 5 topic priority & random selection tests
```

---

## The two output formats explained

### `dialogue_carousel.json` — hand to a carousel-rendering LLM

Contains `carousel_slides` — one entry per arc stage:

```
Slide 1  HOOK          Arjun asks the beginner question
Slide 2  SCENARIO      Riya describes a real-life situation
Slide 3  EXPLANATION   Riya explains the concept in plain language
Slide 4  EXAMPLE       Riya works through it with verified numbers
Slide 5  CONSEQUENCES  Riya explains trade-offs and why it matters
Slide 6  TAKEAWAY      Riya gives one concrete action step
Slide 7  CTA           Follow / save prompt
```

Each slide has: `title`, `guide_line`, `learner_line`, `on_screen_text`,
`visual_prompt` (image generation description), `key_fact`, `footnote`.

**Instruction to give the rendering LLM:**
> *"Render each slide as an Instagram carousel image. Keep the Riya / Arjun
> conversation. Use only the facts listed in `verified_facts`. Do not add
> numbers or claims that are not there."*

### `dialogue_video.json` — hand to a video-generation LLM

Contains `video_scenes` with the same arc stages plus:
- `duration_seconds` per scene
- `visual_direction` (cinematography / animation direction)
- `guide_voiceover` / `learner_voiceover` (spoken lines)
- `visual_prompt` (B-roll / illustration prompt)
- `aspect_ratio: "9:16"`

**Instruction to give the rendering LLM:**
> *"Render each scene as a short vertical video segment. Alternate voice
> between Riya and Arjun. Use only the facts in `verified_facts`."*

---

## What you need to remember and maintain

### ⚠️ Things to update regularly

#### 1. Source URLs — `src/research/source_discovery.py`

This is the most important file to keep current. It maps topic categories to
specific official page URLs. These pages **go stale**:

| Category | Key source to watch |
|---|---|
| `repo_rate` | RBI MPC press release — update URL after every policy decision |
| `home_loan` | RBI Master Circulars — update when superseded |
| `inflation` | MOSPI CPI page — stable but verify annually |
| `compounding` | SEBI Investor portal — stable |
| `credit_score` | CIBIL loan-approval page |
| `tax` | CBIC GST page + Income Tax portal |

**When RBI announces a new repo rate decision:**
1. Find the new press release URL on `rbi.org.in`.
2. Update the `repo_rate` entry in `SOURCES` in `source_discovery.py`.
3. Update the `published_at` date string.

#### 2. Topic pool — `config/topics.json`

Add new topics here. Each topic needs:

```json
{
  "title": "Exact topic title (used as key)",
  "reason": "What to research and why — becomes part of the research question",
  "content_type": "carousel",
  "priority": "high | medium | low"
}
```

> **Important:** The research system only knows how to fetch sources for
> categories mapped in `source_discovery.py`. If you add a topic that doesn't
> match any category keyword (`repo rate`, `inflation`, `compound`,
> `credit score`, `tax`, `home loan`, `emi`, `floating rate`,
> `fixed versus floating`), research will return zero sources and the run
> will fail. Add a new source entry to `source_discovery.py` first.

#### 3. Ollama model — environment variable

```bash
export OLLAMA_BASE_URL=http://127.0.0.1:11434   # default
export OLLAMA_MODEL=qwen2.5-coder:3b             # default
```

The model is called three times per run:
1. To draft plain-language claims from verbatim quotes.
2. To verify each claim against its quote.
3. To write the Riya + Arjun dialogue wrapper.

If you switch models, re-run the full test suite to check that JSON output
formats are still parseable.

#### 4. Database — `data/scripts.db`

SQLite. Created automatically on first run. Backed up by copying the file.

```bash
# List all stored scripts
python generate_dialogue.py --list

# View full JSON for a specific record
python generate_dialogue.py --show <id>
```

Schema:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `topic` | TEXT | Topic title |
| `generated_at` | TEXT | ISO-8601 UTC timestamp |
| `status` | TEXT | `ready` / `published` / `failed` |
| `carousel_json` | TEXT | Full `DialogueScript` JSON |
| `video_json` | TEXT | Same `DialogueScript` JSON |
| `verified_facts` | TEXT | JSON array of verified fact strings |
| `sources` | TEXT | JSON array of source URLs |
| `output_dir` | TEXT | Path to the output folder on disk |
| `error` | TEXT | Error message when `status=failed` |

---

## The teaching characters

| Character | Role | Description |
|---|---|---|
| **👩 Riya** | GUIDE | Friendly 28-year-old finance professional who explains money concepts simply. Always explains *why* before *what*. Never gives personalised advice. |
| **🧑 Arjun** | LEARNER | Curious 16-year-old beginner who asks honest, relatable questions. Speaks only at the HOOK stage. |

The characters are defined in `src/dialogue_script.py` as default field
values on `DialogueScript`. Change them there if you want different names or
descriptions.

---

## Verified facts — the safety guarantee

**`verified_facts` is never rewritten by the dialogue generator.** It is
copied directly from the research pipeline output and stored unchanged in
the database.

The dialogue generator (Ollama call #3) writes only the conversational
wrapper text. If it introduces numbers that do not appear in any verified
fact, a warning is printed and logged. The verified facts in the JSON output
always reflect what the research pipeline found and verified from official
sources.

The content validator (`content_validator.py`) additionally checks:
- No forbidden claims ("guaranteed returns", "risk-free", "100% safe").
- No personalised advice ("you should buy", "invest in this").
- All numbers in the carousel are present in the research report.
- All claims are supported by the verified facts.
- All source URLs are from the research report.

---

## Adding a new topic category — step by step

1. **Add the source URL** in `src/research/source_discovery.py`:

   ```python
   "mutual_funds": [
       (
           "SEBI",
           "https://www.sebi.gov.in/sebi_data/commondocs/mf_p.html",
           "SEBI: Mutual Funds Overview",
       ),
       (
           "AMFI",
           "https://www.amfiindia.com/investor-corner/knowledge-center",
           "AMFI Investor Knowledge Center",
       ),
   ],
   ```

2. **Add the keyword detection** in `ResearchSourceDiscovery.discover()`:

   ```python
   elif "mutual fund" in normalized or "sip" in normalized:
       category = "mutual_funds"
   ```

3. **Add authority domain** in `src/research/source_rules.py` if the new
   source domain is not already listed:

   ```python
   HIGH_AUTHORITY_DOMAINS = {
       ...,
       "amfiindia.com",
   }
   ```

4. **Add the topic** to `config/topics.json`.

5. **Run the tests** to confirm nothing broke:

   ```bash
   python -m pytest
   ```

---

## Known limitations

- **Small topic set.** Research only works for categories with curated source
  mappings. General-purpose web search is not supported.
- **Source pages can go offline or change.** If a source page returns an
  error or less than 400 bytes of text, it is skipped. A topic can fail if
  all its sources are unavailable.
- **Ollama is required.** Three calls are made per run. If Ollama is down
  or the model is not pulled, the run will fail. The pipeline prints a clear
  error in that case.
- **Verification is probabilistic for prose claims.** The local model
  checks whether a verbatim quote entails the drafted claim, but this is not
  a guarantee of semantic correctness. Numbers are checked deterministically
  (they must appear in the quote).
- **Rate/date data goes stale.** The repo rate URL must be updated manually
  after each RBI MPC decision.
- **No Instagram publishing yet.** `instagram_publisher.py` contains the
  Graph API stub but is not wired to the dialogue workflow. The current
  pipeline stops at DB storage. Publishing would require Instagram Business
  account credentials and Graph API access tokens.

---

## Optional: MCP claim-verification server

An MCP server exposing `verify_claim` and `verify_claims` tools is available
for use with AI coding assistants that support the Model Context Protocol:

```bash
pip install mcp pydantic
python src/mcp/server.py
```

This is separate from `generate_dialogue.py` and is not required for normal
operation.
