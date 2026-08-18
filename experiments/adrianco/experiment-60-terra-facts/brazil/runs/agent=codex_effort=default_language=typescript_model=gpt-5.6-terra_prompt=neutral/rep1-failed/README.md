# Brazilian Soccer MCP

An MCP stdio server over the six supplied Brazilian-football CSV datasets. It loads the files once at startup, normalizes team-name accents/state suffixes, and returns structured results an MCP-capable LLM can format naturally.

## Run

This project is dependency-free and uses Node 26's built-in TypeScript stripping:

```sh
npm start
```

For an MCP client configuration, use:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "npm",
      "args": ["start"],
      "cwd": "/absolute/path/to/this/repository"
    }
  }
}
```

Set `SOCCER_DATA_DIR` when the six CSV files live outside `data/kaggle`.

## Tools

- `search_matches` — filter by team, opponent, competition, season, dates, round, or stage.
- `team_record` and `head_to_head` — team statistics and rivalry comparisons.
- `search_players` — FIFA player name, nationality, club, and position searches.
- `standings` and `competition_statistics` — calculated tables and aggregate results.
- `ask_question` — convenience support for common natural-language prompts; an LLM can use the focused tools for richer questions.

Every tool returns JSON text content, the normal MCP representation for structured tool results. Match search defaults to 50 results and supports up to 20,000; aggregates evaluate all matching data.

## Verify

```sh
npm test
```

The tests exercise CSV ingestion, name-variation matching, computed records/standings, player filtering, and MCP initialize/tool-call behavior.

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
