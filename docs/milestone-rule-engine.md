# Milestone: Rule Engine and Safety Tooling

## Summary
- Registered MCP tools (`suggest_organization`, `stage_changes`, `preview_diff`,
  `apply_manifest`, `rollback_manifest`) that orchestrate the existing rule,
  staging, and rollback subsystems through a unified server interface.
- Added payload coercion so suggestions can be generated from memory-backed rule
  definitions or inline overrides, enabling deterministic move/rename/tag
  proposals with safe defaults for destination handling.
- Exposed manifest lifecycle helpers that keep staging manifests, diff previews,
  apply logs, and rollback actions consistent with the safety guarantees in the
  project plan.

## Implementation Notes
- Rule definitions are loaded from persistent memory (`organizer.memory.json`) or
  provided request-side; duplicates are overridden predictably and validated with
  the shared DSL parser.
- File metadata ingestion normalizes paths, casing, and tags before invoking
  `build_suggestions`, preventing downstream staging from encountering malformed
  payloads.
- Staging results include per-entry checksums and staged file paths so the CLI/TUI
  can present previews before asking for confirmation.

## Tests
- `tests/test_server_rules.py` covers suggestion generation, staging, preview,
  apply, and rollback flows end-to-end against temporary files.
- Existing unit suites for staging (`tests/test_storage_index.py`,
  `tests/test_indexing.py`) continue to validate checksum creation and manifest
  persistence.

## Next Steps
- Surface these server tools inside the CLI/TUI review flows so users can apply
  manifests interactively.
- Extend rule actions with richer tagging/prompt semantics to feed future agent
  confirmation loops.
