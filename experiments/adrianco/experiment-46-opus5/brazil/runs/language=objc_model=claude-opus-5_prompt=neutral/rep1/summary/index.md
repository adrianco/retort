# Summary: language=objc · model=claude-opus-5 · prompt=neutral · rep 1

- **Shape:** Objective-C (Foundation) MCP server — JSON-RPC 2.0 over stdio — exposing 17 tools over an in-memory knowledge graph built from six Brazilian-soccer Kaggle CSVs.
- **Structure:** 31 source files in `src/` (16 module pairs + `main.m`) and 8 test files in `tests/` (BDD harness + 6 scenario suites, ~108 scenarios).
- **Interfaces:** 5 MCP/JSON-RPC methods (initialize, ping, tools/list, tools/call, notifications/initialized), 17 MCP tools, and a dev-oriented CLI (`--list-tools`, `--call`); no HTTP, no database.
- **Notable:** Substantial data-engineering focus — a streaming RFC-4180 CSV parser, per-file loader adapters, a fold/peel/lookup club-name registry (~700 raw strings → ~90 clubs), and cross-file fixture reconciliation to avoid triple-counting overlapping seasons. Analytics compute league tables with CBF tie-break order. Scores: code_quality 1.0, test_coverage 1.0, defect_rate 1.0, idiomatic 0.86.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
