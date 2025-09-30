# Repository Guidelines

- Use conda for managing the project environment when creating or updating tooling/documentation that references environment setup.
- Restrict LLM usage to the Llama API for runtime integrations; avoid wiring up alternate models during development.
- When adding CLI options, expose only parameters that are practical for quick suggestions (e.g., avoid verbose paths like `--input_path=/path/to/file`).
- Testing and documentation updates should accompany each feature or component change rather than being deferred to separate milestones.
- Uphold the safety guarantees described in the project plan: stage changes before applying them, provide diff previews, require explicit yes/no confirmations, and ensure rollback manifests are available for recovery.
- Maintain durable state using the established storage layout (`organizer.memory.json`, `organizer.index.sqlite`, `.organizer/staging/`, `.organizer/logs/`) so agent memory, indexing, and staging remain consistent.
- Design search and indexing features to scale to large collections (100k+ files) while keeping response times fast.
