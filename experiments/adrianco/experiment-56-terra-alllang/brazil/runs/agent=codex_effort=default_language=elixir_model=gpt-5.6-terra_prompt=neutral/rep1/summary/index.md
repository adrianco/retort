# Architecture Summary — Brazilian Soccer MCP (Elixir)

_Generated inline (the `run-summary` skill is not in the invocable set for this session)._

## Modules

| Module | File | Responsibility |
|--------|------|----------------|
| `BrazilianSoccer` | `lib/brazilian_soccer.ex` | Public query API: `search_matches/2`, `team_statistics/3`, `head_to_head/4`, `search_players/2`, `standings/3`, `competition_statistics/2`. |
| `BrazilianSoccer.Data` | `lib/brazilian_soccer/data.ex` | Loads the 5 match CSVs + FIFA players into in-memory maps; per-source row mappers (standard / extended / historical). |
| `BrazilianSoccer.CSV` | `lib/brazilian_soccer/csv.ex` | RFC-4180-style streaming CSV parser (quoted commas, escaped quotes, UTF-8, BOM strip). |
| `BrazilianSoccer.Normalize` | `lib/brazilian_soccer/normalize.ex` | Team-name normalization (accent-fold, strip `-UF` suffix, alias table) and multi-format date parsing (ISO + `DD/MM/YYYY`). |
| `BrazilianSoccer.JSON` | `lib/brazilian_soccer/json.ex` | Hand-rolled JSON encode/decode (no deps). |
| `BrazilianSoccer.MCP` | `lib/brazilian_soccer/mcp.ex` | stdio JSON-RPC MCP server: `initialize`, `tools/list`, `tools/call`; 6 registered tools with `inputSchema`. Escript entrypoint. |

## Flow

`MCP.main/0` → `BrazilianSoccer.load()` (reads `data/kaggle/*.csv` via `Data`/`CSV`, normalizing teams/dates) → serves stdin JSON-RPC lines → dispatches `tools/call` to the `BrazilianSoccer` query functions → returns `content` + `structuredContent`.

## Notable design choices

- **Zero external dependencies** (`deps: []`) — CSV and JSON parsers are hand-written, so no network/hex fetch is needed in the sandbox.
- **Name normalization** folds accents (NFD + strip combining marks), removes the `-UF` state suffix, and maps a small alias table (e.g. "Sport Club Corinthians Paulista" → "corinthians").
- **Competition merging** — 5 match CSVs are unified into one match list tagged by `competition`; the extended `BR-Football-Dataset.csv` is tagged `"Extended Statistics"`.
- **Incomplete-row tolerance** — rows with unparseable dates are dropped (`safe_match` rescues `ArgumentError`); rows with non-integer goals ("NA"/"-") are excluded from result-based aggregates via `completed?/1`.

## Known issue

The aggregate functions (`standings/3`, `team_statistics/3`, `competition_statistics/2`, `head_to_head/4`) reuse `search_matches/2`, which applies a **default `limit: 100`**. Over the real datasets (~34k matches) this silently truncates aggregates to the 100 most-recent matches — see `findings.jsonl` (`agg-limit`).
