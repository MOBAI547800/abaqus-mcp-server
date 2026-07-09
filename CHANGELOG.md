# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] — 2026-07-09

### Added

- Initial release of Abaqus MCP Server
- 11 MCP tools for complete Abaqus FEM workflow automation
- `check_environment` — verify Abaqus installation and configuration
- `validate_workspace` — set up and validate workspace directory structure
- `generate_script` — generate Abaqus Python modeling scripts (cantilever beam, modal, contact, static)
- `run_script` — execute Python scripts via Abaqus bundled Python interpreter
- `submit_job` — submit `.inp` files for analysis with CPU control
- `job_status` — check job progress from `.sta` and `.lck` files
- `read_job_logs` — read and parse `.sta`, `.msg`, `.dat`, `.log` files with automatic error/warning extraction
- `extract_odb_summary` — extract ODB metadata (steps, frames, instances, field outputs)
- `extract_field_output` — extract field output (stress, displacement, strain) as CSV
- `extract_history_output` — extract history output (energy, forces, displacement history) as CSV
- `clean_job` — remove intermediate job files while preserving `.odb`, `.inp`, `.cae`
- Workspace sandboxing — all file operations scoped to configurable workspace directory
- Path traversal protection — blocks `../` and absolute path escapes
- Dangerous character rejection for shell injection prevention
- Confirmation gates on destructive operations (`submit_job`, `clean_job`)
- Output truncation to prevent token blowout
- ODB extraction via generated Abaqus Python scripts using `odbAccess`
- Windows subprocess support — correct `cmd.exe /c call abaqus.bat` handling
- 85 tests across 6 test files covering security, CLI, log parsing, ODB extraction, and config

[0.1.0]: https://github.com/user/abaqus-mcp-server/releases/tag/v0.1.0
