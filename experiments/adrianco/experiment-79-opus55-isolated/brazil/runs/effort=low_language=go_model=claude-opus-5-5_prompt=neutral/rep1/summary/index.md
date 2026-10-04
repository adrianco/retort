# Summary: effort=low language=go model=claude-opus-5-5 prompt=neutral · rep 1

- **Shape:** Go stdlib-only MCP server (JSON-RPC 2.0 over stdio) with an in-memory store over six Brazilian-soccer Kaggle CSVs; no external dependencies, no HTTP.
- **Structure:** 6 source modules (one flat `package main`) + 1 test file with 10 BDD-style `TestFeature_*` functions.
- **Interfaces:** 0 HTTP routes / 15 MCP tools + a CLI (`-call`/`-data`) / 6 JSON-RPC methods.
- **Notable:** Heavy investment in team-name normalisation (`normalize.go`): accent folding, (base, state) canonical keys, alias/special/foreign-club tables, a frequency-based display-name resolver, and a derbies registry. Multi-source match de-duplication merges overlapping CSVs (first source wins on score, later ones add stadium/extended stats). Tool errors surface as `isError:true` text, not JSON-RPC errors.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
