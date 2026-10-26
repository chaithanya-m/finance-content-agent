import re

from .claim import Claim, Evidence
from .evidence import EvidenceRecord


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _extract_numbers(text: str) -> set[str]:
    text = re.sub(r"(\d+(?:\.\d+)?)\s*(?:per\s*cent|percent)", r"\1%", text.lower())

    return set(
        re.findall(r"\d+(?:\.\d+)?%?", text)
    )

def verify_claim(claim: Claim, evidence: EvidenceRecord) -> Claim:
    claim_text = _normalize(claim.claim)
    evidence_text = _normalize(evidence.supporting_text)

    claim_numbers = _extract_numbers(claim_text)
    evidence_numbers = _extract_numbers(evidence_text)

    numbers_match = claim_numbers.issubset(evidence_numbers)

    keywords = {
        "repo",
        "rate",
        "policy",
        "rbi",
        "inflation",
        "gdp",
        "tax",
        "income",
        "interest",
        "market",
    }

    claim_keywords = {
        word for word in claim_text.split()
        if word in keywords
    }

    evidence_keywords = {
        word for word in evidence_text.split()
        if word in keywords
    }

    keyword_match = bool(claim_keywords & evidence_keywords)

    claim.evidence.append(
        Evidence(
            source_name=evidence.source.source_name,
            source_url=evidence.source.source_url,
            evidence_text=evidence.supporting_text,
            published_at=evidence.source.published_at,
        )
    )

    if numbers_match and keyword_match:
        claim.status = "verified"
        claim.notes = (
            "Claim is supported by matching numeric values "
            "and relevant factual terminology."
        )
    else:
        claim.status = "unverified"
        claim.notes = (
            "The supplied evidence does not sufficiently support "
            "the claim's numeric values and terminology."
        )

    return claim

def detect_conflict(
    claim: Claim,
    evidence_records: list[EvidenceRecord],
) -> Claim:
    claim_numbers = _extract_numbers(claim.claim)

    if not claim_numbers:
        claim.status = "unverified"
        claim.notes = "Claim does not contain a numeric value to compare."
        return claim

    claimed_value = next(iter(claim_numbers))

    matching_evidence = []

    for record in evidence_records:
        evidence_text = _normalize(record.supporting_text)

        if claimed_value in evidence_text:
            matching_evidence.append(record)

    if len(matching_evidence) == len(evidence_records):
        claim.status = "verified"
        claim.notes = (
            "All supplied evidence records contain the claimed value."
        )
        return claim

    if matching_evidence:
        claim.status = "conflicting"
        claim.notes = (
            "Some evidence supports the claimed value while other "
            "evidence does not."
        )
        return claim

    claim.status = "unverified"
    claim.notes = (
        "None of the supplied evidence records contain the claimed value."
    )

    return claim

def evidence_supports_claim(
    claim: Claim,
    evidence: EvidenceRecord,
) -> bool:
    claim_text = _normalize(claim.claim)
    evidence_text = _normalize(evidence.supporting_text)

    claim_numbers = _extract_numbers(claim_text)
    evidence_numbers = _extract_numbers(evidence_text)

    numbers_match = claim_numbers.issubset(evidence_numbers)

    keywords = {
        "repo",
        "rate",
        "policy",
        "rbi",
        "inflation",
        "gdp",
        "tax",
        "income",
        "interest",
        "market",
    }

    claim_keywords = {
        word for word in claim_text.split()
        if word in keywords
    }

    evidence_keywords = {
        word for word in evidence_text.split()
        if word in keywords
    }

    keyword_match = bool(claim_keywords & evidence_keywords)

    return numbers_match and keyword_match

def evidence_relation(
    claim: Claim,
    evidence: EvidenceRecord,
) -> str:
    claim_text = _normalize(claim.claim)
    evidence_text = _normalize(evidence.supporting_text)

    # Numerical claims must match the supplied source evidence.
    claim_numbers = {
        number.rstrip("%")
        for number in _extract_numbers(claim_text)
    }
    evidence_numbers = {
        number.rstrip("%")
        for number in _extract_numbers(evidence_text)
    }

    if not claim_numbers.issubset(evidence_numbers):
        return "not_relevant"

    # Normalize common variations before comparing terminology.
    aliases = {
        "rates": "rate",
        "loans": "loan",
        "emis": "emi",
        "affects": "affect",
        "affecting": "affect",
        "increases": "increase",
        "increased": "increase",
        "increasing": "increase",
        "rises": "rise",
        "rising": "rise",
        "reduces": "reduce",
        "reduced": "reduce",
        "reducing": "reduce",
        "falls": "fall",
        "falling": "fall",
        "payments": "payment",
        "installments": "installment",
        "instalments": "installment",
    }

    stopwords = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on",
        "at", "as", "by", "for", "is", "are", "was", "were",
        "be", "been", "being", "it", "this", "that", "these",
        "those", "with", "from", "than", "then", "they", "their",
        "can", "could", "will", "may", "should", "does", "do",
        "how", "what", "why", "when",
    }

    def terms(text: str) -> set[str]:
        words = re.findall(r"[a-z]+", text.lower())
        return {
            aliases.get(word, word)
            for word in words
            if word not in stopwords and len(word) > 1
        }

    claim_terms = terms(claim_text)
    evidence_terms = terms(evidence_text)
    overlap = claim_terms & evidence_terms

    # Require meaningful overlap, not merely a shared generic word.
    if (
        len(overlap) < 2
        or not claim_terms
        or len(overlap) / len(claim_terms) < 0.4
    ):
        return "not_relevant"

    # Do not accept an obvious opposite direction as supporting evidence.
    upward = {"increase", "rise", "higher", "raise", "grow", "growth", "up"}
    downward = {"decrease", "fall", "lower", "reduce", "drop", "decline", "down"}

    claim_up = claim_terms & upward
    claim_down = claim_terms & downward
    evidence_up = evidence_terms & upward
    evidence_down = evidence_terms & downward

    if claim_up and evidence_down and not evidence_up:
        return "not_relevant"

    if claim_down and evidence_up and not evidence_down:
        return "not_relevant"

    return "supporting"
