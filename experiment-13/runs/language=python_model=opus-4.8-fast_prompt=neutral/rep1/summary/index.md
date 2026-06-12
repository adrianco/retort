# Run Summary: Brazilian Soccer MCP Server (python · opus-4.8-fast · prompt=neutral · rep1)

## Surface

An MCP (Model Context Protocol) server that answers natural-language questions
about Brazilian soccer over six pre-downloaded Kaggle CSVs (five match sources +
the FIFA player database). It exposes ~15 `@mcp.tool()` capabilities — match
search, head-to-head, team records, league standings, player search, and
aggregate statistics — each returning pre-formatted human-readable text backed
by a pandas query engine.

## Architecture

A clean three-layer pipeline:

```
CSVs ──> data_loader (unify schema) ──> KnowledgeGraph (query engine)
                                              │
                              server.py (FastMCP tools) ──> formatting (text)
```

- **data_loader.py** — reconciles six heterogeneous CSV schemas (different
  column names, date formats, team-naming) into two unified DataFrames
  (`matches`, `players`). Each row tagged with `source`; no rows dropped at load.
- **normalization.py** — team-name canonicalization (accent stripping, state-suffix
  handling, bidirectional whole-word matching) — the backbone of cross-source joins.
- **knowledge_graph.py** — the query engine (627 LOC). Notable: `dedupe_matches`
  collapses the 3 overlapping Série A sources per (competition, season) by
  preferring a *complete* round-robin season, guarding standings against
  double-counting and calendar-year spill.
- **server.py** — the MCP boundary; thin `@mcp.tool()` wrappers over the engine.
- **formatting.py** — turns engine dicts into spec-shaped answer text.

## Tests

49 test functions across 4 files (448 LOC), 0 skipped. A session-scoped `kg`
fixture builds the graph once. Coverage spans loader integrity, normalization,
every query family, MCP tool text, known-result assertions (2019 standings,
2021 Atlético-MG champion, Neymar top-rated), and the spec's <2s/<5s perf budgets.

See `modules.md` for the per-module table.
