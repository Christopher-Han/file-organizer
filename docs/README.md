# Organizer Architecture & Debugging Guide

This document helps new engineers ramp up on the Agentic File Organizer. It
covers architecture, key modules, data flow, and common debugging tactics.

## System Overview

```
          ┌────────────┐      ┌──────────────────┐
          │ CLI / TUI │─────▶│ MCP Server Tools │
          └────────────┘      └──────────────────┘
                │                     │
   ┌────────────┴────────────┐ ┌──────┴────────────┐
   │ Runtime (Prompts)       │ │ Storage Layer     │
   │ + Llama Client          │ │ (JSON + SQLite)   │
   └────────────┬────────────┘ └─────────┬─────────┘
                │                        │
          ┌─────▼─────┐           ┌──────▼────────┐
          │ Filesystem│           │ Staging & Logs│
          └────────────┘           └──────────────┘
```

All flows run through the MCP server. The CLI (or an MCP runtime) issues tool
requests, which operate over persistent storage and staging directories to keep
changes safe and auditable.

## Core Components

### Configuration (`organizer.config`)
- Resolves working directories under `~/.organizer` (configurable via
  `--base-dir`).
- Ensures durable storage layout:
  - `organizer.memory.json` – user preferences, confirmation history, rule
    overrides.
  - `organizer.index.sqlite` – metadata index for fast search.
  - `.organizer/staging/` – manifests containing staged files and checksums.
  - `.organizer/logs/` – application logs for applied manifests and rollback.

### Storage Layer (`organizer.storage`)
- **JsonMemoryStore** (`memory.py`) – atomic reads/writes, deep merges handled at
  higher levels. Used by memory tools and CLI.
- **SQLiteIndex** (`index.py`) – manages file metadata tables, tags, and FTS
  virtual table. Provides upsert, prune, search helpers. Keep in mind: generator
  arguments must be parenthesized for Python 3.11+.

### Rule Engine (`organizer.rules`)
- Parses rule DSL into typed dataclasses with validation.
- `build_suggestions` generates `SuggestedChange` objects. Only the first rule to
  match a file fires, ensuring deterministic proposals.
- Used by MCP `suggest_organization` tool and any runtime automation.

### Staging & Safety (`organizer.staging`)
- `stage_changes` copies files into manifest-specific directories with SHA-256
  checksums. Each manifest has a JSON summary of operations.
- `preview_diff` renders human-readable summaries for CLI/TUI review.
- `apply_manifest` moves staged files into place while backing up originals to
  `.organizer/logs/<manifest_id>/` for rollback.
- `rollback_manifest` replays log entries in reverse order to restore state.

### MCP Server (`organizer.server`)
- `FileOrganizerServer` orchestrates tool handlers.
- Tool registration modules:
  - `filesystem.py`: `scan_paths`, `index_paths`, `search_files`.
  - `rules.py`: `suggest_organization`, `stage_changes`, `preview_diff`,
    `apply_manifest`, `rollback_manifest`.
  - `memory.py`: `get_memory`, `update_memory`, `learn_from_confirmations`.
- `ServerContext` wires config, memory store, SQLite index, and the Llama client.
- To embed in another runtime, instantiate `ServerContext.from_base_dir()` and
  register the tool modules.

### Runtime (`organizer.runtime`)
- `prompts.py` builds adaptive prompts (`build_review_prompt`) using stored
  preferences (tone, batching, preview limit) plus guardrail reminders (stage →
  diff → apply → rollback).
- Exports `PromptContext` for custom prompt generation.

### LLM Client (`organizer.llm`)
- Wraps `llama-api-client` with explicit key management.
- API keys are persisted via CLI or `set_api_key()`. Environment fallback is
  optional (disabled in tests).
- Always ensure the key exists before invoking `complete()`; if missing, the
  client raises `LlamaAPIError`.

### CLI (`organizer.cli.main`)
- `organizer init` ensures directories exist and displays resolved paths.
- `organizer configure-llm` persists the key (secure prompt). Use `--base-dir` to
  target non-default locations.
- `organizer memory show/set-pref` present or modify preferences without editing
  JSON directly.
- Typer-based command structure to keep UX consistent.

## Typical Workflow

1. **Scan/Index** – `scan_paths` gathers metadata, `index_paths` upserts into
   SQLite, optionally pruning missing files.
2. **Suggest** – `suggest_organization` merges rules from memory + request
   payload, building `SuggestedChange` entries.
3. **Stage** – `stage_changes` copies assets into staging while computing checksums.
4. **Review** – CLI/TUI uses `preview_diff` and `build_review_prompt` to surface
   human-readable diffs and prompt content.
5. **Apply/Rollback** – `apply_manifest` commits the manifest; rollback is
   available through logs or `rollback_manifest`.
6. **Learn** – `learn_from_confirmations` tracks acceptance stats to drive future
   automation.

## Debugging Guide

### General Tips
- Reproduce issues with `python -m pytest` before diving into manual tests.
- Use `organizer memory show` to confirm preferences/rules are stored as expected.
- Inspect `.organizer/staging/<manifest_id>/manifest.json` for staging issues.
- Check `.organizer/logs/<manifest_id>/manifest.json` when debugging rollback.

### MCP Tool Issues
- Enable additional logging by wrapping tool handlers or using `print()` while
  running `pytest -s`.
- Validate payloads: many handlers coerce boolean/int values and raise
  `ValueError` when types are unexpected.
- Use `ServerContext.from_base_dir(tmp_path)` in tests to sandbox state.

### Indexing Problems
- Run `index.purge_missing([root])` after deletes to keep metadata fresh.
- If FTS queries fail (e.g., missing BM25), the search helper automatically
  falls back to `LIKE`. Confirm the fallback results include expected paths.
- Vacuum via `SQLiteIndex.vacuum()` after large churn when debugging performance.

### Staging/Apply Failures
- Missing staged files usually indicate a previous step cleared the staging
  directory. Verify manifests exist before applying.
- If destination conflicts occur, inspect the log directory to confirm backups
  were created; the apply helper moves both source and destination into log
  subdirectories before writing to the final location.

### LLM Prompting
- `build_review_prompt` can be exercised in isolation. Feed it a list of
  `SuggestedChange` objects along with a memory payload to verify tone/batch
  settings before invoking the Llama API.
- The CLI stores the key in `~/.organizer/llama.api.key` (configurable via
  `--base-dir`). Ensure this file exists when `complete()` raises key errors.

### Tests & Coverage
- New features should include targeted tests in `tests/` mirroring the component
  under development (e.g., `tests/test_server_*`, `tests/test_cli_*`).
- Run subsets with `python -m pytest tests/test_server_rules.py` to speed up
  debugging.
- For CLI tests using Typer, prefer `CliRunner.invoke` with `--base-dir` pointing
  at a temp directory, keeping the real `~/.organizer` untouched.

## Frequently Used Commands

```bash
# Install with dev extras
pip install -e '.[dev]'

# Run all tests
python -m pytest

# Only storage tests
python -m pytest tests/test_storage_index.py tests/test_storage_memory.py

# Launch CLI help
organizer --help
organizer memory --help

# Manually run a scan/index cycle (from a Python REPL)
from organizer.config import load_organizer_paths
from organizer.server import FileOrganizerServer, ServerContext, register_filesystem_tools

ctx = ServerContext.from_base_dir()
server = FileOrganizerServer(ctx)
register_filesystem_tools(server)
server.handle('scan_paths', {'paths': ['/tmp']})
```

## Updating This Document

When components evolve (new tools, CLI commands, or prompt behaviors), update
this README alongside relevant milestone documentation so new engineers have a
single source of truth.
