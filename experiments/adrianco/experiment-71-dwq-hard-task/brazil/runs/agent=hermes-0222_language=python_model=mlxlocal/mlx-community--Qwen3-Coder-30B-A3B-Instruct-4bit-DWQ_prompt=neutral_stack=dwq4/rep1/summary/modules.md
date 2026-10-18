# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer_mcp_server.py | MCP server exposing 10 soccer-query tools over CSV-backed match/player data | `BrazilianSoccerData`, `soccer_data`, `mcp`, `find_matches_between_teams`, `find_matches_by_team`, `get_team_statistics`, `find_players_by_club`, `find_players_by_name`, `find_top_players`, `calculate_statistics`, `find_biggest_victories`, `get_competition_standings`, `get_head_to_head` |
| test_brazilian_soccer_mcp_server.py | Smoke tests: module import, tool registration, data loading | `test_import`, `test_tools_registered`, `test_data_loading` |
| integration_test.py | Calls two tool functions end-to-end against loaded data | `test_find_matches_between_teams`, `test_get_team_statistics` |
| verify_implementation.py | Prints a manual check of files, import, match count, registered tools | `main` |

Notes:
- The data source is `data/kaggle/` (6 CSVs: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv`).
- Markdown docs present but not source: `README.md`, `prompts.txt`, `brazilian-soccer-mcp-guide.md`, `IMPLEMENTATION_SUMMARY.md`, `FINAL_IMPLEMENTATION_REPORT.md`, `TASK.md`, `FEEDBACK.md`.
- This is a repair run: the task directory arrived with a failing prior attempt and `FEEDBACK.md` listing the defects to fix.
