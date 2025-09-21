"""CLI application for web scraping and RAG queries."""

from typing import List, Optional
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
        n_results: int = typer.Option(5, "--results", help="Number of context documents to retrieve")
    ):
        """Start an interactive chat session."""

        console.print(f"\n[bold green]Interactive Chat Mode[/bold green]")
        console.print("Type 'quit', 'exit', or press Ctrl+C to end the session\n")

        # Initialize components
        vector_store = VectorStore(collection_name=collection)
        llm_client = LLMClient()

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

                # Retrieve context and generate response
                context_docs = vector_store.search(question, n_results=n_results) if stats['document_count'] > 0 else []
                result = llm_client.generate_response(question, context_docs)

                # Display response
                if result['success']:
                    console.print(f"\n[bold green]Answer:[/bold green]")
                    console.print(Panel(result['response'], border_style="green"))
                else:
                    console.print(f"[bold red]Error:[/bold red] {result.get('error', 'Unknown error')}")

        except KeyboardInterrupt:
            console.print("\n[green]Goodbye![/green]")

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