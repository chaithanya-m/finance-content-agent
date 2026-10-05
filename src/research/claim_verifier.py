import re

from .claim import Claim, Evidence
from .evidence import EvidenceRecord


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", text))


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
