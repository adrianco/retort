# Brazilian Soccer MCP with spec and basic data sets

An [MCP](https://modelcontextprotocol.io) server that exposes a knowledge-graph
interface over Brazilian soccer data (matches, teams, players, competitions),
so an LLM can answer natural-language questions about it. Implements the
specification in `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## Specification
brazilian-soccer-mcp-guide.md

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python server.py --selftest   # load all data and print a summary
pytest -q                     # run the test suite (80 tests)
python server.py              # start the MCP server (stdio transport)
```

### Connecting it to an MCP client (e.g. Claude Desktop)

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

## Architecture

The code is split into three layers; only the server layer needs the `mcp`
package, so the engine and its tests run on the standard library alone.

| File | Responsibility |
|------|----------------|
| `soccer_data.py`    | Loads the 6 CSV files into normalized `Match` / `Player` records. Team-name normalization, multi-format date parsing, cross-file de-duplication. |
| `soccer_queries.py` | `SoccerQueryEngine` — every query capability, returning JSON-serializable dicts. |
| `server.py`         | FastMCP server exposing the engine as MCP tools (stdio transport). |
| `test_soccer.py`    | 80 pytest tests, incl. 22 end-to-end sample questions. |

### MCP tools

`find_matches`, `last_match`, `head_to_head`, `team_record`, `compare_teams`,
`search_players`, `players_by_club`, `players_by_nationality`, `top_players`,
`standings`, `list_competitions`, `list_seasons`, `competition_stats`,
`biggest_wins`, `best_record`, `database_summary`.

## How the data-quality notes from the spec are handled

* **Team-name variations** — `Palmeiras-SP`, `Palmeiras`, and the full legal
  names are normalized to one identity key (accent- and case-insensitive).
  State/country suffixes are stripped *except* where they disambiguate clubs
  that share a base name (`Atlético-MG` vs `Atlético-PR` vs `Atlético-GO`,
  `Nacional (URU)`). Known long/short and rebrand variants (`Vasco da Gama` ⇄
  `Vasco`, `Athletico` ⇄ `Atlético-PR`, `Red Bull Bragantino` ⇄ `Bragantino`)
  are mapped explicitly so they merge without collapsing genuinely different
  clubs (`Grêmio` is kept distinct from `Grêmio Prudente`).
* **Date formats** — ISO, ISO+time and Brazilian `DD/MM/YYYY` are all parsed.
* **Character encoding** — files are read as UTF-8 (BOM-aware).
* **Overlapping datasets** — the same Brasileirão/Copa do Brasil fixtures
  appear in several files. Records are de-duplicated by `(competition, season,
  home, away, score)`; the curated single-competition files are authoritative,
  and the broad `BR-Football-Dataset.csv` (calendar-year seasons, its own
  spellings) is used only to fill the gaps it uniquely covers (Série B & C).
  Without this, computed standings were inflated 2–3×.

Computed standings reproduce the historical record, e.g. the spec's worked
example — **2019 Brasileirão: Flamengo champions, 90 pts (28-6-4)** — as well
as 2020 (Flamengo, 71), 2021 (Atlético-MG, 84), and the 2003–2004 24-team /
2005 22-team formats.

### Known data limitations
* The **2022 Brasileirão is only partially present** in the provided CSV
  (~30 of 38 rounds), so 2022 records/standings are incomplete.
* `fifa_data.csv` is a single FIFA snapshot (≈2019). It is great for
  player attributes and Brazilian *nationals*, but contains few Brazilian
  *club* rosters, so some "players at club X" queries return small lists.

## Data Sources

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
