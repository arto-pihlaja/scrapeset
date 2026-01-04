"""Task factory functions for CrewAI analysis."""

from pathlib import Path

import yaml
from crewai import Task, Agent


_task_config: dict | None = None


def load_task_config() -> dict:
    """Load task configurations from YAML file (cached)."""
    global _task_config
    if _task_config is None:
        config_path = Path(__file__).parent / "config" / "tasks.yaml"
        with open(config_path) as f:
            _task_config = yaml.safe_load(f)
    return _task_config


def create_summarize_task(agent: Agent, full_text: str) -> Task:
    """Create task to extract summary, main argument, and key claims (neutral, no analysis)."""
    config = load_task_config()["summarize"]
    return Task(
        description=config["description"].format(full_text=full_text),
        expected_output=config["expected_output"],
        agent=agent,
    )


def create_source_assessment_task(
    agent: Agent,
    title: str,
    source_type: str,
    url: str,
    metadata: str,
    content_preview: str,
) -> Task:
    """Create task to assess source credibility."""
    config = load_task_config()["source_assessment"]
    return Task(
        description=config["description"].format(
            title=title,
            source_type=source_type,
            url=url,
            metadata=metadata,
            content_preview=content_preview,
        ),
        expected_output=config["expected_output"],
        agent=agent,
    )


def create_claims_task(agent: Agent, key_claims: str, full_text: str) -> Task:
    """Create task to classify key claims from summary."""
    config = load_task_config()["claims"]
    return Task(
        description=config["description"].format(
            key_claims=key_claims,
            full_text=full_text,
        ),
        expected_output=config["expected_output"],
        agent=agent,
    )


def create_controversy_task(
    agent: Agent,
    summary: str,
    main_argument: str,
    key_claims: str,
) -> Task:
    """Create task to detect controversial content and conspiracy patterns."""
    config = load_task_config()["controversy"]
    return Task(
        description=config["description"].format(
            summary=summary,
            main_argument=main_argument,
            key_claims=key_claims,
        ),
        expected_output=config["expected_output"],
        agent=agent,
    )


def create_fallacies_task(agent: Agent, key_claims: str, full_text: str) -> Task:
    """Create task to detect logical fallacies in claims."""
    config = load_task_config()["fallacies"]
    return Task(
        description=config["description"].format(
            key_claims=key_claims,
            full_text=full_text,
        ),
        expected_output=config["expected_output"],
        agent=agent,
    )


def create_counterargument_task(
    agent: Agent,
    summary: str,
    main_argument: str,
    key_claims: str,
) -> Task:
    """Create task to find counterarguments to key claims."""
    config = load_task_config()["counterargument"]
    return Task(
        description=config["description"].format(
            summary=summary,
            main_argument=main_argument,
            key_claims=key_claims,
        ),
        expected_output=config["expected_output"],
        agent=agent,
    )
