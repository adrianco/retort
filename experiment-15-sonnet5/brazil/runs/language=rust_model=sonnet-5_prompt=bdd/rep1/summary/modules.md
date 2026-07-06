# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Crate root; re-exports loader + knowledge base | `load_from_dir`, `KnowledgeBase` |
| src/main.rs | Binary entry point; serves MCP over stdio | `main()`, `resolve_data_dir()` |
| src/model.rs | Core data types for matches and players | `Competition`, `Venue`, `MatchOutcome`, `MatchRecord`, `PlayerRecord` |
| src/normalize.rs | Team-name normalization (accents, state suffixes, legal names) | `normalize_team_name`, `display_team_name`, `keys_match`, `name_matches`, `strip_diacritics` |
| src/dates.rs | Flexible parsing of the datasets' mixed date formats | `parse_flexible_date` |
| src/loaders.rs | CSV loaders for all six datasets into the unified model | `load_from_dir`, `load_brasileirao`, `load_copa_do_brasil`, `load_libertadores`, `load_extended_stats`, `load_historical_brasileirao`, `load_players` |
| src/store.rs | In-memory query engine over loaded records | `KnowledgeBase` with `find_matches`, `head_to_head`, `team_record`, `standings`, `biggest_wins`, `match_stats`, `list_teams`, `competitions_overview`, `search_players` |
| src/server.rs | MCP tool wiring (rmcp `#[tool_router]`/`#[tool_handler]`) | `BrazilianSoccerServer` + 9 `#[tool]` methods |
| tests/data_integration.rs | Integration tests against the real checked-in CSVs | 8 BDD-style test functions |

Unit tests live in `#[cfg(test)]` modules inside `dates.rs`, `normalize.rs`, `loaders.rs`, and `store.rs`. Total across the crate: 48 tests.
