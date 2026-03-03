"""Entry point: start FastAPI in background, then launch the CLI chatbot."""

import asyncio
import os
import sys
import threading
import time

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uvicorn
from rich.console import Console

from src.config import settings

console = Console()


def start_api_server():
    """Run FastAPI server in a background thread."""
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level="warning",
    )


async def main():
    # Start API server in background
    console.print("[dim]Starting API server...[/dim]")
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # Wait for server to be ready
    import httpx
    for _ in range(30):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://{settings.api_host}:{settings.api_port}/health"
                )
                if resp.status_code == 200:
                    break
        except httpx.ConnectError:
            await asyncio.sleep(0.5)
    else:
        console.print("[red]Failed to start API server[/red]")
        return

    console.print("[dim]API server ready.[/dim]")

    # Start CLI
    from src.chatbot.cli import run_cli
    await run_cli()


if __name__ == "__main__":
    asyncio.run(main())
