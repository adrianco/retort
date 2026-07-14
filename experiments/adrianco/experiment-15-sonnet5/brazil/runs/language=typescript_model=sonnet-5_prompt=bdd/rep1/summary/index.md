# Summary: language=typescript_model=sonnet-5_prompt=bdd · rep 1

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk`) over an in-memory store of 6 Brazilian soccer CSV datasets, exposed as 14 stdio tools.
- **Structure:** 12 source modules (data/, queries/, server), 8 test files (65 vitest specs).
- **Interfaces:** 14 MCP tools (match search, head-to-head, team records/rankings, player search, calculated standings, goal stats) — no HTTP/CLI.
- **Notable:** Handles a real data-quality trap — several CSVs redundantly cover the same seasons; the store designates one primary source per competition/season and skips overlapping rows to avoid double-counting stats. Standings use CBF tie-break rules to match the spec's worked example. BDD prompt followed faithfully (Given/When/Then comments + `test_given_..._when_..._then_...` names).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
