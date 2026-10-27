from urllib.parse import urlparse

from .source_authority import SourceAuthority


HIGH_AUTHORITY_DOMAINS = {
    "rbi.org.in", "sebi.gov.in", "incometax.gov.in",
    "incometaxindia.gov.in", "mof.gov.in", "dea.gov.in",
    "financialservices.gov.in", "mospi.gov.in", "pib.gov.in",
    "cbic.gov.in", "nhb.org.in", "indiabudget.gov.in",
    "nsiindia.gov.in",
}

MEDIUM_AUTHORITY_DOMAINS = {
    "reuters.com", "bloomberg.com", "ft.com",
    "economictimes.indiatimes.com", "moneycontrol.com",
    "sbi.co.in", "hdfcbank.com", "icicibank.com", "cibil.com",
}


def _matches_domain(host, domains):
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def classify_source(
    source_name: str,
    source_type: str,
    source_url: str | None = None,
) -> SourceAuthority:
    host = (urlparse(source_url).hostname or "").lower() if source_url else ""

    if _matches_domain(host, HIGH_AUTHORITY_DOMAINS):
        return SourceAuthority(
            source_name=source_name,
            authority_level="high",
            source_type=source_type,
            reason="Official or primary source domain.",
        )

    if _matches_domain(host, MEDIUM_AUTHORITY_DOMAINS):
        return SourceAuthority(
            source_name=source_name,
            authority_level="medium",
            source_type=source_type,
            reason="Established financial/news source domain.",
        )

    return SourceAuthority(
        source_name=source_name,
        authority_level="unknown",
        source_type=source_type,
        reason="Source authority has not been established.",
    )


def authority_rank(level: str) -> int:
    return {"high": 3, "medium": 2, "low": 1, "unknown": 0}.get(level, 0)
