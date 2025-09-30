# Milestone: MCP Server Foundations

## Summary
- Scaffolded the `FileOrganizerServer` with a registration router, error handling, and invocation helper to host MCP tool handlers.
- Added a reusable `ServerContext` that provisions organizer paths, JSON memory storage, and the SQLite index adapter for handlers.
- Implemented durable storage adapters: a JSON-backed memory store with atomic writes and a SQLite index initializer with WAL mode and FTS triggers.

## Implementation Notes
- `JsonMemoryStore` seeds empty rule and preference collections when no memory file exists and preserves data via atomic rename operations.
- `SQLiteIndex` creates baseline tables (`files`, `file_tags`, `files_fts`) plus triggers to synchronize the FTS index and enforces `foreign_keys` with WAL journaling for concurrency.
- Tool handlers register through a decorator on `FileOrganizerServer`, keeping the orchestration logic separate from future MCP wiring.

## Next Steps
- Implement filesystem scanning and indexing tools using the new storage adapters.
- Expose `scan_paths`, `index_paths`, and `search_files` handlers via the server scaffold.
- Expand tests with integration coverage once filesystem tooling is added.
