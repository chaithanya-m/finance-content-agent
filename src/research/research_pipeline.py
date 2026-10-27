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

    seen_source_urls: set[str] = set()

    for claim_text in claims:
        evidence = evidence_by_claim.get(claim_text, [])

        result = research_claim(
            claim_text=claim_text,
            evidence_records=evidence,
        )

        fact = {
            "fact": result.claim,
            "status": result.status,
            "evidence": [
                {
                    "source_name": item.source_name,
                    "source_url": item.source_url,
                    "evidence_text": item.evidence_text,
                    "support": item.support,
                    "published_at": item.published_at,
                    "as_of_date": item.as_of_date,
                }
                for item in result.evidence
            ],
            "notes": result.notes,
        }

        if result.status == "verified":
            report.verified_facts.append(fact)
        else:
            report.unverified_claims.append(fact)

        for record in evidence:
            source = record.source

            if source.source_url in seen_source_urls:
                continue

            seen_source_urls.add(source.source_url)
            report.sources.append(
                {
                    "source_name": source.source_name,
                    "source_url": source.source_url,
                    "published_at": source.published_at,
                    "as_of_date": source.as_of_date,
                }
            )
            
    return report
