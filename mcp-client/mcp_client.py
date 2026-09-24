#!/usr/bin/env python3
"""
Infinity Analytics MCP Client

A Model Context Protocol (MCP) client for querying Avaya Infinity Contact Center Analytics.
Enables AI agents (Claude Desktop, Cursor, etc.) to securely access analytics data through
natural language queries with structured output support.

Usage:
    python mcp_client.py

Configuration:
    Required environment variables (set in agent configuration):
        INFINITY_URL    - Infinity contact center URL (e.g. https://core.your-instance.ec.avayacloud.com/)
        CLIENT_ID       - OAuth client ID
        CLIENT_SECRET   - OAuth client secret

Authentication:
    Uses OAuth 2.0 client credentials grant (M2M).

Version: 2.0.0
"""

import asyncio
import contextlib
import os
import sys
import time
from typing import Dict

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent

__version__ = "2.0.0"

MCP_PATH = "/api/mcp/v1/mcp"
TOKEN_PATH = "/auth/realms/avaya/protocol/openid-connect/token"

SSE_READ_TIMEOUT = 300.0
DEFAULT_TIMEOUT = 30.0


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


class OAuthClientCredentials:
    """OAuth 2.0 client credentials token manager.

    Fetches and caches bearer tokens from a Keycloak token endpoint,
    refreshing automatically before expiry. All token fetches use an
    async httpx client so the event loop is never blocked.
    """

    def __init__(self, token_url: str, client_id: str, client_secret: str):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._expires_at: float = 0

    async def _fetch_token(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["access_token"]
            self._expires_at = time.time() + data.get("expires_in", 300) - 30

    async def on_request(self, request: httpx.Request) -> None:
        """httpx event hook — refreshes the token and sets the header."""
        if not self._token or time.time() >= self._expires_at:
            await self._fetch_token()
        request.headers["Authorization"] = f"Bearer {self._token}"


def load_configuration() -> Dict[str, str]:
    """Load and validate configuration from environment.

    Returns:
        Dictionary with configuration values:
            - host: Infinity global URL
            - mcp_url: Derived MCP server endpoint
            - token_url: Derived OAuth token endpoint
            - client_id: OAuth client ID
            - client_secret: OAuth client secret

    Raises:
        ConfigurationError: If required configuration is missing
    """
    host = os.getenv("INFINITY_URL")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    missing = []
    if not host:
        missing.append("INFINITY_URL")
    if not client_id:
        missing.append("CLIENT_ID")
    if not client_secret:
        missing.append("CLIENT_SECRET")

    if missing:
        raise ConfigurationError(
            f"Missing required configuration: {', '.join(missing)}\n"
            "Please set these in your AI agent configuration.\n"
            "See README.md for setup instructions."
        )

    host = host.rstrip("/")

    return {
        "host": host,
        "mcp_url": f"{host}{MCP_PATH}",
        "token_url": f"{host}{TOKEN_PATH}",
        "client_id": client_id,
        "client_secret": client_secret,
    }


async def serve_stdio():
    """Run as STDIO MCP server for AI agent integration.

    This mode enables AI agents like Claude Desktop and Cursor to query
    analytics data through natural language by exposing MCP tools via STDIO.
    """
    try:
        config = load_configuration()
        mcp_url = config["mcp_url"]
        token_url = config["token_url"]
        client_id = config["client_id"]
        client_secret = config["client_secret"]

        print(f"[MCP Client] Connecting to {mcp_url}", file=sys.stderr)
        print(f"[MCP Client] Token endpoint: {token_url}", file=sys.stderr)

        credentials = OAuthClientCredentials(token_url, client_id, client_secret)

        async with contextlib.AsyncExitStack() as stack:
            http_client = await stack.enter_async_context(
                httpx.AsyncClient(
                    event_hooks={"request": [credentials.on_request]},
                    timeout=httpx.Timeout(DEFAULT_TIMEOUT, read=SSE_READ_TIMEOUT),
                )
            )

            upstream_read, upstream_write, _ = await stack.enter_async_context(
                streamable_http_client(mcp_url, http_client=http_client)
            )

            upstream_session = await stack.enter_async_context(
                ClientSession(upstream_read, upstream_write)
            )
            await upstream_session.initialize()
            print("[MCP Client] Connected successfully", file=sys.stderr)

            server = Server("infinity-analytics")

            @server.list_tools()
            async def list_tools():
                """List available analytics query tools."""
                try:
                    result = await upstream_session.list_tools()
                    print(
                        f"[MCP Client] Found {len(result.tools)} tools "
                        "from upstream server",
                        file=sys.stderr,
                    )
                    return result.tools
                except Exception as e:
                    print(
                        f"[MCP Client] Error listing tools: {e}",
                        file=sys.stderr,
                    )
                    return []

            @server.call_tool()
            async def call_tool(name: str, arguments: dict):
                """Execute tool from upstream MCP server."""
                try:
                    print(
                        f"[MCP Client] Executing tool: {name}",
                        file=sys.stderr,
                    )
                    result = await upstream_session.call_tool(name, arguments)
                    print(
                        "[MCP Client] Tool executed successfully",
                        file=sys.stderr,
                    )
                    return result
                except Exception as e:
                    error_msg = f"Tool execution failed: {str(e)}"
                    print(
                        f"[MCP Client] Error: {error_msg}",
                        file=sys.stderr,
                    )
                    return CallToolResult(
                        content=[TextContent(type="text", text=error_msg)],
                        isError=True,
                    )

            stdio_read, stdio_write = await stack.enter_async_context(
                stdio_server()
            )
            print("[MCP Client] Ready for requests", file=sys.stderr)
            await server.run(
                stdio_read,
                stdio_write,
                server.create_initialization_options(),
            )

    except ConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        return
    except BaseException as e:
        if isinstance(e, SystemExit):
            raise
        root = _unwrap_exception(e)
        print(f"Connection Error: {root}", file=sys.stderr)
        print(
            "\nTroubleshooting:\n"
            "  - Verify INFINITY_URL is correct\n"
            "  - Check that the MCP server is running and reachable\n"
            "  - Confirm CLIENT_ID and CLIENT_SECRET are valid",
            file=sys.stderr,
        )
        sys.exit(1)


def _unwrap_exception(exc: BaseException) -> BaseException:
    """Recursively unwrap ExceptionGroups to find the root cause."""
    while hasattr(exc, "exceptions") and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


def main():
    """Main entry point for MCP client.

    Runs as STDIO MCP server for AI agent integration.
    """
    if len(sys.argv) > 1 and sys.argv[1] in ["--version", "-v"]:
        print(f"Infinity Analytics MCP Client v{__version__}")
        print("Mode: STDIO MCP Server for AI Agents")
        print("Authentication: OAuth 2.0 Client Credentials")
        sys.exit(0)

    elif len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print(__doc__)
        sys.exit(0)

    elif len(sys.argv) > 1:
        print(
            "Infinity Analytics MCP Client\n"
            "\n"
            "Usage:\n"
            "  STDIO Mode (AI Agents):       python mcp_client.py\n"
            "  Version Info:                 python mcp_client.py --version\n"
            "  Help:                         python mcp_client.py --help\n"
            "\n"
            "See README.md for detailed documentation.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    asyncio.run(serve_stdio())


if __name__ == "__main__":
    main()
