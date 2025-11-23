"""
Interactive CLI chatbot for querying the vector database.

Each message is a fresh call to the vector database with thinking mode.
Beautiful markdown output that adapts to terminal size.
"""

# CRITICAL: Set TOKENIZERS_PARALLELISM before any tokenizer imports
# This prevents warnings when tokenizers are used after forking
import os
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

import sys
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.prompt import Prompt
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.text import Text
    from rich.align import Align
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich not installed. Install with: pip install rich")

# Import from ask.py
from conductor.ask import (
    query_chromadb,
    format_context,
    query_claude,
    DEFAULT_DB_PATH
)

# Import prompt system
from conductor.prompt_refiner import (
    query_claude_with_system_prompt
)

import logging

# Load environment variables
load_dotenv()

# Quiet logging for clean output
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Rich console - adapts to terminal size automatically
console = Console() if RICH_AVAILABLE else None


def create_app_layout() -> Layout:
    """Create the main app layout structure."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main", ratio=3),
        Layout(name="input_area", size=3),
        Layout(name="footer", size=2)
    )
    return layout


def create_header(db_path: Path) -> Panel:
    """Create app header."""
    header_text = Text()
    header_text.append("🔍 ", style="bold cyan")
    header_text.append("Vector Database Chatbot", style="bold white")
    header_text.append(" • ", style="dim")
    header_text.append("Thinking Mode", style="bold green")
    header_text.append(" • ", style="dim")
    header_text.append("Fresh Calls", style="bold yellow")
    
    subtitle = f"DB: {db_path.name} | Type '/help' for commands | '/exit' to quit"
    
    return Panel(
        Align.center(header_text, vertical="middle"),
        subtitle=subtitle,
        style="bold white on blue",
        box=box.ROUNDED,
        height=3
    )


def create_footer(message: str = "Ready") -> Panel:
    """Create app footer."""
    footer_text = Text()
    footer_text.append("💡 ", style="bold yellow")
    footer_text.append(message, style="dim")
    
    return Panel(
        footer_text,
        style="white on dark_green",
        box=box.ROUNDED,
        height=2
    )


def create_chat_message(user_message: str, response: str, query_num: int) -> Layout:
    """Create a chat message layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="user_msg"),
        Layout(name="assistant_msg")
    )
    
    # User message
    user_panel = Panel(
        user_message,
        title=f"[bold cyan]You[/bold cyan] (Query #{query_num})",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1)
    )
    layout["user_msg"].update(user_panel)
    
    # Assistant response as markdown
    markdown = Markdown(response, code_theme="monokai")
    assistant_panel = Panel(
        markdown,
        title="[bold green]Assistant[/bold green]",
        subtitle="[dim]Thinking mode • Vector DB • Fresh call[/dim]",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    layout["assistant_msg"].update(assistant_panel)
    
    return layout


def create_loading_panel(stage: str) -> Panel:
    """Create loading panel."""
    return Panel(
        Align.center(
            f"\n[bold cyan]{stage}[/bold cyan]\n[dim]Please wait...[/dim]\n",
            vertical="middle"
        ),
        border_style="cyan",
        box=box.ROUNDED
    )


def process_query(
    query: str,
    db_path: Path,
    use_thinking: bool = True,
    use_hybrid: bool = False,
    use_cache: bool = True,
    use_reranking: bool = True,
    where_filter: Optional[Dict] = None,
    use_refinement: bool = True,
    use_deep_research: bool = True,
    deep_research_n_results: int = 50,
    max_final_results: int = 40
) -> tuple[str, str]:
    """
    Process a single query - fresh call every time, no memory.
    
    Now includes prompt refinement step using Context7 best practices:
    1. Refine user query with AI
    2. Query ChromaDB with refined query
    3. Format context
    4. Query Claude with XML-formatted prompt
    
    Args:
        query: User's question
        db_path: Path to ChromaDB database
        use_thinking: Enable thinking mode
        use_hybrid: Use hybrid search
        use_cache: Use query caching
        use_reranking: Use result reranking
        where_filter: Optional metadata filter
        use_refinement: Enable query refinement (default: True)
        
    Returns:
        Tuple of (Claude's response, query)
    """
    # Step 1: Query ChromaDB (system prompt handles query understanding)
    results = query_chromadb(
        query,
        db_path=db_path,
        where=where_filter,
        use_reranking=use_reranking,
        use_cache=use_cache if not use_deep_research else False,  # Disable cache for deep research
        use_hybrid=use_hybrid or use_deep_research,  # Use hybrid in deep research
        use_deep_research=use_deep_research,
        deep_research_n_results=deep_research_n_results,
        max_final_results=max_final_results
    )
    
    # Step 2: Format context
    context = format_context(results)
    
    # Step 3: Query Claude with system prompt
    response = query_claude_with_system_prompt(
        query=query,
        context=context,
        use_thinking=use_thinking
    )
    
    return response, query  # No longer using separate refinement


def display_help():
    """Display help information."""
    help_text = """
[bold cyan]Available Commands:[/bold cyan]

  /help          Show this help message
  /exit, /quit   Exit the chatbot
  /clear         Clear the screen
  /db <path>     Change database path
  /hybrid        Toggle hybrid search (semantic + keyword)
  /thinking      Toggle thinking mode
  /cache         Toggle query caching
  /refinement    Toggle query refinement (Context7-guided)
  /deep-research Toggle exhaustive deep research mode (multi-query + RRF)

[bold cyan]Usage:[/bold cyan]
  Just type your question and press Enter. Each query is a fresh call to the vector database.
  The chatbot uses thinking mode by default for better reasoning.

[bold cyan]Examples:[/bold cyan]
  What do agents say when they have listings?
  How long does it take admins to complete tasks?
  Show me examples of deal processing workflows
"""
    console.print(Panel(help_text, title="[bold yellow]Help[/bold yellow]", border_style="yellow", box=box.ROUNDED))


def chat_loop(
    db_path: Optional[Path] = None,
    initial_thinking: bool = True,
    initial_hybrid: bool = False
):
    """
    Main chat loop - interactive chatbot interface.
    
    Args:
        db_path: Path to ChromaDB database
        initial_thinking: Initial thinking mode state
        initial_hybrid: Initial hybrid search state
    """
    if not RICH_AVAILABLE or not console:
        print("Error: Rich library is required for the chatbot interface.")
        print("Install with: pip install rich")
        sys.exit(1)
    
    # Determine database path
    db_path_obj = db_path if db_path else DEFAULT_DB_PATH
    
    # State
    use_thinking = initial_thinking
    use_hybrid = initial_hybrid
    use_cache = True
    use_reranking = True
    use_refinement = True  # Enable query refinement by default
    use_deep_research = True  # Enable deep research by default
    deep_research_n_results = 50
    max_final_results = 40
    query_count = 0
    
    # Clear screen and show welcome
    console.clear()
    
    # Welcome message
    welcome_text = """
[bold cyan]Welcome to Vector Database Chatbot![/bold cyan]

[dim]Each message queries the vector database with thinking mode enabled.[/dim]
[dim]No memory between queries - every call is fresh.[/dim]

Type your question or '/help' for commands.
"""
    console.print(Panel(welcome_text, title="[bold green]Welcome[/bold green]", border_style="green", box=box.ROUNDED))
    console.print()
    
    # Main chat loop
    while True:
        try:
            # Get user input with Rich prompt
            user_input = Prompt.ask(
                "[bold cyan]You[/bold cyan]",
                default=""
            ).strip()
            
            # Handle empty input
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if command in ["/exit", "/quit"]:
                    console.print("\n[yellow]Goodbye![/yellow]\n")
                    break
                elif command == "/help":
                    display_help()
                    continue
                elif command == "/clear":
                    console.clear()
                    continue
                elif command == "/db":
                    if args:
                        new_path = Path(args)
                        if new_path.exists():
                            db_path_obj = new_path
                            console.print(f"[green]Database changed to: {db_path_obj}[/green]")
                        else:
                            console.print(f"[red]Path not found: {new_path}[/red]")
                    else:
                        console.print(f"[cyan]Current database: {db_path_obj}[/cyan]")
                    continue
                elif command == "/hybrid":
                    use_hybrid = not use_hybrid
                    status = "enabled" if use_hybrid else "disabled"
                    console.print(f"[green]Hybrid search {status}[/green]")
                    continue
                elif command == "/thinking":
                    use_thinking = not use_thinking
                    status = "enabled" if use_thinking else "disabled"
                    console.print(f"[green]Thinking mode {status}[/green]")
                    continue
                elif command == "/cache":
                    use_cache = not use_cache
                    status = "enabled" if use_cache else "disabled"
                    console.print(f"[green]Query caching {status}[/green]")
                    continue
                elif command == "/refinement":
                    use_refinement = not use_refinement
                    status = "enabled" if use_refinement else "disabled"
                    console.print(f"[green]Query refinement {status}[/green]")
                    continue
                elif command == "/deep-research":
                    use_deep_research = not use_deep_research
                    status = "enabled" if use_deep_research else "disabled"
                    console.print(f"[green]Deep research mode {status}[/green]")
                    continue
                else:
                    console.print(f"[yellow]Unknown command: {command}. Type /help for help.[/yellow]")
                    continue
            
            # Process query
            query_count += 1
            
            # Show loading with Live display
            loading_layout = create_app_layout()
            loading_layout["header"].update(create_header(db_path_obj))
            loading_layout["footer"].update(create_footer(f"Processing query #{query_count}..."))
            loading_layout["main"].update(create_loading_panel("Querying vector database..."))
            loading_layout["input_area"].update(Panel(f"[dim]Query: {user_input[:60]}{'...' if len(user_input) > 60 else ''}[/dim]", box=box.ROUNDED))
            
            with Live(loading_layout, refresh_per_second=10, screen=False) as live:
                try:
                    # Step 1: Refine query
                    loading_layout["main"].update(create_loading_panel("Refining query with AI..."))
                    loading_layout["footer"].update(create_footer(f"Step 1/4: Refining query..."))
                    live.update(loading_layout)
                    
                    # Process query (now includes refinement and deep research)
                    response, refined_query = process_query(
                        query=user_input,
                        db_path=db_path_obj,
                        use_thinking=use_thinking,
                        use_hybrid=use_hybrid,
                        use_cache=use_cache,
                        use_reranking=use_reranking,
                        use_refinement=True,
                        use_deep_research=use_deep_research,
                        deep_research_n_results=deep_research_n_results,
                        max_final_results=max_final_results
                    )
                    
                    # Display result with refined query info
                    display_query = user_input
                    if refined_query != user_input:
                        display_query = f"{user_input}\n\n[dim]Refined: {refined_query}[/dim]"
                    
                    result_layout = create_chat_message(display_query, response, query_count)
                    loading_layout["main"].update(result_layout)
                    loading_layout["footer"].update(create_footer(f"Query #{query_count} complete • Ready for next question"))
                    live.update(loading_layout)
                    
                except Exception as e:
                    error_panel = Panel(
                        f"[bold red]Error:[/bold red] {e}",
                        title="[bold red]Error[/bold red]",
                        border_style="red",
                        box=box.ROUNDED
                    )
                    loading_layout["main"].update(error_panel)
                    loading_layout["footer"].update(create_footer("Error occurred"))
                    live.update(loading_layout)
            
            # Small pause to show result
            import time
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type /exit to quit or continue chatting.[/yellow]\n")
            continue
        except EOFError:
            console.print("\n[yellow]Goodbye![/yellow]\n")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Interactive CLI chatbot for querying the vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --db-path conductor_db
  %(prog)s --no-thinking --no-hybrid

Commands in chat:
  /help          Show help
  /exit          Exit chatbot
  /clear         Clear screen
  /db <path>     Change database
  /hybrid        Toggle hybrid search
  /thinking      Toggle thinking mode
        """
    )
    
    parser.add_argument(
        "--db-path",
        help=f"Path to ChromaDB database (default: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="Disable thinking mode (default: enabled)"
    )
    parser.add_argument(
        "--no-hybrid",
        action="store_true",
        help="Disable hybrid search (default: disabled)"
    )
    
    args = parser.parse_args()
    
    # Determine database path
    db_path_obj = Path(args.db_path) if args.db_path else DEFAULT_DB_PATH
    
    # Start chat loop
    chat_loop(
        db_path=db_path_obj,
        initial_thinking=not args.no_thinking,
        initial_hybrid=not args.no_hybrid
    )


if __name__ == "__main__":
    main()

