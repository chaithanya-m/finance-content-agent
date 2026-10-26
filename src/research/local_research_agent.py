import json
import os
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser

from .research_agent import ResearchAgent
from .research_report import ResearchReport
from .research_pipeline import build_research_report
from .research_request import ResearchRequest
from .source_discovery import ResearchSourceDiscovery
from .source_ingestion import create_evidence_record, create_source_document


class _PageTextParser(HTMLParser):
    IGNORED = {
        "script", "style", "noscript", "nav", "header", "footer",
        "aside", "form", "svg",
    }

    def __init__(self):
        super().__init__()
        self.ignored_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORED:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in {"p", "br", "div", "li", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self.IGNORED and self.ignored_depth:
            self.ignored_depth -= 1
        elif not self.ignored_depth and tag in {"p", "div", "li", "h1", "h2", "h3"}:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.ignored_depth:
            self.parts.append(data)


def _normalize(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


class LocalResearchAgent(ResearchAgent):
    def __init__(self):
        self.discovery = ResearchSourceDiscovery()
        self.ollama_url = os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        ).rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")

    def _fetch_page(self, candidate):
        request = urllib.request.Request(
            candidate.source_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; FinanceResearchBot/1.0)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                content_type = response.headers.get_content_type()
                if content_type not in {"text/html", "application/xhtml+xml"}:
                    return None
                raw = response.read(1_500_000).decode("utf-8", errors="replace")
                final_url = response.geturl()
        except (urllib.error.URLError, TimeoutError, ValueError):
            return None

        parser = _PageTextParser()
        parser.feed(raw)
        text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()

        if len(text) < 400:
            return None

        candidate.source_url = final_url
        return text[:6000]

    def research(self, request: ResearchRequest) -> ResearchReport:
        report = ResearchReport(
            topic=request.topic,
            research_question=request.research_question,
        )

        candidates = self.discovery.discover(request)
        pages = []

        for candidate in candidates:
            content = self._fetch_page(candidate)
            if content:
                pages.append({
                    "source_id": f"S{len(pages) + 1}",
                    "candidate": candidate,
                    "content": content,
                })
            if len(pages) >= 4:
                break

        if not pages:
            report.unverified_claims.append({
                "fact": "No usable source pages were retrieved.",
                "status": "unverified",
                "evidence": [],
                "notes": "Check search connectivity and source accessibility.",
            })
            return report

        source_material = [
            {
                "source_id": page["source_id"],
                "url": page["candidate"].source_url,
                "title": page["candidate"].title,
                "text": page["content"],
            }
            for page in pages
        ]

        prompt = f"""
Extract candidate finance facts from the source material below.

Question: {request.research_question}
Topic: {request.topic}

Rules:
- Use only the supplied source text.
- Each claim must be directly supported by its named source.
- Prefer claims stated explicitly in the source; do not infer advice or causation.
- evidence_text must be a verbatim, contiguous quotation copied from that source.
- Keep each quotation long enough to preserve the meaning, usually one full sentence.
- Use the source_id, not an invented URL.
- Do not invent figures, dates, rates, source text, or publication dates.
- Return {"claims": [{"claim": "...", "source_id": "S1", "evidence_text": "verbatim quote"}]}.
- If the sources do not support a useful claim, return an empty claims array.

SOURCE MATERIAL:
{json.dumps(source_material, ensure_ascii=False)}
"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_ctx": 16384},
        }
        http_request = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(http_request, timeout=240) as response:
                model_response = json.loads(response.read().decode("utf-8"))
            extraction = json.loads(model_response.get("response", "{}"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Local claim extraction failed: {exc}") from exc

        pages_by_id = {page["source_id"]: page for page in pages}
        evidence_by_claim = {}
        source_urls = set()

        for item in extraction.get("claims", []):
            if not isinstance(item, dict):
                continue
            claim_text = item.get("claim")
            source_id = item.get("source_id")
            quote = item.get("evidence_text")

            if not all(isinstance(value, str) for value in (claim_text, source_id, quote)):
                continue
            page = pages_by_id.get(source_id)
            if not page or len(claim_text.strip()) < 15 or len(quote.strip()) < 35:
                continue

            # The alleged quotation must actually appear in the fetched page.
            if _normalize(quote) not in _normalize(page["content"]):
                continue

            candidate = page["candidate"]
            source = create_source_document(
                source_name=candidate.source_name,
                source_url=candidate.source_url,
                title=candidate.title,
                content=page["content"],
                source_type=candidate.source_type,
                published_at=candidate.published_at,
            )
            record = create_evidence_record(
                claim=claim_text.strip(),
                source=source,
                supporting_text=quote.strip(),
            )
            evidence_by_claim.setdefault(claim_text.strip(), []).append(record)
            source_urls.add(candidate.source_url)

        claims = list(evidence_by_claim)
        report = build_research_report(
            topic=request.topic,
            research_question=request.research_question,
            claims=claims,
            evidence_by_claim=evidence_by_claim,
        )

        # Keep every successfully fetched source for audit and review.
        existing = {source.get("source_url") for source in report.sources}
        for page in pages:
            candidate = page["candidate"]
            if candidate.source_url not in existing:
                report.sources.append({
                    "source_name": candidate.source_name,
                    "source_url": candidate.source_url,
                    "published_at": candidate.published_at,
                })
                existing.add(candidate.source_url)

        report.important_numbers = sorted({
            number
            for fact in report.verified_facts
            for number in re.findall(
                r"(?<!\\w)\\d[\\d,]*(?:\\.\\d+)?%?",
                fact["fact"],
            )
        })
        return report
