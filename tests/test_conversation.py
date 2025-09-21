"""Tests for the conversation memory module."""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from src.conversation import ConversationMemory, ConversationMessage


class TestConversationMessage:
    """Test cases for the ConversationMessage class."""

    def test_message_creation(self):
        """Test creating a conversation message."""
        timestamp = datetime.now()
        message = ConversationMessage(
            role="user",
            content="Hello, how are you?",
            timestamp=timestamp
        )

        assert message.role == "user"
        assert message.content == "Hello, how are you?"
        assert message.timestamp == timestamp
        assert message.message_id is not None
        assert len(message.message_id) == 8  # UUID truncated to 8 chars

    def test_message_serialization(self):
        """Test message to/from dict conversion."""
        timestamp = datetime.now()
        message = ConversationMessage(
            role="assistant",
            content="I'm doing well, thank you!",
            timestamp=timestamp,
            metadata={"model": "gpt-4"}
        )

        # Test to_dict
        data = message.to_dict()
        assert data["role"] == "assistant"
        assert data["content"] == "I'm doing well, thank you!"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["metadata"] == {"model": "gpt-4"}

        # Test from_dict
        restored_message = ConversationMessage.from_dict(data)
        assert restored_message.role == message.role
        assert restored_message.content == message.content
        assert restored_message.timestamp == message.timestamp
        assert restored_message.metadata == message.metadata


class TestConversationMemory:
    """Test cases for the ConversationMemory class."""

    def test_memory_creation(self):
        """Test creating conversation memory."""
        memory = ConversationMemory(max_history=3)

        assert memory.max_history == 3
        assert len(memory.messages) == 0
        assert memory.session_id is not None
        assert len(memory.session_id) == 8

    def test_add_messages(self):
        """Test adding messages to conversation memory."""
        memory = ConversationMemory()

        memory.add_user_message("What is Python?")
        memory.add_assistant_message("Python is a programming language.")

        assert len(memory.messages) == 2
        assert memory.messages[0].role == "user"
        assert memory.messages[0].content == "What is Python?"
        assert memory.messages[1].role == "assistant"
        assert memory.messages[1].content == "Python is a programming language."

    def test_conversation_context(self):
        """Test getting conversation context for LLM."""
        memory = ConversationMemory()

        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi there!")
        memory.add_user_message("How are you?")

        context = memory.get_conversation_context()
        assert len(context) == 3
        assert context[0] == {"role": "user", "content": "Hello"}
        assert context[1] == {"role": "assistant", "content": "Hi there!"}
        assert context[2] == {"role": "user", "content": "How are you?"}

    def test_recent_context(self):
        """Test getting recent conversation pairs."""
        memory = ConversationMemory()

        # Add 3 complete pairs (6 messages)
        memory.add_user_message("Question 1")
        memory.add_assistant_message("Answer 1")
        memory.add_user_message("Question 2")
        memory.add_assistant_message("Answer 2")
        memory.add_user_message("Question 3")
        memory.add_assistant_message("Answer 3")

        # Get last 2 pairs (4 messages)
        recent = memory.get_recent_context(max_pairs=2)
        assert len(recent) == 4
        assert recent[0]["content"] == "Question 2"
        assert recent[1]["content"] == "Answer 2"
        assert recent[2]["content"] == "Question 3"
        assert recent[3]["content"] == "Answer 3"

    def test_memory_limit(self):
        """Test conversation memory size limiting."""
        memory = ConversationMemory(max_history=2)  # Only keep 2 pairs

        # Add 3 pairs (6 messages)
        memory.add_user_message("Q1")
        memory.add_assistant_message("A1")
        memory.add_user_message("Q2")
        memory.add_assistant_message("A2")
        memory.add_user_message("Q3")
        memory.add_assistant_message("A3")

        # Should only keep last 2 pairs (4 messages)
        assert len(memory.messages) == 4
        assert memory.messages[0].content == "Q2"
        assert memory.messages[1].content == "A2"
        assert memory.messages[2].content == "Q3"
        assert memory.messages[3].content == "A3"

    def test_clear_history(self):
        """Test clearing conversation history."""
        memory = ConversationMemory()

        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi!")
        assert len(memory.messages) == 2

        memory.clear_history()
        assert len(memory.messages) == 0

    def test_conversation_stats(self):
        """Test conversation statistics."""
        memory = ConversationMemory()

        memory.add_user_message("Question 1")
        memory.add_assistant_message("Answer 1")
        memory.add_user_message("Question 2")

        stats = memory.get_stats()
        assert stats["total_messages"] == 3
        assert stats["user_messages"] == 2
        assert stats["assistant_messages"] == 1
        assert stats["session_id"] == memory.session_id

    def test_memory_serialization(self):
        """Test conversation memory serialization."""
        memory = ConversationMemory(session_id="test123", max_history=5)
        memory.add_user_message("Hello")
        memory.add_assistant_message("Hi there!")

        # Test to_dict
        data = memory.to_dict()
        assert data["session_id"] == "test123"
        assert data["max_history"] == 5
        assert len(data["messages"]) == 2

        # Test from_dict
        restored_memory = ConversationMemory.from_dict(data)
        assert restored_memory.session_id == "test123"
        assert restored_memory.max_history == 5
        assert len(restored_memory.messages) == 2
        assert restored_memory.messages[0].content == "Hello"
        assert restored_memory.messages[1].content == "Hi there!"