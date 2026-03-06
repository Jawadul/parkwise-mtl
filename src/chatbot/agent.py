"""OpenAI tool-calling agent for the parking chatbot."""

import json

from openai import OpenAI

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

# Convert tools to OpenAI function format
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }
    for tool in TOOLS
]


class ParkingAgent:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.model = "gpt-4o-mini"

    async def chat(self, user_message: str) -> str:
        """Send a message and handle tool calls. Returns the final text response."""
        self.messages.append({"role": "user", "content": user_message})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=OPENAI_TOOLS,
        )

        message = response.choices[0].message

        # Handle tool call loop
        while message.tool_calls:
            self.messages.append(message)

            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = await execute_tool(tool_call.function.name, args)
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=OPENAI_TOOLS,
            )
            message = response.choices[0].message

        self.messages.append({"role": "assistant", "content": message.content})
        return message.content or ""

    def reset(self):
        """Clear conversation history."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
