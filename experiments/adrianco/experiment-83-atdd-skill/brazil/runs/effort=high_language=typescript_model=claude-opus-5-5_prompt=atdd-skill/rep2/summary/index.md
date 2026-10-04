# Architecture summary — brazilian-soccer-mcp (rep2)

> The `run-summary` skill is not available in this session; this is a hand-written
> equivalent based on a read of the source tree.

## Shape

An MCP (stdio) server exposing 16 tools over a single in-memory knowledge base built
from the six Kaggle CSVs.

```
src/server.ts        MCP entrypoint: loadDatasets() -> SoccerKnowledge -> registerTools()
src/datasets.ts      Loads + de-duplicates the 6 CSVs into {matches, players, datasets}
src/knowledge.ts     SoccerKnowledge: all query/aggregation logic (619 LOC, the core)
src/tools.ts         16 MCP tool registrations (zod input schemas) -> kb methods
src/teams.ts         TeamRegistry: normalises name variants (state suffixes, accents)
src/competitions.ts  Competition ids/names, league vs knockout, relegation places
src/dates.ts         Multi-format date parsing (ISO, DD/MM/YYYY, with time)
src/derbies.ts       Known traditional-rivalry pairs
src/format.ts        Human-readable text rendering of each answer
src/model.ts         Match / Player / Stats types
src/text.ts          String normalisation helpers
```

## Test infrastructure (textbook ATDD four-layer model)

```
acceptance/specs/*.spec.ts   Executable specs in football language (6 files, ~61 cases)
acceptance/dsl/*             DSL decomposed by domain area (given/matches/teams/...)
acceptance/drivers/
  soccer-system-driver.ts    Protocol-driver CONTRACT (interface)
  mcp-soccer-driver.ts       Protocol driver: talks real MCP-over-stdio to the SUT
  dataset-stub.ts            Stub-as-translator: writes real CSV dialects to a temp dir
test/*.test.ts               Unit tests for edge cases (teams, dates/competitions)
```

Each acceptance test gets its own temp dataset dir and its own SUT process (full
functional + temporal isolation). Specs assert on domain outcomes, never on tool
names or JSON shapes.

## Data flow

CSV files → `loadDatasets()` (parse + merge duplicate match records across files) →
`SoccerKnowledge` (filter/aggregate) → tool handler → `format.*` text + structured
content → MCP client.
