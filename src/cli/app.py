"""CLI application for web scraping and RAG queries."""

from typing import List, Optional
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt

from src.config import settings, ensure_directories
from src.scraper import WebScraper, ScrapedContent
from src.text import TextProcessor
from src.vector import VectorStore
from src.llm import LLMClient
from src.conversation import ConversationMemory
from src.utils.logger import setup_logging, get_logger

# Initialize Rich console and logger
console = Console()
logger = None  # Will be initialized in create_app


def create_app() -> typer.Typer:
    """Create and configure the Typer CLI application."""
    app = typer.Typer(
        name="scrape-rag",
        help="Web scraping and RAG (Retrieval-Augmented Generation) tool",
        add_completion=False
    )

    @app.callback()
    def main(
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
        log_level: str = typer.Option("INFO", "--log-level", help="Set log level")
    ):
        """Initialize the application."""
        global logger

        # Update log level if provided
        if verbose:
            settings.log_level = "DEBUG"
        elif log_level:
            settings.log_level = log_level.upper()

        # Setup logging and directories
        logger = setup_logging()
        ensure_directories()

        console.print(f"[bold green]Scrape-RAG Tool[/bold green]")
        console.print(f"Log level: {settings.log_level}")

    @app.command()
    def scrape(
        url: str = typer.Argument(..., help="URL to scrape"),
        interactive: bool = typer.Option(True, "--interactive/--auto", help="Interactive text selection"),
        collection: Optional[str] = typer.Option(None, "--collection", help="Collection name for vector store")
    ):
        """Scrape a website and optionally add content to vector store."""

        console.print(f"\n[bold blue]Scraping URL:[/bold blue] {url}")

        # Initialize components
        scraper = WebScraper()
        text_processor = TextProcessor()
        vector_store = VectorStore(collection_name=collection)

        # Scrape the website
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Scraping website...", total=None)
            scraped_content = scraper.scrape(url)

        if not scraped_content.success:
            console.print(f"[bold red]Failed to scrape URL:[/bold red] {scraped_content.error_message}")
            raise typer.Exit(1)

        # Display scraped content summary
        console.print(f"\n[bold green]Successfully scraped:[/bold green] {scraped_content.title}")
        console.print(f"Found {len(scraped_content.text_elements)} text elements")
        console.print(f"Total text length: {scraped_content.total_text_length:,} characters")

        if not scraped_content.text_elements:
            console.print("[yellow]No text elements found meeting minimum length criteria.[/yellow]")
            return

        # Interactive text selection
        selected_elements = []
        if interactive:
            console.print(f"\n[bold cyan]Text Selection[/bold cyan]")
            console.print("Review each text element and choose which to include:\n")

            for i, element in enumerate(scraped_content.text_elements):
                console.print(f"[bold]Element {i+1}[/bold] ({element.tag}, {element.word_count} words):")
                console.print(Panel(element.preview, border_style="dim"))

                include = Confirm.ask(f"Include this element?", default=True)
                if include:
                    selected_elements.append(element)

            console.print(f"\n[green]Selected {len(selected_elements)} out of {len(scraped_content.text_elements)} elements[/green]")
        else:
            selected_elements = scraped_content.text_elements
            console.print(f"[green]Auto-selected all {len(selected_elements)} elements[/green]")

        if not selected_elements:
            console.print("[yellow]No elements selected. Nothing to add to vector store.[/yellow]")
            return

        # Process text into chunks
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing text into chunks...", total=None)
            chunks = text_processor.create_chunks_from_elements(
                selected_elements,
                scraped_content.url,
                scraped_content.title
            )

        console.print(f"Created {len(chunks)} text chunks")

        # Add to vector store
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Adding to vector store...", total=None)
            success = vector_store.add_chunks(chunks)

        if success:
            console.print(f"[bold green]✓ Successfully added content to vector store[/bold green]")

            # Show collection stats
            stats = vector_store.get_collection_stats()
            console.print(f"Collection now contains {stats['document_count']} documents")
        else:
            console.print(f"[bold red]✗ Failed to add content to vector store[/bold red]")

    @app.command()
    def query(
        question: str = typer.Argument(..., help="Question to ask"),
        collection: Optional[str] = typer.Option(None, "--collection", help="Collection name for vector store"),
        n_results: int = typer.Option(5, "--results", help="Number of context documents to retrieve")
    ):
        """Ask a question using RAG (Retrieval-Augmented Generation)."""

        console.print(f"\n[bold blue]Question:[/bold blue] {question}")

        # Initialize components
        vector_store = VectorStore(collection_name=collection)
        llm_client = LLMClient()

        # Check if collection has content
        stats = vector_store.get_collection_stats()
        if stats['document_count'] == 0:
            console.print("[yellow]No content in vector store. Please scrape some websites first.[/yellow]")
            raise typer.Exit(1)

        # Retrieve relevant context
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Searching for relevant context...", total=None)
            context_docs = vector_store.search(question, n_results=n_results)

        if not context_docs:
            console.print("[yellow]No relevant context found. Generating response without context.[/yellow]")

        # Generate response
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating response...", total=None)
            result = llm_client.generate_response(question, context_docs)

        # Display response
        if result['success']:
            console.print(f"\n[bold green]Answer:[/bold green]")
            console.print(Panel(result['response'], border_style="green"))

            # Show sources if available
            if result['metadata']['sources']:
                console.print(f"\n[bold]Sources used ({len(result['metadata']['sources'])}):[/bold]")
                for i, source in enumerate(result['metadata']['sources'], 1):
                    console.print(f"{i}. {source['title']} - {source['url']}")
        else:
            console.print(f"[bold red]Failed to generate response:[/bold red] {result.get('error', 'Unknown error')}")

    @app.command()
    def chat(
        collection: Optional[str] = typer.Option(None, "--collection", help="Collection name for vector store"),
        n_results: int = typer.Option(5, "--results", help="Number of context documents to retrieve"),
        memory: bool = typer.Option(True, "--memory/--no-memory", help="Enable conversation memory"),
        save_conversation: bool = typer.Option(None, "--save/--no-save", help="Save conversation to file")
    ):
        """Start an interactive chat session with conversation memory."""

        console.print(f"\n[bold green]Interactive Chat Mode[/bold green]")
        console.print("Type 'quit', 'exit', 'clear', or press Ctrl+C to end the session")

        # Initialize components
        vector_store = VectorStore(collection_name=collection)
        llm_client = LLMClient()

        # Initialize conversation memory
        conversation = ConversationMemory() if memory else None

        # Use configured save setting if not specified
        if save_conversation is None:
            save_conversation = settings.conversation_persistence

        if conversation:
            console.print(f"[dim]Conversation memory enabled (session: {conversation.session_id})[/dim]")
        console.print("")

        # Check if collection has content
        stats = vector_store.get_collection_stats()
        console.print(f"Vector store contains {stats['document_count']} documents")

        if stats['document_count'] == 0:
            console.print("[yellow]No content in vector store. You can still ask general questions.[/yellow]")

        try:
            while True:
                # Get user question
                question = Prompt.ask("\n[bold cyan]Your question[/bold cyan]")

                if question.lower() in ['quit', 'exit', 'q']:
                    console.print("[green]Goodbye![/green]")
                    break
                elif question.lower() == 'clear':
                    if conversation:
                        conversation.clear_history()
                        console.print("[yellow]Conversation history cleared.[/yellow]")
                    else:
                        console.print("[yellow]Conversation memory is disabled.[/yellow]")
                    continue
                elif question.lower() == 'history':
                    if conversation and len(conversation) > 0:
                        console.print(f"\n[bold]Conversation History ({len(conversation)} messages):[/bold]")
                        for i, msg in enumerate(conversation.get_messages(), 1):
                            role_color = "cyan" if msg.role == "user" else "green"
                            console.print(f"[{role_color}]{i}. {msg.role.title()}:[/{role_color}] {msg.content[:100]}...")
                    else:
                        console.print("[yellow]No conversation history available.[/yellow]")
                    continue

                # Add user message to conversation memory
                if conversation:
                    conversation.add_user_message(question)

                # Retrieve context and generate response
                context_docs = vector_store.search(question, n_results=n_results) if stats['document_count'] > 0 else []

                # Get conversation history for LLM context
                conversation_history = None
                if conversation:
                    # Get recent conversation context (exclude the current question)
                    recent_context = conversation.get_recent_context(max_pairs=3)
                    # Remove the last message (current question) as it's passed separately
                    conversation_history = recent_context[:-1] if recent_context else None

                result = llm_client.generate_response(question, context_docs, conversation_history)

                # Display response
                if result['success']:
                    console.print(f"\n[bold green]Answer:[/bold green]")
                    console.print(Panel(result['response'], border_style="green"))

                    # Add assistant response to conversation memory
                    if conversation:
                        conversation.add_assistant_message(result['response'])

                    # Show sources if available
                    if result['metadata']['sources']:
                        console.print(f"\n[dim]Sources: {len(result['metadata']['sources'])} documents used[/dim]")
                else:
                    console.print(f"[bold red]Error:[/bold red] {result.get('error', 'Unknown error')}")

        except KeyboardInterrupt:
            console.print("\n[green]Goodbye![/green]")

        finally:
            # Save conversation if enabled and has content
            if conversation and save_conversation and len(conversation) > 0:
                if conversation.save_to_file():
                    console.print(f"[dim]Conversation saved (session: {conversation.session_id})[/dim]")
                else:
                    console.print(f"[dim]Failed to save conversation[/dim]")

    @app.command()
    def status(
        collection: Optional[str] = typer.Option(None, "--collection", help="Collection name for vector store")
    ):
        """Show status of the vector store and sources."""

        vector_store = VectorStore(collection_name=collection)

        # Get collection stats
        stats = vector_store.get_collection_stats()
        sources = vector_store.get_sources()

        console.print(f"\n[bold green]Vector Store Status[/bold green]")
        console.print(f"Collection: {stats['collection_name']}")
        console.print(f"Documents: {stats['document_count']}")
        console.print(f"Sources: {len(sources)}")

        if sources:
            console.print(f"\n[bold]Sources:[/bold]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Title", style="cyan", no_wrap=False)
            table.add_column("URL", style="blue", no_wrap=False)
            table.add_column("Chunks", justify="right", style="green")

            for source in sources:
                table.add_row(source['title'], source['url'], str(source['chunk_count']))

            console.print(table)

    @app.command()
    def collections():
        """List all collections in the vector store."""

        # Note: We create a temporary VectorStore just to access the client
        vector_store = VectorStore()
        collections = vector_store.list_collections()

        console.print(f"\n[bold green]Vector Store Collections[/bold green]")
        console.print(f"Database: {settings.chroma_persist_directory}")

        if not collections:
            console.print("[yellow]No collections found.[/yellow]")
            return

        console.print(f"\n[bold]Found {len(collections)} collection(s):[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", no_wrap=False)
        table.add_column("Documents", justify="right", style="green")
        table.add_column("ID", style="dim", no_wrap=True)
        table.add_column("Description", style="blue", no_wrap=False)

        for collection in collections:
            description = collection.get('metadata', {}).get('description', 'No description')
            table.add_row(
                collection['name'],
                str(collection['document_count']),
                str(collection['id'])[:8] + "...",  # Truncate ID for display
                description
            )

        console.print(table)

        # Show current default collection
        console.print(f"\n[dim]Default collection: {settings.collection_name}[/dim]")

    @app.command()
    def conversations(
        list_saved: bool = typer.Option(False, "--list", help="List saved conversations"),
        load: Optional[str] = typer.Option(None, "--load", help="Load conversation by session ID"),
        delete: Optional[str] = typer.Option(None, "--delete", help="Delete conversation by session ID")
    ):
        """Manage saved conversations."""

        conversations_dir = Path(settings.chroma_persist_directory).parent / "conversations"

        if list_saved:
            # List all saved conversations
            if not conversations_dir.exists():
                console.print("[yellow]No conversations directory found.[/yellow]")
                return

            conversation_files = list(conversations_dir.glob("conversation_*.json"))
            if not conversation_files:
                console.print("[yellow]No saved conversations found.[/yellow]")
                return

            console.print(f"\n[bold green]Saved Conversations[/bold green]")
            console.print(f"Directory: {conversations_dir}")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Session ID", style="cyan", no_wrap=True)
            table.add_column("Messages", justify="right", style="green")
            table.add_column("Created", style="blue")
            table.add_column("Duration", style="yellow")

            for file_path in sorted(conversation_files):
                try:
                    conversation = ConversationMemory.load_from_file(file_path)
                    if conversation:
                        stats = conversation.get_stats()
                        table.add_row(
                            stats['session_id'],
                            str(stats['total_messages']),
                            stats['created_at'][:19],  # Truncate timestamp
                            stats['duration']
                        )
                except Exception as e:
                    console.print(f"[red]Error loading {file_path.name}: {e}[/red]")

            console.print(table)

        elif load:
            # Load and display a specific conversation
            file_path = conversations_dir / f"conversation_{load}.json"
            if not file_path.exists():
                console.print(f"[red]Conversation {load} not found.[/red]")
                return

            conversation = ConversationMemory.load_from_file(file_path)
            if not conversation:
                console.print(f"[red]Failed to load conversation {load}.[/red]")
                return

            console.print(f"\n[bold green]Conversation {load}[/bold green]")
            stats = conversation.get_stats()
            console.print(f"Messages: {stats['total_messages']}, Created: {stats['created_at'][:19]}")

            for i, msg in enumerate(conversation.get_messages(), 1):
                role_color = "cyan" if msg.role == "user" else "green"
                console.print(f"\n[{role_color}]{i}. {msg.role.title()} ({msg.timestamp.strftime('%H:%M:%S')}):[/{role_color}]")
                console.print(Panel(msg.content, border_style="dim"))

        elif delete:
            # Delete a specific conversation
            file_path = conversations_dir / f"conversation_{delete}.json"
            if not file_path.exists():
                console.print(f"[red]Conversation {delete} not found.[/red]")
                return

            confirm = Confirm.ask(f"Delete conversation {delete}?", default=False)
            if confirm:
                try:
                    file_path.unlink()
                    console.print(f"[green]✓ Deleted conversation {delete}[/green]")
                except Exception as e:
                    console.print(f"[red]✗ Failed to delete conversation: {e}[/red]")

        else:
            # Show usage help
            console.print("[yellow]Use --list to see saved conversations, --load <id> to view, or --delete <id> to remove.[/yellow]")

    @app.command()
    def clear(
        collection: Optional[str] = typer.Option(None, "--collection", help="Collection name for vector store"),
        url: Optional[str] = typer.Option(None, "--url", help="Clear only documents from specific URL")
    ):
        """Clear documents from the vector store."""

        vector_store = VectorStore(collection_name=collection)

        if url:
            confirm = Confirm.ask(f"Clear all documents from URL: {url}?", default=False)
            if confirm:
                success = vector_store.delete_by_url(url)
                if success:
                    console.print(f"[green]✓ Cleared documents from {url}[/green]")
                else:
                    console.print(f"[red]✗ Failed to clear documents from {url}[/red]")
        else:
            confirm = Confirm.ask(f"Clear ALL documents from collection '{vector_store.collection_name}'?", default=False)
            if confirm:
                success = vector_store.clear_collection()
                if success:
                    console.print(f"[green]✓ Cleared all documents from collection[/green]")
                else:
                    console.print(f"[red]✗ Failed to clear collection[/red]")

    return app