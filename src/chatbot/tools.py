"""Tool definitions for the Claude chatbot — each tool calls a local FastAPI endpoint."""

import httpx

from src.config import settings

BASE_URL = f"http://{settings.api_host}:{settings.api_port}"

# Tool schemas for Claude
TOOLS = [
    {
        "name": "search_parking",
        "description": (
            "Search for paid parking spaces on a given street in Montréal. "
            "Returns parking space locations, types, and rates. "
            "Use this when the user asks about parking on a specific street."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "street": {
                    "type": "string",
                    "description": "Street name to search (e.g., 'Saint-Alexandre', 'Sainte-Catherine')",
                },
                "borough": {
                    "type": "string",
                    "description": "Optional borough/arrondissement to narrow results",
                },
                "mode": {
                    "type": "string",
                    "enum": ["search", "summary"],
                    "description": "Use 'summary' for counts and overview, 'search' for detailed list",
                },
            },
            "required": ["street"],
        },
    },
    {
        "name": "check_parking_rules",
        "description": (
            "Check parking rules and regulations at a specific location and time. "
            "Returns whether parking is allowed, payment required, rates, and max duration. "
            "Use this when the user asks about parking rules, restrictions, or rates at a location."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude"},
                "lon": {"type": "number", "description": "Longitude"},
                "at": {
                    "type": "string",
                    "description": "ISO datetime to check (e.g., '2025-01-15T19:00:00'). Defaults to now.",
                },
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "search_signs",
        "description": (
            "Search for parking signs on a given street. "
            "Returns sign codes (RPA) and their decoded descriptions. "
            "Use this to find what parking signs say on a street."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "street": {"type": "string", "description": "Street name to search"},
                "borough": {"type": "string", "description": "Optional borough"},
            },
            "required": ["street"],
        },
    },
    {
        "name": "find_snow_lots",
        "description": (
            "Find nearby snow-removal parking lots. "
            "Returns lots with capacity, free/paid status, and distance. "
            "Use this when the user asks about parking during snow removal operations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude"},
                "lon": {"type": "number", "description": "Longitude"},
                "radius_km": {
                    "type": "number",
                    "description": "Search radius in km (default 2)",
                },
            },
            "required": ["lat", "lon"],
        },
    },
]


async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by calling the corresponding FastAPI endpoint."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        try:
            if name == "search_parking":
                mode = args.get("mode", "summary")
                params = {"street": args["street"], "limit": 20}
                if args.get("borough"):
                    params["borough"] = args["borough"]
                endpoint = f"/parking/{mode}"
                resp = await client.get(endpoint, params=params)

            elif name == "check_parking_rules":
                params = {"lat": args["lat"], "lon": args["lon"]}
                if args.get("at"):
                    params["at"] = args["at"]
                resp = await client.get("/parking/rules", params=params)

            elif name == "search_signs":
                params = {"street": args["street"]}
                if args.get("borough"):
                    params["borough"] = args["borough"]
                resp = await client.get("/signs/search", params=params)

            elif name == "find_snow_lots":
                params = {"lat": args["lat"], "lon": args["lon"]}
                if args.get("radius_km"):
                    params["radius_km"] = args["radius_km"]
                resp = await client.get("/snow/lots", params=params)

            else:
                return f"Unknown tool: {name}"

            resp.raise_for_status()
            return resp.text

        except httpx.HTTPStatusError as e:
            return f"API error {e.response.status_code}: {e.response.text}"
        except httpx.ConnectError:
            return "Error: Could not connect to the API. Is the server running?"
