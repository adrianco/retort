# Brazilian Soccer MCP with spec and basic data sets

## Implementation

A TypeScript MCP server (stdio transport, built on `@modelcontextprotocol/sdk`)
that loads all six Kaggle CSVs into memory and answers natural-language-style
queries about Brazilian soccer through eleven MCP tools.

### Build, test, run

```bash
npm install
npm run build      # compiles src/ -> dist/
npm test           # vitest BDD suite (87 tests)
npm start          # runs the MCP server on stdio
```

Register with an MCP client (e.g. Claude Desktop / Claude Code):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["<repo>/dist/index.js", "<repo>/data/kaggle"]
    }
  }
}
```

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Matches by team, opponent, competition, season, date range |
| `head_to_head` | Full head-to-head record between two teams |
| `team_stats` | W/D/L, goals, win rate; filter by season/competition/venue |
| `league_standings` | Season table computed from results (3 pts/win) |
| `search_players` | FIFA players by name/nationality/club/position/rating |
| `player_profile` | Detailed single-player profile with closest-name fallback |
| `competition_stats` | Match counts, goal averages, home/away win rates |
| `biggest_wins` | Most lopsided results |
| `best_records` | Teams ranked by home or away win rate |
| `team_competitions` | Competitions and seasons a team appears in |
| `data_summary` | Loaded files, row counts, coverage overview |

### Design notes

- **Team-name normalization** (`src/teams.ts`): strips accents, state
  suffixes ("Palmeiras-SP", "América - MG", "America MG"), country codes
  ("Nacional (URU)"), club-type tokens ("EC Bahia", "Fortaleza FC") and
  applies aliases ("Athletico Paranaense" ≡ "Atlético-PR"), while keeping
  same-named clubs from different states distinct (América-MG ≠ América-RN).
- **Cross-file deduplication** (`src/loader.ts`): the same fixture appears in
  up to three files; matches are merged on (date ±1 day, home, away) and the
  extended-stats file contributes corners/shots/attacks to merged matches
  (~7,000 duplicates merged; ~16,800 unique matches + 18,207 players load in
  well under a second).
- **Standings** use the authoritative league files when they cover the
  requested season, falling back to the extended dataset (which is the only
  source for Série B/C). Computed tables reproduce real history (2019
  Flamengo 90 pts; 2003 Cruzeiro 100 pts; 2022 Série B Cruzeiro).
- **Dates** in ISO and DD/MM/YYYY forms are normalized; all text is UTF-8.
- **Tests** (`tests/`) are BDD Given/When/Then scenarios covering loading,
  normalization, match/team/player/competition queries, 20+ sample questions
  driven through a real MCP client over the SDK's in-memory transport, and
  the spec's performance limits.

## Specification
brazilian-soccer-mcp-guide.md

## Data Sources
Kaggle data can't be downloaded without an account so these (freely available with attribution) data sets have been downloaded for use here:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- data/kaggle/Brasileirao_Matches.csv
- data/kaggle/Brazilian_Cup_Matches.csv
- data/kaggle/Libertadores_Matches.csv

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- data/kaggle/BR-Football-Dataset.csv

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: World Bank - Attribution 4.0 International (CC BY 4.0)
- data/kaggle/novo_campeonato_brasileiro.csv

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- data/kaggle/fifa_data.csv
