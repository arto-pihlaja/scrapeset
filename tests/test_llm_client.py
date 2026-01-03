import pytest
from unittest.mock import MagicMock, patch
from src.llm.utils import format_model_name
from src.config.settings import Settings

@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.default_llm_provider = "openai"
    settings.default_model = "gpt-3.5-turbo"
    settings.openai_api_key = "sk-..."
    settings.anthropic_api_key = None
    settings.openrouter_api_key = None
    settings.deepseek_api_key = None
    settings.llm_api_base = None
    settings.llm_api_key = None
    return settings

def test_format_model_name_default_openai(mock_settings):
    with patch("src.llm.utils.settings", mock_settings):
        assert format_model_name("gpt-4") == "openai/gpt-4"

def test_format_model_name_explicit_deepseek(mock_settings):
    mock_settings.default_llm_provider = "deepseek"
    with patch("src.llm.utils.settings", mock_settings):
        assert format_model_name("deepseek-chat") == "deepseek/deepseek-chat"

def test_format_model_name_explicit_openrouter(mock_settings):
    mock_settings.default_llm_provider = "openrouter"
    with patch("src.llm.utils.settings", mock_settings):
        assert format_model_name("openai/gpt-4o") == "openai/gpt-4o"  # Stays as is
        assert format_model_name("gpt-4o") == "openrouter/gpt-4o"

def test_format_model_name_auto_detect_anthropic(mock_settings):
    mock_settings.anthropic_api_key = "sk-ant-..."
    with patch("src.llm.utils.settings", mock_settings):
        assert format_model_name("claude-3-opus") == "anthropic/claude-3-opus"

def test_format_model_name_generic_api_base(mock_settings):
    mock_settings.llm_api_base = "https://my-local-ai.com"
    with patch("src.llm.utils.settings", mock_settings):
        assert format_model_name("my-model") == "openai/my-model"
