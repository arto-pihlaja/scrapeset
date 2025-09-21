"""Vector store implementation using ChromaDB for text embeddings."""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from src.config import settings
from src.text.processor import TextChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Vector store for storing and retrieving text embeddings using ChromaDB."""

    def __init__(self, collection_name: Optional[str] = None):
        """Initialize the vector store.

        Args:
            collection_name: Name of the collection to use (defaults to config setting)
        """
        self.collection_name = collection_name or settings.collection_name
        self.client = None
        self.collection = None
        self._setup_client()

    def _get_embedding_function(self):
        """Get embedding function based on configuration."""
        model = settings.embedding_model.lower()

        if model == "default":
            # ChromaDB default (sentence-transformers/all-MiniLM-L6-v2)
            return embedding_functions.DefaultEmbeddingFunction()

        elif model == "openai":
            # OpenAI embeddings (requires OPENAI_API_KEY)
            return embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.openai_api_key,
                model_name="text-embedding-ada-002"
            )

        elif model == "huggingface" or model.startswith("sentence-transformers/"):
            # Sentence transformers model
            model_name = model if model.startswith("sentence-transformers/") else "sentence-transformers/all-mpnet-base-v2"
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )

        elif model == "instructor":
            # Instructor embeddings
            return embedding_functions.InstructorEmbeddingFunction(
                model_name="hkunlp/instructor-large"
            )

        else:
            # Fallback to default
            logger.warning(f"Unknown embedding model '{model}', using default")
            return embedding_functions.DefaultEmbeddingFunction()

    def _setup_client(self):
        """Setup ChromaDB client and collection."""
        try:
            # Ensure the persist directory exists
            persist_dir = Path(settings.chroma_persist_directory)
            persist_dir.mkdir(parents=True, exist_ok=True)

            # Initialize ChromaDB client with persistent storage
            self.client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Setup embedding function based on configuration
            embedding_function = self._get_embedding_function()

            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name,
                    embedding_function=embedding_function
                )
                logger.info(f"Connected to existing collection: {self.collection_name}")
            except Exception:  # Catch any exception when collection doesn't exist
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    embedding_function=embedding_function,
                    metadata={"description": "Scraped text content for RAG"}
                )
                logger.info(f"Created new collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to setup ChromaDB client: {e}")
            raise

    def add_chunks(self, chunks: List[TextChunk]) -> bool:
        """Add text chunks to the vector store.

        Args:
            chunks: List of TextChunk objects to add

        Returns:
            True if successful, False otherwise
        """
        try:
            if not chunks:
                logger.warning("No chunks provided to add")
                return True

            # Prepare data for ChromaDB
            ids = [chunk.id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]

            # Add to collection
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"Successfully added {len(chunks)} chunks to vector store")
            return True

        except Exception as e:
            logger.error(f"Failed to add chunks to vector store: {e}")
            return False

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents in the vector store.

        Args:
            query: Search query text
            n_results: Number of results to return
            where: Optional metadata filters

        Returns:
            List of search results with documents, metadata, and distances
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'][0] else {},
                        'distance': results['distances'][0][i] if results['distances'][0] else 0.0
                    }
                    formatted_results.append(result)

            logger.info(f"Found {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to search vector store: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": settings.chroma_persist_directory
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "collection_name": self.collection_name,
                "document_count": 0,
                "error": str(e)
            }

    def clear_collection(self) -> bool:
        """Clear all documents from the collection.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all document IDs
            results = self.collection.get()
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Cleared {len(results['ids'])} documents from collection")
            else:
                logger.info("Collection is already empty")
            return True

        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False

    def delete_by_url(self, source_url: str) -> bool:
        """Delete all documents from a specific source URL.

        Args:
            source_url: URL of documents to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Query for documents with the specific URL
            results = self.collection.get(
                where={"source_url": source_url},
                include=["metadatas"]
            )

            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} documents from URL: {source_url}")
            else:
                logger.info(f"No documents found for URL: {source_url}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete documents by URL: {e}")
            return False

    def get_sources(self) -> List[Dict[str, Any]]:
        """Get a list of all source URLs in the collection.

        Returns:
            List of dictionaries with source information
        """
        try:
            results = self.collection.get(include=["metadatas"])

            # Extract unique sources
            sources = {}
            for metadata in results['metadatas']:
                url = metadata.get('source_url', 'Unknown')
                title = metadata.get('source_title', 'Untitled')

                if url not in sources:
                    sources[url] = {
                        'url': url,
                        'title': title,
                        'chunk_count': 0
                    }
                sources[url]['chunk_count'] += 1

            return list(sources.values())

        except Exception as e:
            logger.error(f"Failed to get sources: {e}")
            return []

    def list_collections(self) -> List[Dict[str, Any]]:
        """Get a list of all collections in the database.

        Returns:
            List of dictionaries with collection information
        """
        try:
            collections = self.client.list_collections()

            collection_info = []
            for collection in collections:
                # Get collection stats
                temp_collection = self.client.get_collection(collection.name)
                doc_count = temp_collection.count()

                collection_info.append({
                    'name': collection.name,
                    'id': collection.id,
                    'document_count': doc_count,
                    'metadata': collection.metadata
                })

            logger.info(f"Found {len(collection_info)} collections")
            return collection_info

        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []