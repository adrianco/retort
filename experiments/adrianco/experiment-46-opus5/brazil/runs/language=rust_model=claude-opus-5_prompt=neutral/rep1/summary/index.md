# Architecture Summary

**Surface:** An MCP (Model Context Protocol) server over six Kaggle Brazilian-soccer
datasets. It loads the CSVs into an in-memory knowledge graph (teams, matches,
competitions, FIFA players) and exposes 14 tools plus MCP resources/prompts over
JSON-RPC 2.0 on newline-delimited stdio.

## Layered design

```
main.rs ── CLI: `serve` (stdio MCP loop) | `ask <tool> <json>` (one-shot)
  │
mcp.rs ─── JSON-RPC 2.0 protocol: initialize/tools/resources/prompts, batch support
  │
tools.rs ─ 14 tool specs (JSON schemas) + arg parsing + dispatch → ToolOutput{text,data}
  │
queries.rs ─ query engine: match search, h2h, team_stats, standings, rankings,
  │           competition_stats, biggest_wins, player search/squad
format.rs ─ renders query results to NL text + structured JSON
  │
graph.rs ── KnowledgeGraph: nodes, edges, team resolution, dedup of overlapping files
  │
model.rs ── domain types: Competition, Source, Date, Team, Match, Player
normalize.rs ─ team-name normalization (state suffixes, accents, aliases)
data.rs ─── CSV loading (csv crate), header BOM/casefold handling, per-file reports
samples.rs ─ built-in sample questions
```

## Notable design decisions

- **De-duplication:** overlapping source files (multiple Brasileirão files) are
  reconciled — a canonical file per competition/season is chosen; aggregates use only
  canonical rows unless `include_all_sources=true`.
- **Name normalization:** clubs appear as "Palmeiras-SP", "Palmeiras", full names;
  `normalize.rs` + alias resolution unify them; `find_team` resolves ambiguity.
- **Graceful tool errors:** tool failures returned as MCP results with `isError:true`
  (not protocol errors) so the model can recover.
- **Honest data caveats:** surfaces FIFA-19 licensing gaps, absence of goalscorer data.

See `../src/` for detail; `modules.md` for the file-level map.
