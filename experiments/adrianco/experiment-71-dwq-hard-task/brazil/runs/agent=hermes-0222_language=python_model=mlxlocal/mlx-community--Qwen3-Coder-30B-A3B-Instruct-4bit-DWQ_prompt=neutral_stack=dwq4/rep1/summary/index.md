# Summary: experiment-71-dwq-hard-task / brazil · agent=hermes-0222 · model=Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ · prompt=neutral · stack=dwq4 · rep1

- **Shape:** Single-file Python MCP server (`FastMCP`) over 6 in-memory Kaggle CSVs, exposing 10 soccer-query tools; repair run started from a failing prior attempt.
- **Structure:** 1 source module + 3 ad-hoc test/verify scripts (`test_...py`, `integration_test.py`, `verify_implementation.py`); no pytest suite or package layout.
- **Interfaces:** 0 HTTP routes / 10 MCP tools (match, team, player, competition, stats, head-to-head) / 10 importable tool functions.
- **Notable:** `get_competition_standings` (R9) is left as a placeholder stub, so standings are never computed. Data loads eagerly at import via a global singleton; all match/player fields stored as strings and coerced ad hoc. Tests are presence/execution checks rather than value assertions. MCP registration and the SDK import are guarded by broad try/except with a `MockServer` fallback.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
