# Fixtures

Self-contained conformance data so a port can be built and verified without a
live FunkyGibbon server. They encode the load-bearing rules of `inbetweenies-v2`
(see `../funkygibbon-mcp-port-guide.md` and the-goodies `inbetweenies/PROTOCOL.md`).

- **`version-strings.json`** — the canonical version format. `parse` cases must
  yield the given UTC timestamp (tolerate a legacy doubled-`Z` and hyphenated
  user ids; never *emit* a `Z`); `format` builds the canonical string;
  `lexical_order` must equal chronological+counter order.
- **`knowledge-graph.json`** — a small house graph (latest version per entity,
  including one tombstone) used to seed the local cache for the tool tests.
- **`sync-exchanges.json`** — golden `SyncRequest → SyncResponse` pairs with an
  `assert` list per exchange: full sync, an **exclusive** delta watermark, a
  concurrent-edit conflict resolved by the version tiebreak, and a tombstone
  delete.
- **`mcp-tool-golden.json`** — tool calls against the graph with the entity ids
  the result must contain (tombstoned entities are excluded from active results).

The JSON envelope your port emits should match the reference clients; what these
fixtures pin is the essential *content* (which timestamps, which ordering, which
winner, which entity ids).
