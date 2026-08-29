"""MCP (Model Context Protocol) layer for Samantha."""

from samantha.mcp.client import MCPClient
from samantha.mcp.protocol import MCPError, MCPNotification, MCPRequest, MCPResponse
from samantha.mcp.server import MCPServer
from samantha.mcp.transport import (
    InProcessTransport,
    MCPTransport,
    SSETransport,
    StdioTransport,
    StreamableHTTPTransport,
)

__all__ = [
    "MCPClient",
    "MCPError",
    "MCPNotification",
    "MCPRequest",
    "MCPResponse",
    "MCPServer",
    "MCPTransport",
    "InProcessTransport",
    "SSETransport",
    "StdioTransport",
    "StreamableHTTPTransport",
]
