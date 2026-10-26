import json
import subprocess
import uuid

from .research_agent import ResearchAgent
from .research_report import ResearchReport
from .research_request import ResearchRequest


class OpenClawResearchAgent(ResearchAgent):
    def research(self, request: ResearchRequest) -> ResearchReport:
        prompt = f"""
You are the research engine for an Indian finance content system.

Topic: {request.topic}
Research question: {request.research_question}

STEP 1 — RESEARCH
- Use current web sources.
- Prefer primary sources: RBI, SEBI, Government of India, and official company filings.
- Collect factual claims needed to answer the research question.
- Record the source URL and supporting evidence for each claim.

STEP 2 — VERIFY
- You MUST use the finance-research MCP tool `verify_claims`.
- Send the researched claims and their supporting evidence to `verify_claims`.
- Do not decide that a claim is verified yourself.
- MCP verification status is authoritative.

STEP 3 — CLASSIFY
- verified_facts: ONLY claims whose MCP verification status is exactly "verified".
- unverified_claims: claims whose MCP status is "unverified" or "conflicting".
- Never put an unverified or conflicting claim into verified_facts.
- Preserve source URLs and evidence for verified claims.
- Important numbers must come from researched evidence.

FACT OBJECT SCHEMA:
Every verified_facts item MUST be a JSON object containing:
{{
  "fact": "the exact researched claim",
  "status": "verified",
  "evidence": [
    {{
      "source_name": "official source name",
      "source_url": "https://...",
      "support": "supporting",
      "evidence_text": "relevant source text",
      "published_at": null
    }}
  ],
  "notes": "verification result notes"
}}
Use the exact key "fact", not "claim".
Copy status and evidence from the verify_claims tool result; never invent them.
If no claim is verified by the tool, return an empty verified_facts array.
Do not turn an unverified result into a verified fact.

STEP 4 — OUTPUT
Return ONLY valid JSON.
Do NOT use Markdown.
Do NOT use code fences.
Do NOT add comments.
Do NOT add explanations before or after the JSON.

Return exactly this structure:
{{
  "topic": "{request.topic}",
  "research_question": "{request.research_question}",
  "verified_facts": [],
  "important_numbers": [],
  "analysis": [],
  "unverified_claims": [],
  "sources": []
}}

If verify_claims cannot be successfully called, return an empty verified_facts array rather than guessing.
"""

        session_key = f"finance-research-{uuid.uuid4().hex[:12]}"

        def run_agent(agent_prompt: str) -> str:
            result = subprocess.run(
                [
                    "openclaw",
                    "agent",
                    "--json",
                    "--session-key",
                    session_key,
                    "--message",
                    agent_prompt,
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    "OpenClaw research agent failed.\n"
                    f"stdout:\n{result.stdout}\n"
                    f"stderr:\n{result.stderr}"
                )

            response = json.loads(result.stdout)
            return response["result"]["payloads"][0]["text"].strip()

        text = run_agent(prompt)

        if text.startswith("```"):
            lines = text.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            retry_prompt = prompt + """

CRITICAL OUTPUT REQUIREMENT:

Your previous response was rejected because it was not valid JSON.

Return ONLY the JSON object.
Do not provide reasoning.
Do not provide an explanation.
Do not use Markdown.
Do not use code fences.
Do not write anything before or after the JSON object.

The first character of your response must be {.
The last character of your response must be }.
"""

            text = run_agent(retry_prompt).strip()

            if text.startswith("```"):
                lines = text.splitlines()

                if lines and lines[0].startswith("```"):
                    lines = lines[1:]

                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]

                text = "\n".join(lines).strip()

            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "OpenClaw research agent returned invalid JSON "
                    "after retry. Research report was rejected."
                ) from exc
        except json.JSONDecodeError as exc:
            raise ValueError(
                "OpenClaw research agent returned invalid JSON. "
                "Research report was rejected."
            ) from exc

        required_fields = {
            "topic",
            "research_question",
            "verified_facts",
            "important_numbers",
            "analysis",
            "unverified_claims",
            "sources",
        }

        missing_fields = required_fields - data.keys()

        if missing_fields:
            raise ValueError(
                f"OpenClaw research report is missing fields: "
                f"{sorted(missing_fields)}"
            )

        return ResearchReport(
            topic=data["topic"],
            research_question=data["research_question"],
            verified_facts=data["verified_facts"],
            important_numbers=data["important_numbers"],
            analysis=data["analysis"],
            unverified_claims=data["unverified_claims"],
            sources=data["sources"],
        )
