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

## Brazilian Soccer MCP Server

A Python MCP (Model Context Protocol) server that answers natural-language questions about Brazilian soccer through an LLM client. It loads the six Kaggle files in `data/kaggle/` into memory (standard library only) and exposes structured query tools over stdio.

### What it covers
- **Matches**: search by team, opponent, date range, competition and season; venue filters (home/away).
- **Teams**: win/draw/loss and goal records, head-to-head, home and away win-rate rankings.
- **Competitions**: league tables calculated from results (3 points for a win, relegation marking), season statistics, biggest wins.
- **Players**: name search, filters by nationality, club and position group, club squad profiles.

### Data handling
- Each (competition, season) is taken from one source file, in priority order, because the files overlap (Brasileirão 2012-2019 appears in three of them) and spell clubs differently.
- Team names are normalised (state suffixes such as `-SP` or `(RJ)`, full club names, accents, a few known aliases). A club keeps its state in the standings only when one name maps to several states in the same competition, so Atlético-MG and Athletico-PR stay separate.
- Rows with `NA` dates or scores are skipped.

### Running
```bash
# Start the MCP server (stdio); data defaults to data/kaggle
./venv/bin/python -m brazilian_soccer_mcp.server --data-dir data/kaggle

# Run the tests
./venv/bin/python -m pytest
```

Example MCP client config:
```json
{"mcpServers": {"brazilian-soccer": {"command": "python", "args": ["-m", "brazilian_soccer_mcp.server", "--data-dir", "data/kaggle"], "cwd": "/path/to/repo"}}}
```

### Layout
- `brazilian_soccer_mcp/names.py`: team and competition normalisation
- `brazilian_soccer_mcp/data.py`: CSV loaders for the six files
- `brazilian_soccer_mcp/queries.py`: knowledge base queries
- `brazilian_soccer_mcp/formatting.py`: answer text in the spec's layout
- `brazilian_soccer_mcp/server.py`: MCP stdio server and tool definitions
- `tests/`: Given/When/Then scenarios (pytest), including acceptance checks on the real data

### Known limitations
- The player file is FIFA 2019 and does not include every club or player (for example, no Flamengo squad and no "Gabriel Barbosa").
- The match data has no goal scorers, so "top scorers" is not answerable.
- Relegation is inferred as the bottom N places, which is correct for the 20-team era only.
- Neo4j, mentioned in the sample prompt, is not used. The data fits comfortably in memory and the spec does not require a graph database.
