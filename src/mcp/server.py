import asyncio

from mcp.server.mcpserver import MCPServer

from src.research.research_service import research_claim
from src.research.source_ingestion import (
    create_source_document,
    create_evidence_record,
)
from pydantic import BaseModel


server = MCPServer("finance-research")

class EvidenceInput(BaseModel):
    source_name: str
    source_url: str
    source_type: str
    supporting_text: str
    published_at: str | None = None
    title: str | None = None


class ClaimInput(BaseModel):
    claim: str
    evidence: list[EvidenceInput]

@server.tool()
async def verify_claim(
    claim: str,
    source_name: str,
    source_url: str,
    source_type: str,
    supporting_text: str,
    published_at: str | None = None,
) -> dict:
    """Verify a finance claim against supplied source evidence."""

    source = create_source_document(
        source_name=source_name,
        source_url=source_url,
        title=source_name,
        content=supporting_text,
        source_type=source_type,
        published_at=published_at,
    )

    evidence = create_evidence_record(
        claim=claim,
        source=source,
        supporting_text=supporting_text,
    )

    result = research_claim(
        claim_text=claim,
        evidence_records=[evidence],
    )

    return {
        "claim": result.claim,
        "status": result.status,
        "notes": result.notes,
        "evidence": [
            {
                "source_name": item.source_name,
                "source_url": item.source_url,
                "support": item.support,
                "evidence_text": item.evidence_text,
                "published_at": item.published_at,
            }
            for item in result.evidence
        ],
    }


@server.tool()
async def verify_claims(
    claims: list[ClaimInput],
) -> dict:
    """Verify multiple finance claims against multiple source evidence records."""

    results = []

    for item in claims:
        evidence_records = []

        for evidence_item in item.evidence:
            source = create_source_document(
                source_name=evidence_item.source_name,
                source_url=evidence_item.source_url,
                title=evidence_item.title or evidence_item.source_name,
                content=evidence_item.supporting_text,
                source_type=evidence_item.source_type,
                published_at=evidence_item.published_at,
            )

            evidence_records.append(
                create_evidence_record(
                    claim=item.claim,
                    source=source,
                    supporting_text=evidence_item.supporting_text,
                )
            )

        result = research_claim(
            claim_text=item.claim,
            evidence_records=evidence_records,
        )

        results.append({
            "claim": result.claim,
            "status": result.status,
            "notes": result.notes,
            "evidence": [
                {
                    "source_name": evidence_item.source_name,
                    "source_url": evidence_item.source_url,
                    "support": evidence_item.support,
                    "evidence_text": evidence_item.evidence_text,
                    "published_at": evidence_item.published_at,
                }
                for evidence_item in result.evidence
            ],
        })

    counts = {
        "verified": sum(
            result["status"] == "verified"
            for result in results
        ),
        "unverified": sum(
            result["status"] == "unverified"
            for result in results
        ),
        "conflicting": sum(
            result["status"] == "conflicting"
            for result in results
        ),
    }

    return {
        "total_claims": len(results),
        "counts": counts,
        "all_verified": (
            len(results) > 0
            and counts["verified"] == len(results)
        ),
        "results": results,
    }

async def main() -> None:
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
