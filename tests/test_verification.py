"""Tests for claim verification infrastructure."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTavilySearchTool:
    """Tests for TavilySearchTool."""

    def test_tavily_tool_without_api_key(self):
        """Test that tool raises error when API key is not configured."""
        from src.analysis.tools.tavily import TavilySearchTool

        with patch('src.analysis.tools.tavily.settings') as mock_settings:
            mock_settings.tavily_api_key = None
            tool = TavilySearchTool()

            with pytest.raises(RuntimeError) as exc_info:
                tool._run("test query")

            assert "TAVILY_API_KEY is not configured" in str(exc_info.value)

    def test_tavily_tool_with_mock_client(self):
        """Test Tavily tool with mocked API response."""
        from src.analysis.tools.tavily import TavilySearchTool

        mock_response = {
            "results": [
                {
                    "url": "https://example.com/article1",
                    "title": "Test Article",
                    "content": "This is a test snippet about the claim.",
                    "score": 0.95,
                },
                {
                    "url": "https://example.com/article2",
                    "title": "Another Article",
                    "content": "More evidence about the topic.",
                    "score": 0.85,
                },
            ]
        }

        with patch('src.analysis.tools.tavily.settings') as mock_settings:
            mock_settings.tavily_api_key = "test-api-key"

            # Mock the tavily module import inside the function
            with patch.dict('sys.modules', {'tavily': Mock()}):
                import sys
                mock_tavily = sys.modules['tavily']
                mock_client = Mock()
                mock_client.search.return_value = mock_response
                mock_tavily.TavilyClient.return_value = mock_client

                tool = TavilySearchTool()
                result = tool._run("vaccines cause autism")

                assert result["success"] is True
                assert result["error"] is None
                assert len(result["results"]) == 2
                assert result["results"][0]["title"] == "Test Article"
                assert result["results"][0]["url"] == "https://example.com/article1"

    def test_search_for_claim_function(self):
        """Test the convenience function raises on missing API key."""
        from src.analysis.tools.tavily import search_for_claim

        with patch('src.analysis.tools.tavily.settings') as mock_settings:
            mock_settings.tavily_api_key = None

            with pytest.raises(RuntimeError) as exc_info:
                search_for_claim("test claim")

            assert "TAVILY_API_KEY" in str(exc_info.value)


class TestVerificationStore:
    """Tests for VerificationStore."""

    def test_create_and_retrieve_verification(self, tmp_path):
        """Test creating and retrieving a verification."""
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        # Create verification
        verification = store.create_verification(
            claim_text="The sky is blue",
            source_url="https://example.com/article",
            claim_id="claim-123"
        )

        assert verification.id is not None
        assert verification.claim_text == "The sky is blue"
        assert verification.source_url == "https://example.com/article"
        assert verification.status == "pending"
        assert verification.claim_id == "claim-123"

        # Retrieve verification
        retrieved = store.get_verification(verification.id)
        assert retrieved is not None
        assert retrieved.claim_text == "The sky is blue"
        assert retrieved.status == "pending"

    def test_update_status(self, tmp_path):
        """Test updating verification status."""
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        verification = store.create_verification(
            claim_text="Test claim",
            source_url="https://example.com"
        )

        # Update to in_progress
        success = store.update_status(verification.id, "in_progress")
        assert success is True

        retrieved = store.get_verification(verification.id)
        assert retrieved.status == "in_progress"

        # Update to failed with error
        success = store.update_status(
            verification.id,
            "failed",
            error_message="API timeout"
        )
        assert success is True

        retrieved = store.get_verification(verification.id)
        assert retrieved.status == "failed"
        assert retrieved.error_message == "API timeout"

    def test_save_results(self, tmp_path):
        """Test saving verification results."""
        from src.storage.verification import VerificationStore, Evidence

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        verification = store.create_verification(
            claim_text="Test claim",
            source_url="https://example.com"
        )

        evidence_for = [
            Evidence(
                source_url="https://source1.com",
                source_title="Supporting Source",
                snippet="This supports the claim.",
                credibility_score=8.5,
                credibility_reasoning="Peer-reviewed journal"
            )
        ]

        evidence_against = [
            Evidence(
                source_url="https://source2.com",
                source_title="Opposing Source",
                snippet="This contradicts the claim.",
                credibility_score=7.0,
                credibility_reasoning="News article"
            )
        ]

        success = store.save_results(
            verification_id=verification.id,
            evidence_for=evidence_for,
            evidence_against=evidence_against,
            conclusion="The claim is partially supported.",
            conclusion_type="inconclusive"
        )

        assert success is True

        retrieved = store.get_verification(verification.id)
        assert retrieved.status == "completed"
        assert retrieved.conclusion_type == "inconclusive"
        assert len(retrieved.evidence_for) == 1
        assert len(retrieved.evidence_against) == 1
        assert retrieved.evidence_for[0].source_title == "Supporting Source"
        assert retrieved.completed_at is not None

    def test_list_verifications(self, tmp_path):
        """Test listing verifications."""
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        # Create multiple verifications
        store.create_verification("Claim 1", "https://example.com/1")
        store.create_verification("Claim 2", "https://example.com/1")
        store.create_verification("Claim 3", "https://example.com/2")

        # List all
        all_verifications = store.list_verifications()
        assert len(all_verifications) == 3

        # List by source URL
        filtered = store.list_verifications(source_url="https://example.com/1")
        assert len(filtered) == 2

    def test_delete_verification(self, tmp_path):
        """Test deleting a verification."""
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        verification = store.create_verification(
            claim_text="Test claim",
            source_url="https://example.com"
        )

        # Delete
        success = store.delete_verification(verification.id)
        assert success is True

        # Verify deleted
        retrieved = store.get_verification(verification.id)
        assert retrieved is None

    def test_verification_to_dict(self, tmp_path):
        """Test ClaimVerification.to_dict() method."""
        from src.storage.verification import VerificationStore, Evidence

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        verification = store.create_verification(
            claim_text="Test claim",
            source_url="https://example.com"
        )

        evidence_for = [
            Evidence(
                source_url="https://source.com",
                source_title="Source",
                snippet="Snippet"
            )
        ]

        store.save_results(
            verification_id=verification.id,
            evidence_for=evidence_for,
            evidence_against=[],
            conclusion="Supported",
            conclusion_type="supported"
        )

        retrieved = store.get_verification(verification.id)
        result_dict = retrieved.to_dict()

        assert result_dict["id"] == verification.id
        assert result_dict["claim_text"] == "Test claim"
        assert result_dict["status"] == "completed"
        assert len(result_dict["evidence_for"]) == 1
        assert result_dict["evidence_for"][0]["source_url"] == "https://source.com"

    def test_get_verification_by_claim(self, tmp_path):
        """Test getting verification by claim_id or claim_text+source_url."""
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        # Create verifications
        v1 = store.create_verification(
            claim_text="The sky is blue",
            source_url="https://example.com/article",
            claim_id="claim-001"
        )
        v2 = store.create_verification(
            claim_text="Water is wet",
            source_url="https://example.com/article2",
            claim_id="claim-002"
        )

        # Get by claim_id
        result = store.get_verification_by_claim(claim_id="claim-001")
        assert result is not None
        assert result.id == v1.id
        assert result.claim_text == "The sky is blue"

        # Get by claim_text + source_url
        result = store.get_verification_by_claim(
            claim_text="Water is wet",
            source_url="https://example.com/article2"
        )
        assert result is not None
        assert result.id == v2.id

        # Get non-existent
        result = store.get_verification_by_claim(claim_id="claim-999")
        assert result is None

        # Get without required params
        result = store.get_verification_by_claim()
        assert result is None


class TestVerificationAgents:
    """Tests for verification agent creation."""

    def test_load_verification_agent_config(self):
        """Test loading agent configuration from YAML."""
        from src.analysis.verification_agents import load_verification_agent_config

        config = load_verification_agent_config()

        assert "web_search_agent" in config
        assert "evidence_analyzer_agent" in config
        assert "credibility_assessor_agent" in config
        assert "conclusion_synthesizer_agent" in config

        # Check required fields
        for agent_name in config:
            assert "role" in config[agent_name]
            assert "goal" in config[agent_name]
            assert "backstory" in config[agent_name]


class TestVerificationTasks:
    """Tests for verification task factory functions."""

    def test_web_search_task_description(self):
        """Test web search task contains correct elements."""
        from src.analysis.verification_tasks import create_web_search_task

        # Create a mock that satisfies CrewAI's Agent validation
        with patch('crewai.Task.__init__', return_value=None) as mock_task:
            mock_agent = Mock()
            create_web_search_task(mock_agent, "The earth is flat")

            # Verify Task was called with correct parameters
            call_kwargs = mock_task.call_args[1]
            assert "The earth is flat" in call_kwargs["description"]
            assert "tavily_search" in call_kwargs["description"]
            assert call_kwargs["agent"] == mock_agent

    def test_evidence_analysis_task_description(self):
        """Test evidence analysis task contains correct elements."""
        from src.analysis.verification_tasks import create_evidence_analysis_task

        with patch('crewai.Task.__init__', return_value=None) as mock_task:
            mock_agent = Mock()
            search_results = {"query": "test", "results": []}
            create_evidence_analysis_task(mock_agent, "Test claim", search_results)

            call_kwargs = mock_task.call_args[1]
            assert "Test claim" in call_kwargs["description"]
            assert "evidence_for" in call_kwargs["description"]
            assert "evidence_against" in call_kwargs["description"]

    def test_credibility_assessment_task_description(self):
        """Test credibility assessment task contains correct elements."""
        from src.analysis.verification_tasks import create_credibility_assessment_task

        with patch('crewai.Task.__init__', return_value=None) as mock_task:
            mock_agent = Mock()
            evidence = {"evidence_for": [], "evidence_against": []}
            create_credibility_assessment_task(mock_agent, evidence)

            call_kwargs = mock_task.call_args[1]
            assert "credibility" in call_kwargs["description"].lower()
            assert "1-10" in call_kwargs["description"]

    def test_conclusion_synthesis_task_description(self):
        """Test conclusion synthesis task contains correct elements."""
        from src.analysis.verification_tasks import create_conclusion_synthesis_task

        with patch('crewai.Task.__init__', return_value=None) as mock_task:
            mock_agent = Mock()
            scored_evidence = {"evidence_for": [], "evidence_against": []}
            create_conclusion_synthesis_task(mock_agent, "Test claim", scored_evidence)

            call_kwargs = mock_task.call_args[1]
            assert "Test claim" in call_kwargs["description"]
            assert "supported" in call_kwargs["description"].lower()
            assert "refuted" in call_kwargs["description"].lower()
            assert "inconclusive" in call_kwargs["description"].lower()


class TestVerificationCrew:
    """Tests for VerificationCrew orchestration."""

    def test_verification_crew_initialization(self, tmp_path):
        """Test VerificationCrew initialization."""
        from src.analysis.verification_crew import VerificationCrew
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        with patch('src.analysis.verification_crew.create_all_verification_agents') as mock_create:
            mock_create.return_value = {
                "web_search": Mock(),
                "evidence_analyzer": Mock(),
                "credibility_assessor": Mock(),
                "conclusion_synthesizer": Mock(),
            }

            crew = VerificationCrew(store=store)

            assert crew.store == store
            assert "web_search" in crew.agents

    def test_build_evidence_list(self, tmp_path):
        """Test building Evidence objects from raw data."""
        from src.analysis.verification_crew import VerificationCrew
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        with patch('src.analysis.verification_crew.create_all_verification_agents') as mock_create:
            mock_create.return_value = {
                "web_search": Mock(),
                "evidence_analyzer": Mock(),
                "credibility_assessor": Mock(),
                "conclusion_synthesizer": Mock(),
            }

            crew = VerificationCrew(store=store)

            raw_evidence = [
                {
                    "source_url": "https://example.com",
                    "source_title": "Test Source",
                    "snippet": "Evidence snippet",
                    "credibility_score": 7.5,
                    "credibility_reasoning": "Reputable source"
                },
                {
                    "source_url": "https://example2.com",
                    "source_title": "Another Source",
                    "snippet": "More evidence"
                }
            ]

            evidence_list = crew._build_evidence_list(raw_evidence)

            assert len(evidence_list) == 2
            assert evidence_list[0].source_url == "https://example.com"
            assert evidence_list[0].credibility_score == 7.5
            assert evidence_list[1].credibility_score is None

    def test_run_verification_with_mock_pipeline(self, tmp_path):
        """Test running verification with mocked agent pipeline."""
        from src.analysis.verification_crew import VerificationCrew
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        # Create a verification record
        verification = store.create_verification(
            claim_text="Vaccines are safe",
            source_url="https://example.com"
        )

        # Mock settings to have API key (for pre-flight validation)
        with patch('src.analysis.verification_crew.settings') as mock_settings:
            mock_settings.tavily_api_key = "test-api-key"

            with patch('src.analysis.verification_crew.create_all_verification_agents') as mock_create:
                mock_agents = {
                    "web_search": Mock(),
                    "evidence_analyzer": Mock(),
                    "credibility_assessor": Mock(),
                    "conclusion_synthesizer": Mock(),
                }
                mock_create.return_value = mock_agents

                crew = VerificationCrew(store=store)

                # Mock all task creation functions to return Mocks
                with patch('src.analysis.verification_crew.create_web_search_task') as mock_ws_task, \
                     patch('src.analysis.verification_crew.create_evidence_analysis_task') as mock_ea_task, \
                     patch('src.analysis.verification_crew.create_credibility_assessment_task') as mock_ca_task, \
                     patch('src.analysis.verification_crew.create_conclusion_synthesis_task') as mock_cs_task:

                    mock_ws_task.return_value = Mock()
                    mock_ea_task.return_value = Mock()
                    mock_ca_task.return_value = Mock()
                    mock_cs_task.return_value = Mock()

                    # Mock _run_single_task to return canned responses
                    def mock_run_task(agent_name, task):
                        if agent_name == "web_search":
                            return '{"query": "test", "results": [{"url": "https://cdc.gov/vaccines", "title": "CDC Vaccines", "snippet": "Vaccines are thoroughly tested."}]}'
                        elif agent_name == "evidence_analyzer":
                            return '{"evidence_for": [{"source_url": "https://cdc.gov/vaccines", "source_title": "CDC Vaccines", "snippet": "Vaccines are thoroughly tested."}], "evidence_against": []}'
                        elif agent_name == "credibility_assessor":
                            return '{"evidence_for": [{"source_url": "https://cdc.gov/vaccines", "source_title": "CDC Vaccines", "snippet": "Vaccines are thoroughly tested.", "credibility_score": 9, "credibility_reasoning": "Government health agency"}], "evidence_against": []}'
                        elif agent_name == "conclusion_synthesizer":
                            return '{"conclusion": "The claim is well supported by evidence.", "conclusion_type": "supported", "confidence_notes": "High confidence based on authoritative sources."}'

                    crew._run_single_task = Mock(side_effect=mock_run_task)

                    # Run verification
                    result = crew.run(verification.id, "Vaccines are safe")

                    assert result["success"] is True
                    assert result["conclusion_type"] == "supported"
                    assert len(result["evidence_for"]) == 1

                    # Verify database was updated
                    updated = store.get_verification(verification.id)
                    assert updated.status == "completed"
                    assert updated.conclusion_type == "supported"

    def test_run_verification_handles_errors(self, tmp_path):
        """Test verification handles errors gracefully."""
        from src.analysis.verification_crew import VerificationCrew
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        verification = store.create_verification(
            claim_text="Test claim",
            source_url="https://example.com"
        )

        # Mock settings to have API key (for pre-flight validation)
        with patch('src.analysis.verification_crew.settings') as mock_settings:
            mock_settings.tavily_api_key = "test-api-key"

            with patch('src.analysis.verification_crew.create_all_verification_agents') as mock_create:
                mock_create.return_value = {
                    "web_search": Mock(),
                    "evidence_analyzer": Mock(),
                    "credibility_assessor": Mock(),
                    "conclusion_synthesizer": Mock(),
                }

                crew = VerificationCrew(store=store)

                # Mock task creation
                with patch('src.analysis.verification_crew.create_web_search_task') as mock_task:
                    mock_task.return_value = Mock()

                    # Make the first task fail
                    crew._run_single_task = Mock(side_effect=Exception("API timeout"))

                    result = crew.run(verification.id, "Test claim")

                    assert result["success"] is False
                    assert "API timeout" in result["error"]

                    # Verify database was updated to failed
                    updated = store.get_verification(verification.id)
                    assert updated.status == "failed"
                    assert "API timeout" in updated.error_message

    def test_run_verification_fails_without_api_key(self, tmp_path):
        """Test verification fails fast when API key is not configured."""
        from src.analysis.verification_crew import VerificationCrew
        from src.storage.verification import VerificationStore

        db_path = tmp_path / "test.db"
        store = VerificationStore(db_path=db_path)

        verification = store.create_verification(
            claim_text="Test claim",
            source_url="https://example.com"
        )

        # Mock settings to have NO API key
        with patch('src.analysis.verification_crew.settings') as mock_settings:
            mock_settings.tavily_api_key = None  # No API key

            with patch('src.analysis.verification_crew.create_all_verification_agents') as mock_create:
                mock_create.return_value = {
                    "web_search": Mock(),
                    "evidence_analyzer": Mock(),
                    "credibility_assessor": Mock(),
                    "conclusion_synthesizer": Mock(),
                }

                crew = VerificationCrew(store=store)

                result = crew.run(verification.id, "Test claim")

                # Should fail with configuration error
                assert result["success"] is False
                assert "[configuration]" in result["error"]
                assert "TAVILY_API_KEY" in result["error"]

                # Verify database was updated to failed
                updated = store.get_verification(verification.id)
                assert updated.status == "failed"

    def test_fabricated_url_detection(self):
        """Test that fabricated URLs are detected."""
        from src.analysis.verification_crew import is_url_likely_fabricated

        # Fabricated URLs should be detected
        assert is_url_likely_fabricated("https://ft.com/content/abc123def456") is True
        assert is_url_likely_fabricated("https://example.com/article") is True
        assert is_url_likely_fabricated("https://news.com/article/12345") is True
        assert is_url_likely_fabricated("") is True
        assert is_url_likely_fabricated(None) is True

        # Real-looking URLs should pass
        assert is_url_likely_fabricated("https://cdc.gov/vaccines/safety") is False
        assert is_url_likely_fabricated("https://nytimes.com/2024/01/01/health/vaccines.html") is False
        assert is_url_likely_fabricated("https://reuters.com/world/us/story-about-topic-2024") is False
