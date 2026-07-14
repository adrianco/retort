# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/soccer/data.clj | Load & normalize the Kaggle CSVs into a uniform `{:matches :players}` model (accents, name suffixes, multi-format dates, float goals) | `load-dataset`, `norm`, `display-name`, `parse-date`, `parse-int-ish` |
| src/soccer/query.clj | Domain query/analysis functions returning human-readable answer strings | `find-matches`, `team-stats`, `compare-teams`, `search-players`, `competition-standings`, `competition-stats` |
| src/soccer/tools.clj | MCP tool catalogue mapping each query to a tool `{:name :description :inputSchema :handler}` | `tools`, `by-name`, `public-list` |
| src/soccer/server.clj | JSON-RPC 2.0 / MCP server over stdio; protocol boundary | `create-server`, `process-line`, `handle-request`, `-main` |
| test/soccer/test_helpers.clj | Isolated on-disk CSV fixtures + JSON-RPC client through the public MCP surface | `make-fixture-dir!`, `new-server`, `call-tool`, `list-tools` |
| test/soccer/acceptance_test.clj | Executable acceptance spec exercising the SUT only through MCP tools/call | 13 deftests |
| test/soccer/data_test.clj | Unit TDD layer for normalization internals (names, dates, goals) | 6 deftests |
| test/soccer/real_data_test.clj | Coverage tests against the real `data/kaggle` datasets | 1 deftest |
