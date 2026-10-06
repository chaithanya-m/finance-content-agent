import asyncio

from mcp.server.mcpserver import MCPServer

from src.research.research_service import research_claim
from src.research.source_ingestion import (
    create_source_document,
    create_evidence_record,
)


server = MCPServer("finance-research")


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


async def main() -> None:
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())