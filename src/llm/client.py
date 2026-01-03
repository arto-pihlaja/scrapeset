"""LLM client for RAG queries and response generation using LiteLLM."""

from typing import List, Dict, Any, Optional
import litellm

from src.config import settings
from src.llm.utils import format_model_name
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """LLM client for generating responses to queries using retrieved context."""

    def __init__(self):
        """Initialize the LLM client."""
        self._setup_litellm()

    def _setup_litellm(self):
        """Setup LiteLLM with configured provider and API keys."""
        # Set API keys based on configuration
        if settings.openai_api_key:
            litellm.openai_key = settings.openai_api_key

        if settings.anthropic_api_key:
            litellm.anthropic_key = settings.anthropic_api_key

        if settings.openrouter_api_key:
            litellm.openrouter_key = settings.openrouter_api_key

        if settings.deepseek_api_key:
            litellm.deepseek_key = settings.deepseek_api_key
            
        # Enable dropping unsupported params (e.g. temperature for o1 models)
        litellm.drop_params = True
            
        # Generic LLM support
        if settings.llm_api_base:
            litellm.api_base = settings.llm_api_base
        
        if settings.llm_api_key:
            # If using generic key, we might need to set it for specific providers or letting litellm handle it
            # Typically for OpenAI-compatible, we can set openai_key to this if not already set,
            # or rely on litellm's discovery. For safety, let's set openai_key if it's "openai/" provider usage.
            # But safer:
            if not litellm.openai_key:
                litellm.openai_key = settings.llm_api_key

        # Set default model with proper provider prefix
        self.model = format_model_name(settings.default_model)
        logger.info(f"LLM client initialized with model: {self.model}")

    def _build_rag_prompt(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Build a RAG prompt with query, retrieved context, and conversation history.

        Args:
            query: User's query
            context_documents: List of retrieved documents with content and metadata
            conversation_history: Optional conversation history for context

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Add conversation history if available
        if conversation_history:
            prompt_parts.append("CONVERSATION HISTORY:")
            for msg in conversation_history:
                role = "Human" if msg["role"] == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}")
            prompt_parts.append("")

        # Add context documents if available
        if context_documents:
            prompt_parts.append("CONTEXT DOCUMENTS:")
            for i, doc in enumerate(context_documents, 1):
                content = doc.get('document', '')
                metadata = doc.get('metadata', {})
                source_title = metadata.get('source_title', 'Unknown')
                source_url = metadata.get('source_url', 'Unknown')

                prompt_parts.append(f"[Context {i}]")
                prompt_parts.append(f"Source: {source_title}")
                prompt_parts.append(f"URL: {source_url}")
                prompt_parts.append(f"Content: {content}")
                prompt_parts.append("")

        # Add instructions
        if context_documents and conversation_history:
            instruction = """Based on the conversation history and context documents above, please answer the following question. Use the conversation history to understand the context and flow of our discussion, and use the context documents to provide accurate, relevant information. If you need to reference previous parts of our conversation, feel free to do so."""
        elif context_documents:
            instruction = """Based on the following context documents, please answer the question. Use the information from the context to provide a comprehensive and accurate response. If the context doesn't contain enough information to fully answer the question, please indicate that."""
        elif conversation_history:
            instruction = """Based on our conversation history above, please answer the following question. You can reference previous parts of our conversation as needed."""
        else:
            instruction = """Please answer the following question based on your knowledge:"""

        prompt_parts.append(instruction)
        prompt_parts.append("")
        prompt_parts.append(f"CURRENT QUESTION: {query}")
        prompt_parts.append("")
        prompt_parts.append("ANSWER:")

        return "\n".join(prompt_parts)

    def generate_response(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate a response to a query using retrieved context documents and conversation history.

        Args:
            query: User's query
            context_documents: List of retrieved documents with content and metadata
            conversation_history: Optional conversation history for context
            temperature: Temperature for response generation (uses config default if None)
            max_tokens: Maximum tokens for response (uses config default if None)

        Returns:
            Dictionary with response, metadata, and success status
        """
        try:
            # Use configured values if not provided
            if temperature is None:
                temperature = settings.llm_temperature
            if max_tokens is None:
                max_tokens = settings.max_tokens

            # Build the prompt with conversation history
            prompt = self._build_rag_prompt(query, context_documents, conversation_history)

            logger.info(f"Generating response for query: {query[:50]}...")

            # Generate response using LiteLLM
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Extract response content
            content = response.choices[0].message.content

            result = {
                "response": content,
                "query": query,
                "model": self.model,
                "context_count": len(context_documents),
                "success": True,
                "metadata": {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "usage": response.usage.dict() if hasattr(response, 'usage') else {},
                    "sources": [
                        {
                            "title": doc.get('metadata', {}).get('source_title', 'Unknown'),
                            "url": doc.get('metadata', {}).get('source_url', 'Unknown'),
                            "distance": doc.get('distance', 0.0)
                        }
                        for doc in context_documents
                    ]
                }
            }

            logger.info(f"Successfully generated response ({len(content)} characters)")
            return result

        except Exception as e:
            error_msg = f"Failed to generate response: {e}"
            logger.error(error_msg)

            return {
                "response": f"I apologize, but I encountered an error while generating a response: {error_msg}",
                "query": query,
                "model": self.model,
                "context_count": len(context_documents),
                "success": False,
                "error": error_msg,
                "metadata": {}
            }

    def generate_simple_response(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Generate a simple response without RAG context.

        Args:
            query: User's query
            conversation_history: Optional conversation history for context

        Returns:
            Dictionary with response and metadata
        """
        return self.generate_response(query, [], conversation_history)

    def summarize_content(self, content: str, max_length: int = 200) -> str:
        """Generate a summary of content.

        Args:
            content: Content to summarize
            max_length: Maximum length of summary

        Returns:
            Summary text
        """
        try:
            prompt = f"""Please provide a concise summary of the following content in no more than {max_length} words:

{content}

Summary:"""

            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_length * 2  # Allow some buffer for tokens vs words
            )

            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated summary ({len(summary)} characters)")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Summary unavailable: {e}"