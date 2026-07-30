# Brazilian Soccer MCP Server

An MCP (Model Context Protocol) server for the six bundled Brazilian soccer CSV
datasets. It provides normalized match, team, competition, and FIFA player
queries without requiring a database or third-party runtime library.

## Run

The project needs Python 3.10 or newer. No runtime packages are required.

```sh
python3 server.py
```

To inspect the loaded coverage without starting the stdio server:

```sh
python3 server.py --summary
```

An MCP client can use this configuration (replace the path with this checkout):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python3",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

The server uses newline-delimited JSON-RPC 2.0 on standard input/output and
implements the MCP `initialize`, `tools/list`, and `tools/call` lifecycle.

## Available tools

- `search_matches`, `latest_match`, and `find_finals` search fixtures across all match sources.
- `team_statistics`, `compare_teams`, `best_team_records`, and `biggest_wins` provide calculated records.
- `standings`, `relegated_teams`, `top_scoring_teams`, `competition_statistics`, `competition_bracket`, and `compare_seasons` provide competition analysis.
- `search_players` and `top_players` query FIFA player data.
- `team_competitions`, `team_profile`, and `derbies` cover relationships across teams, players, and competitions.
- `ask_brazilian_soccer` routes common natural-language questions to the matching structured tool.

Team searches are accent-insensitive and normalize common variations such as
`Flamengo-RJ`, `Flamengo - RJ`, and `Sport Club Corinthians Paulista`. Dates
accept ISO, ISO datetime, and Brazilian `DD/MM/YYYY` formats.

Raw match searches retain their source row so overlapping datasets remain
traceable. Aggregate queries choose one complete, authoritative source per
competition and season, preventing duplicated games from inflating standings
and team records.

## Development and tests

```sh
python3 -m pytest
```

The BDD-style tests cover CSV loading, name/date normalization, match search,
statistics, standings, cup finals, player filtering, natural-language routing,
and an end-to-end MCP stdio exchange.

## Data sources

- `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, and `Libertadores_Matches.csv`: [Kaggle Brazilian soccer data](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro), CC BY 4.0.
- `BR-Football-Dataset.csv`: [Brazilian football matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches), CC0.
- `novo_campeonato_brasileiro.csv`: [Campeonato Brasileiro 2003–2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019), CC BY 4.0.
- `fifa_data.csv`: [FIFA players data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data), Apache 2.0.
