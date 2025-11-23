"""
Beautiful app-like CLI for querying the vector database with thinking mode.

Designed using Context7 best practices - full-screen TUI that adapts to terminal size.
"""

import os
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
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
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
from conductor.monitoring import get_metrics_summary
from conductor.cache import get_cache_stats

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


def create_header(query: str, db_path: Path) -> Panel:
    """Create app header."""
    header_text = Text()
    header_text.append("🔍 ", style="bold cyan")
    header_text.append("Vector Database Query", style="bold white")
    header_text.append(" • ", style="dim")
    header_text.append("Thinking Mode", style="bold green")
    
    subtitle = f"Query: {query[:60]}{'...' if len(query) > 60 else ''} | DB: {db_path.name}"
    
    return Panel(
        Align.center(header_text, vertical="middle"),
        subtitle=subtitle,
        style="bold white on blue",
        box=box.ROUNDED,
        height=3
    )


def create_footer(status: str = "Ready") -> Panel:
    """Create app footer."""
    footer_text = Text()
    footer_text.append("💡 ", style="bold yellow")
    footer_text.append("Tip: ", style="bold")
    footer_text.append(status, style="dim")
    footer_text.append(" • ", style="dim")
    footer_text.append("Press Ctrl+C to exit", style="dim")
    
    return Panel(
        footer_text,
        style="white on dark_green",
        box=box.ROUNDED,
        height=3
    )


def create_loading_layout(query: str, db_path: Path, stage: str) -> Layout:
    """Create loading layout."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    
    layout["header"].update(create_header(query, db_path))
    layout["footer"].update(create_footer(f"Status: {stage}"))
    
    # Loading content
    loading_panel = Panel(
        Align.center(
            f"\n[bold cyan]{stage}[/bold cyan]\n\n[dim]Please wait...[/dim]",
            vertical="middle"
        ),
        box=box.ROUNDED,
        border_style="cyan"
    )
    layout["main"].update(loading_panel)
    
    return layout


def create_result_layout(query: str, db_path: Path, response: str, metrics: Optional[Dict] = None) -> Layout:
    """Create result layout that adapts to terminal size."""
    layout = Layout()
    
    # Split into header, main content, and footer
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )
    
    # Update header
    layout["header"].update(create_header(query, db_path))
    
    # Update footer
    layout["footer"].update(create_footer("Query complete • Results displayed above"))
    
    # Format response as markdown
    markdown_content = f"""# Query Result

**Question:** {query}

---

{response}

---

*Generated from vector database with thinking mode enabled*
"""
    
    markdown = Markdown(markdown_content, code_theme="monokai")
    
    # Create main content panel that adapts to terminal width
    main_panel = Panel(
        markdown,
        title="[bold cyan]Response[/bold cyan]",
        subtitle="[dim]Thinking mode • Context7-guided[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    
    layout["main"].update(main_panel)
    
    return layout


def create_metrics_layout(metrics: Dict, cache_stats: Dict) -> Layout:
    """Create metrics layout."""
    from rich.table import Table
    
    layout = Layout()
    layout.split_column(
        Layout(name="metrics"),
        Layout(name="cache")
    )
    
    # Metrics table
    metrics_table = Table(title="Query Metrics", show_header=True, header_style="bold magenta", box=box.ROUNDED)
    metrics_table.add_column("Metric", style="cyan", no_wrap=True)
    metrics_table.add_column("Value", style="green", justify="right")
    
    metrics_table.add_row("Total Queries", str(metrics['queries']['total']))
    metrics_table.add_row("Success Rate", f"{metrics['queries']['success_rate']:.2%}")
    metrics_table.add_row("Avg Latency", f"{metrics['queries']['avg_latency_seconds']:.3f}s")
    metrics_table.add_row("P95 Latency", f"{metrics['queries']['p95_latency_seconds']:.3f}s")
    
    # Cache stats table
    cache_table = Table(title="Cache Statistics", show_header=True, header_style="bold blue", box=box.ROUNDED)
    cache_table.add_column("Stat", style="cyan", no_wrap=True)
    cache_table.add_column("Value", style="green", justify="right")
    
    cache_table.add_row("Total Entries", str(cache_stats['total_entries']))
    cache_table.add_row("Valid Entries", str(cache_stats['valid_entries']))
    cache_table.add_row("TTL", f"{cache_stats['ttl_seconds']}s")
    
    layout["metrics"].update(Panel(metrics_table, border_style="magenta", box=box.ROUNDED))
    layout["cache"].update(Panel(cache_table, border_style="blue", box=box.ROUNDED))
    
    return layout


def main():
    """Main CLI entry point with app-like interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Query the vector database - Beautiful app-like TUI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "How did we handle the 156 Seymour negotiation?"
  %(prog)s "What do agents say when they have listings?" --db-path conductor_db
  %(prog)s "Show me admin task completion times" --hybrid --metrics
        """
    )
    
    parser.add_argument(
        "query",
        help="Your question to query the vector database"
    )
    parser.add_argument(
        "--db-path",
        help=f"Path to ChromaDB database (default: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        "--filter-files",
        action="store_true",
        help="Only return sessions with file attachments"
    )
    parser.add_argument(
        "--no-reranking",
        action="store_true",
        help="Disable result reranking"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable query caching"
    )
    parser.add_argument(
        "--hybrid",
        action="store_true",
        help="Use hybrid search (semantic + keyword)"
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        default=True,
        help="Enable thinking mode (default: enabled)"
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="Disable thinking mode"
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Show performance metrics"
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Plain text output (no Rich formatting)"
    )
    
    args = parser.parse_args()
    
    # Handle thinking mode
    use_thinking = args.thinking and not args.no_thinking
    
    # Determine database path
    db_path_obj = Path(args.db_path) if args.db_path else DEFAULT_DB_PATH
    
    # Fallback to plain text if Rich not available or --plain flag
    if args.plain or not RICH_AVAILABLE or not console:
        # Use original ask.py functionality
        from conductor.ask import main as ask_main
        ask_main(
            args.query,
            db_path=str(db_path_obj),
            filter_files=args.filter_files,
            use_reranking=not args.no_reranking,
            use_cache=not args.no_cache,
            use_hybrid=args.hybrid,
            use_thinking=use_thinking,
            show_metrics=args.metrics
        )
        return
    
    try:
        # Build metadata filter if requested
        where_filter = None
        if args.filter_files:
            where_filter = {"file_count": {"$gt": 0}}

        # Use Live display for app-like experience
        with Live(create_loading_layout(args.query, db_path_obj, "Initializing..."), 
                  refresh_per_second=10, 
                  screen=True) as live:
            
            # Step 1: Query ChromaDB
            live.update(create_loading_layout(args.query, db_path_obj, "Querying vector database..."))
            results = query_chromadb(
                args.query,
                db_path=db_path_obj,
                where=where_filter,
                use_reranking=not args.no_reranking,
                use_cache=not args.no_cache,
                use_hybrid=args.hybrid
            )

            # Step 2: Format context
            live.update(create_loading_layout(args.query, db_path_obj, "Formatting context..."))
            context = format_context(results)

            # Step 3: Query Claude
            stage = "Querying Claude with thinking mode..." if use_thinking else "Querying Claude..."
            live.update(create_loading_layout(args.query, db_path_obj, stage))
            response = query_claude(args.query, context, use_thinking=use_thinking)

            # Step 4: Display results
            if args.metrics:
                try:
                    metrics = get_metrics_summary()
                    cache_stats = get_cache_stats()
                    
                    # Create combined layout with results and metrics
                    combined_layout = Layout()
                    combined_layout.split_column(
                        Layout(name="header", size=3),
                        Layout(name="main"),
                        Layout(name="metrics_section", size=12),
                        Layout(name="footer", size=3)
                    )
                    
                    combined_layout["header"].update(create_header(args.query, db_path_obj))
                    combined_layout["footer"].update(create_footer("Query complete • Scroll to see metrics"))
                    
                    # Main response
                    markdown_content = f"""# Query Result

**Question:** {args.query}

---

{response}

---

*Generated from vector database with thinking mode enabled*
"""
                    markdown = Markdown(markdown_content, code_theme="monokai")
                    combined_layout["main"].update(Panel(
                        markdown,
                        title="[bold cyan]Response[/bold cyan]",
                        border_style="cyan",
                        box=box.ROUNDED,
                        padding=(1, 2)
                    ))
                    
                    # Metrics section
                    metrics_layout = create_metrics_layout(metrics, cache_stats)
                    combined_layout["metrics_section"].update(metrics_layout)
                    
                    live.update(combined_layout)
                except Exception as e:
                    logger.debug(f"Could not display metrics: {e}")
                    live.update(create_result_layout(args.query, db_path_obj, response))
            else:
                live.update(create_result_layout(args.query, db_path_obj, response))
            
            # Keep display until user exits
            import time
            time.sleep(0.1)  # Brief pause to show final result
            
    except KeyboardInterrupt:
        if console:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        else:
            print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        if console:
            # Show error in app-like format
            error_layout = Layout()
            error_layout.split_column(
                Layout(name="header", size=3),
                Layout(name="main"),
                Layout(name="footer", size=3)
            )
            error_layout["header"].update(create_header(args.query, db_path_obj))
            error_layout["footer"].update(create_footer("Error occurred"))
            error_layout["main"].update(Panel(
                f"[bold red]Error:[/bold red] {e}",
                title="[bold red]Error[/bold red]",
                border_style="red",
                box=box.ROUNDED
            ))
            console.print(error_layout)
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
