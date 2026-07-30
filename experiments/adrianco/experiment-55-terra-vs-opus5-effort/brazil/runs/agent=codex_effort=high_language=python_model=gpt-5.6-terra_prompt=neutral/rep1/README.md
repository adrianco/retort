# Brazilian Soccer MCP

An MCP (Model Context Protocol) stdio server over the six supplied Brazilian
soccer CSV datasets. It has no runtime dependency beyond Python 3.10+.

## Run

```bash
python3 brazilian_soccer_mcp.py
# or, after installation:
pip install .
brazilian-soccer-mcp
```

The server implements MCP `initialize`, `tools/list`, and `tools/call` over
newline-delimited JSON-RPC on standard input/output. Configure an MCP client
with `python3` as the command and `brazilian_soccer_mcp.py` as its argument.

Available tools are `search_matches`, `team_stats`, `head_to_head`,
`search_players`, `standings`, `competition_stats`, and
`competitions_for_team`. Team searches are accent-, punctuation-, and
state-suffix-insensitive (for example, `São Paulo-SP` and `Sao Paulo FC`).

Run the BDD-style tests with:

```bash
python3 -m pytest
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
