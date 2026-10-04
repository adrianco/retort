# Brazilian Soccer MCP with spec and basic data sets

## Specification
brazilian-soccer-mcp-guide.md

## What was built
An MCP (Model Context Protocol) server, `brazilian_soccer_mcp`, that lets an LLM answer natural-language
questions about Brazilian soccer from the six provided Kaggle datasets. It is pure Python 3 standard library
(no runtime dependencies) and speaks MCP JSON-RPC over stdio. It loads all six files at startup (about 0.6s) and
answers every question in milliseconds.

### Tools offered to the assistant
| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals", "When did Flamengo last play Corinthians?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" (names the derby, e.g. Fla-Flu, Grenal) |
| `find_derbies` | "Show me all derbies in 2023" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `team_overview` | "What competitions has Palmeiras played in?" (results and FIFA squad combined) |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `knockout_bracket` | "Show the 2018 Copa Libertadores bracket" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `rank_teams` | "Which team has the best away record?", "Which team scored the most goals in Serie A 2023?" |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Santos" |
| `get_player` | "Who is Gabriel Jesus?" (suggests similar names when there is no exact match) |
| `club_squads` | "Brazilian players at Brazilian clubs" (player data joined with match data) |
| `dataset_summary` | Which files are loaded and what they cover |

Each answer comes as readable text, laid out like the examples in the specification, plus `structuredContent` JSON.

### Data handling
- **Team names**: every spelling ("Palmeiras-SP", "Palmeiras - SP", "Sociedade Esportiva Palmeiras", "Gremio RS",
  "Grêmio") is reduced to one canonical club. A state suffix is kept only when it isn't the club's home state, so
  Flamengo-PI stays separate from Flamengo and Atlético-MG/-GO/Athletico-PR are distinct. Clubs are shown with
  their Portuguese spelling. Minor-club spellings are unified when two datasets clearly record the same match.
- **Duplicates**: a Brasileirão match can appear in three files. Records of the same fixture are merged into one
  match that remembers all its sources and keeps the corners/shots statistics. Within a league season the merge key
  is the season; otherwise it is a date window. The two primary Brasileirão files win when the extended dataset's
  score disagrees.
- **Dates**: ISO, ISO with time and Brazilian DD/MM/YYYY are all understood. Rows without a result (`NA`, `-`)
  are skipped and counted.
- **Standings**: 3 points a win; ties broken by wins, then goal difference, then goals scored. The bottom four are
  relegated (two in 2003). Copa do Brasil's numbered rounds are mapped to final/semifinals/quarterfinals.

## Running it
```bash
python3 -m brazilian_soccer_mcp                    # uses data/kaggle
python3 -m brazilian_soccer_mcp --data-dir /path/to/csvs
```
To connect it to Claude Desktop or Claude Code, add it to the MCP configuration:
```json
{"mcpServers": {"brazilian-soccer": {"command": "python3", "args": ["-m", "brazilian_soccer_mcp"],
                                      "cwd": "/path/to/this/repo"}}}
```
or `claude mcp add brazilian-soccer -- python3 -m brazilian_soccer_mcp` from this directory.

## Tests: Acceptance Test-Driven Development
The system was built following Dave Farley's ATDD approach: executable specifications were written first, in the
language of the problem domain, and then the implementation was written to make them pass. The acceptance tests use
his four-layer model:

1. **Specifications** (`tests/acceptance/test_*.py`): short Given/When/Then specs named after capabilities, e.g.
   ```python
   def test_should_find_every_meeting_between_two_teams(archive, matches):
       archive.has_match("Flamengo 2-1 Fluminense", date="2023-09-03")
       archive.has_match("Fluminense 1-0 Flamengo", date="2023-05-28")
       archive.has_match("Flamengo 3-0 Santos")

       matches.search_between("Flamengo", "Fluminense")

       matches.confirm_found("Flamengo 2-1 Fluminense", "Fluminense 1-0 Flamengo")
   ```
2. **DSL** (`tests/acceptance/dsl/`): split by domain area (archive, matches, teams, rivalries, players,
   competitions, statistics, assistant), with defaults for everything a spec doesn't care about.
3. **Protocol drivers** (`tests/acceptance/drivers/`): the only code that knows how the system works.
   `ArchiveDriver` writes each spec's synthetic data in the exact layout of the six Kaggle files, standing in for the
   external data source. The query drivers start the real server as a subprocess and talk MCP over stdio, as an AI
   host would. All assertions live here.
4. **System under test**: `brazilian_soccer_mcp/`.

Each spec owns its own synthetic archive and server instance (functional isolation), so specs are independent and
order-free. `test_provided_datasets.py` runs against the real data: all six files load, the 2019 champion and 2020
relegations come out right, and 24 sample questions are each answered within 2s (lookups) or 5s (aggregates).
Unit tests (`tests/unit/`) cover name normalisation and protocol edge cases.

```bash
python3 -m venv venv && venv/bin/pip install -r requirements-dev.txt
venv/bin/pytest            # 133 tests, about 2 seconds
```
Findings that the ATDD work surfaced are logged in `docs/atdd-findings.md`.

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
