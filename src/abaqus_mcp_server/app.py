"""FastMCP application singleton.

All tool modules import ``mcp`` from here and decorate with ``@mcp.tool()``.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    name="Abaqus MCP Server",
    instructions="Abaqus FEM automation — model generation, job submission, log monitoring, result extraction",
)

# Import tool modules so @mcp.tool() decorators fire
import abaqus_mcp_server.tools  # noqa: E402, F401
