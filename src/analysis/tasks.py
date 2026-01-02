"""Task factory functions for CrewAI analysis."""

from pathlib import Path

import yaml
from crewai import Task, Agent


def load_task_config() -> dict:
    """Load task configurations from YAML file."""
    config_path = Path(__file__).parent / "config" / "tasks.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def create_fetch_task(agent: Agent, url: str) -> Task:
    """Create task to fetch content from URL."""
    config = load_task_config()["fetch_content"]
    return Task(
        description=config["description"].format(url=url),
        expected_output=config["expected_output"],
        agent=agent,
    )


def create_analyze_task(agent: Agent, content: str, context: list[Task] | None = None) -> Task:
    """Create task to analyze content."""
    config = load_task_config()["analyze_content"]
    return Task(
        description=config["description"].format(content=content),
        expected_output=config["expected_output"],
        agent=agent,
        context=context or [],
    )


def create_fallacy_detection_task(
    agent: Agent, claims: str, content: str, context: list[Task] | None = None
) -> Task:
    """Create task to detect logical fallacies."""
    config = load_task_config()["detect_fallacies"]
    return Task(
        description=config["description"].format(claims=claims, content=content),
        expected_output=config["expected_output"],
        agent=agent,
        context=context or [],
    )


def create_summarize_task(
    agent: Agent, content: str, analysis: str, context: list[Task] | None = None
) -> Task:
    """Create task to summarize content."""
    config = load_task_config()["summarize_content"]
    return Task(
        description=config["description"].format(content=content, analysis=analysis),
        expected_output=config["expected_output"],
        agent=agent,
        context=context or [],
    )
