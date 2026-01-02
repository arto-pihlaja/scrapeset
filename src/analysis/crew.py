"""CrewAI crew orchestration for content analysis, modified for ScrapeSET."""

import json
import re
from typing import Any, Callable

from crewai import Crew, Task, Process

from .agents import create_all_agents
from .tools import YouTubeMetadataTool, WebContentTool
from .renderer import ReportRenderer, parse_json_output


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

    def run_step(self, step_name: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run a specific step of the analysis pipeline."""
        
        if step_name == "fetch":
            return fetch_content(input_data["url"])
            
        elif step_name == "summary":
            # Step 1: Source Assessment + Summarize
            content_data = input_data["content_data"]
            full_text = content_data.get("content", "")
            if content_data["source_type"] == "youtube":
                full_text = content_data.get("content_with_timestamps", full_text)
            
            # Source Assessment
            content_preview = full_text[:2000] if len(full_text) > 2000 else full_text
            source_task = Task(
                description=f"""Assess the credibility of this source:
Title: {content_data.get('title', 'Unknown')}
Type: {content_data['source_type']}
URL: {content_data.get('url', 'N/A')}
Metadata: {json.dumps(content_data.get('metadata', {}), indent=2)}

Content preview:
{content_preview}

Evaluate:
1. Source credibility (high/medium/low/unknown)
2. Reasoning for your assessment
3. Potential biases you can identify

Return as JSON with:
- credibility: "high", "medium", "low", or "unknown"
- reasoning: string explaining your assessment
- potential_biases: array of identified biases""",
                expected_output="JSON object with credibility, reasoning, and potential_biases",
                agent=self.agents["analyzer"],
            )
            source_output = self._run_single_task("analyzer", source_task)
            source_assessment = parse_json_output(source_output)
            
            # Summarize
            summarize_task = Task(
                description=f"""Create a focused summary of this content:
{full_text}

Create:
1. A 2-3 paragraph summary
2. 5-7 key points (with timestamps if video)
3. Main argument
4. Key conclusions

Return as JSON with:
- summary: string
- key_points: array of {{point, location}} (MAX 7)
- main_argument: string
- conclusions: array of strings""",
                expected_output="JSON object with summary, key_points, main_argument, and conclusions",
                agent=self.agents["summarizer"],
            )
            summarize_output = self._run_single_task("summarizer", summarize_task)
            summary = parse_json_output(summarize_output)
            
            return {
                "source_assessment": source_assessment,
                "summary": summary
            }

        elif step_name == "claims":
            summary = input_data["summary_data"]
            claims_task = Task(
                description=f"""Extract 5-7 KEY claims from this summary:
{json.dumps(summary, indent=2)}

For each claim:
- text (concise)
- type: "factual", "opinion", or "prediction"

Also identify 3-5 key entities.

Return as JSON with:
- claims: array of {{text, type}} (MAX 7)
- key_entities: array of strings (MAX 5)
- main_topic: string""",
                expected_output="JSON object with claims, key_entities, and main_topic",
                agent=self.agents["analyzer"],
            )
            claims_output = self._run_single_task("analyzer", claims_task)
            return parse_json_output(claims_output)

        elif step_name == "controversy":
            summary = input_data["summary_data"]
            claims = input_data["claims_data"]
            content = input_data.get("full_text", "")[:3000]
            
            controversy_task = Task(
                description=f"""Analyze for controversial views and conspiracy patterns:
Summary: {json.dumps(summary)}
Claims: {json.dumps(claims)}
Context: {content}

Return as JSON with:
- controversial_views: array of {{target, sentiment, claim_text, reasoning}}
- conspiracy_indicators: array of {{pattern, severity, evidence, quote}}
- overall_assessment: {{controversy_level, summary}}""",
                expected_output="JSON object with controversial_views, conspiracy_indicators, and overall_assessment",
                agent=self.agents["controversy_detector"],
            )
            controversy_output = self._run_single_task("controversy_detector", controversy_task)
            return parse_json_output(controversy_output)

        elif step_name == "fallacies":
            claims = input_data["claims_data"]
            full_text = input_data["full_text"]
            
            fallacy_task = Task(
                description=f"""Analyze these claims for logical fallacies:
Claims: {json.dumps(claims)}
Text: {full_text}

For each ACTUAL fallacy:
- type, quote, location, explanation

Return as JSON with:
- fallacies: array of {{type, quote, location, explanation}}
- overall_reasoning_quality: "strong", "moderate", or "weak" """,
                expected_output="JSON object with fallacies array and overall_reasoning_quality",
                agent=self.agents["fallacy_detector"],
            )
            fallacy_output = self._run_single_task("fallacy_detector", fallacy_task)
            return parse_json_output(fallacy_output)

        elif step_name == "counterargument":
            claims = input_data["claims_data"]
            summary = input_data["summary_data"]
            
            counter_task = Task(
                description=f"""Find counterarguments to these claims:
Claims: {json.dumps(claims)}
Summary: {json.dumps(summary)}

Use web_search tool to find real sources.

Return as JSON with:
- selected_claims: array
- counterargument: string (~100 words)
- sources: array of {{title, url}}""",
                expected_output="JSON object with selected_claims, counterargument, and sources",
                agent=self.agents["counterargument_searcher"],
            )
            counter_output = self._run_single_task("counterargument_searcher", counter_task)
            return parse_json_output(counter_output)

        return {"error": f"Unknown step: {step_name}"}
