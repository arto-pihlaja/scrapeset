"""CrewAI crew orchestration for content analysis, modified for ScrapeSET."""

import json
import re
from typing import Any, Callable

from crewai import Crew, Process, Task

from src.utils.logger import get_logger

from .agents import create_all_agents
from .tools import YouTubeMetadataTool, WebContentTool
from .renderer import ReportRenderer, parse_json_output
from .tasks import (
    create_source_assessment_task,
    create_summarize_task,
    create_claims_task,
    create_controversy_task,
    create_fallacies_task,
    create_counterargument_task,
)

logger = get_logger(__name__)


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video."""
    youtube_patterns = [
        r'youtube\.com/watch',
        r'youtu\.be/',
        r'youtube\.com/embed/',
        r'youtube\.com/v/',
    ]
    return any(re.search(pattern, url) for pattern in youtube_patterns)


def fetch_content(url: str) -> dict[str, Any]:
    """Fetch content from URL using appropriate tool."""
    if is_youtube_url(url):
        tool = YouTubeMetadataTool()
        result = tool._run(url)
        # Restructure for consistency
        return {
            "source_type": "youtube",
            "url": url,
            "title": result.get("title"),
            "content": result.get("transcript", ""),
            "content_with_timestamps": result.get("transcript_with_timestamps", ""),
            "metadata": {
                "channel": result.get("channel"),
                "duration": result.get("duration"),
                "description": result.get("description"),
            },
            "error": result.get("error") or result.get("transcript_error"),
        }
    else:
        tool = WebContentTool()
        result = tool._run(url)
        return {
            "source_type": "webpage",
            "url": url,
            "title": result.get("title"),
            "content": result.get("content", ""),
            "metadata": {
                "author": result.get("author"),
                "publish_date": result.get("publish_date"),
            },
            "error": result.get("error"),
        }


# Type alias for progress callback
ProgressCallback = Callable[[str, str, int], None]


class AnalysisCrew:
    """Crew for analyzing content and detecting logical fallacies."""

    def __init__(self):
        """Initialize the crew with all agents."""
        self.agents = create_all_agents()
        self.renderer = ReportRenderer()

    def _run_single_task(
        self,
        agent_name: str,
        task: Task,
    ) -> str:
        """Run a single task with its agent and return the output."""
        crew = Crew(
            agents=[self.agents[agent_name]],
            tasks=[task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()
        return str(result)

    def run_step(
        self,
        step_name: str,
        input_data: dict[str, Any],
        progress_callback: ProgressCallback | None = None
    ) -> dict[str, Any]:
        """Run a specific step of the analysis pipeline.

        Args:
            step_name: The analysis step to run
            input_data: Input data for the step
            progress_callback: Optional callback for progress updates (message, step, progress%)
        """

        def emit(message: str, progress: int):
            """Emit progress update if callback is registered."""
            if progress_callback:
                progress_callback(message, step_name, progress)

        if step_name == "fetch":
            emit("Fetching content from URL...", 10)
            result = fetch_content(input_data["url"])
            emit("Content fetched successfully", 100)
            return result
            
        elif step_name == "summary":
            # Neutral content extraction - no analysis or judgment
            # Returns: summary, main_argument, key_claims
            content_data = input_data["content_data"]
            full_text = content_data.get("content", "")
            if content_data["source_type"] == "youtube":
                full_text = content_data.get("content_with_timestamps", full_text)

            emit("Extracting summary and key claims...", 10)

            summarize_task = create_summarize_task(
                agent=self.agents["summarizer"],
                full_text=full_text,
            )
            summarize_output = self._run_single_task("summarizer", summarize_task)
            logger.debug(f"Raw summarizer output: {summarize_output[:500]}...")
            result = parse_json_output(summarize_output)

            # Check for parse errors
            if "error" in result:
                logger.error(f"Failed to parse summary JSON: {result.get('raw', '')[:500]}")

            # Validate key_claims structure
            key_claims = result.get("key_claims", [])
            if not isinstance(key_claims, list):
                logger.warning(f"key_claims is not a list: {type(key_claims)} - {key_claims}")
                result["key_claims"] = []
            else:
                # Ensure each claim has required fields
                validated_claims = []
                for i, claim in enumerate(key_claims):
                    if isinstance(claim, dict) and "text" in claim:
                        validated_claims.append({
                            "text": claim.get("text", ""),
                            "location": claim.get("location", "")
                        })
                    else:
                        logger.warning(f"Invalid claim at index {i}: {claim}")
                result["key_claims"] = validated_claims

            emit("Summary complete", 100)

            return result

        elif step_name == "source_assessment":
            # Optional step to assess source credibility
            content_data = input_data["content_data"]
            full_text = content_data.get("content", "")
            if content_data["source_type"] == "youtube":
                full_text = content_data.get("content_with_timestamps", full_text)

            emit("Assessing source credibility...", 10)

            content_preview = full_text[:2000] if len(full_text) > 2000 else full_text
            source_task = create_source_assessment_task(
                agent=self.agents["analyzer"],
                title=content_data.get("title", "Unknown"),
                source_type=content_data["source_type"],
                url=content_data.get("url", "N/A"),
                metadata=json.dumps(content_data.get("metadata", {}), indent=2),
                content_preview=content_preview,
            )
            source_output = self._run_single_task("analyzer", source_task)

            emit("Source assessment complete", 100)

            return parse_json_output(source_output)

        elif step_name == "claims":
            # Classify key_claims from summary step
            emit("Classifying claims...", 10)
            summary_data = input_data["summary_data"]
            key_claims = summary_data.get("key_claims", [])
            full_text = input_data["full_text"]

            claims_task = create_claims_task(
                agent=self.agents["analyzer"],
                key_claims=json.dumps(key_claims, indent=2),
                full_text=full_text,
            )
            claims_output = self._run_single_task("analyzer", claims_task)
            emit("Claims classification complete", 100)
            return parse_json_output(claims_output)

        elif step_name == "controversy":
            # Analyze key_claims from summary for controversial content
            emit("Analyzing for controversial content...", 10)
            summary_data = input_data["summary_data"]

            controversy_task = create_controversy_task(
                agent=self.agents["controversy_detector"],
                summary=summary_data.get("summary", ""),
                main_argument=summary_data.get("main_argument", ""),
                key_claims=json.dumps(summary_data.get("key_claims", []), indent=2),
            )
            controversy_output = self._run_single_task("controversy_detector", controversy_task)
            emit("Controversy analysis complete", 100)
            return parse_json_output(controversy_output)

        elif step_name == "fallacies":
            # Detect logical fallacies in key_claims from summary
            emit("Detecting logical fallacies...", 10)
            summary_data = input_data["summary_data"]
            full_text = input_data["full_text"]

            fallacy_task = create_fallacies_task(
                agent=self.agents["fallacy_detector"],
                key_claims=json.dumps(summary_data.get("key_claims", []), indent=2),
                full_text=full_text,
            )
            fallacy_output = self._run_single_task("fallacy_detector", fallacy_task)
            emit("Fallacy detection complete", 100)
            return parse_json_output(fallacy_output)

        elif step_name == "counterargument":
            # Find counterarguments to key_claims from summary
            emit("Searching for counterarguments...", 10)
            summary_data = input_data["summary_data"]

            counter_task = create_counterargument_task(
                agent=self.agents["counterargument_searcher"],
                summary=summary_data.get("summary", ""),
                main_argument=summary_data.get("main_argument", ""),
                key_claims=json.dumps(summary_data.get("key_claims", []), indent=2),
            )
            counter_output = self._run_single_task("counterargument_searcher", counter_task)
            emit("Counterargument search complete", 100)
            return parse_json_output(counter_output)

        return {"error": f"Unknown step: {step_name}"}
