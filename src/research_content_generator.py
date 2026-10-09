import json
import subprocess

from .content_post import InstagramPost
from .research.research_report import ResearchReport


class ResearchContentGenerator:
    def generate(self, report: ResearchReport) -> InstagramPost:
        if not report.verified_facts:
            raise ValueError("Cannot generate content without verified facts.")

        verified_facts = [
            fact
            for fact in report.verified_facts
            if fact.get("status") == "verified"
        ]

        if not verified_facts:
            raise ValueError("No verified facts are available for content generation.")

        prompt = f"""
Create an educational Instagram carousel about this Indian finance topic.

Topic:
{report.topic}

Research question:
{report.research_question}

VERIFIED FACTS:
{json.dumps(verified_facts, indent=2)}

IMPORTANT NUMBERS:
{json.dumps(report.important_numbers, indent=2)}

Use these numbers ONLY when they are already explicitly supported by VERIFIED FACTS.

ANALYSIS:
{json.dumps(report.analysis, indent=2)}

Analysis may be used only for general explanation and must NOT introduce new factual claims.

SOURCES:
{json.dumps(report.sources, indent=2)}

Rules:
1. Use ONLY the verified facts and information provided above.
2. Do not invent statistics, dates, rates, examples, or claims.
3. Do not provide personalized financial advice.
4. Do not promise returns or guaranteed outcomes.
5. Make the content understandable to an Indian young professional.
6. Create a useful educational carousel.
7. Keep each slide concise and easy to read.
8. Clearly distinguish facts from explanation.
9. Do not mention claims that are unverified or conflicting.
10. Preserve important financial numbers exactly as provided.
11. The sources must be the URLs provided above.
12. Every factual statement in the post must be listed in the "claims" array.
13. The "claims" array may contain ONLY the exact factual statements from VERIFIED FACTS.
14. Do not convert important numbers into new claims.
15. Do not use analysis or source descriptions as factual claims.
16. Do not add, combine, infer, or expand factual claims beyond VERIFIED FACTS.
17. If a fact is not in VERIFIED FACTS, do not state it as a fact in the post.

Return ONLY valid JSON in this exact structure:

{{
  "topic": "...",
  "hook": "...",
  "slides": [
    "...",
    "...",
    "..."
  ],
  "caption": "...",
  "call_to_action": "...",
  "sources": [
    "https://..."
  ],
  "claims": [
    "..."
  ]
}}
"""

        result = subprocess.run(
            [
                "openclaw",
                "agent",
                "--json",
                "--message",
                prompt,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        response = json.loads(result.stdout)
        text = response["result"]["payloads"][0]["text"].strip()

        if text.startswith("```"):
            lines = text.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        data = json.loads(text)

        required_fields = {
            "topic",
            "hook",
            "slides",
            "caption",
            "call_to_action",
            "sources",
            "claims",
        }

        missing_fields = required_fields - data.keys()

        if missing_fields:
            raise ValueError(
                f"Generated content is missing required fields: "
                f"{sorted(missing_fields)}"
            )

        return InstagramPost(
            topic=data["topic"],
            hook=data["hook"],
            slides=data["slides"],
            caption=data["caption"],
            call_to_action=data["call_to_action"],
            sources=data["sources"],
            claims=data["claims"],
        )
