# Milestone: Rule Engine and Safety Tooling

This milestone introduces the foundations for reasoning about file operations and
ensures the organizer can propose, stage, apply, and roll back changes safely.

## Highlights

- **Rule DSL:** Define conditions (extension, path pattern, tags, etc.) and actions
  (`move`, `rename`, `tag`, `trash`). Rules are parsed with validation so malformed
  inputs are rejected early.
- **Suggestion Engine:** Combine scanned file metadata with the rule set to produce
  `SuggestedChange` objects. Only the first matching rule fires for determinism.
- **Staging Pipeline:** Copy files into a manifest-specific staging directory with
  checksums, making it safe to inspect diffs before applying.
- **Diff Preview:** Provide human-readable summaries listing all operations in the
  manifest to support CLI/TUI review flows.
- **Apply & Rollback:** Applying a manifest moves staged files into place while
  backing up originals and previous destinations. Rollback uses the log manifest to
  restore prior state.

## Next Steps

- Integrate the rule engine with the MCP server interface.
- Surface staged manifests and diff previews through the CLI/TUI review workflow.
- Extend rule actions to capture additional metadata (e.g., user prompts, tagging
  semantics) and hook them into agent feedback loops.

