# Finance Content Agent

A command-line tool for researching selected personal-finance topics for an
Indian audience and creating source-backed Instagram carousel and short-video
drafts. It does not publish content.

The intended workflow is:

1. Select a topic from `config/topics.json`, or provide a topic yourself.
2. Fetch relevant pages from the project's curated source list.
3. Extract claims supported by those pages and check the evidence.
4. Ask a local Ollama language model to draft an Instagram carousel.
5. Validate the draft and save it with its research report and a video script.

## Requirements

- Python 3.10 or newer.
- Internet access to retrieve the configured source pages.
- [Ollama](https://ollama.com/) running locally, with the default model available.
- `pytest` to run the test suite (optional).

The standard draft-generation workflow uses Python's standard library; there is
currently no dependency manifest in the repository. The optional MCP server
requires the `mcp` and `pydantic` Python packages.

## Setup

From the project directory, create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

Install Ollama, start it, and download the default model:

```bash
ollama pull qwen2.5-coder:3b
```

The application expects Ollama at `http://127.0.0.1:11434` by default. If your
Ollama server or model differs, set these environment variables before running:

```bash
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=qwen2.5-coder:3b
```

In Windows PowerShell, use `$env:OLLAMA_BASE_URL` and `$env:OLLAMA_MODEL`
instead of `export`.

## Generate drafts

Generate a draft for the next configured topic:

```bash
python generate_content.py
```

Choose a configured topic by its exact title:

```bash
python generate_content.py --topic "What is the RBI repo rate and how does it affect borrowers?"
```

You can also provide a new topic title. The research system only has curated
source mappings for selected finance categories, so an arbitrary title may
not have suitable configured sources.

Change the topic configuration or output directory:

```bash
python generate_content.py \
  --topics-file config/topics.json \
  --output-dir output/drafts
```

Each successful run creates a timestamped folder under `output/drafts/` with:

- `research_report.json` — claims, evidence, verification status, and sources.
- `carousel.json` and `carousel.md` — the Instagram carousel draft.
- `video_script.json` and `video_script.md` — a simple vertical-video script
  based on the carousel.

The workflow also keeps `output/drafts/.topic_history.json` so it can skip
configured topics that have already been generated. It selects the highest
priority available topic; it does not use post-performance data.

## Topics

`config/topics.json` is a JSON list. Each topic needs a `title` and `reason`;
`content_type` and `priority` are optional:

```json
[
  {
    "title": "How does inflation affect household budgets in India?",
    "reason": "Explain inflation using reliable Indian sources.",
    "content_type": "carousel",
    "priority": "high"
  }
]
```

## Tests

Install pytest if it is not already available, then run:

```bash
python -m pytest
```

## Important limitations

- This is a draft-generation tool, not an autonomous publishing system. The
  command above saves files and does not post to Instagram.
- Research depends on a small, curated list of source URLs and supported topic
  categories; it is not a general-purpose web search engine.
- A topic can fail to produce a draft if source pages cannot be fetched, no
  claims can be verified, Ollama is unavailable, or the generated draft fails
  validation.
- Verification and validation reduce the chance of unsupported content but do
  not guarantee that every financial statement is correct. Review the evidence
  and draft before sharing. This project does not provide personalized
  financial advice.

An optional MCP server exposing claim-verification tools is available at
`src/mcp/server.py`. It is separate from the standard draft-generation command.
