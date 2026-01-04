"""Task factory functions for claim verification pipeline."""

import json
from typing import Any

from crewai import Task, Agent


def create_web_search_task(agent: Agent, claim_text: str) -> Task:
    """Create task to search the web for evidence about a claim.

    Args:
        agent: The web search agent with Tavily tool
        claim_text: The claim to search for

    Returns:
        Task configured for web search
    """
    return Task(
        description=f"""Search the web for evidence related to this claim:

CLAIM: "{claim_text}"

Use the tavily_search tool to find relevant sources. Search for:
1. Direct evidence supporting the claim
2. Direct evidence refuting the claim
3. Related factual information

Return the search results as JSON with:
- query: the search query you used
- results: array of search results, each with:
  - url: source URL
  - title: page title
  - snippet: relevant text excerpt
  - score: relevance score from search API

Return raw results without interpreting whether they support or refute the claim.""",
        expected_output="JSON object with query and results array containing url, title, snippet, score for each result",
        agent=agent,
    )


def create_evidence_analysis_task(
    agent: Agent,
    claim_text: str,
    search_results: dict[str, Any]
) -> Task:
    """Create task to categorize evidence as for or against the claim.

    Args:
        agent: The evidence analyzer agent
        claim_text: The original claim
        search_results: Raw search results from web search

    Returns:
        Task configured for evidence categorization
    """
    return Task(
        description=f"""Analyze these search results and categorize them as evidence FOR or AGAINST this claim:

CLAIM: "{claim_text}"

SEARCH RESULTS:
{json.dumps(search_results, indent=2)}

For each search result, determine:
1. Does it support the claim (evidence_for)?
2. Does it contradict the claim (evidence_against)?
3. Extract the specific text snippet that serves as evidence

Handle ambiguous evidence by:
- If mixed, include in the most relevant category with explanation
- If truly neutral/irrelevant, you may exclude it

Return as JSON with:
- evidence_for: array of {{source_url, source_title, snippet, reasoning}}
- evidence_against: array of {{source_url, source_title, snippet, reasoning}}
- analysis_notes: brief notes on any ambiguous evidence""",
        expected_output="JSON object with evidence_for and evidence_against arrays, plus analysis_notes",
        agent=agent,
    )


def create_credibility_assessment_task(
    agent: Agent,
    evidence: dict[str, Any]
) -> Task:
    """Create task to assess credibility of evidence sources.

    Args:
        agent: The credibility assessor agent
        evidence: Categorized evidence from analyzer

    Returns:
        Task configured for credibility assessment
    """
    return Task(
        description=f"""Assess the credibility of each source in this evidence:

EVIDENCE:
{json.dumps(evidence, indent=2)}

For each source (both evidence_for and evidence_against), evaluate:
1. Domain reputation (academic, news, government, blog, unknown)
2. Apparent expertise of author/publication
3. Presence of citations or references
4. Balanced vs biased language
5. Overall trustworthiness

Assign a credibility score from 1-10:
- 9-10: Highly credible (academic, major news, government)
- 7-8: Generally credible (established publications)
- 5-6: Moderately credible (mixed signals)
- 3-4: Low credibility (clear bias, no citations)
- 1-2: Not credible (known misinformation sources)

Return as JSON with:
- evidence_for: array of {{source_url, source_title, snippet, credibility_score, credibility_reasoning}}
- evidence_against: array of {{source_url, source_title, snippet, credibility_score, credibility_reasoning}}""",
        expected_output="JSON object with evidence_for and evidence_against arrays, each item including credibility_score and credibility_reasoning",
        agent=agent,
    )


def create_conclusion_synthesis_task(
    agent: Agent,
    claim_text: str,
    scored_evidence: dict[str, Any]
) -> Task:
    """Create task to synthesize a final conclusion about the claim.

    Args:
        agent: The conclusion synthesizer agent
        claim_text: The original claim
        scored_evidence: Evidence with credibility scores

    Returns:
        Task configured for conclusion synthesis
    """
    return Task(
        description=f"""Synthesize a final conclusion about this claim based on the evidence:

CLAIM: "{claim_text}"

EVIDENCE WITH CREDIBILITY SCORES:
{json.dumps(scored_evidence, indent=2)}

Consider:
1. Weight evidence by credibility score (high-credibility sources matter more)
2. Compare quantity and quality of evidence for vs against
3. Acknowledge any limitations or gaps in the evidence

Classify your conclusion as:
- "supported": Strong evidence supports the claim, minimal credible contradicting evidence
- "refuted": Strong evidence contradicts the claim, minimal credible supporting evidence
- "inconclusive": Mixed evidence, insufficient evidence, or credibility concerns prevent a clear verdict

Return as JSON with:
- conclusion: A 2-4 sentence summary of your verdict explaining the reasoning
- conclusion_type: "supported", "refuted", or "inconclusive"
- confidence_notes: Any caveats or limitations of this conclusion""",
        expected_output="JSON object with conclusion text, conclusion_type (supported/refuted/inconclusive), and confidence_notes",
        agent=agent,
    )
