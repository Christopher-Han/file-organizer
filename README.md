# Agentic File Organizer

This repository contains the implementation of an MCP-powered agent that organizes files safely and
intelligently. The project roadmap, including milestones and major tasks, is documented in
[`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md).

## Getting Started

### Prerequisites

- Python 3.11+ (the project templates target 3.11)
- [Conda](https://docs.conda.io/en/latest/) or another environment manager
- Optional: the MCP runtime you plan to pair with this server

### Installation

Create an isolated environment and install the toolkit in editable mode so the CLI
entry point is available:

```bash
conda create -n organizer python=3.11
conda activate organizer
pip install -e '.[dev]'

# Store your Llama API key once; it will be reused for future runs
organizer configure-llm
```

The CLI persists the key to `.organizer/llama.api.key`, respecting the `LLAMA_API_KEY`
environment variable if you prefer to manage credentials that way.

### Building the MCP Server

No separate build step is required beyond the editable install. The server can be
imported and wired into your MCP runner:

```python
from organizer.server import FileOrganizerServer, ServerContext, register_filesystem_tools, register_rule_tools, register_memory_tools

context = ServerContext.from_base_dir()
server = FileOrganizerServer(context)
register_filesystem_tools(server)
register_rule_tools(server)
register_memory_tools(server)
```

### Running the CLI

- Initialise the working directories: `organizer init`
- Inspect or tweak memory preferences: `organizer memory show`,
  `organizer memory set-pref tone casual`
- Configure the LLM key (if you skipped it earlier): `organizer configure-llm`

### Test Suite

After installing the `dev` extras you can run all tests with:

```bash
python -m pytest
```

Individual tests can be targeted, for example `python -m pytest tests/test_server_rules.py`.

### Development Tips

- Use `pip install -e '.[dev]'` whenever dependencies change so the CLI remains
  editable.
- The MCP server exposes tools for filesystem scanning, rule evaluation, staging,
  and memory management; use the helper registration functions exported from
  `organizer.server`.

Additional documentation for each milestone will be recorded in the `docs/` directory as the project
progresses. Current deep dives:

- [`docs/milestone-setup.md`](docs/milestone-setup.md) – environment scaffolding and path helpers.
- [`docs/milestone-mcp-server-foundations.md`](docs/milestone-mcp-server-foundations.md) – server routing scaffold, shared context, and storage adapters.
- [`docs/milestone-filesystem-scanning.md`](docs/milestone-filesystem-scanning.md) – filesystem scanning, indexing, and search tooling.
- [`docs/milestone-rule-engine.md`](docs/milestone-rule-engine.md) – rule DSL, suggestion engine, and
  safety tooling for staging, applying, and rolling back manifests.
- [`docs/milestone-memory-prompts.md`](docs/milestone-memory-prompts.md) – memory tools, adaptive
  prompts, and CLI polish for preference management.
