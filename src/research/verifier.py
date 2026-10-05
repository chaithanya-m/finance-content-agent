from .claim import Claim, Evidence


def create_claim(
    claim: str,
    source_name: str,
    source_url: str,
    evidence_text: str,
    published_at: str | None = None,
) -> Claim:
    evidence = Evidence(
        source_name=source_name,
        source_url=source_url,
        evidence_text=evidence_text,
        published_at=published_at,
    )

    return Claim(
        claim=claim,
        status="verified",
        evidence=[evidence],
    )
