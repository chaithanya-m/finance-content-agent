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
        "script", "style", "noscript", "svg", "nav", "header",
        "footer", "aside",
    }
    RECOVERY_TAGS = {"body", "main", "article"}
    BLOCK_TAGS = {
        "p", "br", "div", "li", "h1", "h2", "h3",
        "table", "tr", "section",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored_tags = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.RECOVERY_TAGS and self.ignored_tags:
            self.ignored_tags.clear()

        if tag in self.IGNORED:
            self.ignored_tags.append(tag)
        elif not self.ignored_tags and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.IGNORED:
            for index in range(len(self.ignored_tags) - 1, -1, -1):
                if self.ignored_tags[index] == tag:
                    del self.ignored_tags[index:]
                    break
        elif not self.ignored_tags and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored_tags:
            self.parts.append(data)


def _normalize(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "that", "this",
    "does", "how", "what", "when", "where", "why", "about", "using",
    "india", "indian", "affect", "affects", "explain",
}


def _topic_terms(topic: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-z]+", topic.casefold())
        if len(term) > 2 and term not in _STOPWORDS
    }


def _source_statements(content: str) -> list[str]:
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in content.splitlines()
        if line.strip()
    ]
    statements = []
    for start in range(len(lines)):
        for end in range(start + 1, min(start + 5, len(lines)) + 1):
            statement = " ".join(lines[start:end])
            if len(statement) > 500:
                break
            if len(statement) >= 15:
                for part in re.split(
                    r"(?<=[.!?])\s+(?=[A-Z0-9])",
                    statement,
                ):
                    part = part.strip()
                    if re.search(r"\b[A-Za-z]+\s+\d+\[", part):
                        continue
                    has_number = bool(re.search(r"\d", part))
                    is_complete_sentence = (
                        len(part) >= 40 and part.endswith((".", "?", "!"))
                    )
                    if (
                        20 <= len(part) <= 500
                        and (has_number or is_complete_sentence)
                    ):
                        statements.append(part)
    return list(dict.fromkeys(statements))


def _relevant_statements(content: str, topic: str) -> list[str]:
    terms = _topic_terms(topic)
    if not terms:
        return []

    ranked = []
    for statement in _source_statements(content):
        words = re.findall(r"[a-z]+", statement.casefold())
        statement_terms = set(words)
        matched = terms & statement_terms
        required_matches = 1 if len(terms) == 1 else 2
        if len(matched) >= required_matches:
            first_number = re.search(r"\d", statement)
            if first_number:
                matched_positions = [
                    index
                    for index, word in enumerate(words)
                    if word in matched
                ]
                number_position = len(
                    re.findall(r"[a-z]+", statement[:first_number.start()].casefold())
                )
                if not matched_positions or max(matched_positions) >= number_position:
                    continue
            ranked.append((len(matched), len(statement), statement))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return list(dict.fromkeys(statement for _, _, statement in ranked))


class LocalResearchAgent(ResearchAgent):
    def __init__(self):
        self.discovery = ResearchSourceDiscovery()

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
        text = "\n".join(
            re.sub(r"[ \t]+", " ", line).strip()
            for line in "".join(parser.parts).splitlines()
            if line.strip()
        )

        if len(text) < 400:
            return None

        candidate.source_url = final_url
        return text[:12000]

    def research(self, request: ResearchRequest) -> ResearchReport:
        report = ResearchReport(
            topic=request.topic,
            research_question=request.research_question,
        )

        candidates = self.discovery.discover(request)
        if not candidates:
            report.unverified_claims.append({
                "fact": "No curated sources are configured for this topic.",
                "status": "unverified",
                "evidence": [],
                "notes": "Add an authoritative source mapping before generating drafts.",
            })
            return report

        pages = []

        for candidate in candidates:
            content = self._fetch_page(candidate)
            if content:
                pages.append({
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
                "notes": "All configured sources were unavailable or returned unusable content.",
            })
            return report

        evidence_by_claim = {}
        for page in pages:
            candidate = page["candidate"]
            statements = _relevant_statements(
                page["content"],
                request.topic,
            )
            source = create_source_document(
                source_name=candidate.source_name,
                source_url=candidate.source_url,
                title=candidate.title,
                content=page["content"],
                source_type=candidate.source_type,
                published_at=candidate.published_at,
            )
            for statement in statements[:3]:
                record = create_evidence_record(
                    claim=statement,
                    source=source,
                    supporting_text=statement,
                )
                evidence_by_claim.setdefault(statement, []).append(record)

        claims = list(evidence_by_claim)
        report = build_research_report(
            topic=request.topic,
            research_question=request.research_question,
            claims=claims,
            evidence_by_claim=evidence_by_claim,
        )
        if not claims:
            report.unverified_claims.append({
                "fact": "No source statements directly matched the topic.",
                "status": "unverified",
                "evidence": [],
                "notes": "The retrieved pages did not contain suitable verbatim claims.",
            })

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

        numbers = {
            number
            for fact in report.verified_facts
            for number in re.findall(
                r"(?<!\w)\d[\d,]*(?:\.\d+)?%?",
                fact["fact"],
            )
        }
        report.important_numbers = [
            {"number": number} for number in sorted(numbers)
        ]
        return report
