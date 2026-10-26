import json
import os
import urllib.error
import urllib.request

from .content_post import InstagramPost
from .content_validator import ContentValidator
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

        facts = [fact["fact"] for fact in verified_facts]
        source_urls = [
            source["source_url"]
            for source in report.sources
            if isinstance(source, dict)
            and isinstance(source.get("source_url"), str)
        ]
        prompt = f"""
Create an Instagram carousel for an Indian finance topic.
Return only one JSON object with exactly these fields:
{{
  "topic": {json.dumps(report.topic, ensure_ascii=False)},
  "hook": {json.dumps(ContentValidator.hook_for_topic(report.topic), ensure_ascii=False)},
  "slides": ["exact verified fact copied verbatim"],
  "caption": {json.dumps(ContentValidator.SAFE_CAPTION)},
  "call_to_action": {json.dumps(ContentValidator.SAFE_CALL_TO_ACTION)},
  "sources": {json.dumps(source_urls, ensure_ascii=False)},
  "claims": ["same exact verified facts used as slide text"]
}}

Verified facts, the only statements allowed on slides:
{json.dumps(facts, ensure_ascii=False)}

Rules:
- Copy each slide exactly from one verified fact. Do not paraphrase, shorten,
  explain, add headings, or add any other slide text.
- The claims array must contain the exact same statements in the same order
  as the slides.
- Do not add facts, numbers, dates, predictions, advice, or financial claims.
- Keep the caption and call_to_action exactly as supplied in the JSON template.
- Use only the listed source URLs.
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
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama returned invalid API JSON.") from exc

        if not isinstance(result, dict):
            raise ValueError("Ollama returned an invalid API response.")

        response_text = result.get("response")
        if not isinstance(response_text, str):
            raise ValueError("Ollama response is missing generated text.")

        text = response_text.strip()
        if not text:
            raise ValueError("Ollama returned an empty content response.")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Ollama returned invalid JSON: {text[:300]}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError("Generated content must be a JSON object.")

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

        for field in ("topic", "hook", "caption", "call_to_action"):
            if not isinstance(data[field], str) or not data[field].strip():
                raise ValueError(
                    f"Generated content field '{field}' must be a non-empty string."
                )

        for field in ("slides", "sources", "claims"):
            if not isinstance(data[field], list) or not all(
                isinstance(item, str) and item.strip()
                for item in data[field]
            ):
                raise ValueError(
                    f"Generated content field '{field}' must be a list of non-empty strings."
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
