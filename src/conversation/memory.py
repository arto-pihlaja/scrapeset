"""Conversation memory management for chat sessions."""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    message_id: str = None

    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create message from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class ConversationMemory:
    """Manages conversation history for chat sessions."""

    def __init__(self, session_id: Optional[str] = None, max_history: Optional[int] = None):
        """Initialize conversation memory.

        Args:
            session_id: Unique identifier for this conversation session
            max_history: Maximum number of message exchanges to remember
        """
        self.session_id = session_id or str(uuid4())[:8]
        self.max_history = max_history or settings.conversation_memory_size
        self.messages: List[ConversationMessage] = []
        self.created_at = datetime.now()

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None, auto_save: bool = True):
        """Add a message to the conversation history.

        Args:
            role: Either "user" or "assistant"
            content: The message content
            metadata: Optional metadata about the message
            auto_save: Whether to auto-save to disk after adding
        """
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.messages.append(message)

        # Trim history if it exceeds max_history pairs
        # Keep pairs together (user + assistant messages)
        if len(self.messages) > self.max_history * 2:
            # Remove oldest pair (user + assistant)
            self.messages = self.messages[2:]

        logger.debug(f"Added {role} message to conversation {self.session_id}")

        # Auto-save to disk for persistence
        if auto_save:
            self.save_to_file()

    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a user message to the conversation."""
        self.add_message("user", content, metadata)

    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add an assistant message to the conversation."""
        self.add_message("assistant", content, metadata)

    def get_messages(self, limit: Optional[int] = None) -> List[ConversationMessage]:
        """Get conversation messages, optionally limited to recent messages.

        Args:
            limit: Maximum number of messages to return (default: all)

        Returns:
            List of conversation messages
        """
        if limit is None:
            return self.messages.copy()
        return self.messages[-limit:] if limit > 0 else []

    def get_conversation_context(self, include_metadata: bool = False) -> List[Dict[str, str]]:
        """Get conversation history formatted for LLM context.

        Args:
            include_metadata: Whether to include metadata in the context

        Returns:
            List of message dictionaries with role and content
        """
        context = []
        for message in self.messages:
            msg_dict = {
                "role": message.role,
                "content": message.content
            }
            if include_metadata and message.metadata:
                msg_dict["metadata"] = message.metadata
            context.append(msg_dict)

        return context

    def get_recent_context(self, max_pairs: int = 3) -> List[Dict[str, str]]:
        """Get recent conversation pairs for context.

        Args:
            max_pairs: Maximum number of user-assistant pairs to include

        Returns:
            List of recent message dictionaries
        """
        # Get last N pairs (each pair = user + assistant message)
        recent_messages = self.messages[-(max_pairs * 2):] if max_pairs > 0 else []
        return [{"role": msg.role, "content": msg.content} for msg in recent_messages]

    def clear_history(self):
        """Clear all conversation history."""
        self.messages.clear()
        logger.info(f"Cleared conversation history for session {self.session_id}")

    def delete_file(self) -> bool:
        """Delete the persisted conversation file.

        Returns:
            True if successful or file doesn't exist, False otherwise
        """
        try:
            # Use absolute path for consistency
            chroma_path = Path(settings.chroma_persist_directory)
            if not chroma_path.is_absolute():
                chroma_path = Path(__file__).parent.parent.parent / settings.chroma_persist_directory
            conversations_dir = chroma_path.parent / "conversations"
            file_path = conversations_dir / f"conversation_{self.session_id}.json"

            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted conversation file {file_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete conversation file: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get conversation statistics.

        Returns:
            Dictionary with conversation stats
        """
        user_messages = sum(1 for msg in self.messages if msg.role == "user")
        assistant_messages = sum(1 for msg in self.messages if msg.role == "assistant")

        return {
            "session_id": self.session_id,
            "total_messages": len(self.messages),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "created_at": self.created_at.isoformat(),
            "duration": str(datetime.now() - self.created_at) if self.messages else "0:00:00"
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "max_history": self.max_history,
            "created_at": self.created_at.isoformat(),
            "messages": [msg.to_dict() for msg in self.messages]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMemory':
        """Create conversation from dictionary."""
        memory = cls(
            session_id=data["session_id"],
            max_history=data["max_history"]
        )
        memory.created_at = datetime.fromisoformat(data["created_at"])
        memory.messages = [ConversationMessage.from_dict(msg) for msg in data["messages"]]
        return memory

    def save_to_file(self, file_path: Optional[Path] = None) -> bool:
        """Save conversation to JSON file.

        Args:
            file_path: Path to save file (default: auto-generated)

        Returns:
            True if successful, False otherwise
        """
        try:
            if file_path is None:
                # Auto-generate filename using absolute path
                chroma_path = Path(settings.chroma_persist_directory)
                if not chroma_path.is_absolute():
                    # Make it absolute relative to the project root
                    chroma_path = Path(__file__).parent.parent.parent / settings.chroma_persist_directory
                conversations_dir = chroma_path.parent / "conversations"
                conversations_dir.mkdir(parents=True, exist_ok=True)
                file_path = conversations_dir / f"conversation_{self.session_id}.json"

            logger.debug(f"Saving conversation {self.session_id} to {file_path}")

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(f"Saved conversation {self.session_id} to {file_path} ({len(self.messages)} messages)")
            return True

        except Exception as e:
            logger.error(f"Failed to save conversation {self.session_id}: {e}", exc_info=True)
            return False

    @classmethod
    def load_from_file(cls, file_path: Path) -> Optional['ConversationMemory']:
        """Load conversation from JSON file.

        Args:
            file_path: Path to the conversation file

        Returns:
            ConversationMemory instance or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            memory = cls.from_dict(data)
            logger.info(f"Loaded conversation {memory.session_id} from {file_path}")
            return memory

        except Exception as e:
            logger.error(f"Failed to load conversation from {file_path}: {e}")
            return None

    @classmethod
    def load_all_conversations(cls) -> Dict[str, 'ConversationMemory']:
        """Load all persisted conversations from the conversations directory.

        Returns:
            Dictionary mapping session_id to ConversationMemory instances
        """
        conversations = {}

        # Use absolute path for consistency
        chroma_path = Path(settings.chroma_persist_directory)
        if not chroma_path.is_absolute():
            chroma_path = Path(__file__).parent.parent.parent / settings.chroma_persist_directory
        conversations_dir = chroma_path.parent / "conversations"

        logger.info(f"Looking for conversations in: {conversations_dir}")

        if not conversations_dir.exists():
            logger.info("No conversations directory found, starting fresh")
            conversations_dir.mkdir(parents=True, exist_ok=True)
            return conversations

        for file_path in conversations_dir.glob("conversation_*.json"):
            memory = cls.load_from_file(file_path)
            if memory:
                conversations[memory.session_id] = memory

        logger.info(f"Loaded {len(conversations)} conversations from disk")
        return conversations

    def __str__(self) -> str:
        """String representation of the conversation."""
        stats = self.get_stats()
        return (f"Conversation {self.session_id}: "
                f"{stats['total_messages']} messages, "
                f"created {stats['created_at']}")

    def __len__(self) -> int:
        """Return number of messages in conversation."""
        return len(self.messages)

    def __bool__(self) -> bool:
        """Return True if memory object exists (regardless of message count)."""
        return True