from .research_agent import ResearchAgent
from .research_report import ResearchReport
from .research_service import research_claim
from .evidence import EvidenceRecord


class SimpleResearchAgent(ResearchAgent):
    def research(
        self,
        topic: str,
        claims: list[str],
        evidence_by_claim: dict[str, list[EvidenceRecord]],
    ) -> ResearchReport:
        report = ResearchReport(
            topic=topic,
            research_question=f"What should we know about {topic}?",
        )

        for claim in claims:
            result = research_claim(
                claim_text=claim,
                evidence_records=evidence_by_claim.get(claim, []),
            )

            if result.status == "verified":
                report.verified_facts.append(claim)
            else:
                report.unverified_claims.append(claim)

            for evidence in result.evidence:
                if evidence.source_url not in report.sources:
                    report.sources.append(evidence.source_url)

        return report