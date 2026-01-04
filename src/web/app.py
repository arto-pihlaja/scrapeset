"""FastAPI application for web interface."""

import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

import re
import json
import traceback

from src.config import settings, ensure_directories
from src.scraper import WebScraper, ScrapedContent
from src.text import TextProcessor
from src.vector import VectorStore
from src.llm import LLMClient
from src.conversation import ConversationMemory
from src.storage import ResultsStore
from src.storage.verification import VerificationStore
from src.storage.analysis import AnalysisStore
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


# Saved Results models
class SaveResultRequest(BaseModel):
    name: str
    url: str
    title: Optional[str] = None
    content: str


class SaveResultResponse(BaseModel):
    success: bool
    result_id: Optional[int] = None
    error_message: Optional[str] = None


class CreateVectorDBRequest(BaseModel):
    collection_name: Optional[str] = None


# Claim Verification models
class VerifyClaimRequest(BaseModel):
    claim_text: str
    source_url: str
    claim_id: Optional[str] = None


class VerifyClaimResponse(BaseModel):
    success: bool
    id: Optional[str] = None
    status: Optional[str] = None
    claim_text: Optional[str] = None
    created_at: Optional[str] = None
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


# Saved Results endpoints

@app.post("/api/results/save", response_model=SaveResultResponse)
async def save_scrape_result(request: SaveResultRequest):
    """Save scraped content to SQLite database."""
    try:
        results_store = ResultsStore()
        result_id = results_store.save_result(
            name=request.name,
            url=request.url,
            title=request.title,
            content=request.content
        )
        return SaveResultResponse(success=True, result_id=result_id)
    except Exception as e:
        logger.error(f"Failed to save result: {e}")
        return SaveResultResponse(success=False, error_message=str(e))


@app.get("/api/results")
async def list_scrape_results():
    """Get all saved scraping results."""
    try:
        results_store = ResultsStore()
        results = results_store.list_results()
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Failed to list results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results/{result_id}")
async def get_scrape_result(result_id: int):
    """Get a single scraping result by ID."""
    try:
        results_store = ResultsStore()
        result = results_store.get_result(result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        return {
            "success": True,
            "result": {
                "id": result.id,
                "name": result.name,
                "url": result.url,
                "title": result.title,
                "content": result.content,
                "char_count": result.char_count,
                "saved_at": result.saved_at.isoformat(),
                "vector_collection": result.vector_collection
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/results/{result_id}")
async def delete_scrape_result(result_id: int):
    """Delete a scraping result."""
    try:
        results_store = ResultsStore()

        # Get result to check if it has a vector collection
        result = results_store.get_result(result_id)
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")

        # Optionally drop the vector collection if it exists
        if result.vector_collection:
            try:
                store = VectorStore(collection_name=result.vector_collection)
                store.drop_collection()
            except Exception as e:
                logger.warning(f"Failed to drop vector collection: {e}")

        deleted = results_store.delete_result(result_id)
        return {"success": deleted, "message": "Result deleted" if deleted else "Result not found"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/results/{result_id}/create-vector-db")
async def create_vector_db_from_result(result_id: int, request: CreateVectorDBRequest):
    """Create a vector database from a saved scraping result."""
    try:
        results_store = ResultsStore()
        result = results_store.get_result(result_id)

        if not result:
            raise HTTPException(status_code=404, detail="Result not found")

        if result.vector_collection:
            return {
                "success": False,
                "error": f"Vector DB already exists: {result.vector_collection}"
            }

        # Generate collection name if not provided
        collection_name = request.collection_name
        if not collection_name:
            # Create a safe collection name from the result name
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', result.name.lower())
            collection_name = f"result_{result.id}_{safe_name[:30]}"

        # Create text processor and vector store
        text_processor = TextProcessor()
        store = VectorStore(collection_name=collection_name)

        # Create chunks from content
        chunks = text_processor.create_chunks(
            text=result.content,
            source_url=result.url,
            source_title=result.title or result.name
        )

        # Add to vector store
        success = store.add_chunks(chunks)

        if success:
            # Update the result with the collection name
            results_store.update_vector_collection(result_id, collection_name)
            stats = store.get_collection_stats()
            return {
                "success": True,
                "collection_name": collection_name,
                "chunks_created": len(chunks),
                "stats": stats
            }
        else:
            return {"success": False, "error": "Failed to add chunks to vector store"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create vector DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/results/{result_id}/vector-db")
async def delete_vector_db_for_result(result_id: int):
    """Delete the vector database for a result (but keep the result)."""
    try:
        results_store = ResultsStore()
        result = results_store.get_result(result_id)

        if not result:
            raise HTTPException(status_code=404, detail="Result not found")

        if not result.vector_collection:
            return {"success": False, "error": "No vector DB exists for this result"}

        # Drop the collection
        store = VectorStore(collection_name=result.vector_collection)
        store.drop_collection()

        # Clear the reference
        results_store.clear_vector_collection(result_id)

        return {"success": True, "message": "Vector DB deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete vector DB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analysis Models
class AnalysisStepRequest(BaseModel):
    step: str
    url: Optional[str] = None
    text: Optional[str] = None
    previous_data: Optional[Dict[str, Any]] = None


@app.post("/api/analysis/step")
async def analysis_step(request: AnalysisStepRequest):
    """Run a specific step of the analysis pipeline."""
    try:
        from src.analysis import AnalysisCrew
        crew = AnalysisCrew()

        input_data = {}
        if request.step == "fetch":
            input_data["url"] = request.url
        elif request.step == "summary":
            input_data["content_data"] = request.previous_data
        elif request.step == "source_assessment":
            input_data["content_data"] = request.previous_data
        elif request.step == "claims":
            # Claims step uses key_claims from summary_data
            input_data["summary_data"] = request.previous_data.get("summary_data", request.previous_data)
            input_data["full_text"] = request.previous_data.get("full_text", "")
        elif request.step == "controversy":
            # Controversy step uses summary_data (summary, main_argument, key_claims)
            input_data["summary_data"] = request.previous_data.get("summary_data", request.previous_data)
        elif request.step == "fallacies":
            # Fallacies step uses key_claims from summary_data
            input_data["summary_data"] = request.previous_data.get("summary_data", request.previous_data)
            input_data["full_text"] = request.previous_data.get("full_text", "")
        elif request.step == "counterargument":
            # Counterargument step uses summary_data (summary, main_argument, key_claims)
            input_data["summary_data"] = request.previous_data.get("summary_data", request.previous_data)

        result = await asyncio.to_thread(crew.run_step, request.step, input_data)

        if "error" in result:
            return {"success": False, "error": result["error"]}

        # Auto-save analysis results after summary step completes
        if request.step == "summary" and request.previous_data:
            try:
                analysis_store = AnalysisStore()
                url = request.previous_data.get("url", "")
                source_type = request.previous_data.get("source_type")
                title = request.previous_data.get("title")

                # Summary result now contains: summary, main_argument, key_claims
                summary = {
                    "summary": result.get("summary"),
                    "main_argument": result.get("main_argument"),
                    "key_claims": result.get("key_claims", [])
                }

                # Create or update analysis record and save results
                analysis = analysis_store.create_or_update_analysis(
                    url=url,
                    source_type=source_type,
                    title=title
                )
                analysis_store.save_analysis_results(
                    analysis_id=analysis.id,
                    summary=summary
                )
                logger.info(f"Auto-saved analysis {analysis.id} after summary step")

                # Add analysis_id to result for frontend reference
                result["analysis_id"] = analysis.id
            except Exception as save_error:
                logger.warning(f"Failed to auto-save analysis: {save_error}")
                # Don't fail the request, just log the warning

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Analysis step {request.step} failed: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/analysis/step/stream")
async def analysis_step_stream(request: AnalysisStepRequest):
    """Run analysis step with SSE streaming for progress updates.

    Returns Server-Sent Events with progress messages during execution,
    followed by the final result.
    """
    from src.analysis import AnalysisCrew

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def progress_callback(message: str, step: str, progress: int):
            """Callback invoked by AnalysisCrew to report progress."""
            asyncio.run_coroutine_threadsafe(
                queue.put({"type": "progress", "message": message, "step": step, "progress": progress}),
                loop
            )

        async def run_analysis():
            """Run the analysis in a thread pool with progress callback."""
            crew = AnalysisCrew()

            input_data = {}
            if request.step == "fetch":
                input_data["url"] = request.url
            elif request.step == "summary":
                input_data["content_data"] = request.previous_data
            elif request.step == "source_assessment":
                input_data["content_data"] = request.previous_data
            elif request.step == "claims":
                # Claims step uses key_claims from summary_data
                input_data["summary_data"] = request.previous_data.get("summary_data", request.previous_data)
                input_data["full_text"] = request.previous_data.get("full_text", "")
            elif request.step == "controversy":
                # Controversy step uses summary_data (summary, main_argument, key_claims)
                input_data["summary_data"] = request.previous_data.get("summary_data", request.previous_data)
            elif request.step == "fallacies":
                # Fallacies step uses key_claims from summary_data
                input_data["summary_data"] = request.previous_data.get("summary_data", request.previous_data)
                input_data["full_text"] = request.previous_data.get("full_text", "")
            elif request.step == "counterargument":
                # Counterargument step uses summary_data (summary, main_argument, key_claims)
                input_data["summary_data"] = request.previous_data.get("summary_data", request.previous_data)

            return await asyncio.to_thread(
                crew.run_step, request.step, input_data, progress_callback
            )

        # Start the analysis task
        task = asyncio.create_task(run_analysis())

        # Stream progress events while task is running
        while not task.done():
            try:
                event = await asyncio.wait_for(queue.get(), timeout=2.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        # Drain any remaining progress messages
        while not queue.empty():
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"

        # Get the final result
        try:
            result = await task
            if "error" in result:
                yield f"data: {json.dumps({'type': 'error', 'error': result['error']})}\n\n"
            else:
                # Auto-save analysis results after summary step completes
                if request.step == "summary" and request.previous_data:
                    try:
                        analysis_store = AnalysisStore()
                        url = request.previous_data.get("url", "")
                        source_type = request.previous_data.get("source_type")
                        title = request.previous_data.get("title")

                        # Summary result now contains: summary, main_argument, key_claims
                        summary = {
                            "summary": result.get("summary"),
                            "main_argument": result.get("main_argument"),
                            "key_claims": result.get("key_claims", [])
                        }

                        analysis = analysis_store.create_or_update_analysis(
                            url=url,
                            source_type=source_type,
                            title=title
                        )
                        analysis_store.save_analysis_results(
                            analysis_id=analysis.id,
                            summary=summary
                        )
                        result["analysis_id"] = analysis.id
                        logger.info(f"Auto-saved analysis {analysis.id} after summary step (streaming)")
                    except Exception as save_error:
                        logger.warning(f"Failed to auto-save analysis: {save_error}")

                yield f"data: {json.dumps({'type': 'complete', 'success': True, 'data': result})}\n\n"
        except Exception as e:
            logger.error(f"Analysis step {request.step} failed: {e}\n{traceback.format_exc()}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# Claim Verification endpoints

@app.post("/api/analysis/verify-claim", response_model=VerifyClaimResponse)
async def verify_claim(request: VerifyClaimRequest):
    """Trigger claim verification.

    Creates a pending verification record and returns immediately.
    Use /api/analysis/verify-claim/stream to run the full verification pipeline.
    """
    try:
        verification_store = VerificationStore()

        # Create the verification record
        verification = verification_store.create_verification(
            claim_text=request.claim_text,
            source_url=request.source_url,
            claim_id=request.claim_id
        )

        logger.info(f"Created verification {verification.id} for claim: {request.claim_text[:50]}...")

        return VerifyClaimResponse(
            success=True,
            id=verification.id,
            status=verification.status,
            claim_text=verification.claim_text,
            created_at=verification.created_at.isoformat() if verification.created_at else None
        )

    except Exception as e:
        logger.error(f"Failed to create verification: {e}")
        return VerifyClaimResponse(
            success=False,
            error_message=str(e)
        )


@app.post("/api/analysis/verify-claim/stream")
async def verify_claim_stream(request: VerifyClaimRequest):
    """Run claim verification with SSE streaming for progress updates.

    Creates a verification record and runs the full 4-agent pipeline:
    WebSearchAgent → EvidenceAnalyzerAgent → CredibilityAssessorAgent → ConclusionSynthesizerAgent

    Returns Server-Sent Events with progress messages during execution,
    followed by the final result.
    """
    from src.analysis.verification_crew import VerificationCrew

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def progress_callback(message: str, step: str, progress: int):
            """Callback invoked by VerificationCrew to report progress."""
            asyncio.run_coroutine_threadsafe(
                queue.put({
                    "type": "progress",
                    "message": message,
                    "step": step,
                    "progress": progress
                }),
                loop
            )

        async def run_verification():
            """Run the verification in a thread pool with progress callback."""
            verification_store = VerificationStore()

            # Create the verification record
            verification = verification_store.create_verification(
                claim_text=request.claim_text,
                source_url=request.source_url,
                claim_id=request.claim_id
            )

            # Run the verification pipeline
            crew = VerificationCrew(store=verification_store)
            return await asyncio.to_thread(
                crew.run,
                verification.id,
                request.claim_text,
                progress_callback
            )

        # Start the verification task
        task = asyncio.create_task(run_verification())

        # Stream progress events while task is running
        while not task.done():
            try:
                event = await asyncio.wait_for(queue.get(), timeout=2.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        # Drain any remaining progress messages
        while not queue.empty():
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"

        # Get the final result
        try:
            result = await task
            if result.get("success"):
                yield f"data: {json.dumps({'type': 'complete', 'success': True, 'data': result})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'error': result.get('error', 'Unknown error')})}\n\n"
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@app.get("/api/analysis/verification/by-claim")
async def get_verification_by_claim(
    claim_id: Optional[str] = None,
    claim_text: Optional[str] = None,
    source_url: Optional[str] = None
):
    """Get the most recent verification for a claim.

    Query by either:
    - claim_id: The unique claim identifier
    - claim_text + source_url: The exact claim text and source URL
    """
    try:
        if not claim_id and not (claim_text and source_url):
            raise HTTPException(
                status_code=400,
                detail="Must provide either claim_id or both claim_text and source_url"
            )

        verification_store = VerificationStore()
        verification = verification_store.get_verification_by_claim(
            claim_id=claim_id,
            claim_text=claim_text,
            source_url=source_url
        )

        if not verification:
            return {
                "success": True,
                "verification": None
            }

        return {
            "success": True,
            "verification": verification.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get verification by claim: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/verification/{verification_id}")
async def get_verification(verification_id: str):
    """Get a verification result by ID."""
    try:
        verification_store = VerificationStore()
        verification = verification_store.get_verification(verification_id)

        if not verification:
            raise HTTPException(status_code=404, detail="Verification not found")

        return {
            "success": True,
            "verification": verification.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/verifications")
async def list_verifications(source_url: Optional[str] = None, limit: int = 50):
    """List verifications, optionally filtered by source URL."""
    try:
        verification_store = VerificationStore()
        verifications = verification_store.list_verifications(
            source_url=source_url,
            limit=limit
        )

        return {
            "success": True,
            "verifications": verifications
        }

    except Exception as e:
        logger.error(f"Failed to list verifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Content Analysis Persistence Endpoints ==============


class SaveAnalysisRequest(BaseModel):
    """Request body for saving analysis results."""
    url: str
    source_type: Optional[str] = None
    title: Optional[str] = None
    source_assessment: Dict[str, Any]
    summary: Dict[str, Any]


@app.post("/api/analysis/save")
async def save_analysis(request: SaveAnalysisRequest):
    """Save analysis results for a URL.

    Creates or updates an analysis record with the summary step results.
    """
    try:
        analysis_store = AnalysisStore()

        # Create or update the analysis record
        analysis = analysis_store.create_or_update_analysis(
            url=request.url,
            source_type=request.source_type,
            title=request.title
        )

        # Save the results
        success = analysis_store.save_analysis_results(
            analysis_id=analysis.id,
            summary=request.summary,
            source_assessment=request.source_assessment
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save analysis results")

        # Get the full analysis to return
        saved_analysis = analysis_store.get_analysis(analysis.id)

        return {
            "success": True,
            "analysis_id": analysis.id,
            "analysis": saved_analysis.to_dict() if saved_analysis else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/by-url")
async def get_analysis_by_url(url: str):
    """Get existing analysis for a URL, if any."""
    try:
        analysis_store = AnalysisStore()
        analysis = analysis_store.get_analysis_by_url(url)

        return {
            "success": True,
            "analysis": analysis.to_dict() if analysis else None
        }

    except Exception as e:
        logger.error(f"Failed to get analysis by URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/history")
async def get_analysis_history(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get analysis history with optional filtering."""
    try:
        analysis_store = AnalysisStore()
        analyses, total = analysis_store.list_analyses(
            status=status,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "analyses": analyses,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Failed to get analysis history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/content/{analysis_id}")
async def get_analysis_content(analysis_id: str):
    """Get full analysis content by ID."""
    try:
        analysis_store = AnalysisStore()
        analysis = analysis_store.get_analysis(analysis_id)

        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        return {
            "success": True,
            "analysis": analysis.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/analysis/content/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """Delete an analysis by ID."""
    try:
        analysis_store = AnalysisStore()
        deleted = analysis_store.delete_analysis(analysis_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Analysis not found")

        return {
            "success": True,
            "deleted": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete analysis: {e}")
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