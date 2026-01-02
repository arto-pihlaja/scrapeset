"""FastAPI application for web interface."""

import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.config import settings, ensure_directories
from src.scraper import WebScraper, ScrapedContent
from src.text import TextProcessor
from src.vector import VectorStore
from src.llm import LLMClient
from src.conversation import ConversationMemory
from src.utils.logger import setup_logging, get_logger


# Setup logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    ensure_directories()
    logger.info("ScrapeSET Web Interface starting up")
    yield
    # Shutdown
    logger.info("ScrapeSET Web Interface shutting down")


# Create FastAPI app
app = FastAPI(
    title="ScrapeSET Web Interface",
    description="Web interface for scraping and RAG tool",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

# Shared VectorStore instance for efficiency
# This uses the default collection from settings
# Individual endpoints can still specify a collection_name if needed
vector_store = VectorStore()


# Pydantic models for API
class ScrapeRequest(BaseModel):
    url: str
    collection: Optional[str] = None
    interactive: bool = True
    dynamic: bool = False


class ScrapeResponse(BaseModel):
    success: bool
    title: str
    text_elements: List[Dict[str, Any]]
    total_text_length: int
    error_message: Optional[str] = None


class QueryRequest(BaseModel):
    question: str
    collection: Optional[str] = None
    n_results: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    success: bool
    error_message: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    collection: Optional[str] = None  # Backward compatibility
    collections: Optional[List[str]] = None  # Multi-collection support
    n_results: int = 5
    use_memory: bool = True
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    session_id: str
    success: bool
    collections_used: Optional[List[str]] = None
    results_per_collection: Optional[Dict[str, int]] = None
    error_message: Optional[str] = None


# API Routes

@app.get("/")
async def read_root():
    """Serve the main application."""
    return {"message": "ScrapeSET Web Interface API", "version": "1.0.0"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ScrapeSET Web Interface"}


@app.get("/api/collections")
async def get_collections():
    """Get all collections."""
    try:
        collections = vector_store.list_collections()
        return {"success": True, "collections": collections}
    except Exception as e:
        logger.error(f"Failed to get collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collections/{collection_name}/stats")
async def get_collection_stats(collection_name: str):
    """Get statistics for a specific collection."""
    try:
        vector_store = VectorStore(collection_name=collection_name)
        stats = vector_store.get_collection_stats()
        sources = vector_store.get_sources()
        return {"success": True, "stats": stats, "sources": sources}
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collections/{collection_name}/content")
async def get_collection_content(
    collection_name: str,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    url: Optional[str] = None
):
    """Get content for a specific collection."""
    try:
        store = VectorStore(collection_name=collection_name)
        where = {"source_url": url} if url else None
        content = store.get_content(limit=limit, offset=offset, where=where)
        return {"success": True, "content": content}
    except Exception as e:
        logger.error(f"Failed to get collection content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scrape", response_model=ScrapeResponse)
def scrape_url(request: ScrapeRequest):
    """Scrape a URL and return text elements."""
    try:
        # Initialize scraper
        scraper = WebScraper()

        # Scrape the URL
        scraped_content = scraper.scrape(request.url, dynamic=request.dynamic)

        if not scraped_content.success:
            return ScrapeResponse(
                success=False,
                title="",
                text_elements=[],
                total_text_length=0,
                error_message=scraped_content.error_message
            )

        # Convert text elements to dict format
        text_elements = []
        for i, element in enumerate(scraped_content.text_elements):
            text_elements.append({
                "id": i,
                "content": element.content,
                "tag": element.tag,
                "preview": element.preview,
                "word_count": element.word_count,
                "char_count": element.char_count
            })

        return ScrapeResponse(
            success=True,
            title=scraped_content.title,
            text_elements=text_elements,
            total_text_length=scraped_content.total_text_length
        )

    except Exception as e:
        logger.error(f"Failed to scrape URL {request.url}: {e}")
        return ScrapeResponse(
            success=False,
            title="",
            text_elements=[],
            total_text_length=0,
            error_message=str(e)
        )


@app.post("/api/scrape/add-to-collection")
async def add_to_collection(request: Dict[str, Any]):
    """Add selected text elements to vector store."""
    try:
        url = request["url"]
        title = request["title"]
        selected_elements = request["selected_elements"]
        collection = request.get("collection")

        # Initialize components
        text_processor = TextProcessor()
        vector_store = VectorStore(collection_name=collection)

        # Convert selected elements back to TextElement objects
        from src.scraper.scraper import TextElement
        elements = []
        for elem_data in selected_elements:
            element = TextElement(
                content=elem_data["content"],
                tag=elem_data["tag"],
                preview=elem_data["preview"],
                word_count=elem_data["word_count"],
                char_count=elem_data["char_count"]
            )
            elements.append(element)

        # Create chunks
        chunks = text_processor.create_chunks_from_elements(elements, url, title)

        # Add to vector store
        success = vector_store.add_chunks(chunks)

        if success:
            stats = vector_store.get_collection_stats()
            return {
                "success": True,
                "chunks_created": len(chunks),
                "collection_stats": stats
            }
        else:
            return {"success": False, "error": "Failed to add to vector store"}

    except Exception as e:
        logger.error(f"Failed to add to collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query", response_model=QueryResponse)
async def query_collection(request: QueryRequest):
    """Query the collection using RAG."""
    try:
        # Initialize components
        vector_store = VectorStore(collection_name=request.collection)
        llm_client = LLMClient()

        # Search for relevant documents
        search_results = vector_store.search(
            query=request.question,
            n_results=request.n_results
        )

        if not search_results:
            return QueryResponse(
                answer="No relevant documents found in the collection.",
                sources=[],
                success=True
            )

        # Generate response using LLM
        generated_result = llm_client.generate_response(
            query=request.question,
            context_documents=search_results
        )
        
        response_text = generated_result["response"]

        # Format sources
        sources = []
        for result in search_results:
            sources.append({
                "content": result["document"][:200] + "..." if len(result["document"]) > 200 else result["document"],
                "metadata": result["metadata"],
                "similarity": 1 - result["distance"]  # Convert distance to similarity
            })

        return QueryResponse(
            answer=response_text,
            sources=sources,
            success=True
        )

    except Exception as e:
        logger.error(f"Failed to query collection: {e}")
        return QueryResponse(
            answer="",
            sources=[],
            success=False,
            error_message=str(e)
        )


# In-memory storage for chat sessions (in production, use Redis or database)
chat_sessions: Dict[str, ConversationMemory] = {}


def search_multiple_collections(collections: List[str], query: str, n_results: int) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Search across multiple collections and aggregate results."""
    all_results = []
    results_per_collection = {}

    # Calculate results per collection
    results_per_col = max(1, n_results // len(collections))

    for collection_name in collections:
        try:
            vector_store = VectorStore(collection_name=collection_name)
            search_results = vector_store.search(
                query=query,
                n_results=results_per_col
            )

            # Add collection name to metadata
            for result in search_results:
                result["metadata"]["source_collection"] = collection_name
                all_results.append(result)

            results_per_collection[collection_name] = len(search_results)

        except Exception as e:
            logger.warning(f"Failed to search collection {collection_name}: {e}")
            results_per_collection[collection_name] = 0

    # Sort all results by similarity (distance) and take top N
    all_results.sort(key=lambda x: x["distance"])
    return all_results[:n_results], results_per_collection


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_collection(request: ChatRequest):
    """Chat with collection(s) using conversation memory."""
    try:
        # Initialize components
        llm_client = LLMClient()

        # Get or create conversation memory
        if request.use_memory:
            session_id = request.session_id or f"session_{len(chat_sessions)}"
            if session_id not in chat_sessions:
                chat_sessions[session_id] = ConversationMemory(session_id=session_id)
            memory = chat_sessions[session_id]
        else:
            session_id = "no_memory"
            memory = None

        # Determine collections to search
        collections_to_search = []
        if request.collections:
            collections_to_search = request.collections
        elif request.collection:
            collections_to_search = [request.collection]
        else:
            # If no collections specified, get default collection
            vector_store = VectorStore()
            collections_to_search = [vector_store.collection_name]

        # Search for relevant documents
        if len(collections_to_search) == 1:
            # Single collection search
            vector_store = VectorStore(collection_name=collections_to_search[0])
            search_results = vector_store.search(
                query=request.message,
                n_results=request.n_results
            )
            results_per_collection = {collections_to_search[0]: len(search_results)}
        else:
            # Multi-collection search
            search_results, results_per_collection = search_multiple_collections(
                collections=collections_to_search,
                query=request.message,
                n_results=request.n_results
            )

        # Generate response with conversation context
        conversation_history = memory.get_conversation_context() if memory else None

        generated_result = llm_client.generate_response(
            query=request.message,
            context_documents=search_results,
            conversation_history=conversation_history
        )
        
        response_text = generated_result["response"]

        # Update conversation memory
        if memory:
            memory.add_user_message(request.message)
            memory.add_assistant_message(response_text)

        # Format sources
        sources = []
        for result in search_results:
            sources.append({
                "content": result["document"][:200] + "..." if len(result["document"]) > 200 else result["document"],
                "metadata": result["metadata"],
                "similarity": 1 - result["distance"]
            })

        return ChatResponse(
            response=response_text,
            sources=sources,
            session_id=session_id,
            success=True,
            collections_used=collections_to_search,
            results_per_collection=results_per_collection
        )

    except Exception as e:
        logger.error(f"Failed to chat with collection(s): {e}")
        return ChatResponse(
            response="",
            sources=[],
            session_id="",
            success=False,
            error_message=str(e)
        )


@app.get("/api/chat/sessions")
async def get_chat_sessions():
    """Get all chat sessions."""
    sessions = []
    for session_id, memory in chat_sessions.items():
        stats = memory.get_stats()
        sessions.append({
            "session_id": session_id,
            "total_messages": stats["total_messages"],
            "last_updated": memory.messages[-1].timestamp.isoformat() if memory.messages else None
        })
    return {"success": True, "sessions": sessions}


@app.get("/api/chat/sessions/{session_id}")
async def get_chat_session(session_id: str):
    """Get a specific chat session."""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    memory = chat_sessions[session_id]
    messages = []
    for msg in memory.messages:
        messages.append({
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "message_id": msg.message_id
        })

    return {
        "success": True,
        "session_id": session_id,
        "messages": messages,
        "stats": memory.get_stats()
    }


@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session."""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    del chat_sessions[session_id]
    return {"success": True, "message": "Session deleted"}


@app.delete("/api/collections/{collection_name}")
async def clear_collection(collection_name: str):
    """Clear all documents from a collection."""
    try:
        # Use a temporary store for the specific collection
        temp_store = VectorStore(collection_name=collection_name)
        success = temp_store.clear_collection()
        return {"success": success, "operation": "clear"}
    except Exception as e:
        logger.error(f"Failed to clear collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/collections/{collection_name}/drop")
async def drop_collection(collection_name: str):
    """Completely remove a collection from ChromaDB."""
    try:
        # Use a temporary store for the specific collection
        temp_store = VectorStore(collection_name=collection_name)
        success = temp_store.drop_collection()
        return {"success": success, "operation": "drop"}
    except Exception as e:
        logger.error(f"Failed to drop collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)