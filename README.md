# Abaqus MCP Server

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-stdio-orange)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-85%20passed-brightgreen)](tests/)

A local **stdio MCP server** that enables Claude Code to interact with [Abaqus](https://www.3ds.com/products/simulia/abaqus) FEM software — model generation, job submission, log monitoring, and result extraction from ODB files.

> 🎓 Ideal for simulation automation, parametric studies, post-processing pipelines, and teaching FEM scripting through natural language.

## ✨ Features

- **11 MCP tools** covering the full Abaqus workflow — from script generation to result extraction
- **Workspace sandboxing** — all file operations are scoped to a configurable directory
- **ODB extraction** via generated Abaqus Python scripts (no direct binary parsing — uses `odbAccess`)
- **Security-first** — no arbitrary shell execution, path traversal blocked, confirmation required for destructive operations
- **Windows support** — correctly handles Abaqus `.bat` file execution via `cmd.exe /c call`
- **Output truncation** — prevents token blowout in LLM context windows
- **85 tests** across unit, mocked integration, and MCP protocol layers

## 📋 Requirements

- **Python** 3.10+
- **Abaqus** (tested with Abaqus 2025; the `abaqus` command must be available)
- The `mcp` Python SDK (≥1.28.0) is installed automatically as a dependency

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/abaqus-mcp-server.git
cd abaqus-mcp-server

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Copy and edit environment config (optional)
copy .env.example .env

# Run the server
abaqus-mcp serve
```

## 🔌 Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "abaqus": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "abaqus_mcp_server.cli", "serve"],
      "env": {
        "ABAQUS_COMMAND": "abaqus",
        "ABAQUS_MCP_WORKSPACE_DIR": "./abaqus_work"
      },
      "timeout": 600000
    }
  }
}
```

Or with Claude Code, add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "abaqus": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "abaqus_mcp_server.cli", "serve"],
      "env": {
        "ABAQUS_COMMAND": "D:\\SIMULIA\\Commands\\abaqus.bat",
        "ABAQUS_MCP_WORKSPACE_DIR": "${CLAUDE_PROJECT_DIR:-.}/abaqus_work"
      }
    }
  }
}
```

## ⚙️ Configuration

All settings via environment variables (prefix `ABAQUS_MCP_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ABAQUS_COMMAND` | auto-detect | Path to Abaqus launcher (`abaqus.bat`) |
| `ABAQUS_MCP_WORKSPACE_DIR` | `./abaqus_work` | Workspace root directory |
| `ABAQUS_MCP_MAX_CPUS` | `4` | Maximum CPUs per job |
| `ABAQUS_MCP_SCRIPT_TIMEOUT` | `300` | Script execution timeout (seconds) |
| `ABAQUS_MCP_JOB_TIMEOUT` | `3600` | Job execution timeout (seconds) |
| `ABAQUS_MCP_MAX_OUTPUT_CHARS` | `20000` | Max chars in a single tool output |
| `ABAQUS_MCP_ALLOW_OVERWRITE` | `false` | Allow overwriting existing files |
| `ABAQUS_MCP_LOG_LEVEL` | `WARNING` | Server-side logging level |

## 🛠️ Tools

| Tool | Description | Confirm? |
|------|-------------|:---:|
| `check_environment` | Verify Abaqus installation, Python paths, and workspace status | |
| `validate_workspace` | Create or validate workspace directory structure | |
| `generate_script` | Generate Abaqus Python modeling scripts (cantilever, static, modal, contact) | |
| `run_script` | Execute Python scripts via `abaqus python` with timeout control | |
| `submit_job` | Submit an `.inp` file for FEM analysis | ✓ |
| `job_status` | Check job progress from `.sta` and `.lck` files | |
| `read_job_logs` | Read `.sta`/`.msg`/`.dat`/`.log` with automatic error/warning extraction | |
| `extract_odb_summary` | Extract ODB metadata — steps, frames, instances, field outputs | |
| `extract_field_output` | Extract field output (S, U, E, PEEQ, RF, etc.) as CSV with statistics | |
| `extract_history_output` | Extract history output (ALLIE, ALLSE, RF, etc.) as time-value CSV | |
| `clean_job` | Remove intermediate files, preserving `.odb`/`.inp`/`.cae` | ✓ |

## 🏗️ Architecture

```
src/abaqus_mcp_server/
├── app.py                  # FastMCP singleton — all tools register here
├── cli.py                  # argparse entry point
├── config.py               # pydantic Settings (ABAQUS_MCP_ prefix)
├── security.py             # Workspace sandboxing & path validation
├── abaqus_cli.py           # Abaqus subprocess abstraction (all calls go here)
├── log_parser.py           # .sta/.msg/.dat parsers
├── odb_script_templates.py # Generate Abaqus Python scripts for ODB extraction
├── constants.py            # Status strings, file extensions, error keywords
└── tools/                  # 11 MCP tool implementations (one per file)
```

### Key Design Decisions

1. **[FastMCP](https://github.com/jlowin/fastmcp)** — high-level MCP SDK with auto-generated JSON schemas from type annotations
2. **ODB extraction via generated scripts** — the server generates temporary Python scripts that run under `abaqus python` (which has `odbAccess`); system Python cannot import `odbAccess`
3. **Windows subprocess** — Abaqus `.bat` files require `cmd.exe /c "call abaqus.bat ..."` (no `shell=True`)
4. **Workspace sandboxing** — `security.validate_path()` enforces all file ops stay within the workspace
5. **Confirmation gates** — destructive tools require `confirmed=True` as an explicit user gate

## 🔒 Security

- All file paths are validated against the workspace directory
- Path traversal (`../../`) is blocked
- Dangerous shell characters (`;`, `|`, `&`, `` ` ``, `$`, etc.) are rejected
- `submit_job`, `run_script`, and `clean_job` require explicit `confirmed=True`
- No arbitrary shell execution — all Abaqus calls use explicit argument lists
- Output is truncated to `ABAQUS_MCP_MAX_OUTPUT_CHARS` to prevent context overflow

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific area
python -m pytest tests/test_security.py -v

# Run with coverage
python -m pytest tests/ --cov=abaqus_mcp_server --cov-report=html
```

### Test Layers

| Layer | What | Requires Abaqus |
|-------|------|:---:|
| Unit | security, config, log parsers | No |
| Mocked integration | AbaqusCLI, ODB extraction | No |
| MCP protocol | Server subprocess, tool listing | No |
| Live integration | Real Abaqus calls | Yes |

## 📁 Example: Cantilever Beam

[`examples/simple_beam/`](examples/simple_beam/) contains a complete cantilever beam analysis:

1. `beam.inp` — linear elastic beam with C3D8 elements
2. Ask Claude Code: *"Submit the beam.inp and extract the maximum Mises stress"*

The server will: validate the workspace → submit the job → check status → extract ODB summary → extract field output.

## 🐛 Troubleshooting

### Abaqus not found
Set `ABAQUS_COMMAND` to the full path:
```bash
set ABAQUS_COMMAND=D:\SIMULIA\Commands\abaqus.bat
```

### ODB extraction fails
- The `.odb` file may be locked (job still running) — check with `job_status` first
- Abaqus Python must be able to read the workspace directory
- The generated temp scripts run under `abaqus python`, not system Python

### Path traversal errors
All file paths must be relative to `ABAQUS_MCP_WORKSPACE_DIR`.

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, project structure, and guidelines.

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
