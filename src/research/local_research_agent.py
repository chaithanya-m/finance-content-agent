import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser

from .claim import Claim
from .evidence import EvidenceRecord
from .research_agent import ResearchAgent
from .research_report import ResearchReport
from .research_pipeline import build_research_report
from .research_request import ResearchRequest
from .source_rules import classify_source
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

_DATE_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y")


def _topic_terms(topic: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-z]+", topic.casefold())
        if len(term) > 2 and term not in _STOPWORDS
    }


def _parse_date(value: str) -> str | None:
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), date_format).date().isoformat()
        except ValueError:
            continue
    return None


def _source_dates(content: str) -> tuple[str | None, str | None]:
    as_of_match = re.search(
        r"\b(?:as at|as of)\b.{0,35}?\b("
        r"January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},\s+\d{4}",
        content,
        re.IGNORECASE,
    )
    if as_of_match:
        date_text = re.search(
            r"(?:January|February|March|April|May|June|July|August|September|"
            r"October|November|December)\s+\d{1,2},\s+\d{4}",
            as_of_match.group(0),
            re.IGNORECASE,
        )
        as_of_date = _parse_date(date_text.group(0)) if date_text else None
        if as_of_date:
            return None, as_of_date

    updated_match = re.search(
        r"\bupdated as (?:on|of)\s+("
        r"January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},\s+\d{4}",
        content,
        re.IGNORECASE,
    )
    if updated_match:
        date_text = re.search(
            r"(?:January|February|March|April|May|June|July|August|September|"
            r"October|November|December)\s+\d{1,2},\s+\d{4}",
            updated_match.group(0),
            re.IGNORECASE,
        )
        return (_parse_date(date_text.group(0)) if date_text else None), None

    coverage_match = re.search(
        r"\b(?:updated to reflect.*?\b(?:up to|upto)|instructions issued "
        r"(?:up to|upto))\s+("
        r"January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},\s+\d{4}",
        content,
        re.IGNORECASE,
    )
    if coverage_match:
        date_text = re.search(
            r"(?:January|February|March|April|May|June|July|August|September|"
            r"October|November|December)\s+\d{1,2},\s+\d{4}",
            coverage_match.group(0),
            re.IGNORECASE,
        )
        return None, (_parse_date(date_text.group(0)) if date_text else None)
    return None, None


def _source_statements(content: str) -> list[str]:
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in content.splitlines()
        if line.strip()
    ]
    statements = []
    for line in lines:
        for sentence in re.split(
            r"(?<=[.!?])\s+(?=[A-Z0-9])",
            line,
        ):
            sentence = sentence.strip()
            if (
                20 <= len(sentence) <= 500
                and sentence.endswith((".", "?", "!"))
                and not re.match(r"^\d+(?:\.\d+)+\s", sentence)
            ):
                statements.append(sentence)

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
                    if re.match(r"^\d+(?:\.\d+)+\s", part):
                        continue
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


def _relevant_statements(
    content: str,
    topic: str,
    category: str | None = None,
) -> list[str]:
    statements = _source_statements(content)
    if category == "repo_rate":
        return [
            statement
            for statement in statements
            if re.search(
                r"\b(?:policy\s+repo\s+rate|repo\s+rate|monetary\s+policy\s+committee)\b",
                statement,
                re.IGNORECASE,
            )
            and not re.search(
                r"\b(?:EMI|equated monthly instalments?|personal loan reset)\b",
                statement,
                re.IGNORECASE,
            )
        ]

    if category == "home_loan":
        requires_emi = bool(
            re.search(r"\b(?:EMI|instalments?)\b", topic, re.IGNORECASE)
        )
        return [
            statement
            for statement in statements
            if statement.endswith((".", "?", "!"))
            and re.search(
                r"\b(?:housing loans?|home loans?)\b",
                statement,
                re.IGNORECASE,
            )
            and (
                not requires_emi
                or re.search(r"\b(?:EMI|instalments?)\b", statement, re.IGNORECASE)
            )
            and re.search(
                r"\b(?:EMI|instalments?|benchmark rate|interest rate|floating rate|reset)\b",
                statement,
                re.IGNORECASE,
            )
        ]

    terms = _topic_terms(topic)
    if not terms:
        return []

    ranked = []
    for statement in statements:
        words = re.findall(r"[a-z]+", statement.casefold())
        statement_terms = set(words)
        matched = terms & statement_terms
        required_matches = 1 if len(terms) == 1 else 2
        if len(matched) >= required_matches:
            ranked.append((len(matched), len(statement), statement))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return list(dict.fromkeys(statement for _, _, statement in ranked))


def _repo_rate_observation(content: str) -> tuple[str, str] | None:
    for statement in _source_statements(content):
        if not re.search(r"\bpolicy\s+repo\s+rate\b", statement, re.IGNORECASE):
            continue
        match = re.search(
            r"\bpolicy\s+repo\s+rate\b.{0,240}?(?:\bto\b|:)\s*"
            r"(\d+(?:\.\d+)?)\s*(%|per\s+cent|percent)?",
            statement,
            re.IGNORECASE,
        )
        if match:
            value = match.group(1)
            return f"Policy Repo Rate is {value}%.", statement
    return None


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
        text = "\n".join(
            re.sub(r"[ \t]+", " ", line).strip()
            for line in "".join(parser.parts).splitlines()
            if line.strip()
        )

        if len(text) < 400:
            return None

        candidate.source_url = final_url
        updated_at, as_of_date = _source_dates(text)
        candidate.published_at = candidate.published_at or updated_at
        candidate.as_of_date = as_of_date
        return text[:80000]

    def _ask_ollama(self, prompt: str, num_predict: int) -> dict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_ctx": 4096,
                "num_predict": num_predict,
            },
        }
        request = urllib.request.Request(
            f"{self.ollama_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                api_result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama returned HTTP {exc.code}: {detail[:300]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.ollama_url}: {exc}"
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError("Ollama research request timed out after 90 seconds.") from exc
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama returned invalid API JSON.") from exc

        if not isinstance(api_result, dict) or not isinstance(
            api_result.get("response"), str
        ):
            raise ValueError("Ollama returned a malformed response.")
        try:
            result = json.loads(api_result["response"])
        except json.JSONDecodeError as exc:
            excerpt = api_result["response"][:300].replace("\n", " ")
            raise ValueError(
                f"Ollama returned malformed JSON content: {excerpt}"
            ) from exc
        if not isinstance(result, dict):
            raise ValueError("Ollama research output must be a JSON object.")
        return result

    @staticmethod
    def _source_document(candidate, content: str):
        return create_source_document(
            source_name=candidate.source_name,
            source_url=candidate.source_url,
            title=candidate.title,
            content=content,
            source_type=candidate.source_type,
            published_at=candidate.published_at,
            as_of_date=candidate.as_of_date,
        )

    @staticmethod
    def _source_summary(candidate) -> dict:
        return {
            "source_name": candidate.source_name,
            "source_url": candidate.source_url,
            "published_at": candidate.published_at,
            "as_of_date": candidate.as_of_date,
        }

    @staticmethod
    def _numbers_are_in_evidence(claim: str, quotes: list[str]) -> bool:
        def numbers(text: str) -> set[str]:
            return {
                format(float(value.replace(",", "")), ".10g")
                for value in re.findall(r"\d[\d,]*(?:\.\d+)?", text)
            }

        claim_numbers = numbers(claim)
        evidence_numbers = set().union(*(numbers(quote) for quote in quotes))
        return claim_numbers.issubset(evidence_numbers)

    @staticmethod
    def _claim_matches_topic(claim: str, category: str | None) -> bool:
        text = claim.casefold()
        required_terms = {
            "repo_rate": ("repo rate", "policy repo"),
            "home_loan": ("loan", "emi", "borrower"),
            "inflation": ("inflation", "price"),
            "compounding": ("compound", "interest"),
            "credit_score": ("credit score", "credit history"),
            "tax": ("tax", "gst"),
        }.get(category, ())
        return not required_terms or any(term in text for term in required_terms)

    @staticmethod
    def _claim_terms_are_grounded(claim: str, quotes: list[str]) -> bool:
        stopwords = {
            "a", "an", "and", "are", "as", "at", "by", "can", "for",
            "from", "in", "including", "is", "it", "of", "on", "or",
            "the", "to",
            "was", "were", "when", "will", "with",
        }
        canonical = {
            "affect": "impact",
            "affects": "impact",
            "affecting": "impact",
            "advised": "obligation",
            "assess": "assess",
            "banks": "lender",
            "borrowers": "borrower",
            "check": "assess",
            "consider": "assess",
            "decrease": "change",
            "decreasing": "change",
            "determine": "decide",
            "explain": "inform",
            "floating": "floating",
            "have": "implement",
            "housing": "housing",
            "increased": "increase",
            "increases": "increase",
            "increasing": "increase",
            "inform": "inform",
            "lenders": "lender",
            "loans": "loan",
            "must": "obligation",
            "put": "implement",
            "place": "implement",
            "rates": "rate",
            "required": "obligation",
            "repayments": "repayment",
            "resetting": "reset",
            "rise": "increase",
            "rising": "increase",
            "shall": "obligation",
            "should": "obligation",
            "take": "assess",
            "account": "assess",
            "tell": "inform",
            "term": "tenor",
            "tenure": "tenor",
            "ucb": "lender",
            "ucbs": "lender",
        }

        def terms(text: str) -> set[str]:
            output = set()
            for term in re.findall(r"[a-z]+", text.casefold()):
                if len(term) <= 2 or term in stopwords:
                    continue
                output.add(canonical.get(term, term))
            return output

        claim_terms = terms(claim)
        evidence_terms = set().union(*(terms(quote) for quote in quotes))
        return bool(claim_terms) and claim_terms.issubset(evidence_terms)

    def _make_claims(self, request: ResearchRequest, quote_items: list[dict]) -> list[dict]:
        if quote_items and quote_items[0]["category"] == "home_loan":
            claims = []
            for quote in quote_items:
                text = quote["text"].casefold()
                claim = None
                if (
                    "emi based floating rate housing loans" in text
                    and "repayment capacity" in text
                    and "increase in emi" in text
                    and "benchmark rate" in text
                ):
                    claim = (
                        "UCBs must check borrowers' repayment capacity for "
                        "floating-rate housing loans, including possible EMI "
                        "increases when benchmark rates rise."
                    )
                elif (
                    "policy framework" in text
                    and "reset of floating interest rates" in text
                    and "emi based housing loans" in text
                ):
                    claim = (
                        "UCBs are advised to have a policy for resetting "
                        "floating rates on EMI-based housing loans."
                    )
                if (
                    claim
                    and self._claim_terms_are_grounded(claim, [quote["text"]])
                ):
                    claims.append(
                        {
                            "id": f"C{len(claims) + 1}",
                            "claim": claim,
                            "evidence_ids": [quote["id"]],
                        }
                    )
            return claims

        prompt = (
            "Write up to 4 short, plain-language finance claims for the topic. "
            "Each claim must be a concise paraphrase directly entailed by its "
            "listed verbatim source quote; do not add implications, advice, "
            "dates, or numbers absent from that quote. Use 1-2 quote IDs per "
            "claim. Claims must be at most 180 characters and must not copy "
            "the entire quote. Return JSON only: "
            '{"claims":[{"claim":"...","evidence_ids":["Q1"]}]}\n'
            f"Topic: {request.topic}\n"
            f"Question: {request.research_question}\n"
            f"Quotes: {json.dumps(quote_items, ensure_ascii=False)}"
        )
        result = self._ask_ollama(prompt, num_predict=450)
        proposals = result.get("claims")
        if not isinstance(proposals, list):
            raise ValueError("Claim drafting output must contain a claims list.")

        known_ids = {item["id"] for item in quote_items}
        quotes_by_id = {item["id"]: item["text"] for item in quote_items}
        accepted = []
        seen = set()
        for proposal in proposals:
            if not isinstance(proposal, dict):
                continue
            claim = proposal.get("claim")
            evidence_ids = proposal.get("evidence_ids")
            if (
                not isinstance(claim, str)
                or not claim.strip()
                or len(claim.strip()) > 180
                or not isinstance(evidence_ids, list)
                or not evidence_ids
                or not all(
                    isinstance(item, str) and item in known_ids
                    for item in evidence_ids
                )
            ):
                continue
            claim = claim.strip()
            if not self._claim_matches_topic(claim, quote_items[0]["category"]):
                continue
            selected_quotes = [quotes_by_id[item] for item in evidence_ids]
            if not self._numbers_are_in_evidence(claim, selected_quotes):
                continue
            if not self._claim_terms_are_grounded(claim, selected_quotes):
                continue
            if _normalize(claim) in {_normalize(quote) for quote in selected_quotes}:
                continue
            if _normalize(claim) in seen:
                continue
            seen.add(_normalize(claim))
            accepted.append(
                {
                    "id": f"C{len(accepted) + 1}",
                    "claim": claim,
                    "evidence_ids": list(dict.fromkeys(evidence_ids)),
                }
            )
        return accepted

    def _verify_claims(self, claims: list[dict], quotes_by_id: dict[str, dict]) -> dict[str, str]:
        valid = {}
        allowed = {"supported", "contradicted", "insufficient"}
        for item in claims:
            prompt_data = {
                "claim": item["claim"],
                "evidence": [
                    quotes_by_id[quote_id]["text"]
                    for quote_id in item["evidence_ids"]
                ],
            }
            prompt = (
                "Independently check whether the complete claim is entailed "
                "by its quoted source evidence. Say supported only if the "
                "quotes explicitly establish its full meaning, qualifiers, "
                "and numbers. Use contradicted only for an explicit opposing "
                "statement; otherwise use insufficient. Do not use outside "
                'knowledge. Return JSON only: {"verdict":"supported",'
                '"reason":"..."}. Claim and quotation:\n'
                f"{json.dumps(prompt_data, ensure_ascii=False)}"
            )
            result = self._ask_ollama(prompt, num_predict=120)
            verdict = result.get("verdict")
            if isinstance(verdict, str) and verdict in allowed:
                valid[item["id"]] = verdict
        return valid

    def _research_repo_rate(self, request, pages) -> ResearchReport:
        observations = []
        report = ResearchReport(
            topic=request.topic,
            research_question=request.research_question,
            sources=[
                self._source_summary(page["candidate"])
                for page in pages
            ],
        )
        for page in pages:
            observation = _repo_rate_observation(page["content"])
            if not observation:
                continue
            fact, quote = observation
            candidate = page["candidate"]
            observations.append(
                {
                    "value": fact,
                    "normalized_value": format(
                        float(re.search(r"\d+(?:\.\d+)?", fact).group(0)),
                        ".10g",
                    ),
                    "quote": quote,
                    "candidate": candidate,
                    "source": self._source_document(candidate, page["content"]),
                }
            )

        if not observations:
            report.unverified_claims.append({
                "fact": "No policy repo rate was found in the retrieved RBI sources.",
                "status": "unverified",
                "evidence": [],
                "notes": "A current rate requires an explicit policy-repo-rate value and date.",
            })
            return report

        value_match = re.search(r"\d+(?:\.\d+)?", observations[0]["value"])
        value = value_match.group(0) if value_match else ""
        observation_dates = [
            item["candidate"].as_of_date or item["candidate"].published_at
            for item in observations
        ]
        valid_dates = [date for date in observation_dates if date]
        latest_date = max(valid_dates) if valid_dates else None
        date_label = (
            datetime.fromisoformat(latest_date).strftime("%B %-d, %Y")
            if latest_date
            else None
        )
        claim_text = (
            f"The RBI policy repo rate is {value}%"
            + (f" as of {date_label}." if date_label else ".")
        )
        unique_urls = {item["candidate"].source_url for item in observations}
        values = {item["normalized_value"] for item in observations}
        independently_confirmed = (
            len(unique_urls) >= 2
            and len(valid_dates) == len(observations)
            and len(observations) >= 2
        )
        evidence_by_claim = []
        for item in observations:
            evidence = create_evidence_record(
                claim=claim_text,
                source=item["source"],
                supporting_text=item["quote"],
            )
            evidence.verification_status = (
                "contradicting"
                if (
                    len(values) > 1
                    and item["normalized_value"]
                    != observations[0]["normalized_value"]
                )
                else "supported"
                if independently_confirmed
                else "insufficient"
            )
            evidence_by_claim.append(evidence)

        report = build_research_report(
            topic=request.topic,
            research_question=request.research_question,
            claims=[claim_text],
            evidence_by_claim={claim_text: evidence_by_claim},
        )
        report.sources = [
            self._source_summary(page["candidate"])
            for page in pages
        ]
        if not independently_confirmed and len(values) == 1:
            report.unverified_claims.append({
                "fact": claim_text,
                "status": "unverified",
                "evidence": [
                    {
                        "source_name": item["candidate"].source_name,
                        "source_url": item["candidate"].source_url,
                        "evidence_text": item["quote"],
                        "support": "not_relevant",
                        "published_at": item["candidate"].published_at,
                        "as_of_date": item["candidate"].as_of_date,
                    }
                    for item in observations
                ],
                "notes": (
                    "A current policy rate needs matching dated values from "
                    "at least two authoritative RBI source pages."
                ),
            })
        report.important_numbers = (
            [{"number": value + "%"}] if value and report.verified_facts else []
        )
        return report

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

        if not pages:
            report.unverified_claims.append({
                "fact": "No usable source pages were retrieved.",
                "status": "unverified",
                "evidence": [],
                "notes": "All configured sources were unavailable or returned unusable content.",
            })
            return report

        category = candidates[0].category
        if category == "repo_rate":
            return self._research_repo_rate(request, pages)

        quote_items = []
        source_by_id = {}
        for page in pages:
            candidate = page["candidate"]
            source = self._source_document(candidate, page["content"])
            statements = _relevant_statements(
                page["content"],
                request.topic,
                category,
            )
            for statement in statements[:3]:
                quote_id = f"Q{len(quote_items) + 1}"
                quote_items.append(
                    {
                        "id": quote_id,
                        "text": statement,
                        "source_name": candidate.source_name,
                        "source_url": candidate.source_url,
                        "published_at": candidate.published_at,
                        "as_of_date": candidate.as_of_date,
                        "category": category,
                    }
                )
                source_by_id[quote_id] = source

        if not quote_items:
            report.sources = [self._source_summary(page["candidate"]) for page in pages]
            report.unverified_claims.append({
                "fact": "No source quotations matched the requested topic.",
                "status": "unverified",
                "evidence": [],
                "notes": "No sufficiently relevant verbatim source statements were found.",
            })
            return report

        try:
            claims = self._make_claims(request, quote_items)
            verifications = self._verify_claims(
                claims,
                {item["id"]: item for item in quote_items},
            ) if claims else {}
            verification_error = None
        except (RuntimeError, ValueError) as exc:
            claims = []
            verifications = {}
            verification_error = str(exc)

        evidence_by_claim = {}
        for claim_item in claims:
            claim_text = claim_item["claim"]
            linked_quotes = [
                quote_by_id
                for quote_by_id in quote_items
                if quote_by_id["id"] in claim_item["evidence_ids"]
            ]
            if (
                verifications.get(claim_item["id"]) == "supported"
                and not self._claim_matches_topic(claim_text, category)
            ):
                verdict = "insufficient"
            else:
                verdict = verifications.get(claim_item["id"], "insufficient")
            if not self._numbers_are_in_evidence(
                claim_text,
                [item["text"] for item in linked_quotes],
            ):
                verdict = "insufficient"

            records = []
            for quote in linked_quotes:
                record = create_evidence_record(
                    claim=claim_text,
                    source=source_by_id[quote["id"]],
                    supporting_text=quote["text"],
                )
                record.verification_status = verdict
                records.append(record)
            evidence_by_claim[claim_text] = records

        claim_texts = list(evidence_by_claim)
        report = build_research_report(
            topic=request.topic,
            research_question=request.research_question,
            claims=claim_texts,
            evidence_by_claim=evidence_by_claim,
        )
        report.sources = [self._source_summary(page["candidate"]) for page in pages]
        if not claim_texts:
            report.unverified_claims.append({
                "fact": "No verified claim candidates were returned.",
                "status": "unverified",
                "evidence": [],
                "notes": verification_error or "Claim extraction produced no usable paraphrases.",
            })
        elif verification_error:
            report.unverified_claims.append({
                "fact": "Claims could not be independently verified.",
                "status": "unverified",
                "evidence": [],
                "notes": verification_error,
            })
        numbers = set()
        for fact in report.verified_facts:
            fact_text = re.sub(
                r"\b(?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{1,2},\s+\d{4}\b",
                "",
                fact["fact"],
                flags=re.IGNORECASE,
            )
            numbers.update(
                re.findall(r"(?<!\w)\d[\d,]*(?:\.\d+)?%?", fact_text)
            )
        report.important_numbers = [
            {"number": number} for number in sorted(numbers)
        ]
        return report
