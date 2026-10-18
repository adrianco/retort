# Architecture summary — brazilian-soccer MCP server (TypeScript)

> `run-summary` skill was not available in this harness; this is a lightweight hand-written
> summary from reading the source.

## Modules (`src/`)

| File | Role |
|------|------|
| `index.ts` | stdio-transport entrypoint; wires `createServer()` to the MCP SDK's stdio transport. |
| `server.ts` | MCP wiring. Registers 8 zod-validated tools, lazily loads the dataset, maps `QueryError` to MCP tool errors. |
| `queries.ts` | Pure query functions over the in-memory `Dataset` (search, stats, standings, h2h, aggregates, player search, club summaries). |
| `dataset.ts` | Loads + normalizes all six Kaggle CSVs into one cached `Dataset`; two-pass team-key disambiguation and cross-source de-duplication. |
| `normalize.ts` | Team-name folding, state-suffix handling, canonical key derivation, fuzzy text match. |
| `csv.ts` | CSV reader + numeric coercion helpers. |
| `dates.ts` | Multi-format date parsing (ISO, Brazilian DD/MM/YYYY, datetime). |
| `format.ts` | Human-readable formatting of query results for the LLM. |
| `types.ts` | `Dataset`, `Match`, `Player`, `Venue` type definitions. |

## MCP tools exposed

`search_matches`, `team_stats`, `head_to_head`, `standings`, `biggest_wins`,
`aggregate_stats`, `search_players`, `club_squad_summary`.

## Data flow

CSV files → `buildDataset()` (parse → normalize team keys → de-dup → index) → cached
`Dataset` → pure `queries.ts` functions → `format.ts` → MCP `TextResult`.

## Testing

`tests/` uses vitest with a synthetic fixture dataset (`tests/fixtures/make-fixture.ts`)
injected via `DATA_DIR`. `server.test.ts` drives a real MCP client over the SDK's in-memory
transport — end-to-end tool registration, schema validation and error reporting.
