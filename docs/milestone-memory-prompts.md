# Milestone: Memory, Prompts, and Polish

## Summary
- Added MCP memory tools (`get_memory`, `update_memory`, `learn_from_confirmations`) to
  expose preference management, configurable merges, and confirmation analytics through
  the server interface.
- Introduced CLI commands (`organizer memory show`, `organizer memory set-pref`) that
  let users inspect and tweak persisted preferences without editing JSON by hand.
- Provided prompt-building utilities that adapt Llama instructions to stored
  preferences (tone, batch confirmations, preview limits), ensuring review flows are
  consistent with user expectations.

## Implementation Notes
- Memory updates use a deep-merge strategy so nested structures (e.g.,
  `preferences`) can be overridden incrementally without overwriting unrelated data.
- Confirmation learning keeps per-rule acceptance/rejection counts and a bounded
  history, supporting future automation heuristics while capping storage growth.
- Prompt helpers default to friendly messaging but honor stored preferences and
  guardrail text that reiterates staging, diffs, and rollback to maintain safety.

## Tests
- `tests/test_server_memory.py` validates read/update/learn flows against the MCP
  server wrapper.
- `tests/test_cli_memory.py` exercises the new CLI commands end-to-end with a
  temporary state directory.
- `tests/test_prompts.py` ensures prompt rendering reflects preferences, truncates
  long suggestion lists, and includes guardrail guidance.

## Next Steps
- Thread prompt utilities into the higher-level agent runtime once the orchestration
  layer evolves beyond MVP.
- Expand confirmation learning into a decay-based model that auto-suggests
  auto-apply candidates when confidence is high.
