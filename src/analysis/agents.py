"""Agent factory functions for CrewAI analysis."""

from pathlib import Path

import yaml
from crewai import Agent, LLM

from src.config.settings import settings
from src.llm.utils import format_model_name, get_api_key_for_model
from src.utils.logger import get_logger

logger = get_logger(__name__)
# We will use tools from argumentanalyzer ported to src/analysis/tools if needed,
# but for now let's use the core tools if they are available or port them too.
# Actually, VibesiiliCrew in crew.py used YouTubeMetadataTool and WebContentTool.
# YouTubeMetadataTool is in youtube.py.

# Let's port the tools too.
from .tools.youtube import YouTubeMetadataTool, WebContentTool, WebSearchTool


def load_agent_config() -> dict:
    """Load agent configurations from YAML file."""
    config_path = Path(__file__).parent / "config" / "agents.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_llm() -> LLM:
    """Get configured LLM instance for agents.

    Uses shared utilities for model formatting and API key selection,
    ensuring consistent behavior with LLMClient used for chat/RAG.
    """
    model = format_model_name(settings.default_model)
    api_key = get_api_key_for_model(model)

    if not api_key:
        raise ValueError("No valid API key configured. Please set a valid API key in .env")

    logger.info(f"Using LLM: {model}")

    return LLM(
        model=model,
        api_key=api_key,
        temperature=0.2,
    )


def create_analyzer_agent() -> Agent:
    """Create the content analyzer agent."""
    config = load_agent_config()["analyzer"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
    )


def create_fallacy_detector_agent() -> Agent:
    """Create the fallacy detector agent."""
    config = load_agent_config()["fallacy_detector"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
    )


def create_summarizer_agent() -> Agent:
    """Create the summarizer agent."""
    config = load_agent_config()["summarizer"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
    )


def create_counterargument_searcher_agent() -> Agent:
    """Create the counterargument searcher agent with web search tool."""
    config = load_agent_config()["counterargument_searcher"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[WebSearchTool()],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
    )


def create_controversy_detector_agent() -> Agent:
    """Create the controversy/conspiracy detector agent."""
    config = load_agent_config()["controversy_detector"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
    )


def create_all_agents() -> dict[str, Agent]:
    """Create all agents and return them in a dictionary."""
    return {
        "analyzer": create_analyzer_agent(),
        "fallacy_detector": create_fallacy_detector_agent(),
        "summarizer": create_summarizer_agent(),
        "controversy_detector": create_controversy_detector_agent(),
        "counterargument_searcher": create_counterargument_searcher_agent(),
    }
