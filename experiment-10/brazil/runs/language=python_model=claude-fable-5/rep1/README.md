# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## Implementation

An MCP (Model Context Protocol) server over the six Kaggle CSV datasets,
answering natural-language questions about Brazilian soccer matches
(2003–2023), teams, competitions, and FIFA player data.

### Files

| File | Purpose |
|------|---------|
| `server.py` | MCP server (FastMCP, stdio transport) exposing 12 tools |
| `queries.py` | Query engine: match search, head-to-head, team stats, standings, player search, statistics |
| `soccer_data.py` | CSV loading, team-name normalization, date parsing, cross-source de-duplication |
| `demo.py` | Answers 25 sample questions from the spec |
| `tests/` | BDD-style pytest suite (60 tests) |

### Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Run

```bash
.venv/bin/python server.py        # MCP server over stdio
.venv/bin/python demo.py          # answer 25 sample questions
.venv/bin/pytest tests/           # run the test suite
```

Claude Desktop / Claude Code config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

### Tools

- `search_matches` — by team, opponent, competition, season, date range
- `get_head_to_head` — all matches + aggregate record between two teams
- `get_team_stats` — W/D/L, goals, win rate (overall, home, or away)
- `get_team_competitions` — competitions/seasons a team appears in
- `get_standings` — league table calculated from results (champion/relegation for complete seasons)
- `get_competition_stats` — goals per match, home/away win rates
- `get_biggest_wins`, `get_best_records` — statistical analysis
- `search_players`, `get_player`, `get_top_players` — FIFA player database
- `get_data_summary` — dataset coverage overview

### Implementation notes

- **Team name normalization**: "Flamengo-RJ", "Flamengo - RJ", and
  "Flamengo" all resolve to one club; accents are optional ("São Paulo" =
  "Sao Paulo"); same-name clubs in different states (Atlético-MG /
  Athletico-PR / Atlético-GO) stay distinct.
- **De-duplication**: the Brasileirão (2012–2022), historical (2003–2019),
  and extended (2012–2023) files overlap; the same real-world match is
  kept once (with ±1 day tolerance — the extended dataset records UTC
  dates). Validated against known results: Flamengo won 2019 with 90
  points from exactly 380 season matches.
- **Player data caveat**: the FIFA dataset is the FIFA 19 player database,
  so most Brazilian-league rosters are absent, but 800+ Brazilian players
  at clubs worldwide are searchable. FIFA's abbreviated names are handled
  ("Gabriel Jesus" finds "G. Jesus").

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
