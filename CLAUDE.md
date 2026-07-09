# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

`abaqus-mcp-server` is a local stdio MCP server that enables Claude Code to interact with Abaqus FEM software. It provides tools for model generation, job submission, log monitoring, and result extraction from ODB files.

## Architecture

```
src/abaqus_mcp_server/
├── app.py          # FastMCP singleton — all tools register here via @mcp.tool()
├── cli.py          # CLI entry point (argparse) — `abaqus-mcp serve`
├── config.py       # pydantic Settings from env vars (ABAQUS_MCP_ prefix)
├── security.py     # Path validation, workspace sandboxing, output truncation
├── abaqus_cli.py   # Abaqus subprocess abstraction (all Abaqus calls go here)
├── log_parser.py   # .sta/.msg/.dat parsers
├── odb_script_templates.py  # Generate Abaqus Python scripts for ODB extraction
├── constants.py    # Job status strings, file extensions, error keywords
└── tools/          # MCP tool implementations (one file per tool)
```

## Key Design Decisions

1. **FastMCP** — uses `mcp.server.fastmcp.FastMCP` for auto-generated JSON schemas
2. **ODB extraction** — generates temp Python scripts that run via `abaqus python` using `odbAccess`; system Python cannot import `odbAccess`
3. **Windows subprocess** — Abaqus `.bat` files require `cmd.exe /c "call abaqus.bat ..."`
4. **Workspace sandboxing** — all file ops scoped to `ABAQUS_MCP_WORKSPACE_DIR`
5. **Confirmation gates** — `submit_job` and `clean_job` require `confirmed=True`

## Adding a New Tool

1. Create `src/abaqus_mcp_server/tools/my_tool.py`
2. Import `mcp` from `abaqus_mcp_server.app` and decorate with `@mcp.tool()`
3. Always call `security.validate_path()` before any filesystem operation
4. Add the import to `src/abaqus_mcp_server/tools/__init__.py`
5. Add tests to `tests/`

## Security Rules

- **Never** use `shell=True` for subprocess calls
- **Always** validate paths through `security.validate_path()`
- **Never** allow arbitrary shell execution
- All dangerous tools must require `confirmed=True`
- Path traversal (`../../`) must be rejected
- Output must be truncated to avoid token blowout

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_security.py -v

# Run with coverage
python -m pytest tests/ --cov=abaqus_mcp_server --cov-report=html
```

### Test Layers

| Layer | What | Requires Abaqus |
|-------|------|----------------|
| Unit | security, config, log parsers | No |
| Mocked integration | AbaqusCLI, ODB extraction | No |
| MCP protocol | Server subprocess, tool listing | No |
| Live integration | Real Abaqus calls | Yes |

## Running the Server

```bash
# Development
python -m abaqus_mcp_server.cli serve

# Installed
abaqus-mcp serve
```
