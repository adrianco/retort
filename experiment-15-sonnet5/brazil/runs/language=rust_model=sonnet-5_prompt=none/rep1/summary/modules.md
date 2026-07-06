# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Binary entrypoint; resolves data dir, loads store, serves MCP over stdio | `main()`, `resolve_data_dir()` |
| src/lib.rs | Library crate root; re-exports the six modules | `data`, `model`, `normalize`, `queries`, `server`, `store` |
| src/model.rs | Unified in-memory data model | `MatchRecord`, `Player`, `MatchRecord::home_outcome()`, `has_result()`, `goal_diff()` |
| src/normalize.rs | Team-name normalization + flexible date/goal parsing | `normalize_team_name()`, `extract_state_suffix()`, `parse_flexible_date()`, `parse_goal()` |
| src/data.rs | CSV loaders for the six Kaggle datasets | `load_brasileirao()`, `load_cup()`, `load_libertadores()`, `load_br_football()`, `load_historical()`, `load_players()` |
| src/store.rs | In-memory store; dedup, ambiguous-base disambiguation, display-name indices | `Store`, `Store::load()`, `resolve_identity()`, `is_ambiguous_base()`, `is_brazilian_club()` |
| src/queries.rs | Pure read queries returning pre-formatted answer strings | `search_matches()`, `compare_teams()`, `team_record()`, `standings()`, `team_leaderboard()`, `biggest_wins()`, `average_stats()`, `derby_matches()`, `team_competitions()`, `search_players()`, `brazilian_club_squads()`, `list_datasets()` |
| src/server.rs | MCP tool surface (rmcp SDK); thin wrappers over `queries` | `SoccerServer`, 12 `#[tool]` methods + `ServerHandler` impl |
| tests/sample_questions.rs | Integration tests against real datasets covering the spec's sample questions | 27 test functions |

Unit tests live inline in `src/normalize.rs` (`#[cfg(test)] mod tests`, 5 tests). Total: 32 tests.
