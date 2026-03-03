"""Rich CLI interface for the ParkWise MTL chatbot."""

import asyncio

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.chatbot.agent import ParkingAgent

console = Console()


WELCOME_BANNER = """\
[bold blue]╔══════════════════════════════════════════════════╗
║           🅿  ParkWise MTL  🅿                    ║
║     Montréal Parking Assistant                   ║
╚══════════════════════════════════════════════════╝[/bold blue]

[dim]Ask me about parking in Montréal:
  • Paid parking locations and rates
  • Parking signs and regulations
  • Snow-removal parking lots

Commands: /reset (clear history) · /quit (exit)[/dim]
"""


async def run_cli():
    """Run the interactive CLI chatbot."""
    console.print(WELCOME_BANNER)

    agent = ParkingAgent()
    session = PromptSession(history=InMemoryHistory())

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: session.prompt("\n🅿 You > ")
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Au revoir![/dim]")
            break

        text = user_input.strip()
        if not text:
            continue

        if text.lower() in ("/quit", "/exit", "quit", "exit"):
            console.print("[dim]Au revoir![/dim]")
            break

        if text.lower() in ("/reset", "/clear"):
            agent.reset()
            console.print("[yellow]Conversation cleared.[/yellow]")
            continue

        # Send to agent
        with console.status("[cyan]Thinking...[/cyan]"):
            try:
                response = await agent.chat(text)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                continue

        console.print()
        console.print(Panel(Markdown(response), title="ParkWise MTL", border_style="blue"))
