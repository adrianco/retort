# Architecture Summary

Single-namespace, dependency-free Clojure stdio MCP server (`src/brazilian_soccer_mcp/core.clj`, 172 lines).

## Modules / flow

1. **Dataset config** — `dataset-files` lists the 5 match CSVs (Brasileirão, Copa do Brasil, Libertadores, extended BR-Football, historical) with per-file `:kind`; FIFA players loaded separately.
2. **Normalization** — `canonical-name` strips state suffixes (`-SP`), club-type words, NFD-normalizes accents, lowercases; `normalize-date` converts ISO / `DD/MM/YYYY` / datetime to `YYYY-MM-DD`; `parse-int` coerces numeric-ish strings.
3. **CSV ingest** — hand-rolled `parse-csv-line` (quote-aware) + `read-csv` (strips BOM); `standard-match`/`extended-match`/`historical-match` map each schema to a common match record; `load-data` returns `{:matches [...] :players [...]}`.
4. **Query layer** — `search-matches` (team/home/away/opponent/competition/season/date-range/round), `team-statistics`+`record-for` (W/L/D + goals for/against + points + win-rate), `head-to-head`, `standings` (points table computed from matches), `competition-statistics` (avg goals/match, home/away/draw counts), `search-players` (name/nationality/club/position/min-overall).
5. **MCP layer** — hand-rolled JSON codec (`parse-json`/`json`), `tool-definitions` (6 tools), `call-tool` dispatch, `handle-request` handling `initialize`/`tools/list`/`tools/call` as JSON-RPC 2.0, and `-main` reading stdin line-by-line.

## Tests

`test/brazilian_soccer_mcp/core_test.clj` — 3 BDD-style deftests / 6 assertions covering normalization, match search, team stats, head-to-head, player search, competition stats. Run via `test-runner` (`deps.edn` `:test` alias), which exits non-zero on failure. All pass.
