# Milestone: Filesystem Scanning & Indexing

## Summary
- Added `organizer.indexing.scan_paths` to crawl requested locations with depth limits,
  hidden-file controls, optional checksum calculation, and structured error reporting.
- Extended `SQLiteIndex` with bulk upsert, pruning of missing entries, and dual-mode
  search (FTS-backed with a resilient LIKE fallback) to keep lookups fast for large
  collections.
- Registered MCP tools (`scan_paths`, `index_paths`, `search_files`) so the server
  can expose scanning, indexing, and search capabilities with consistent payload
  validation and serialization.

## Implementation Notes
- Scans deduplicate paths via resolved canonical locations and return deterministic
  ordering for repeatable previews, while hidden segments remain opt-in.
- Index upserts clear and normalize tags on every refresh to avoid stale metadata
  lingering between runs; pruning uses on-disk checks so staging areas remain
  authoritative.
- Search results include parent metadata and optional scores, with tuple tags
  coerced to lists when crossing the MCP boundary for JSON compatibility.

## Tests
- `tests/test_indexing.py` covers hidden filtering, depth limits, checksum support,
  and missing-path reporting.
- `tests/test_storage_index.py` verifies tag normalization, LIKE/FTS querying, and
  pruning of deleted files.
- `tests/test_server_filesystem.py` exercises the MCP tool flow end-to-end across
  scanning, indexing, and search.

## Next Steps
- Implement the rule engine tooling so indexed metadata can drive actionable change
  suggestions, staging flows, and diff previews.
