"""
Full-screen, scrollable, resizable terminal app for querying the vector database.

Uses Context7 best practices:
- console.screen() for full-screen terminal takeover
- Scrollable containers for long content
- Layout that adapts to terminal size
- Live updates with screen=True
"""

# CRITICAL: Set TOKENIZERS_PARALLELISM before any tokenizer imports
# This prevents warnings when tokenizers are used after forking
import os
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

import sys
import re
from pathlib import Path
from typing import Optional, Dict, List, TYPE_CHECKING
from collections import deque

from anthropic import Anthropic
from dotenv import load_dotenv

# Rich for beautiful terminal output
try:
    from rich.console import Console, ConsoleOptions
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.prompt import Prompt
    from rich.text import Text
    from rich.align import Align
    from rich.measure import Measurement
    from rich import box
    RICH_AVAILABLE = True
except ImportError as e:
    RICH_AVAILABLE = False
    # Create dummy types for type checking
    Console = None  # type: ignore
    ConsoleOptions = None  # type: ignore
    Measurement = None  # type: ignore
    # Don't print warning here - will be handled in chat_loop if needed

# Import from ask.py
from conductor.ask import (
    query_chromadb,
    format_context,
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


def clean_escape_sequences(text: str) -> str:
    """Remove ANSI escape sequences from text (arrow keys, etc.)."""
    if not text:
        return ""
    
    # Remove ANSI escape sequences like \x1b[A, \x1b[B, etc.
    # Pattern: ESC (0x1b) followed by [ and optional numbers/semicolons and a letter
    # Also handle standalone ESC characters
    cleaned = text
    
    # Remove ANSI CSI sequences: ESC[ followed by numbers/semicolons and a letter
    cleaned = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', cleaned)
    
    # Remove standalone ESC characters (from double-escape)
    cleaned = cleaned.replace('\x1b', '')
    
    # Remove other control characters except newline, tab, carriage return
    cleaned = ''.join(c for c in cleaned if ord(c) >= 32 or c in '\n\t\r')
    
    return cleaned


def get_input_with_escape_handling(prompt: str = "") -> str:
    """
    Custom input handler that:
    - Filters out arrow key escape sequences (^[[A, ^[[B, etc.)
    - Handles escape key (twice to clear input)
    - Wraps text display to terminal width
    - Uses Context7 best practices for terminal input
    """
    if not RICH_AVAILABLE or not console:
        return input(prompt)
    
    try:
        # Use Rich's console.input() which handles escape sequences better
        # and works better with screen mode
        user_input = console.input(prompt)
        
        # Clean any escape sequences that might have leaked through
        cleaned_input = clean_escape_sequences(user_input)
        
        # Check for double escape pattern (user pressed ESC twice to clear)
        if '\x1b' in user_input:
            escape_count = user_input.count('\x1b')
            # If multiple escapes and cleaned result is empty or much shorter, treat as clear
            if escape_count >= 2:
                if len(cleaned_input.strip()) == 0 or len(cleaned_input) < len(user_input) - 3:
                    return ""  # Double escape to clear
        
        return cleaned_input.strip()
        
    except (KeyboardInterrupt, EOFError):
        raise
    except Exception:
        # Fallback to standard input
        try:
            return input(prompt).strip()
        except:
            return ""


class ScrollableContent:
    """Scrollable content container that adapts to terminal size."""
    
    def __init__(self, content: str = ""):
        self.content = content
        self.scroll_position = 0
        self.lines = []
        self._update_lines()
    
    def _update_lines(self):
        """Update internal line representation."""
        if self.content:
            self.lines = self.content.split('\n')
        else:
            self.lines = []
    
    def set_content(self, content: str):
        """Set new content and reset scroll position."""
        self.content = content
        self.scroll_position = 0
        self._update_lines()
    
    def scroll_up(self, lines: int = 1):
        """Scroll up."""
        self.scroll_position = max(0, self.scroll_position - lines)
    
    def scroll_down(self, lines: int = 1):
        """Scroll down."""
        max_scroll = max(0, len(self.lines) - 1)
        self.scroll_position = min(max_scroll, self.scroll_position + lines)
    
    def get_visible_lines(self, height: int) -> List[str]:
        """Get visible lines for current scroll position."""
        if not self.lines:
            return []
        
        end_pos = min(self.scroll_position + height, len(self.lines))
        return self.lines[self.scroll_position:end_pos]
    
    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        """Measure required dimensions."""
        if not RICH_AVAILABLE:
            return Measurement(0, 80)  # Fallback
        if self.lines:
            max_width = max(len(line) for line in self.lines) if self.lines else 0
            return Measurement(max_width, options.max_width)
        return Measurement(0, options.max_width)
    
    def __rich__(self) -> Text:
        """Render visible content."""
        if not RICH_AVAILABLE:
            return Text("Rich not available", style="dim")
        
        # Get terminal height from console
        terminal_height = console.height if console else 24
        visible = self.get_visible_lines(terminal_height - 2)  # Account for borders
        
        if not visible:
            return Text("", style="dim")
        
        text = Text("\n".join(visible))
        
        # Add scroll indicator
        if len(self.lines) > terminal_height - 2:
            if self.scroll_position > 0:
                text = Text("↑ Scroll up for more\n", style="dim cyan") + text
            if self.scroll_position + terminal_height - 2 < len(self.lines):
                text = text + Text("\n↓ Scroll down for more", style="dim cyan")
        
        return text


def create_fullscreen_layout(db_path: Path, chat_history: List[tuple], scrollable_content: ScrollableContent) -> Layout:
    """Create full-screen layout that adapts to terminal size."""
    layout = Layout()
    
    # Split into header, main content area, input, and footer
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="input_area", size=3),
        Layout(name="footer", size=2)
    )
    
    # Header
    header_text = Text()
    header_text.append("🔍 ", style="bold cyan")
    header_text.append("Vector Database Chatbot", style="bold white")
    header_text.append(" • ", style="dim")
    header_text.append("Thinking Mode", style="bold green")
    header_text.append(" • ", style="dim")
    header_text.append("Full Screen", style="bold yellow")
    
    subtitle = f"DB: {db_path.name} | /help | /exit | ↑↓ Scroll | Resize terminal"
    
    layout["header"].update(Panel(
        Align.center(header_text, vertical="middle"),
        subtitle=subtitle,
        style="bold white on blue",
        box=box.ROUNDED,
        height=3
    ))
    
    # Main content area - scrollable
    if scrollable_content.content:
        # Get terminal height for scrolling
        terminal_height = console.height if console else 24
        visible_content = scrollable_content.get_visible_lines(terminal_height - 8)  # Account for header, input, footer
        
        # Render content - convert markdown syntax to Rich Text
        content_text = "\n".join(visible_content) if visible_content else "[dim]No content[/dim]"
        
        # Create a renderable that handles markdown properly
        # Use Text to render the content with markdown support
        from rich.text import Text
        renderable_content = Text.from_markup(content_text) if content_text else Text("[dim]No content[/dim]")
        
        content_panel = Panel(
            renderable_content,
            title="[bold cyan]Chat History[/bold cyan]",
            subtitle=f"[dim]Showing {len(visible_content)}/{len(scrollable_content.lines)} lines • Use ↑↓ to scroll[/dim]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2)
        )
    else:
        content_panel = Panel(
            "[dim]Start a conversation by typing a question below...[/dim]",
            title="[bold cyan]Welcome[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        )
    
    layout["main"].update(content_panel)
    
    # Input area
    layout["input_area"].update(Panel(
        "[bold cyan]You:[/bold cyan] [dim]Type your question and press Enter[/dim]",
        border_style="yellow",
        box=box.ROUNDED,
        height=3
    ))
    
    # Footer
    footer_text = Text()
    footer_text.append("💡 ", style="bold yellow")
    footer_text.append("Ready • Terminal adapts to size • All output visible", style="dim")
    
    layout["footer"].update(Panel(
        footer_text,
        style="white on dark_green",
        box=box.ROUNDED,
        height=2
    ))
    
    return layout


def format_chat_message(user_query: str, response: str, query_num: int, refined_query: Optional[str] = None) -> str:
    """Format a chat message for display."""
    parts = []
    parts.append(f"\n{'='*80}\n")
    parts.append(f"[bold cyan]Query #{query_num}[/bold cyan]\n")
    parts.append(f"[bold]You:[/bold] {user_query}\n")
    
    if refined_query and refined_query != user_query:
        # Wrap refined query if too long
        terminal_width = console.width if console else 80
        if len(refined_query) > terminal_width - 20:
            # Split into multiple lines
            words = refined_query.split()
            lines = []
            current_line = []
            current_length = 0
            for word in words:
                if current_length + len(word) + 1 > terminal_width - 20:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    current_length = len(word)
                else:
                    current_line.append(word)
                    current_length += len(word) + 1
            if current_line:
                lines.append(" ".join(current_line))
            refined_display = "\n  ".join(lines)
            parts.append(f"[dim]Refined:[/dim] {refined_display}\n")
        else:
            parts.append(f"[dim]Refined:[/dim] {refined_query}\n")
    
    parts.append(f"\n[bold green]Assistant:[/bold green]\n")
    
    # Add response as-is (will be rendered as markdown in Panel)
    parts.append(response)
    parts.append(f"\n{'='*80}\n")
    
    return "\n".join(parts)


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
    """Process a single query."""
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


def chat_loop(
    db_path: Optional[Path] = None,
    initial_thinking: bool = True,
    initial_hybrid: bool = False
):
    """Main chat loop with full-screen terminal app."""
    if not RICH_AVAILABLE:
        print("Error: Rich library is required for the full-screen chatbot.")
        print("Install with: pip install rich")
        sys.exit(1)
    
    if not console:
        print("Error: Could not initialize Rich Console.")
        sys.exit(1)
    
    # Determine database path
    db_path_obj = db_path if db_path else DEFAULT_DB_PATH
    
    # State
    use_thinking = initial_thinking
    use_hybrid = initial_hybrid
    use_cache = True
    use_reranking = True
    use_refinement = True
    use_deep_research = True  # Enable deep research by default
    deep_research_n_results = 50
    max_final_results = 40
    query_count = 0
    chat_history: List[tuple] = []  # (user_query, response, refined_query)
    scrollable_content = ScrollableContent()
    
    # Use full-screen mode
    # Note: We'll exit screen mode temporarily for input to avoid escape sequence issues
    with console.screen() as screen:
        # Initial welcome
        welcome_text = """Welcome to Vector Database Chatbot!

Each message queries the vector database with thinking mode enabled.
No memory between queries - every call is fresh.

Type your question or '/help' for commands.
The terminal adapts to your window size automatically.
All output is scrollable - use ↑↓ keys to scroll through history.

Commands:
  /help          Show help
  /exit, /quit   Exit
  /clear         Clear history
  /db <path>     Change database
  /hybrid        Toggle hybrid search
  /thinking      Toggle thinking mode
  /refinement    Toggle query refinement
  /deep-research Toggle exhaustive deep research mode (multi-query + RRF)
"""
        
        scrollable_content.set_content(welcome_text)
        layout = create_fullscreen_layout(db_path_obj, chat_history, scrollable_content)
        screen.update(layout)
        
        # Main chat loop
        while True:
            try:
                # Update layout to show current state
                screen.update(layout)
                
                # Exit screen mode temporarily to get clean input
                # This is necessary because input() doesn't work well inside screen()
                # The screen context will be restored after input
                console.print()  # New line
                user_input = get_input_with_escape_handling("[bold cyan]You[/bold cyan]: ").strip()
                
                # Screen mode is automatically restored after input() completes
                if not user_input:
                    screen.update(layout)
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
                        help_text = """
Available Commands:

  /help          Show this help message
  /exit, /quit   Exit the chatbot
  /clear         Clear chat history
  /db <path>     Change database path
  /hybrid        Toggle hybrid search (semantic + keyword)
  /thinking      Toggle thinking mode
  /cache         Toggle query caching
  /refinement    Toggle query refinement (Context7-guided)

Usage:
  Just type your question and press Enter. Each query is a fresh call.
  The terminal adapts to your window size automatically.
  Use ↑↓ keys to scroll through chat history.

Examples:
  What do agents say when they have listings?
  How long does it take admins to complete tasks?
  Show me examples of deal processing workflows
"""
                        scrollable_content.set_content(help_text)
                        layout = create_fullscreen_layout(db_path_obj, chat_history, scrollable_content)
                        screen.update(layout)
                        continue
                    elif command == "/clear":
                        chat_history.clear()
                        scrollable_content.set_content(welcome_text)
                        layout = create_fullscreen_layout(db_path_obj, chat_history, scrollable_content)
                        screen.update(layout)
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
                        screen.update(layout)
                        continue
                    elif command == "/hybrid":
                        use_hybrid = not use_hybrid
                        status = "enabled" if use_hybrid else "disabled"
                        console.print(f"[green]Hybrid search {status}[/green]")
                        screen.update(layout)
                        continue
                    elif command == "/thinking":
                        use_thinking = not use_thinking
                        status = "enabled" if use_thinking else "disabled"
                        console.print(f"[green]Thinking mode {status}[/green]")
                        screen.update(layout)
                        continue
                    elif command == "/refinement":
                        use_refinement = not use_refinement
                        status = "enabled" if use_refinement else "disabled"
                        console.print(f"[green]Query refinement {status}[/green]")
                        screen.update(layout)
                        continue
                    elif command == "/deep-research":
                        use_deep_research = not use_deep_research
                        status = "enabled" if use_deep_research else "disabled"
                        console.print(f"[green]Deep research mode {status}[/green]")
                        screen.update(layout)
                        continue
                    else:
                        console.print(f"[yellow]Unknown command: {command}. Type /help for help.[/yellow]")
                        screen.update(layout)
                        continue
                
                # Process query
                query_count += 1
                
                # Show loading
                loading_text = f"Processing query #{query_count}...\n\n[dim]Refining query...[/dim]"
                scrollable_content.set_content(loading_text)
                layout = create_fullscreen_layout(db_path_obj, chat_history, scrollable_content)
                screen.update(layout)
                
                try:
                    # Process query
                    response, refined_query = process_query(
                        query=user_input,
                        db_path=db_path_obj,
                        use_thinking=use_thinking,
                        use_hybrid=use_hybrid,
                        use_cache=use_cache,
                        use_reranking=use_reranking,
                        use_refinement=use_refinement,
                        use_deep_research=use_deep_research,
                        deep_research_n_results=deep_research_n_results,
                        max_final_results=max_final_results
                    )
                    
                    # Add to history
                    chat_history.append((user_input, response, refined_query))
                    
                    # Format all chat history
                    history_text = welcome_text + "\n\n"
                    for i, (uq, resp, rq) in enumerate(chat_history, 1):
                        history_text += format_chat_message(uq, resp, i, rq)
                    
                    scrollable_content.set_content(history_text)
                    layout = create_fullscreen_layout(db_path_obj, chat_history, scrollable_content)
                    screen.update(layout)
                    
                except Exception as e:
                    error_text = f"[bold red]Error:[/bold red] {e}\n\n{history_text if chat_history else welcome_text}"
                    scrollable_content.set_content(error_text)
                    layout = create_fullscreen_layout(db_path_obj, chat_history, scrollable_content)
                    screen.update(layout)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]\n")
                screen.update(layout)
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
        description="Full-screen terminal chatbot for querying the vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --db-path conductor_db
  %(prog)s --no-thinking

The terminal app adapts to your window size automatically.
All output is scrollable - resize your terminal to see it adapt!
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

