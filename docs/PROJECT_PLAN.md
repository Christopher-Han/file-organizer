# Agentic File Organizer Project Plan

## Project Overview
The Agentic File Organizer is an MCP-powered assistant that analyzes, suggests, and executes file
organization tasks while adapting to user conventions. The system prioritizes safety through
staging, rollback, and explicit confirmation workflows. It remembers preferences across sessions
and exposes both a CLI and menu-driven UI for search and organization flows.

## Objectives
- Automate organization of unstructured files such as downloads and screenshots.
- Provide agentic reasoning that uses tool calls for scanning, suggesting, staging, applying, and
  rolling back changes.
- Guarantee safety with backups, staging manifests, and explicit confirmations.
- Maintain long-term memory of user conventions and naming schemes.
- Offer an intuitive CLI and menu interface for search and organization.
- Demonstrate MCP agent and tool orchestration as a cohesive demo.

## Requirements
### Functional
- Scan the filesystem by path, metadata, or patterns.
- Suggest organization strategies including move, rename, tag, archive, or trash.
- Stage changes before execution with full previews and diffs.
- Apply or rollback changes safely with manifest tracking.
- Persist user conventions and naming schemes durably.
- Prompt users with yes/no questions for clarity.
- Support agent-powered search with indexing.
- Provide a menu-driven CLI for non-technical users.

### Non-Functional
- **Safety:** staging area, manifests, and rollback support.
- **Performance:** index must support 100k+ files with fast search.
- **Reliability:** atomic operations when possible and verified copies before deletion.
- **Extensibility:** rule DSL with pluggable heuristics.

## System Design Summary
### Components
1. **Agent Runtime (MCP client):** Orchestrates tool usage, handles user interaction, and learns from
   confirmations.
2. **MCP Server (`mcp-file-organizer`):** Hosts tools for scanning, suggestion, staging, applying,
   rollback, search, and memory persistence.
3. **Storage:**
   - `organizer.memory.json` for conventions and preferences.
  - `organizer.index.sqlite` for the searchable file index.
  - `.organizer/staging/` for staged file moves with manifests and checksums.
  - `.organizer/logs/` for applied manifests and rollback logs.
4. **CLI + TUI Menu:** Commands such as `review`, `search`, and `rollback` with text-based UI for
   reviewing suggestions and diffs.

### Tools
- `scan_paths`
- `suggest_organization`
- `stage_changes`
- `preview_diff`
- `apply_manifest`
- `rollback_manifest`
- `index_paths`
- `search_files`
- `get_memory`
- `update_memory`
- `learn_from_confirmations`

### Rule DSL
- **Conditions:** file kind, extension, source application, domain, path regex, size, tags.
- **Actions:** move, rename, tag, trash.
- **Optional:** `ask` for explicit user input when needed.

### Safety Model
- Always stage before applying changes.
- Provide diff previews.
- Require explicit yes/no confirmations.
- Support rollback manifests.
- Trash instead of permanently deleting files.

## Example User Flows
### Screenshot Cleanup
1. Agent proposes moving screenshots to a structured folder and renaming using timestamps.
2. User confirms, changes are staged, previewed, applied, and the rule is learned.

### Invoice Normalization
1. Agent suggests renaming invoices to a consistent `{vendor}_{YYYY}-{MM}_inv.pdf` format.
2. User confirms and optionally stores the rule in memory for future automation.

### Search Flow
- User runs `organizer search "invoice acme 2024 ext:pdf"`.
- Agent leverages the indexed search to return results rapidly.

## Milestones and Tasks
### Milestone Progress
- [x] **Setup & Infrastructure** – Base package structure established, configuration loader shipped, and documentation published for environment and scaffolding workflows.
- [x] **MCP Server Foundations** – Server scaffold with router/context completed alongside JSON memory and SQLite index adapters.
- [ ] **Filesystem Scanning & Indexing** – Build `scan_paths`, `index_paths`, and `search_files` tools on top of the new storage layer.
- [ ] **Rule Engine and Safety Tooling** – Implement the Rule DSL and add staging/diff/apply/rollback integrations to the server.
- [ ] **Memory, Prompts, and Polish** – Wire memory tools, agent prompts, TUI flows, and extensive safety testing.

## Testing Checklist
- Cross-device move integrity with hash verification.
- Filename conflict resolution.
- ENOSPC handling with rollback support.
- Hidden file inclusion/exclusion controls.
- Batch size enforcement and guardrails.
- Memory persistence across sessions.
- Index scaling to 100k files.

## Forward Extensions
- Semantic content detection (OCR, PDF titles).
- Lightweight ML classifiers for file type inference.
- Cloud sync awareness for services such as iCloud, Dropbox, or Google Drive.
- Import/export rule packs for community sharing.

## Deliverables
- Fully implemented MCP server with all tools.
- CLI/TUI application built with Typer and Textual (or equivalent).
- Durable storage using JSON and SQLite.
- Demonstrable flows: screenshot cleanup, invoice normalization, and search.

## Success Criteria
- `organizer review` produces actionable suggestions, staged safely, and applied upon confirmation.
- Memory reduces repeated prompts by persisting preferences.
- Search returns results under 200 ms for large indexes.
- Rollback functionality restores files reliably.
