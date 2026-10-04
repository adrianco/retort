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

## Running

    pip install -r requirements.txt
    python server.py          # MCP server over stdio
    python -m pytest          # executable acceptance specs

## Structure (Dave Farley's four-layer model)

- `tests/acceptance/test_brazilian_soccer_questions.py` – specs in domain language
- `tests/acceptance/dsl.py` – DSL: domain vocabulary with defaults
- `tests/acceptance/mcp_driver.py` – protocol driver: calls the tools over the MCP protocol and asserts on answers
- `server.py` (MCP tools) + `soccer_data.py` (loading, team-name normalisation, queries) – the system under test
