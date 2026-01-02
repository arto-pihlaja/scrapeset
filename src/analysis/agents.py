"""Agent factory functions for CrewAI analysis."""

import os
from pathlib import Path

import yaml
from crewai import Agent, LLM

from src.config.settings import settings
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
    """Get configured LLM instance for agents."""
    model = settings.default_model
    provider = settings.default_llm_provider.lower()
    
    api_key = settings.openai_api_key
    
    # Map provider to LiteLLM prefix and use correct API key
    if provider == "deepseek" and settings.deepseek_api_key:
        api_key = settings.deepseek_api_key
        if not model.startswith("deepseek/"):
            model = f"deepseek/{model}"
    elif provider == "openrouter" and settings.openrouter_api_key and "your_openrouter" not in settings.openrouter_api_key:
        api_key = settings.openrouter_api_key
        if not model.startswith("openrouter/"):
            model = f"openrouter/{model}"
    elif "gpt-" in model or "text-" in model:
        if not model.startswith("openai/"):
            model = f"openai/{model}"
            
    # Fallback to any available key if we don't have one yet
    if not api_key:
        api_key = settings.deepseek_api_key or settings.openrouter_api_key or settings.openai_api_key or settings.whisper_api_key

    logger.info(f"Using LLM: {model} with provider: {provider}")

    return LLM(
        model=model,
        api_key=api_key,
        temperature=0.2,
    )


def create_fetcher_agent() -> Agent:
    """Create the content fetcher agent with web and YouTube tools."""
    config = load_agent_config()["fetcher"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[YouTubeMetadataTool(), WebContentTool()],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
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
        "fetcher": create_fetcher_agent(),
        "analyzer": create_analyzer_agent(),
        "fallacy_detector": create_fallacy_detector_agent(),
        "summarizer": create_summarizer_agent(),
        "controversy_detector": create_controversy_detector_agent(),
        "counterargument_searcher": create_counterargument_searcher_agent(),
    }
