# Brazilian Soccer MCP

A Rust stdio MCP server over the six supplied Brazilian soccer CSV datasets. It loads data once at startup and lets an MCP-capable LLM answer natural-language requests through structured tools.

## Run

```sh
cargo run --offline --release
```

The default dataset directory is `data/kaggle`. Set `SOCCER_DATA_DIR` to use another location.

For an MCP client configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "cargo",
      "args": ["run", "--offline", "--release"],
      "cwd": "/absolute/path/to/this/repository"
    }
  }
}
```

## Tools

- `search_matches`: filters by team, opponent, competition, season, and ISO date range.
- `team_record`: calculates W/D/L and goals, optionally by venue.
- `head_to_head`: compares two teams, including the matching match list.
- `search_players`: filters FIFA players by name, nationality, club, or position, ordered by rating.
- `standings`: calculates a season's table from match results.
- `statistics`: returns match count, total/average goals, and biggest win.

Team matching is case-insensitive, accent-insensitive, and handles common state suffixes such as `Palmeiras-SP`.

## Verification

```sh
cargo fmt --check
cargo test --offline
```

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
