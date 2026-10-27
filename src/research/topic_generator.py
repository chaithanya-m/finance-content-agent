"""
AITopicGenerator
================
Autonomously brainstorms fresh, random personal-finance topics for Indian beginners
using a local LLM (Ollama), bypassing static config/topics.json.

Every generated topic is designed to:
  1. Resonate with a 15-16 year old beginner (practical question, relatable hook).
  2. Map to a verified knowledge domain supported by authoritative sources (RBI, SEBI,
     MOSPI, CBIC, Income Tax, CIBIL).
  3. Avoid repeating concepts from previously generated topics.
"""

import json
import os
import random
import urllib.error
import urllib.request
from typing import Collection

from .topic import Topic


# Verified knowledge domains supported by primary Indian sources in source_discovery.py
VERIFIED_DOMAINS = [
    {
        "category": "home_loan",
        "theme": "Home Loans & EMIs",
        "keywords": ["home loan", "emi", "floating rate"],
        "angles": [
            "Why loan tenures increase when interest rates rise instead of EMI",
            "Fixed versus floating interest rates for first-time home buyers",
            "How benchmark-linked interest rates affect monthly bank deductions",
            "Why banks must disclose EMI reset impacts to home loan borrowers",
        ],
    },
    {
        "category": "repo_rate",
        "theme": "RBI Repo Rate & Borrowing Costs",
        "keywords": ["repo rate", "rbi"],
        "angles": [
            "What the RBI repo rate means for a family's borrowing budget",
            "How the Reserve Bank of India policy rate changes loan interest rates",
            "Why RBI changes interest rates and what it means for bank customers",
            "How repo rate cuts or hikes travel from the RBI to commercial banks",
        ],
    },
    {
        "category": "inflation",
        "theme": "Inflation & Purchasing Power",
        "keywords": ["inflation", "purchasing power"],
        "angles": [
            "How inflation quietly shrinks the value of money kept in savings accounts",
            "Understanding CPI inflation and why grocery bills feel higher every year",
            "Why salary increases must beat inflation to improve actual purchasing power",
            "How inflation affects household budgets in India and what you can do",
        ],
    },
    {
        "category": "compounding",
        "theme": "The Power of Compounding",
        "keywords": ["compounding", "compound interest"],
        "angles": [
            "How starting to save 5 years earlier changes compound growth drastically",
            "How compound interest turns small regular savings into wealth over time",
            "The mathematical difference between simple interest and compound interest",
            "Why time in the market matters more than the amount you start with",
        ],
    },
    {
        "category": "credit_score",
        "theme": "Credit Scores & Loan Eligibility",
        "keywords": ["credit score", "cibil"],
        "angles": [
            "How a credit score affects whether banks approve a loan or credit card",
            "What factors make a credit score go up or down in India",
            "Why missing a small bill payment can hurt your credit score for years",
            "How teenagers and first-time earners can build good credit history safely",
        ],
    },
    {
        "category": "tax",
        "theme": "Direct and Indirect Taxes",
        "keywords": ["tax", "gst"],
        "angles": [
            "The fundamental difference between direct income tax and indirect GST",
            "Why you pay GST on everyday purchases even if you don't earn an income",
            "How the Indian tax system works for ordinary citizens and students",
            "Understanding where your tax money goes and why governments collect it",
        ],
    },
]


class AITopicGenerator:
    """Generates novel, grounded financial topics using Ollama or domain templates."""

    def __init__(self) -> None:
        self.base_url = os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        ).rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")

    def _call_ollama(self, prompt: str) -> dict:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.7, "num_ctx": 2048, "num_predict": 300},
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            api_result = json.loads(response.read().decode("utf-8"))

        text = api_result.get("response", "").strip()
        return json.loads(text)

    def _fallback_topic(
        self,
        domain: dict,
        exclude_titles: Collection[str],
    ) -> Topic:
        """Select a pre-vetted angle if the LLM call is unavailable."""
        available_angles = [
            angle for angle in domain["angles"]
            if angle.casefold() not in {t.casefold() for t in exclude_titles}
        ]
        chosen_title = random.choice(available_angles or domain["angles"])
        keyword = domain["keywords"][0]
        return Topic(
            title=chosen_title,
            reason=f"Explain {domain['theme']} using authoritative Indian sources on {keyword}.",
            content_type="carousel",
            priority="high",
        )

    def generate(self, exclude_titles: Collection[str] | None = None) -> Topic:
        """
        Brainstorm a fresh, verified-domain financial topic not in exclude_titles.
        Falls back gracefully to curated domain templates if Ollama is unavailable.
        """
        exclude = set(exclude_titles or [])
        domain = random.choice(VERIFIED_DOMAINS)
        keyword = domain["keywords"][0]

        prompt = f"""
You are a creative educational content director for an Indian personal finance channel.
Your goal is to brainstorm ONE fresh, engaging question to teach finance to 15-16 year old beginners.

TOPIC DOMAIN: {domain['theme']}
REQUIRED KEYWORD (must include in title): "{keyword}"

GUIDELINES:
- Frame it as an intriguing, real-life question or dilemma (e.g. "Why did my parents' loan tenure increase by 5 years?").
- Must be understandable to a 15-year-old with zero finance knowledge.
- Must include the keyword "{keyword}" so it maps to verified primary sources (RBI, SEBI, MOSPI).
- Do NOT repeat these already covered topics:
{json.dumps(list(exclude)[:10], ensure_ascii=False)}

Return JSON ONLY:
{{
  "title": "A captivating, concise question or title including {keyword}",
  "reason": "1-2 sentences on what this teaches and why it matters to ordinary people."
}}
""".strip()

        try:
            data = self._call_ollama(prompt)
            title = data.get("title", "").strip()
            reason = data.get("reason", "").strip()

            # Ensure the required keyword is present so source_discovery matches the domain
            has_keyword = any(kw in title.casefold() for kw in domain["keywords"])
            if not has_keyword:
                # Guarantee keyword presence
                title = f"{title.rstrip('?')} — {domain['theme']}?"

            if title and reason and title.casefold() not in {t.casefold() for t in exclude}:
                return Topic(
                    title=title,
                    reason=reason,
                    content_type="carousel",
                    priority="high",
                )
        except Exception:
            # On any LLM timeout, connection error, or invalid JSON, use vetted domain angles
            pass

        return self._fallback_topic(domain, exclude)

