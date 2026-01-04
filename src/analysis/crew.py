"""CrewAI crew orchestration for content analysis, modified for ScrapeSET."""

import json
import re
from typing import Any, Callable

from crewai import Crew, Process, Task

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
            # Step 1: Source Assessment + Summarize
            content_data = input_data["content_data"]
            full_text = content_data.get("content", "")
            if content_data["source_type"] == "youtube":
                full_text = content_data.get("content_with_timestamps", full_text)

            emit("Assessing source credibility...", 10)

            # Source Assessment
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
            source_assessment = parse_json_output(source_output)

            emit("Source assessment complete. Generating summary...", 50)

            # Summarize
            summarize_task = create_summarize_task(
                agent=self.agents["summarizer"],
                full_text=full_text,
            )
            summarize_output = self._run_single_task("summarizer", summarize_task)
            summary = parse_json_output(summarize_output)

            emit("Summary complete", 100)

            return {
                "source_assessment": source_assessment,
                "summary": summary
            }

        elif step_name == "claims":
            emit("Extracting and classifying claims...", 10)
            summary = input_data["summary_data"]
            claims_task = create_claims_task(
                agent=self.agents["analyzer"],
                summary=json.dumps(summary, indent=2),
            )
            claims_output = self._run_single_task("analyzer", claims_task)
            emit("Claims extraction complete", 100)
            return parse_json_output(claims_output)

        elif step_name == "controversy":
            emit("Analyzing for controversial content...", 10)
            summary = input_data["summary_data"]
            claims = input_data["claims_data"]
            content = input_data.get("full_text", "")[:3000]

            controversy_task = create_controversy_task(
                agent=self.agents["controversy_detector"],
                summary=json.dumps(summary),
                claims=json.dumps(claims),
                content=content,
            )
            controversy_output = self._run_single_task("controversy_detector", controversy_task)
            emit("Controversy analysis complete", 100)
            return parse_json_output(controversy_output)

        elif step_name == "fallacies":
            emit("Detecting logical fallacies...", 10)
            claims = input_data["claims_data"]
            full_text = input_data["full_text"]

            fallacy_task = create_fallacies_task(
                agent=self.agents["fallacy_detector"],
                claims=json.dumps(claims),
                full_text=full_text,
            )
            fallacy_output = self._run_single_task("fallacy_detector", fallacy_task)
            emit("Fallacy detection complete", 100)
            return parse_json_output(fallacy_output)

        elif step_name == "counterargument":
            emit("Searching for counterarguments...", 10)
            claims = input_data["claims_data"]
            summary = input_data["summary_data"]

            counter_task = create_counterargument_task(
                agent=self.agents["counterargument_searcher"],
                claims=json.dumps(claims),
                summary=json.dumps(summary),
            )
            counter_output = self._run_single_task("counterargument_searcher", counter_task)
            emit("Counterargument search complete", 100)
            return parse_json_output(counter_output)

        return {"error": f"Unknown step: {step_name}"}
