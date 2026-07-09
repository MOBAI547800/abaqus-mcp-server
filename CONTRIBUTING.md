# Contributing to Abaqus MCP Server

Thanks for your interest in contributing! This project aims to make Abaqus FEM simulation accessible through Claude Code and MCP.

## Getting Started

```bash
# Clone and set up
git clone https://github.com/YOUR_USERNAME/abaqus-mcp-server.git
cd abaqus-mcp-server
pip install -e ".[dev]"
```

## Development Workflow

1. **Fork and branch** — create a feature branch from `main`
2. **Write tests** — every new tool or parser should have tests
3. **Run tests** — `python -m pytest tests/ -v`
4. **Open a PR** — describe what you changed and why

## Project Structure

```
src/abaqus_mcp_server/
├── app.py          # FastMCP singleton — all tools register here
├── cli.py          # CLI entry point
├── config.py       # Configuration from env vars
├── security.py     # Path validation and workspace sandboxing
├── abaqus_cli.py   # Abaqus subprocess abstraction
├── log_parser.py   # .sta/.msg/.dat parsers
├── odb_script_templates.py  # ODB extraction script generators
└── tools/          # MCP tool implementations (one per file)
```

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

## Testing

```bash
# All tests
python -m pytest tests/ -v

# Specific area
python -m pytest tests/test_security.py -v

# With coverage
python -m pytest tests/ --cov=abaqus_mcp_server --cov-report=html
```

### Test Layers

| Layer | What | Requires Abaqus |
|-------|------|:---:|
| Unit | security, config, log parsers | No |
| Mocked integration | AbaqusCLI, ODB extraction | No |
| MCP protocol | Server subprocess, tool listing | No |
| Live integration | Real Abaqus calls | Yes |

## Code Style

- Follow PEP 8
- Use type annotations for all function signatures
- Tool docstrings are critical — they're the LLM's only documentation for each tool
- Use `from __future__ import annotations` at the top of every module

## Questions?

Open an issue or start a discussion on GitHub.
