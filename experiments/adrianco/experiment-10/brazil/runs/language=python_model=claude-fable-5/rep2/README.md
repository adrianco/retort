# Brazilian Soccer MCP with spec and basic data sets

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

## Implementation

An MCP (Model Context Protocol) server over stdio, written in Python with the
official `mcp` SDK. All six CSVs are loaded into an in-memory knowledge base
at startup (~0.6s); queries answer in milliseconds.

### Files
- `server.py` — the MCP server (FastMCP, stdio transport), 13 tools
- `soccer_kb.py` — knowledge base: match search, head-to-head, team stats,
  standings calculated from results, cup finals, player search, aggregates
- `data_loader.py` — unified loading of the 5 match CSVs + FIFA player CSV,
  with cross-source de-duplication (overlapping Serie A sources are matched
  on season+round or teams+date±1 day; extra stats are merged)
- `team_normalizer.py` — team name normalization: accents (São Paulo / Sao
  Paulo), state suffixes (Flamengo-RJ / Flamengo), org tokens (EC Juventude /
  Juventude-RS), official names (Sport Club Corinthians Paulista), and the
  Atlético-PR → Athletico Paranaense rename
- `tests/` — 96 BDD Given/When/Then structured pytest scenarios, including
  the 20+ sample questions from the spec and an MCP stdio round-trip

### Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest        # run the test suite
.venv/bin/python server.py        # run the MCP server (stdio)
```

MCP client config:

```json
{"mcpServers": {"brazilian-soccer": {"command": "/path/to/.venv/bin/python", "args": ["/path/to/server.py"]}}}
```

### Tools
`search_matches`, `get_head_to_head`, `get_team_statistics`,
`get_team_competitions`, `get_standings` (champion + relegation calculated
from results), `get_cup_finals`, `get_libertadores_bracket`,
`search_players`, `get_players_by_club_summary`, `get_average_goals`,
`get_biggest_wins`, `get_best_record`, `get_data_summary`.

Coverage after de-duplication: 16,837 matches (Série A 2003-2023, Série B/C,
Copa do Brasil, Copa Libertadores) and 18,207 FIFA players (827 Brazilian).
Sanity-checked against history: 2019 champion Flamengo with 90 points,
2020 relegation (Vasco, Goiás, Coritiba, Botafogo), 2013 Copa do Brasil
final, 2018 Libertadores final (River 3-1 Boca).
