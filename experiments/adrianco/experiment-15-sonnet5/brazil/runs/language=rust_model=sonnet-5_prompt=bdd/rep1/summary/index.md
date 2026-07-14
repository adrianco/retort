# Summary: language=rust · model=sonnet-5 · prompt=bdd · rep 1

- **Shape:** Rust MCP server (rmcp 2.0 over stdio) with an in-memory knowledge base over six checked-in Kaggle CSVs.
- **Structure:** 8 source modules + 1 integration test file; 48 tests total (40 unit in `#[cfg(test)]` modules + 8 integration).
- **Interfaces:** 9 MCP tools (find_matches, head_to_head, team_record, standings, biggest_wins, match_stats, list_teams, list_competitions, search_players); 0 HTTP routes; 0 CLI subcommands.
- **Notable:** Careful team-name normalization that *preserves* disambiguating region codes (`-MG` vs `-PR`) instead of naively stripping suffixes; standings use official CBF tiebreak order; BDD Given/When/Then test naming throughout. Query logic concentrated in a large `store.rs` (937 lines).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
