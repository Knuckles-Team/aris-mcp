"""Main FastMCP server and tool registration for aris-mcp."""

import os
import sys
from typing import Any

from agent_utilities.base_utilities import to_boolean
from agent_utilities.mcp_utilities import create_mcp_server, load_config
from fastmcp.utilities.logging import get_logger
from starlette.requests import Request
from starlette.responses import JSONResponse

from aris_mcp.mcp.mcp_aris import register_aris_tools

__version__ = "0.1.0"
logger = get_logger(name="aris_mcp")


def get_mcp_instance() -> tuple[Any, ...]:
    load_config()
    args, mcp, middlewares = create_mcp_server(
        name="ARIS MCP",
        version=__version__,
        instructions=(
            "ARIS MCP Server - Software AG ARIS process/enterprise-architecture "
            "models over the ARIS REST API: model inventory, per-model EPC "
            "objects (functions/events/rule operators) and control-flow "
            "connections, attribute read, and (gated) attribute write for "
            "outbound KG enrichment."
        ),
    )

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "OK"})

    if to_boolean(os.getenv("ARISTOOL", "True")):
        register_aris_tools(mcp)

    for mw in middlewares:
        mcp.add_middleware(mw)
    return mcp, args, middlewares


def mcp_server() -> None:
    mcp, args, middlewares = get_mcp_instance()
    print(f"ARIS MCP v{__version__}", file=sys.stderr)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    mcp_server()
