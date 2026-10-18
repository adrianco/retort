# Run Summary

## Surface

An MCP (Model Context Protocol) server, written in Objective-C against Foundation only,
that answers natural-language-style queries about Brazilian soccer from pre-downloaded
Kaggle datasets. It loads five match CSVs plus the FIFA player CSV into an in-memory store
and exposes nine JSON-RPC tools (match search, head-to-head, team stats, standings,
rankings, league stats, biggest wins, player search, team profile) over newline-delimited
stdin/stdout.

## Architecture

- **Transport/protocol** (`BSMCPServer`): minimal JSON-RPC 2.0 over NDJSON — `initialize`,
  `ping`, `tools/list`, `tools/call`; notifications get no reply, malformed input returns
  JSON-RPC errors.
- **Data layer** (`BSDataStore` + `BSCSVParser`): robust CSV reader (quotes, embedded
  newlines, CRLF, BOM) feeding a loader that normalizes team names/dates, canonicalizes
  competitions, and deduplicates overlapping sources on teams+score with a ±1-day
  tolerance. First file in the spec list wins.
- **Domain** (`BSModels`): `BSMatch`, `BSPlayer`, `BSTeamRecord`, `BSHeadToHead`, and the
  query value objects.
- **Query logic** (`BSQueryEngine`): match filtering, team records, head-to-head,
  points-based standings, venue rankings, league aggregates, biggest wins, player search,
  cross-dataset team profile.
- **Text utilities** (`BSTextUtils`): team-name folding/display, competition canonicalization,
  date normalization across ISO/ISO-time/Brazilian formats.
- **Tools** (`BSMCPTools`): registers the nine tools, each mapping arguments to the engine
  and formatting plain-text answers matching the spec's example formats.
- **Entry point** (`main.m`): loads data (arg / `$BSM_DATA_DIR` / `./data/kaggle`), serves
  the read-eval loop; diagnostics to stderr, protocol to stdout.

See `modules.md` for the per-file table.

## Tests

46 BDD-style scenarios across protocol, tools, parsing, normalization, and the real
datasets; `test_coverage=1.0` (build + all tests pass). No skipped or disabled tests.
