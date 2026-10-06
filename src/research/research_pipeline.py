from .research_report import ResearchReport
from .research_service import research_claim
from .evidence import EvidenceRecord


def build_research_report(
    topic: str,
    research_question: str,
    claims: list[str],
    evidence_by_claim: dict[str, list[EvidenceRecord]],
) -> ResearchReport:
    report = ResearchReport(
        topic=topic,
        research_question=research_question,
    )

    for claim in claims:
        evidence = evidence_by_claim.get(claim, [])

        result = research_claim(
            claim_text=claim,
            evidence_records=evidence,
        )

        report.sources.extend(
            item.source_url
            for item in result.evidence
            if item.source_url not in report.sources
        )

        if result.status == "verified":
            report.verified_facts.append(claim)
        else:
            report.unverified_claims.append(claim)

    return report
