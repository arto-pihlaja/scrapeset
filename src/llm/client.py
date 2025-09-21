"""LLM client for RAG queries and response generation using LiteLLM."""

from typing import List, Dict, Any, Optional
import litellm

from src.config import settings
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

        # Set default model with proper provider prefix
        self.model = self._format_model_name(settings.default_model)
        logger.info(f"LLM client initialized with model: {self.model}")

    def _format_model_name(self, model: str) -> str:
        """Format model name with proper provider prefix for LiteLLM."""
        # If model already has a provider prefix, return as-is
        if "/" in model and any(provider in model for provider in ["openai/", "anthropic/", "openrouter/", "huggingface/"]):
            return model

        # Auto-detect provider and add prefix based on available API keys and model patterns
        if settings.openrouter_api_key and any(provider in model for provider in ["mistralai/", "meta-llama/", "google/", "anthropic/claude"]):
            return f"openrouter/{model}"
        elif settings.openai_api_key and (model.startswith("gpt-") or model.startswith("text-") or model == "gpt-3.5-turbo" or model == "gpt-4"):
            return f"openai/{model}" if not model.startswith("openai/") else model
        elif settings.anthropic_api_key and "claude" in model:
            return f"anthropic/{model}" if not model.startswith("anthropic/") else model
        else:
            # For OpenRouter models, default to openrouter prefix if we have the key
            if settings.openrouter_api_key:
                return f"openrouter/{model}"
            else:
                return model

    def _build_rag_prompt(self, query: str, context_documents: List[Dict[str, Any]]) -> str:
        """Build a RAG prompt with query and retrieved context.

        Args:
            query: User's query
            context_documents: List of retrieved documents with content and metadata

        Returns:
            Formatted prompt string
        """
        if not context_documents:
            return f"""Please answer the following question:

{query}

Note: I don't have any specific context documents to reference for this question."""

        # Build context section
        context_parts = []
        for i, doc in enumerate(context_documents, 1):
            content = doc.get('document', '')
            metadata = doc.get('metadata', {})
            source_title = metadata.get('source_title', 'Unknown')
            source_url = metadata.get('source_url', 'Unknown')

            context_parts.append(f"""[Context {i}]
Source: {source_title}
URL: {source_url}
Content: {content}
""")

        context_text = "\n".join(context_parts)

        prompt = f"""Based on the following context documents, please answer the question. Use the information from the context to provide a comprehensive and accurate response. If the context doesn't contain enough information to fully answer the question, please indicate that.

CONTEXT:
{context_text}

QUESTION:
{query}

ANSWER:"""

        return prompt

    def generate_response(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate a response to a query using retrieved context documents.

        Args:
            query: User's query
            context_documents: List of retrieved documents with content and metadata
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

            # Build the prompt
            prompt = self._build_rag_prompt(query, context_documents)

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

    def generate_simple_response(self, query: str) -> Dict[str, Any]:
        """Generate a simple response without RAG context.

        Args:
            query: User's query

        Returns:
            Dictionary with response and metadata
        """
        return self.generate_response(query, [])

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