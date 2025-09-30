# Agentic File Organizer

This repository contains the implementation of an MCP-powered agent that organizes files safely and
intelligently. The project roadmap, including milestones and major tasks, is documented in
[`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md).

## Getting Started

The codebase targets Python 3.11+. To set up the project locally:

```bash
conda create -n organizer python=3.11
conda activate organizer
pip install -e .[dev]
```

Additional documentation for each milestone will be recorded in the `docs/` directory as the project
progresses. Current deep dives:

- [`docs/milestone-setup.md`](docs/milestone-setup.md) – environment scaffolding and path helpers.
- [`docs/milestone-mcp-server-foundations.md`](docs/milestone-mcp-server-foundations.md) – server routing scaffold, shared context, and storage adapters.
- [`docs/milestone-rule-engine.md`](docs/milestone-rule-engine.md) – rule DSL, suggestion engine, and
  safety tooling for staging, applying, and rolling back manifests.
