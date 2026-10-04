# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server that lets an LLM answer natural-language questions about
Brazilian football — matches, teams, competitions, statistics and players — from the provided Kaggle datasets.
The requirements are in [TASK.md](TASK.md).

Built test-first with Dave Farley's Acceptance Test-Driven Development: the executable specifications in
`tests/acceptance` were written first, in the language of football, and the server was then built until they
passed.

## Quick start

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python -m brazilian_soccer_mcp                         # MCP over stdio, data from data/kaggle
venv/bin/python -m brazilian_soccer_mcp --data-dir /path/to/csvs # or set BRAZILIAN_SOCCER_DATA_DIR
venv/bin/python -m pytest                                        # 111 tests, ~15s
```

Example Claude Desktop / Claude Code configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/repo/venv/bin/python",
      "args": ["-m", "brazilian_soccer_mcp"],
      "cwd": "/path/to/repo"
    }
  }
}
```

## Tools

Every tool returns a formatted text answer (as in TASK.md's examples) **and** the same facts as structured
JSON. Questions the data can't answer (unknown team, malformed date) come back as tool errors with a helpful
message, so the LLM can correct itself.

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2022?", "Find all Copa do Brasil finals" (filters: team, opponent, home/away, competition, season, date range, stage) |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head", "When did Flamengo last play Corinthians?" |
| `team_record` | "What is Corinthians' home record in 2022?" (by season, competition, venue) |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `club_profile` | Match record + competitions + FIFA squad for one club (cross-dataset) |
| `league_table` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `top_scoring_teams` | "Which team scored the most goals in Serie A 2022?" |
| `knockout_bracket` | "Show the 2018 Copa Libertadores bracket" |
| `competition_summary` | "What's the average goals per match in the Brasileirão?", home/draw/away win rates |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `best_records` | "Which team has the best home / away record?" |
| `find_derbies` | "Show me all derbies in 2022" (Fla-Flu, Grenal, Derby Paulista, Choque-Rei, Clássico Mineiro, …) |
| `search_players` | "Find all Brazilian players", "Who are the highest-rated players at Grêmio?", "Show me all forwards from Santos" |
| `player_profile` | "Who is Neymar?" (suggests similar names when a player isn't in the data) |
| `brazilian_players_by_club` | Brazilian players at Brazilian clubs, with average ratings |
| `dataset_overview` | Which files are loaded, row counts, seasons covered |

## How it works

```
brazilian_soccer_mcp/
  server.py        MCP tools (the public interface); loads data once at start-up
  knowledge.py     merges all datasets into one set of matches; every query and its formatted answer
  datasets.py      one loader per CSV file, each handling that file's format quirks
  teams.py         team identity: one club however a dataset writes its name
  competitions.py  canonical competition and knockout-stage names
  text.py          accent-insensitive names, all date formats
```

- **Team names**: raw names are parsed into a base name and a qualifier (Brazilian state or country code), so
  `Palmeiras-SP`, `Palmeiras - SP`, `Palmeiras` and `Sociedade Esportiva Palmeiras` are one club, while
  `Botafogo-RJ` and `Botafogo-PB`, or Argentina's `River Plate` and Sergipe's `River Plate - SE`, stay apart.
  Questions are matched without accents ("gremio", "Sao Paulo FC").
- **One match, many files**: a 2015 Série A match appears in up to three files. Records are merged into one
  match (a league pairing happens once a season; cup ties merge by date), keeping the most authoritative file's
  details and adding corners/shots/attacks from the extended dataset. The Série A seasons 2006-2022 come out at
  exactly 380 matches each.
- **Dates**: `2023-09-24`, `2012-05-19 18:30:00` and `29/03/2003` are all understood, in data and in questions.
- **Seasons**: league matches played in January-March of the extended dataset belong to the previous season
  (the 2020 Brasileirão ended in February 2021).
- **Copa do Brasil stages**: the cup file numbers its rounds; the final is the last round if it holds a single
  tie, and earlier stages are counted back from it.
- **Performance**: all data (≈23k match records, 18k players) loads in ≈0.5s; every query runs in memory in
  milliseconds.

## Acceptance tests (Dave Farley's four-layer model)

```
tests/acceptance/
  test_*.py                 1. Executable specifications, in football language only
  dsl/                      2. DSL: given (what the datasets record), matches, teams, competitions, stats, players
  drivers/datasets.py       3. Protocol driver for the external inputs: writes facts in each CSV's native format
  drivers/soccer_server.py  3. Protocol driver for the SUT: MCP tools/call requests + assertions
  drivers/mcp_client.py        Minimal MCP JSON-RPC client over stdio (poll-with-timeout, no sleeps)
                            4. System under test: the real server, launched as a subprocess
tests/unit/                 Fine-grained cases for name parsing, dates and competition names
```

A spec reads like this:

```python
def test_should_count_a_match_once_when_several_datasets_record_it(soccer):
    soccer.given.match("Palmeiras-SP 6-0 Sao Paulo-SP", source="brasileirão", date="2015-09-13", season=2015)
    soccer.given.match("Palmeiras 6-0 São Paulo", source="historical brasileirão", date="2015-09-13", season=2015)
    soccer.given.match("Palmeiras 6-0 Sao Paulo", source="extended statistics", date="2015-09-13")

    soccer.matches.confirm_meetings("Palmeiras", "São Paulo", count=1)
```

- Most specs generate their own **synthetic data**: the DSL writes just the matches and players a spec needs into
  a private directory and starts a private server, so specs are isolated from each other and from the real data.
- `test_provided_datasets.py` runs against the real `data/kaggle` files: all six load with the expected row
  counts, well-known facts come out right (Flamengo 2019 champions with 90 pts, 28W 6D 4L; 2020 relegations),
  and 24 sample questions from TASK.md are answered within the time limits (simple < 2s, aggregate < 5s).

Findings that writing the specs surfaced about the data are logged in
[docs/atdd-findings.md](docs/atdd-findings.md).

## Data sources

Kaggle data can't be downloaded without an account, so these (freely available with attribution) datasets are
included in `data/kaggle`:

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
