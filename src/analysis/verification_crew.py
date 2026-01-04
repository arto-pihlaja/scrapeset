"""CrewAI crew orchestration for claim verification pipeline."""

import re
from typing import Any, Callable, Optional

from crewai import Crew, Process

from src.config.settings import settings
from src.storage.verification import VerificationStore, Evidence
from src.utils.logger import get_logger
from .renderer import parse_json_output
from .verification_agents import create_all_verification_agents
from .verification_tasks import (
    create_web_search_task,
    create_evidence_analysis_task,
    create_credibility_assessment_task,
    create_conclusion_synthesis_task,
)

logger = get_logger(__name__)


class VerificationConfigError(Exception):
    """Raised when verification cannot proceed due to configuration issues."""
    pass


class HallucinatedEvidenceError(Exception):
    """Raised when evidence appears to be fabricated by the LLM."""
    pass


# Patterns that indicate fabricated URLs
FAKE_URL_PATTERNS = [
    r'/[a-f0-9]{12,}$',           # URLs ending in long hex strings like /abc123def456
    r'/article/\d+$',              # Generic /article/123 patterns
    r'/content/[a-z0-9]+$',        # Generic /content/xyz patterns without real slugs
    r'example\.com',               # Example domain
    r'placeholder',                # Placeholder in URL
    r'/fake/',                     # Obvious fake
    r'/test/',                     # Test URLs
]

# Type alias for progress callback: (message, step_name, progress_percent)
ProgressCallback = Callable[[str, str, int], None]


def validate_tavily_api_key() -> None:
    """Validate that Tavily API key is configured.

    Raises:
        VerificationConfigError: If API key is not configured
    """
    if not settings.tavily_api_key:
        raise VerificationConfigError(
            "TAVILY_API_KEY is not configured. "
            "Please set it in your .env file to enable claim verification. "
            "Get your API key at https://tavily.com"
        )


def is_url_likely_fabricated(url: str) -> bool:
    """Check if a URL appears to be fabricated by an LLM.

    Args:
        url: The URL to check

    Returns:
        True if the URL appears fabricated, False otherwise
    """
    if not url:
        return True

    for pattern in FAKE_URL_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            logger.warning(f"URL appears fabricated (matches pattern '{pattern}'): {url}")
            return True

    return False


def validate_evidence_urls(evidence_list: list[dict], source: str = "unknown") -> None:
    """Validate that evidence URLs are not obviously fabricated.

    Args:
        evidence_list: List of evidence dictionaries with source_url field
        source: Description of where this evidence came from (for logging)

    Raises:
        HallucinatedEvidenceError: If URLs appear to be fabricated
    """
    fabricated_urls = []

    for item in evidence_list:
        url = item.get("source_url", "") or item.get("url", "")
        if is_url_likely_fabricated(url):
            fabricated_urls.append(url)

    if fabricated_urls:
        raise HallucinatedEvidenceError(
            f"Evidence from {source} contains URLs that appear to be fabricated by the AI. "
            f"This usually means the web search failed silently. "
            f"Fabricated URLs detected: {fabricated_urls[:3]}{'...' if len(fabricated_urls) > 3 else ''}"
        )


class VerificationCrew:
    """Crew for verifying claims through web search and analysis."""

    def __init__(self, store: Optional[VerificationStore] = None):
        """Initialize the verification crew.

        Args:
            store: Optional VerificationStore for persisting results.
                   If not provided, a new store will be created.
        """
        self.agents = create_all_verification_agents()
        self.store = store or VerificationStore()

    def _run_single_task(self, agent_name: str, task) -> str:
        """Run a single task with its agent and return the output."""
        crew = Crew(
            agents=[self.agents[agent_name]],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()
        return str(result)

    def run(
        self,
        verification_id: str,
        claim_text: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> dict[str, Any]:
        """Run the complete verification pipeline.

        Sequential pipeline:
        1. WebSearchAgent - Search for evidence using Tavily
        2. EvidenceAnalyzerAgent - Categorize evidence as for/against
        3. CredibilityAssessorAgent - Score source credibility
        4. ConclusionSynthesizerAgent - Generate final verdict

        Args:
            verification_id: The ID of the verification record to update
            claim_text: The claim to verify
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with verification results or error
        """
        def emit(message: str, step: str, progress: int):
            """Emit progress update if callback is registered."""
            if progress_callback:
                progress_callback(message, step, progress)

        # Update status to in_progress
        self.store.update_status(verification_id, "in_progress")

        current_step = "starting"
        try:
            # PRE-FLIGHT VALIDATION: Check API key before starting
            emit("Validating configuration...", "starting", 5)
            try:
                validate_tavily_api_key()
            except VerificationConfigError as e:
                raise ValueError(f"[configuration] {str(e)}")

            # Step 1: Web Search
            current_step = "searching"
            emit("Searching the web for evidence...", "searching", 10)
            logger.info(f"Starting web search for claim: {claim_text[:50]}...")

            search_task = create_web_search_task(
                self.agents["web_search"],
                claim_text
            )
            search_output = self._run_single_task("web_search", search_task)
            search_results = parse_json_output(search_output)

            if "error" in search_results and not search_results.get("results"):
                error_msg = search_results.get('error', 'Unknown error')
                # Provide user-friendly error messages
                if "TAVILY_API_KEY" in error_msg or "not configured" in error_msg:
                    raise ValueError("[searching] Tavily API key not configured. Please set TAVILY_API_KEY in your .env file.")
                elif "not installed" in error_msg:
                    raise ValueError("[searching] Tavily package not installed. Please run: pip install tavily-python")
                else:
                    raise ValueError(f"[searching] Web search failed: {error_msg}")

            # CRITICAL: Validate search results are not hallucinated
            results_list = search_results.get("results", [])
            if not results_list:
                raise ValueError("[searching] Web search returned no results. Cannot verify claim without evidence.")

            try:
                validate_evidence_urls(results_list, source="web search")
            except HallucinatedEvidenceError as e:
                raise ValueError(f"[searching] {str(e)}")

            emit("Search complete. Analyzing evidence...", "searching", 25)
            logger.info(f"Found {len(results_list)} search results")

            # Step 2: Evidence Analysis
            current_step = "analyzing"
            emit("Categorizing evidence for and against the claim...", "analyzing", 30)

            analysis_task = create_evidence_analysis_task(
                self.agents["evidence_analyzer"],
                claim_text,
                search_results
            )
            analysis_output = self._run_single_task("evidence_analyzer", analysis_task)
            categorized_evidence = parse_json_output(analysis_output)

            # Validate categorized evidence URLs
            evidence_for_list = categorized_evidence.get('evidence_for', [])
            evidence_against_list = categorized_evidence.get('evidence_against', [])

            try:
                if evidence_for_list:
                    validate_evidence_urls(evidence_for_list, source="evidence analysis (supporting)")
                if evidence_against_list:
                    validate_evidence_urls(evidence_against_list, source="evidence analysis (opposing)")
            except HallucinatedEvidenceError as e:
                raise ValueError(f"[analyzing] {str(e)}")

            emit("Evidence categorized. Assessing source credibility...", "analyzing", 50)
            logger.info(
                f"Categorized evidence: {len(evidence_for_list)} for, "
                f"{len(evidence_against_list)} against"
            )

            # Step 3: Credibility Assessment
            current_step = "assessing"
            emit("Evaluating source credibility...", "assessing", 55)

            credibility_task = create_credibility_assessment_task(
                self.agents["credibility_assessor"],
                categorized_evidence
            )
            credibility_output = self._run_single_task("credibility_assessor", credibility_task)
            scored_evidence = parse_json_output(credibility_output)

            emit("Credibility assessed. Synthesizing conclusion...", "assessing", 75)
            logger.info("Credibility assessment complete")

            # Step 4: Conclusion Synthesis
            current_step = "concluding"
            emit("Generating final conclusion...", "concluding", 80)

            conclusion_task = create_conclusion_synthesis_task(
                self.agents["conclusion_synthesizer"],
                claim_text,
                scored_evidence
            )
            conclusion_output = self._run_single_task("conclusion_synthesizer", conclusion_task)
            conclusion_data = parse_json_output(conclusion_output)

            emit("Conclusion generated. Saving results...", "concluding", 95)
            logger.info(f"Conclusion: {conclusion_data.get('conclusion_type', 'unknown')}")

            # Build Evidence objects for storage
            evidence_for = self._build_evidence_list(scored_evidence.get("evidence_for", []))
            evidence_against = self._build_evidence_list(scored_evidence.get("evidence_against", []))

            # Save results to database
            conclusion_text = conclusion_data.get("conclusion", "")
            conclusion_type = conclusion_data.get("conclusion_type", "inconclusive")

            # Normalize conclusion_type
            if conclusion_type not in ["supported", "refuted", "inconclusive"]:
                conclusion_type = "inconclusive"

            self.store.save_results(
                verification_id=verification_id,
                evidence_for=evidence_for,
                evidence_against=evidence_against,
                conclusion=conclusion_text,
                conclusion_type=conclusion_type
            )

            emit("Verification complete!", "complete", 100)
            logger.info(f"Verification {verification_id} completed successfully")

            # Return full result
            return {
                "success": True,
                "verification_id": verification_id,
                "claim_text": claim_text,
                "evidence_for": [e.__dict__ for e in evidence_for],
                "evidence_against": [e.__dict__ for e in evidence_against],
                "conclusion": conclusion_text,
                "conclusion_type": conclusion_type,
                "confidence_notes": conclusion_data.get("confidence_notes", ""),
            }

        except Exception as e:
            error_message = str(e)

            # Add step information if not already present
            if not error_message.startswith("["):
                error_message = f"[{current_step}] {error_message}"

            logger.error(f"Verification {verification_id} failed at step '{current_step}': {error_message}")

            # Update status to failed
            self.store.update_status(verification_id, "failed", error_message)

            emit(f"Verification failed: {error_message}", "error", 0)

            return {
                "success": False,
                "verification_id": verification_id,
                "error": error_message,
                "failed_step": current_step,
            }

    def _build_evidence_list(self, evidence_data: list[dict]) -> list[Evidence]:
        """Convert raw evidence dicts to Evidence objects.

        Args:
            evidence_data: List of evidence dictionaries from agent output

        Returns:
            List of Evidence objects
        """
        evidence_list = []
        for item in evidence_data:
            try:
                evidence = Evidence(
                    source_url=item.get("source_url", ""),
                    source_title=item.get("source_title", ""),
                    snippet=item.get("snippet", ""),
                    credibility_score=item.get("credibility_score"),
                    credibility_reasoning=item.get("credibility_reasoning"),
                )
                evidence_list.append(evidence)
            except Exception as e:
                logger.warning(f"Failed to parse evidence item: {e}")
                continue
        return evidence_list


def run_verification(
    verification_id: str,
    claim_text: str,
    progress_callback: Optional[ProgressCallback] = None
) -> dict[str, Any]:
    """Convenience function to run a verification.

    Args:
        verification_id: The verification record ID
        claim_text: The claim to verify
        progress_callback: Optional progress callback

    Returns:
        Verification result dict
    """
    crew = VerificationCrew()
    return crew.run(verification_id, claim_text, progress_callback)
