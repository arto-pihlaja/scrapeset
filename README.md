# ScrapeSET - Web Scraping + RAG Tool

A powerful command-line tool for scraping web content and querying it using Retrieval-Augmented Generation (RAG). Extract text from websites, store it in a vector database, and ask intelligent questions about the content.

## ✨ Features

- **Smart Web Scraping**: Extract and filter text content from any website
- **Interactive Content Selection**: Review and choose which text elements to include
- **Vector Storage**: Automatic chunking and embedding storage using ChromaDB
- **RAG-Powered Q&A**: Ask questions about scraped content with context-aware responses
- **Conversation Memory**: Multi-turn conversations with context retention and history
- **Full Text Preview**: Review concatenated plain text of all scraped content before indexing
- **Multiple LLM Support**: Works with OpenAI, Anthropic, and OpenRouter APIs
- **Web Interface**: Modern React-based web UI with real-time updates
- **Rich CLI Interface**: Beautiful command-line interface with progress indicators
- **Persistent Storage**: Your scraped content and conversations are saved locally

## 🚀 Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd scrape
```

2. Install dependencies:

**Option A: Full installation (recommended)**
```bash
# Create a virtual environment
uv venv

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

**Option B: If you encounter version conflicts**
```bash
uv pip install -r requirements-minimal.txt
```

**Option C: Core functionality only**
```bash
uv pip install -r requirements-core.txt
```

3. Set up environment variables (optional):
```bash
# Create .env file with your API keys
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENROUTER_API_KEY=your_openrouter_key
```

### Basic Usage

1. **Scrape a website**:
```bash
uv run python main.py scrape https://example.com
```
The tool will extract text elements and let you choose which ones to include.

2. **Ask questions about the content**:
```bash
uv run python main.py query "What is the main topic of this article?"
```

3. **Start an interactive chat session**:
```bash
uv run python main.py chat
```

4. **Check your collection status**:
```bash
uv run python main.py status
```

5. **List all collections**:
```bash
uv run python main.py collections
```

## 🌐 Web Interface

ScrapeSET now includes a modern web interface built with React and FastAPI!

### Starting the Web Interface

1. **Install frontend dependencies** (first time only):
```bash
cd frontend
npm install
cd ..
```

2. **Start the web server**:
```bash
uv run python web_server.py
```

3. **Start the frontend** (in another terminal):
```bash
cd frontend
npm run dev
```

4. **Access the application**:
- Web Interface: http://localhost:3000
- API Documentation: http://localhost:8000/docs

### Web Interface Features

- **📊 Dashboard**: Overview of collections, statistics, and quick actions
- **🌐 Web Scraping**: Interactive URL scraping with text element selection
- **📚 Collections**: Visual management with clear documents vs drop collection options
- **💬 Chat Interface**: Real-time conversations with RAG-powered responses
- **📝 Conversation History**: View and manage saved chat sessions
- **⚙️ Settings**: Configure LLM providers, embedding models, and processing options

The web interface provides all CLI functionality in an intuitive, visual format with:
- Real-time progress updates
- Interactive element selection
- Source citation in chat responses
- Responsive design for all devices
- Conversation memory with session management

## 📖 CLI Commands

### `scrape`
Scrape a website and add content to your vector store.

```bash
python main.py scrape URL [OPTIONS]
```

**Options:**
- `--interactive/--auto`: Enable/disable interactive text selection (default: interactive)
- `--collection TEXT`: Specify collection name for vector store

**Example:**
```bash
# Interactive scraping (default)
uv run python main.py scrape https://python.org

# Auto-include all text elements
uv run python main.py scrape https://python.org --auto

# Use custom collection
uv run python main.py scrape https://python.org --collection python_docs
```

### `query`
Ask a question using RAG (Retrieval-Augmented Generation).

```bash
python main.py query "YOUR QUESTION" [OPTIONS]
```

**Options:**
- `--collection TEXT`: Collection name to query
- `--results INTEGER`: Number of context documents to retrieve (default: 5)

**Example:**
```bash
uv run python main.py query "What are the main features mentioned?"
uv run python main.py query "Explain the installation process" --results 3
```

### `chat`
Start an interactive chat session with conversation memory.

```bash
python main.py chat [OPTIONS]
```

**Options:**
- `--collection TEXT`: Collection name to use
- `--results INTEGER`: Number of context documents to retrieve (default: 5)
- `--memory/--no-memory`: Enable/disable conversation memory (default: enabled)
- `--save/--no-save`: Save conversation to file (default: from config)

**Chat Commands:**
- `quit`, `exit`, `q`: End the chat session
- `clear`: Clear conversation history
- `history`: View conversation history

**Example:**
```bash
# Chat with memory enabled (default)
uv run python main.py chat

# Chat without memory
uv run python main.py chat --no-memory

# Chat with auto-save enabled
uv run python main.py chat --save
```

### `status`
Show the status of your vector store and sources.

```bash
python main.py status [OPTIONS]
```

**Options:**
- `--collection TEXT`: Collection name to check

### `collections`
List all collections in the vector store.

```bash
python main.py collections
```

Shows all available collections with their document counts and metadata.

### `conversations`
Manage saved conversations.

```bash
python main.py conversations [OPTIONS]
```

**Options:**
- `--list`: List all saved conversations
- `--load TEXT`: Load and display conversation by session ID
- `--delete TEXT`: Delete conversation by session ID

**Examples:**
```bash
# List all saved conversations
uv run python main.py conversations --list

# View a specific conversation
uv run python main.py conversations --load abc123de

# Delete a conversation
uv run python main.py conversations --delete abc123de
```

### `clear`
Clear documents from the vector store or drop entire collections.

```bash
python main.py clear [OPTIONS]
```

**Options:**
- `--collection TEXT`: Collection name to operate on
- `--url TEXT`: Clear only documents from a specific URL
- `--drop`: Drop the entire collection instead of just clearing documents

**Examples:**
```bash
# Clear all documents from collection (keeps collection structure)
uv run python main.py clear

# Clear documents from specific URL
uv run python main.py clear --url https://example.com

# Drop entire collection (completely removes collection)
uv run python main.py clear --drop

# Drop specific collection
uv run python main.py clear --collection my_collection --drop
```

**Important:**
- **Clear**: Removes all documents but keeps the collection structure
- **Drop**: Completely removes the collection and all its documents (cannot be undone)

## ⚙️ Configuration

The tool can be configured through environment variables or a `.env` file:

### LLM Configuration
```bash
# API Keys (at least one required)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENROUTER_API_KEY=your_openrouter_key

# LLM Settings
DEFAULT_LLM_PROVIDER=openai
DEFAULT_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.1
MAX_TOKENS=2000
```

**Supported Models:**
```bash
# OpenRouter models (when OPENROUTER_API_KEY is set)
DEFAULT_MODEL=mistralai/mistral-small-3.2-24b-instruct
DEFAULT_MODEL=anthropic/claude-3-haiku-20240307
DEFAULT_MODEL=google/gemini-pro-1.5
DEFAULT_MODEL=meta-llama/llama-3.1-8b-instruct

# OpenAI models (when OPENAI_API_KEY is set)
DEFAULT_MODEL=gpt-4
DEFAULT_MODEL=gpt-3.5-turbo

# Anthropic models (when ANTHROPIC_API_KEY is set)
DEFAULT_MODEL=claude-3-sonnet-20240229
```

**Note:** The system automatically adds the correct provider prefix (e.g., `openrouter/`, `openai/`) based on your API keys.

### Text Processing
```bash
TEXT_PREVIEW_WORDS=50        # Words shown in preview
CHUNK_SIZE=1000             # Text chunk size for embedding
CHUNK_OVERLAP=200           # Overlap between chunks
```

### Vector Database
```bash
CHROMA_PERSIST_DIRECTORY=./data/chroma_db
COLLECTION_NAME=scraped_content
EMBEDDING_MODEL=default              # Embedding model to use
```

### Conversation Memory
```bash
CONVERSATION_MEMORY_SIZE=5           # Number of exchange pairs to remember
CONVERSATION_PERSISTENCE=false      # Auto-save conversations
```

### Scraping Settings
```bash
REQUEST_TIMEOUT=30           # HTTP request timeout
USER_AGENT=Mozilla/5.0...   # Custom user agent
```

## 🧠 Embedding Models

Choose different embedding models for RAG by setting the `EMBEDDING_MODEL` environment variable:

### Available Options:

```bash
# Default ChromaDB embedding (sentence-transformers/all-MiniLM-L6-v2)
EMBEDDING_MODEL=default

# OpenAI embeddings (requires OPENAI_API_KEY)
EMBEDDING_MODEL=openai

# High-quality sentence transformers
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2

# Multilingual model
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Instructor embeddings for better domain adaptation
EMBEDDING_MODEL=instructor

# Any sentence-transformers model from Hugging Face
EMBEDDING_MODEL=sentence-transformers/all-distilroberta-v1
```

### Embedding Model Comparison:

| Model | Quality | Speed | Use Case |
|-------|---------|-------|----------|
| `default` | Good | Fast | General purpose, quick setup |
| `openai` | Excellent | Medium | High quality, requires API key |
| `all-mpnet-base-v2` | Excellent | Slow | Best quality for English |
| `all-MiniLM-L6-v2` | Good | Fast | Balanced speed/quality |
| `instructor` | Excellent | Medium | Domain-specific tasks |

### Example Usage:

```bash
# Use OpenAI embeddings
EMBEDDING_MODEL=openai OPENAI_API_KEY=your_key uv run python main.py scrape https://example.com

# Use high-quality sentence transformers
EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2 uv run python main.py scrape https://example.com
```

**Note:** Different embedding models create incompatible vector spaces. Use `python main.py clear` when switching embedding models.

## 🏗️ Architecture

The project follows a modular architecture:

```
src/
├── scraper/        # Web scraping functionality
├── text/          # Text processing and chunking
├── vector/        # Vector database operations
├── llm/           # LLM interface and RAG
├── cli/           # Command-line interface
├── config/        # Configuration management
└── utils/         # Logging and utilities
```

### Core Components

- **WebScraper**: Handles URL fetching, HTML parsing, and text extraction
- **TextProcessor**: Cleans text, creates chunks, and counts tokens
- **VectorStore**: Manages ChromaDB operations and similarity search
- **LLMClient**: Interfaces with multiple LLM providers via LiteLLM
- **CLI**: Provides user-friendly command-line interface

## 🧪 Testing

Run the test suite:

```bash
uv run python -m pytest tests/ -v
```

## 🛠️ Troubleshooting

### Installation Issues

**Problem**: Dependency version conflicts during `pip install`

**Solutions**:
1. Use a fresh virtual environment with uv:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -r requirements-minimal.txt
   ```

2. Update dependencies and try again:
   ```bash
   uv pip install -r requirements.txt
   ```

3. Install core dependencies only:
   ```bash
   uv pip install -r requirements-core.txt
   ```

### Common Runtime Issues

**Problem**: "ChromaDB collection not found" errors

**Solution**: The collection will be created automatically on first use. If issues persist, clear the data directory:
```bash
rm -rf ./data/chroma_db
```

**Problem**: LLM API errors

**Solutions**:
1. Check your API keys in `.env` file
2. Verify your account has sufficient credits
3. Try a different model or provider

**Problem**: Web interface not loading

**Solutions**:
1. Make sure both backend and frontend are running:
   ```bash
   # Terminal 1: Backend
   uv run python web_server.py

   # Terminal 2: Frontend
   cd frontend && npm run dev
   ```

2. Check for port conflicts (default: backend 8000, frontend 3000)

### Collection Management

**Problem**: Understanding the difference between Clear vs Drop operations

**Solution**:
- **Clear Documents** (`uv run python main.py clear`): Removes all documents from the collection but keeps the collection structure. You can add new documents to the same collection later.
- **Drop Collection** (`uv run python main.py clear --drop`): Completely removes the collection and all its documents from ChromaDB. The collection structure is permanently deleted.

**Use Cases**:
- Use **Clear** when you want to refresh the content but keep using the same collection
- Use **Drop** when you want to completely remove a collection you no longer need

## 📝 Tech Stack

- **Python 3.12+**: Core language
- **BeautifulSoup4**: HTML parsing and text extraction
- **ChromaDB**: Vector database for embeddings
- **LiteLLM**: Unified interface for multiple LLM providers
- **Typer**: Command-line interface framework
- **Rich**: Beautiful terminal output
- **Tiktoken**: Token counting
- **Loguru**: Advanced logging

## 🛣️ Roadmap

### Current Version (v1.0)
- ✅ Basic web scraping with interactive selection
- ✅ Vector storage and RAG queries
- ✅ Multi-LLM support
- ✅ CLI interface
- ✅ Conversation memory and context retention
- ✅ Multiple embedding models support
- ✅ Conversation persistence and management

### Future Enhancements
- **Advanced RAG**: Multiple embedding models, re-ranking, optimization
- **Performance**: Async processing, caching, batch operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [documentation](docs/)
2. Look at existing [issues](../../issues)
3. Create a new issue with detailed information

---

**Happy scraping and querying! 🎉**
