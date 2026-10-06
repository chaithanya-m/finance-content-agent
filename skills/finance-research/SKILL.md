---
name: finance-research
description: Research and verify finance topics for Indian finance content using current web sources.
---

# Finance Research

You are responsible for producing reliable, source-backed finance research.

## 1. Research Question

Before researching:

1. Understand the exact research question.
2. Identify what information needs to be established.
3. Identify any time-sensitive requirements.
4. Identify all financial figures, dates, rates, percentages, thresholds, limits, prices, returns, or market statistics that will require verification.

Do not begin analysis before understanding the exact research question.

## 2. Source Discovery

When researching a topic:

1. Use OpenClaw web search to discover current sources.
2. Search for current information whenever the question is time-sensitive.
3. Prefer primary and authoritative sources.

For Indian finance topics, prioritize:

- RBI
- SEBI
- Government of India
- Ministry of Finance
- Income Tax Department
- Official company filings
- Official company investor-relations pages
- Official regulatory publications

Use reputable secondary sources only when primary sources are unavailable or insufficient.

### Source quality priority

Prefer sources in this order:

1. Official regulator/government source
2. Official company/organization source
3. Reputable financial publication
4. Established financial data provider
5. Other secondary sources

If primary and secondary sources disagree:

- Report the disagreement.
- Investigate further.
- Prefer the authoritative primary source.
- Do not silently choose one source.

## 3. Source Inspection

After discovering a potentially relevant source:

1. Fetch and inspect the actual source page whenever possible.
2. Do not treat a search-result snippet as source verification.
3. Never use a search-result snippet as the sole evidence for an important claim.
4. Record the source URL.
5. Record the source publication/update date when available.
6. Preserve the exact supporting text for important claims.

Do not rely on model memory for current financial facts.

## 4. Claim Extraction

Before producing the final research output:

1. Extract every important factual claim from the inspected source evidence.
2. Treat each financial number, rate, percentage, date, threshold, limit, price, return, or market statistic as an important claim.
3. Preserve each claim in a precise form that can be checked against the source evidence.
4. Do not merge separate claims if doing so could change their meaning.
5. For each important claim, preserve:
   - Exact claim
   - Source name
   - Source URL
   - Exact supporting text
   - Source publication/update date when available
   - Source type

Every important extracted claim must go through deterministic MCP verification before it can appear under `Verified Facts` or `Important Numbers`.

## 5. Deterministic Claim Verification

For every important financial claim that will be used in the final research output:

1. Obtain the actual source evidence first.
2. Call the `finance-research` MCP tool `verify_claim` with:
   - Exact claim
   - Source name
   - Source URL
   - Source type
   - Exact supporting text
   - Publication/update date when available
3. Treat the MCP verification result as authoritative for the claim's verification status.
4. Do not mark a claim as verified based only on your own reasoning.
5. If the MCP tool returns `unverified` or `conflicting`, do not present the claim as verified.
6. Preserve the exact source evidence used for verification.
7. Do not change the wording of a verified claim in a way that changes its meaning.
8. If a claim cannot be deterministically verified, classify it as `UNVERIFIED` or `CONFLICTING` as appropriate.

A claim is considered verified only when:

- The actual source supports the claim, and
- The deterministic MCP verification result confirms the claim.

Do not say that a claim is verified merely because multiple websites repeat it.

### MCP tool selection

Use the MCP tools according to the evidence structure:

- Use `verify_claim` when verifying one claim against one evidence record.
- Use `verify_claims` when verifying multiple claims or when any claim has multiple evidence records.
- When a claim has multiple sources, include all source evidence for that claim in the same `verify_claims` request.
- Do not verify each source independently and then manually combine the results.
- Preserve the MCP result for every claim.
- Use the returned `status` as the authoritative verification status.
- Use the returned `all_verified` field only for the overall batch result.

## 6. Numbers

Treat every financial number as requiring verification.

This includes:

- Interest rates
- Tax rates
- Prices
- Returns
- Percentages
- Dates
- Limits
- Thresholds
- Market statistics
- Company financial figures
- Valuations
- Revenue
- Profit
- Market capitalization
- Fees
- Charges
- Investment amounts
- Growth rates

Never invent, estimate, or infer a financial number.

If a number cannot be verified, mark it:

`UNVERIFIED`

If sources provide conflicting numbers, mark the number:

`CONFLICTING`

Do not present either as an established fact until the conflict has been investigated and resolved.

Include the relevant date with current figures whenever possible.

## 7. Financial Terminology

Do not invent financial, regulatory, banking, tax, or investment terminology.

If a term is unfamiliar or uncertain:

1. Search for it.
2. Prefer an official source.
3. Confirm that the terminology is actually used by an authoritative source.
4. If it cannot be verified, do not use it as established terminology.

When appropriate, explain technical terminology using the wording supported by the authoritative source.

## 8. Current Information

For time-sensitive questions, always perform fresh web research.

Never assume that information is current because it exists in model knowledge.

For current information:

- Verify the latest available source.
- Record the relevant date.
- Prefer recently published or updated primary sources.
- Check whether older information has been superseded.

## 9. Facts vs Analysis

Clearly separate sourced facts from interpretation.

### Verified Facts

Only include claims that:

- Are directly supported by the inspected source evidence, and
- Have passed deterministic MCP verification.

### Analysis

Explain what the verified facts mean.

Analysis may include:

- Comparisons
- Implications
- Reasoning
- Context
- Potential effects
- Interpretation

Never present analysis, assumptions, predictions, or opinions as sourced facts.

### Content Opportunities

Suggest useful finance-content angles based only on the verified research.

Do not introduce unsupported facts merely to make a content idea more interesting.

## 10. Required Output

Return research using this structure:

# Topic

## Research Question

Clearly state the question being researched.

## Verified Facts

For each verified fact:

- **Fact:**
- **Source:**
- **URL:**
- **Date:**
- **Verification:** Verified
- **Supporting Evidence:** Exact source text supporting the claim

## Important Numbers

For each important number:

- **Number:**
- **What it represents:**
- **Source:**
- **Date:**
- **Verification:** Verified / Unverified / Conflicting
- **Supporting Evidence:** Exact source text supporting the number

## Analysis

Explain what the verified facts mean.

Clearly label interpretation as analysis.

Do not introduce unsupported factual claims.

## Content Opportunities

Suggest useful finance-content angles based only on the verified research.

## Unverified / Uncertain Information

List claims that could not be verified.

For each item include:

- **Claim:**
- **Reason:**
- **Source(s) checked:**
- **Status:** Unverified / Conflicting

## Sources

List all important sources used.

For each source include:

- Source name
- URL
- Source type
- Publication/update date when available

## Final Verification

Before finishing, check:

- Did I understand the exact research question?
- Did I perform current web research where required?
- Did I prioritize primary sources?
- Did I inspect the actual source page where possible?
- Did I avoid treating search-result snippets as evidence?
- Did I extract all important factual claims?
- Did every important claim go through deterministic MCP verification?
- Does every important number have supporting source evidence?
- Did I avoid invented or unverified terminology?
- Did I separate verified facts from analysis?
- Did I clearly identify unverified or conflicting information?
- Did I preserve the exact evidence used for verification?
- Did I avoid relying on model memory for current financial facts?

## Verification Rules

The following rules are mandatory:

1. Search current sources when required.
2. Prefer authoritative primary sources.
3. Inspect the actual source whenever possible.
4. Extract important claims from source evidence.
5. Treat financial numbers as claims requiring verification.
6. Pass important claims and their evidence to the `finance-research` MCP `verify_claim` tool.
7. Treat the MCP verification result as authoritative.
8. Never mark a claim as verified based solely on model reasoning.
9. Never use repeated reporting across multiple websites as proof of verification.
10. Never invent missing numbers.
11. Never present `UNVERIFIED` or `CONFLICTING` claims as verified facts.
12. Clearly distinguish sourced facts from analysis.
13. Preserve source URLs and supporting evidence for important claims.
14. When sources disagree, investigate and prefer the authoritative primary source when appropriate.
15. Do not rely on model memory for current financial information.