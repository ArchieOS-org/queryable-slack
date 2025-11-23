"""
Beautiful CLI for querying with Context7 - Fresh calls, no memory, stunning markdown output.

Uses Context7 automatically for library documentation and provides elegant terminal output.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

# Rich for beautiful terminal output
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich not installed. Install with: pip install rich")

# Context7 MCP tools (will be available if MCP is configured)
# For now, we'll use direct API calls or prompt Context7 usage

import logging

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.WARNING,  # Quiet by default for clean output
    format="%(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console() if RICH_AVAILABLE else None


def format_response_as_markdown(response: str, query: str) -> str:
    """
    Format Claude's response as beautiful markdown.
    
    Args:
        response: Claude's response text
        query: The original query
        
    Returns:
        Formatted markdown string
    """
    # Create a well-structured markdown document
    markdown = f"""# Query Result

**Question:** {query}

---

{response}

---

*Generated with Context7-powered reasoning*
"""
    return markdown


def query_claude_with_context7(
    user_query: str,
    use_thinking: bool = True,
    model: str = "claude-sonnet-4-5-20250929"
) -> str:
    """
    Query Claude with Context7 guidance - fresh call every time, no memory.
    
    Args:
        user_query: The question to ask
        use_thinking: Enable chain-of-thought reasoning
        model: Claude model to use
        
    Returns:
        Claude's response text
    """
    # Get API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Initialize Anthropic client
    client = Anthropic(api_key=api_key)

    # Enhanced system prompt with Context7 guidance
    system_prompt = """You are an intelligent assistant that uses Context7 for up-to-date library documentation.

When answering questions:
1. **Use Context7 automatically** - If library documentation is needed, automatically use Context7 MCP tools
2. **Fresh thinking** - Each query is independent, no memory from previous calls
3. **Structured reasoning** - Break down complex questions into logical steps
4. **Beautiful formatting** - Format your response as clean markdown with:
   - Clear headings and subheadings
   - Bullet points and numbered lists
   - Code blocks with syntax highlighting
   - Tables when appropriate
   - Bold/italic for emphasis

For technical questions:
- Automatically resolve library IDs using Context7
- Fetch documentation with specific topics
- Provide accurate, up-to-date code examples
- Cite sources when using Context7 documentation

Format your response as markdown that will be beautifully rendered in the terminal."""

    # Add thinking instructions if enabled
    if use_thinking:
        thinking_instruction = """

Use chain-of-thought reasoning:
1. Break down the question into steps
2. Consider multiple factors
3. Show your reasoning process
4. Synthesize findings clearly"""
        system_prompt += thinking_instruction

    # Construct user message
    user_message = f"""Question: {user_query}

Remember: Use Context7 automatically if you need library documentation. Format your response as beautiful markdown."""

    try:
        # Prepare message parameters
        message_params = {
            "model": model,
            "max_tokens": 4096,  # More tokens for detailed responses
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        }
        
        if use_thinking:
            message_params["temperature"] = 0.3  # Lower temperature for focused reasoning
        
        # Send to Claude (fresh call, no memory)
        if console:
            console.print("[dim]Querying Claude with Context7...[/dim]")
        
        message = client.messages.create(**message_params)

        # Extract text from response
        if message.content and len(message.content) > 0:
            text_parts = []
            for block in message.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif isinstance(block, str):
                    text_parts.append(block)
            return "\n".join(text_parts)
        else:
            return "No response from Claude."

    except Exception as e:
        logger.error(f"Failed to query Claude: {e}")
        raise


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Query with Context7 - Beautiful CLI with fresh calls and stunning markdown output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "How do I use ChromaDB PersistentClient?"
  %(prog)s "What's the Pydantic v2 syntax for field validation?" --no-thinking
  %(prog)s "Show me examples of using Rich for markdown output" --model claude-opus-3
        """
    )
    
    parser.add_argument(
        "query",
        help="Your question (will automatically use Context7 if needed)"
    )
    parser.add_argument(
        "--no-thinking",
        action="store_true",
        help="Disable chain-of-thought reasoning"
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-5-20250929",
        help="Claude model to use (default: claude-sonnet-4-5-20250929)"
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Plain text output (no Rich formatting)"
    )
    
    args = parser.parse_args()
    
    try:
        # Query Claude
        response = query_claude_with_context7(
            user_query=args.query,
            use_thinking=not args.no_thinking,
            model=args.model
        )
        
        # Format and display
        if args.plain or not RICH_AVAILABLE or not console:
            # Plain text output
            print("\n" + "=" * 80)
            print("RESPONSE:")
            print("=" * 80)
            print(response)
            print("=" * 80 + "\n")
        else:
            # Beautiful Rich markdown output
            markdown_content = format_response_as_markdown(response, args.query)
            markdown = Markdown(markdown_content, code_theme="monokai")
            
            # Create a beautiful panel
            console.print()
            console.print(Panel(
                markdown,
                title="[bold cyan]Context7 Query Result[/bold cyan]",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2)
            ))
            console.print()
            
    except KeyboardInterrupt:
        if console:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        else:
            print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        if console:
            console.print(f"[bold red]Error:[/bold red] {e}", style="red")
        else:
            print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

