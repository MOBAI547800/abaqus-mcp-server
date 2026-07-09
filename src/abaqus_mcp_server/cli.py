"""CLI entry point for the Abaqus MCP Server."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    """Parse command-line arguments and run the server."""
    parser = argparse.ArgumentParser(
        prog="abaqus-mcp",
        description="Abaqus MCP Server — FEM automation via MCP",
    )
    subparsers = parser.add_subparsers(dest="command", help="sub-commands")

    serve_parser = subparsers.add_parser("serve", help="Start the MCP server")
    serve_parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )

    args = parser.parse_args(argv)

    if args.command == "serve":
        from abaqus_mcp_server.app import mcp

        mcp.run(transport="stdio")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
