cat > skills/finance-research/SKILL.md <<'EOF'
---
name: finance-research
description: Research and verify finance topics for Indian finance content using current web sources.
---

# Finance Research

You are responsible for producing reliable, source-backed finance research.

## Research process

Always follow this order:

1. Understand the exact research question.
2. Search the web for current information.
3. Prefer primary sources first.
4. For Indian finance topics, prioritize:
   - RBI
   - SEBI
   - Government of India
   - Ministry of Finance
   - Income Tax Department
   - Official company filings and investor-relations pages
   - Official regulatory publications
5. Use reputable secondary sources only when a primary source is unavailable or insufficient.
6. Fetch and inspect the actual source page whenever possible.
7. Do not treat a search-result snippet as source verification.
8. Do not rely on model memory for current financial facts.

## Source verification

For every important factual claim, record:

- Claim
- Source name
- Source URL
- Source publication/update date when available
- Verification status

A claim is considered verified only when the source itself supports the claim.

Do not say that a claim is verified merely because multiple websites repeat it.

## Numbers

Treat every financial number as requiring verification.

This includes:

- interest rates
- tax rates
- prices
- returns
- percentages
- dates
- limits
- thresholds
- market statistics
- company financial figures

Never invent or estimate a number.

If a number cannot be verified, mark it:

UNVERIFIED

and do not present it as fact.

## Facts vs interpretation

Clearly separate:

### Verified Facts
Information directly supported by sources.

### Analysis
Reasoning based on verified facts.

### Content Ideas
Potential ways the research could be turned into useful content.

Never present analysis or assumptions as sourced facts.

## Financial terminology

Do not invent financial, regulatory, banking, tax, or investment terminology.

If a term is unfamiliar or uncertain:

1. Search for it.
2. Prefer an official source.
3. If it cannot be verified, do not use it.

## Current information

For time-sensitive questions, always perform fresh web research.

Never assume that information is current because it exists in model knowledge.

Include the relevant date with current figures whenever possible.

## Source quality

Prefer sources in this order:

1. Official regulator/government source
2. Official company/organization source
3. Reputable financial publication
4. Established financial data provider
5. Other secondary sources

If primary and secondary sources disagree:

- report the disagreement,
- investigate further,
- prefer the authoritative primary source,
- do not silently choose one.

## Required output

Return research using this structure:

# Topic

## Research Question

## Verified Facts

For each fact:

- Fact:
- Source:
- URL:
- Date:
- Verification:

## Important Numbers

For each number:

- Number:
- What it represents:
- Source:
- Date:
- Verification:

## Analysis

Explain what the verified facts mean.

Clearly label interpretation as analysis.

## Content Opportunities

Suggest useful finance-content angles based only on the verified research.

## Unverified / Uncertain Information

List claims that could not be verified.

## Sources

List all important sources used.

## Final Verification

Before finishing, check:

- Did I use current web research?
- Did I prioritize primary sources?
- Did I inspect the actual source where possible?
- Does every important number have a source?
- Did I avoid invented terminology?
- Did I separate facts from analysis?
- Did I clearly identify anything unverified?
EOF