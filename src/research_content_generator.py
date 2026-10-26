import json
import os
import urllib.error
import urllib.request

from .content_post import InstagramPost
from .research.research_report import ResearchReport


class ResearchContentGenerator:
    def __init__(self) -> None:
        self.base_url = os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        ).rstrip("/")
        self.model = os.getenv(
            "OLLAMA_MODEL", "qwen2.5-coder:3b"
        )

    def generate(self, report: ResearchReport) -> InstagramPost:
        verified_facts = [
            fact
            for fact in report.verified_facts
            if isinstance(fact, dict)
            and fact.get("status") == "verified"
            and isinstance(fact.get("fact"), str)
        ]

        if not verified_facts:
            raise ValueError(
                "Cannot generate content without verified facts."
            )

        prompt = f"""
Create an educational Instagram carousel about an Indian finance topic.

TOPIC:
{report.topic}

RESEARCH QUESTION:
{report.research_question}

VERIFIED FACTS:
{json.dumps(verified_facts, ensure_ascii=False, indent=2)}

IMPORTANT NUMBERS:
{json.dumps(report.important_numbers, ensure_ascii=False, indent=2)}

ANALYSIS:
{json.dumps(report.analysis, ensure_ascii=False, indent=2)}

SOURCES:
{json.dumps(report.sources, ensure_ascii=False, indent=2)}

Rules:
1. Use only the verified facts supplied above.
2. Never invent financial claims, statistics, dates or rates.
3. Do not give personalized financial advice or guarantee outcomes.
4. Write clearly for young professionals in India.
5. Keep carousel slides concise and useful.
6. Do not mention unverified or conflicting claims.
7. Use only the supplied source URLs.
8. Every factual statement must be included in the claims array.
9. The claims array must contain only exact statements from VERIFIED FACTS.
10. Do not introduce new factual claims through the caption or call to action.
11. Preserve financial numbers exactly as supported by the verified facts.

Return a JSON object with exactly these fields:
{{
  "topic": "string",
  "hook": "string",
  "slides": ["slide 1", "slide 2", "slide 3"],
  "caption": "string",
  "call_to_action": "string",
  "sources": ["https://..."],
  "claims": ["exact verified statement"]
}}
"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
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
                "Ollama content generation timed out after 240 seconds."
            ) from exc

        text = result.get("response", "").strip()
        if not text:
            raise ValueError("Ollama returned an empty content response.")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Ollama returned invalid JSON: {text[:300]}"
            ) from exc

        required_fields = {
            "topic",
            "hook",
            "slides",
            "caption",
            "call_to_action",
            "sources",
            "claims",
        }
        missing_fields = required_fields - data.keys()
        if missing_fields:
            raise ValueError(
                f"Generated content is missing fields: "
                f"{sorted(missing_fields)}"
            )

        for field in ("slides", "sources", "claims"):
            if not isinstance(data[field], list):
                raise ValueError(
                    f"Generated content field '{field}' must be a list."
                )

        return InstagramPost(
            topic=data["topic"],
            hook=data["hook"],
            slides=data["slides"],
            caption=data["caption"],
            call_to_action=data["call_to_action"],
            sources=data["sources"],
            claims=data["claims"],
        )
