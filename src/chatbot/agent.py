"""Claude tool-calling agent for the parking chatbot."""

import json

import anthropic

from src.chatbot.tools import TOOLS, execute_tool
from src.config import settings

SYSTEM_PROMPT = """\
You are ParkWise MTL, a helpful parking assistant for Montréal.

You help users find information about:
- Paid street parking locations, rates, and schedules
- Parking signs and their meanings (RPA codes)
- Parking regulations and restrictions at specific locations/times
- Snow-removal parking lots during winter operations

Important limitations (always clarify when relevant):
- You CANNOT tell if a specific spot is currently occupied (no real-time occupancy data)
- You CANNOT reserve or book parking spots
- Your data comes from open datasets and may not reflect very recent changes
- For emergencies or towing, contact 311 or the borough directly

Always use tools to look up actual data — never guess parking rules or rates.
When giving directions or locations, include lat/lon coordinates when available.
Respond in the same language the user writes in (French or English).
"""


class ParkingAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.messages: list[dict] = []
        self.model = "claude-sonnet-4-20250514"

    async def chat(self, user_message: str) -> str:
        """Send a message and handle tool calls. Returns the final text response."""
        self.messages.append({"role": "user", "content": user_message})

        # Call Claude with tools
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=self.messages,
        )

        # Handle tool use loop
        while response.stop_reason == "tool_use":
            # Collect assistant message
            self.messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await execute_tool(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            self.messages.append({"role": "user", "content": tool_results})

            # Get next response
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=self.messages,
            )

        # Extract final text
        self.messages.append({"role": "assistant", "content": response.content})
        text_parts = [b.text for b in response.content if hasattr(b, "text")]
        return "\n".join(text_parts)

    def reset(self):
        """Clear conversation history."""
        self.messages = []
