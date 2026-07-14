# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
answers natural-language questions about Brazilian soccer — players, teams,
matches, competitions and statistics — over the bundled Kaggle datasets. An LLM
client connects to the server and calls its tools to look up matches, compute
league standings, search players, and more.

The implementation follows the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) / `TASK.md`.

## Quick start

```bash
pip install -r requirements.txt

# Run the MCP server over stdio (standard MCP transport)
python server.py

# See sample answers without an MCP client
python demo.py

# Run the acceptance + unit test suite
pytest
```

To use it from an MCP client (e.g. Claude Desktop), point the client at
`python /path/to/server.py` as a stdio server named `brazilian-soccer`.

## MCP tools

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2019?", "Find Copa do Brasil matches" |
| `get_team_record` | "What is Corinthians' home record in 2019?" |
| `compare_teams` | "Compare Palmeiras and Santos head-to-head" |
| `search_players` | "Find the top Brazilian players", "Who plays for Santos?", "Show me strikers" |
| `get_standings` | "Who won the 2019 Brasileirão?" (table computed from results) |
| `get_competition_summary` | "What's the average goals per match?", "Show the biggest wins" |
| `list_team_competitions` | "What competitions has Palmeiras played in?" |
| `get_team_profile` | Combined match record + FIFA squad for a club (cross-file query) |

Every tool returns a JSON object in the language of the domain (matches,
records, standings, players) that the LLM can render into prose.

## Architecture

```
server.py          MCP adapter — exposes SoccerService methods as MCP tools (FastMCP, stdio)
soccer_service.py  Domain logic — matches, records, head-to-head, players, standings, stats
soccer_data.py     Data layer — loads & normalizes the six CSVs into two pandas tables
team_names.py      Team-name normalization (accents, state suffixes, aliases)
demo.py            CLI demonstration of sample questions
tests/             Executable acceptance tests (via the MCP protocol) + unit tests
```

### Data handling

The spec's three data-quality challenges are handled in the data layer:

- **Team-name variations** — `"Palmeiras-SP"`, `"Palmeiras"` and
  `"Sociedade Esportiva Palmeiras"` all normalize to one canonical key
  (`team_names.normalize_team`), so queries match regardless of spelling.
- **Multiple date formats** — ISO (`2023-09-24`), Brazilian (`29/03/2003`) and
  datetime (`2012-05-19 18:30:00`) are all parsed to a common ISO date.
- **UTF-8 / accents** — accented names (`Grêmio`, `São Paulo`) are matched
  accent-insensitively.

The Brasileirão appears in three overlapping source files. To avoid
double-counting in standings and aggregate statistics, the loader keeps, for
each `(competition, season)`, the rows from a single authoritative source. This
yields a clean 380-match double round-robin per season — e.g. the 2019
Brasileirão standings reproduce the real result (Flamengo champion, 90 pts,
28W-6D-4L).

## Development approach

Built with executable Acceptance Test-Driven Development. Each requirement in
the specification was first written as an automated acceptance test that
exercises the system **only through the MCP protocol** (a real `ClientSession`
talking JSON-RPC to the server), asserting on *what* the system answers rather
than *how*. Finer-grained unit tests drive the internals (`team_names`,
`soccer_data`). Run `pytest` to execute the full suite.

## Data Sources

Kaggle data can't be downloaded without an account, so these freely available
(with attribution) datasets have been downloaded for use here, under
`data/kaggle/`:

[jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)
— License: CC BY 4.0
- `Brasileirao_Matches.csv`
- `Brazilian_Cup_Matches.csv`
- `Libertadores_Matches.csv`

[brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches)
— License: CC0 Public Domain
- `BR-Football-Dataset.csv`

[campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019)
— License: CC BY 4.0
- `novo_campeonato_brasileiro.csv`

[fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data)
— License: Apache 2.0
- `fifa_data.csv`
