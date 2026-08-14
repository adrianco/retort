# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server for querying the six Brazilian soccer
CSV datasets bundled in `data/kaggle/`. It exposes structured tools for match,
team, player, competition, and aggregate-statistics questions, plus a
deterministic `ask_brazilian_soccer` convenience tool for common natural-language
questions.

All answers are derived from the local dataset snapshots. They are not live
scores, rosters, or current standings.

## Install and run

Use a clean environment so the MCP SDK and Pydantic versions are compatible:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/brazilian-soccer-mcp
```

The default transport is MCP stdio, suitable for an LLM client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "brazilian-soccer-mcp"
    }
  }
}
```

Use another dataset location with either `--data-dir /path/to/kaggle` or the
`BRAZILIAN_SOCCER_DATA_DIR` environment variable. The project uses the official
Python MCP SDK when installed. It also has a small core-stdio fallback so a host
with an inconsistent global MCP/Pydantic install can still serve the local tools.

## MCP tools

| Tool | Purpose |
|---|---|
| `data_summary` | Loaded file coverage, row counts, and source attribution. |
| `knowledge_graph` | Compact Team/Match/Competition/Season or Player/FIFA-club-snapshot subgraph. |
| `search_matches` | Filter by team, opponent, competition, season, date range, venue, round, stage, or source. |
| `team_statistics` | W/D/L, goals, points, and win rate. |
| `compare_teams` | Orientation-independent head-to-head record. |
| `search_players` / `compare_players` | FIFA player snapshots by name, nationality, club, position, and rating. |
| `competition_standings` | Calculated standings with explicit tie breakers and coverage caveats. |
| `competition_statistics` / `best_team_record` / `teams_by_goals` | Aggregate goals, home/away rates, largest wins, and rankings. |
| `libertadores_by_stage` | Stage-grouped Libertadores results without invented knockout brackets. |
| `team_competitions`, `derby_matches`, `compare_seasons` | Relationship and trend queries. |
| `players_at_clubs_faced` | Cross-file join with a FIFA-snapshot, not-lineup disclaimer. |
| `top_scorers_status` | Truthful explanation that player-goal events are not in the supplied schemas. |
| `ask_brazilian_soccer` | Routes common natural-language questions to the tools above. |

For a conversational follow-up such as “What was the score?”, pass the previous
match in `context.last_match`; otherwise the server requests clarification rather
than guessing.

## Data behavior and safeguards

- Team and club lookups are accent-, punctuation-, case-, state-suffix-, and
  curated-alias-insensitive. Source names remain intact in returned rows.
- ISO dates, ISO datetimes, and `DD/MM/YYYY` dates are accepted. Date ranges are
  inclusive.
- Raw match search returns the requested dataset rows with `source` and
  `source_file`. Aggregate calculations avoid overlap double-counting by selecting
  one best-covered source per competition/season (most complete rows, then a
  documented source priority), rather than concatenating overlapping feeds.
- Standings use 3 points per win and 1 per draw; ties use points, wins, goal
  difference, goals for, then team name. Relegation is withheld when coverage is
  visibly incomplete.
- Derby matches use the explicit curated `RIVALRIES` mapping in
  `brazilian_soccer_mcp/service.py`; the source data does not label derbies.
- FIFA club fields are snapshots and never presented as historical match lineups.
  Player scorer data is not inferable from final team scores.

## Development and verification

```bash
python -m pytest -q
python -m compileall -q brazilian_soccer_mcp tests
```

The test suite includes BDD-style scenarios, full-source loading assertions,
normalization/date/nullable-score coverage, cross-source aggregate handling, more
than 20 routed natural-language examples, performance checks, and an MCP stdio
initialize/list/call integration test.

## Data attribution

- Brasileirão, Copa do Brasil, and Libertadores matches: Kaggle
  `ricardomattos05/jogos-do-campeonato-brasileiro` (CC BY 4.0)
- Extended Brazilian match statistics: Kaggle
  `cuecacuela/brazilian-football-matches` (CC0)
- Historical Brasileirão: Kaggle
  `macedojleo/campeonato-brasileiro-2003-a-2019` (CC BY 4.0)
- FIFA player dataset: Kaggle `youssefelbadry10/fifa-players-data` (Apache 2.0)
