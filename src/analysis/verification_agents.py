"""Agent factory functions for claim verification pipeline."""

from pathlib import Path

import yaml
from crewai import Agent

from src.utils.logger import get_logger
from .agents import get_llm
from .tools.tavily import TavilySearchTool

logger = get_logger(__name__)


def load_verification_agent_config() -> dict:
    """Load verification agent configurations from YAML file."""
    config_path = Path(__file__).parent / "config" / "verification_agents.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def create_web_search_agent() -> Agent:
    """Create the web search agent with Tavily tool.

    This agent performs web searches using Tavily API to find
    evidence related to a claim.
    """
    config = load_verification_agent_config()["web_search_agent"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[TavilySearchTool()],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
    )


def create_evidence_analyzer_agent() -> Agent:
    """Create the evidence analyzer agent.

    This agent categorizes search results as evidence for or against
    the claim and extracts relevant snippets.
    """
    config = load_verification_agent_config()["evidence_analyzer_agent"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
    )


def create_credibility_assessor_agent() -> Agent:
    """Create the credibility assessor agent.

    This agent evaluates the credibility of each source and
    assigns a score from 1-10 with reasoning.
    """
    config = load_verification_agent_config()["credibility_assessor_agent"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
    )


def create_conclusion_synthesizer_agent() -> Agent:
    """Create the conclusion synthesizer agent.

    This agent synthesizes all evidence into a final verdict:
    supported, refuted, or inconclusive.
    """
    config = load_verification_agent_config()["conclusion_synthesizer_agent"]
    return Agent(
        role=config["role"],
        goal=config["goal"],
        backstory=config["backstory"],
        tools=[],
        llm=get_llm(),
        verbose=config.get("verbose", True),
        allow_delegation=config.get("allow_delegation", False),
    )


def create_all_verification_agents() -> dict[str, Agent]:
    """Create all verification agents and return them in a dictionary."""
    return {
        "web_search": create_web_search_agent(),
        "evidence_analyzer": create_evidence_analyzer_agent(),
        "credibility_assessor": create_credibility_assessor_agent(),
        "conclusion_synthesizer": create_conclusion_synthesizer_agent(),
    }
