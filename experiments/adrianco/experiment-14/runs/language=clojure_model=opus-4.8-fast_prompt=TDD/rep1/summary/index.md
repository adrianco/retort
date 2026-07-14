# Architecture Summary: brazilian-soccer (Clojure)

An MCP server exposing a Brazilian-soccer knowledge graph over JSON-RPC 2.0 (stdio).
Layered, with a pure functional core that keeps every layer unit-testable.

## Modules

| Namespace | Responsibility | Key fns |
|-----------|----------------|---------|
| `brazilian-soccer.normalize` | Canonicalize raw CSV values: accent folding, state/country suffix stripping, multi-format date parsing, float→int goals | `team-key`, `strict-key`, `team-suffix`, `clean-team`, `parse-date`, `parse-int`, `strip-accents` |
| `brazilian-soccer.data` | Load all 6 Kaggle CSVs onto one unified match schema + FIFA player schema; de-duplicate overlapping sources | `load-db`, `read-csv`, `select-best-source` |
| `brazilian-soccer.queries` | Pure query engine over the in-memory db | `find-matches`, `head-to-head`, `team-record`, `standings`, `search-players`, `avg-goals-per-match`, `home-win-rate`, `biggest-wins` |
| `brazilian-soccer.format` | Render query results as the human-readable answer strings shown in the spec | `matches`, `head-to-head`, `team-record`, `standings`, `players`, `statistics` |
| `brazilian-soccer.mcp` | MCP/JSON-RPC layer: tool descriptors, dispatch, stdio pump | `handle-request` (pure), `serve`, `-main`, `tools` |

## Data flow

```
CSV files (data/kaggle/*.csv)
   └─ data/load-db ─► {:matches [...] :players [...]}   (unified schema, deduped)
                          │
        mcp/-main loads once ─► db
                          │
stdin JSON-RPC ─► mcp/serve ─► mcp/handle-request (db, req)   ← pure, fully testable
                          │
              tools/call dispatch ─► queries/* ─► format/* ─► text content
                          │
                       stdout JSON-RPC
```

## Design notes

- **Purity for testability** (TDD): `handle-request` is a pure `(db, request) -> response`; `serve`/`-main` are the only I/O. Query fns return plain data; `format/*` render. This separation is what makes the 39 deftests possible without spinning up a process.
- **Six MCP tools**: `find_matches`, `head_to_head`, `team_record`, `standings`, `search_players`, `statistics` — each with a JSON input schema advertised via `tools/list`.
- **De-duplication**: `select-best-source` picks, per `(competition, season)`, the single source file with the most rows (ties to the dedicated single-competition file) rather than concatenating overlapping files. Deliberate tradeoff documented in `data.clj:160`.
- **Name normalization**: per-season `canonical-keyer` merges spelling variants (`Flamengo`/`Flamengo-RJ`, accented/unaccented) but keeps genuinely distinct clubs apart (`Atlético-MG` vs `Atlético-GO`).
