# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that
exposes an in-memory **knowledge graph** of Brazilian soccer data so that an LLM
can answer natural-language questions about players, teams, matches and
competitions.

Built to the specification in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

---

## What was built

| File | Responsibility |
|------|----------------|
| `team_names.py` | Normalizes the many inconsistent club-name spellings into one canonical key. |
| `data_loader.py` | Reads all six Kaggle CSVs into uniform, typed `Match` / `Player` records. |
| `knowledge_graph.py` | Indexed in-memory knowledge graph + the query engine (matches, teams, players, competitions, statistics). |
| `formatters.py` | Renders query results as the human-readable answer formats from the spec. |
| `server.py` | The FastMCP server: 13 tools wrapping the query engine. |
| `demo.py` | CLI that answers a few sample questions without an MCP client. |
| `tests/` | BDD Given-When-Then PyTest suite (71 tests). |

### Design choices

- **Self-contained, no external database.** The "knowledge graph" is built in
  memory from the CSV files at startup (team nodes connected to match edges,
  player nodes connected to club nodes). This keeps every query an in-RAM lookup
  that comfortably meets the spec's latency targets (< 2 s simple, < 5 s
  aggregate — the whole 24k-match / 18k-player dataset loads in ~0.5 s) and makes
  the test suite fully hermetic.
- **Standard library only for the data/query layers.** `data_loader`,
  `knowledge_graph` and the tests depend on nothing outside the stdlib, so they
  never break on a missing `pandas`/`numpy`. The only third-party dependency is
  `mcp` itself, used purely for the protocol transport in `server.py`.
- **Every code file opens with a context block comment** describing its purpose,
  inputs/outputs and dependencies.

---

## Data normalization (the hard part)

The six datasets spell the same club in mutually incompatible ways. The
normalizer (`team_names.py`) collapses all of these to one key:

```
"Palmeiras-SP"   "Palmeiras"      -> palmeiras        (state suffix dropped)
"São Paulo"      "Sao Paulo"      -> sao paulo        (accents folded)
"América - MG"   "América-MG"     -> america mg       (spaced suffix handled)
"Nacional (URU)" "Nacional"       -> nacional         (country code stripped)
"Atletico Mineiro" "Atletico-MG"  -> atletico mg      (alias + state retained)
```

Crucially, clubs that *share* a base name keep their state code so they never
merge: `Atlético-MG`, `Atlético-GO` and `Athletico-PR` stay three distinct
clubs, while every spelling variant of each still resolves correctly.

Multiple **date formats** (`2012-05-19 18:30:00`, `2023-09-24`, `29/03/2003`),
the FIFA file's **UTF-8 BOM**, and `"NA"` placeholder scores for unplayed games
are all handled.

### Source deduplication

Série A and Copa do Brasil appear in more than one file with overlapping
seasons. For each `(competition, season)` the engine keeps the single
highest-priority source (e.g. the dedicated `Brasileirao_Matches.csv` over the
broader `BR-Football-Dataset.csv`), so fixtures are never double-counted. This
is why computed standings match reality exactly — e.g. **Flamengo won the 2019
Brasileirão with 90 points (28W 6D 4L)**, the spec's own example.

---

## MCP tools

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "What matches did Palmeiras play in 2019?" |
| `head_to_head` | "Show me all Flamengo vs Fluminense matches" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `compare_teams` | "Compare Palmeiras and Santos" |
| `standings` | "Show the 2019 Brasileirão final standings" |
| `season_champion` | "Who won the 2019 Brasileirão?" |
| `search_players` | "Find all Brazilian players / forwards from a club" |
| `top_players` | "Who are the highest-rated players at Flamengo?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `average_goals` | "What's the average goals per match?" |
| `best_record` | "Which team has the best home/away record?" |
| `list_seasons` / `list_competitions` | discovery helpers |

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
# Serve over stdio for an MCP client
python server.py

# Or see sample answers immediately
python demo.py
```

### Connect from an MCP client

Example `claude_desktop_config.json` entry (adjust the absolute paths):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

## Test

```bash
pytest
```

The suite is written in **BDD Given-When-Then** style, one feature file per
capability category, and includes 20+ sample questions exercised through the
real MCP tool functions:

```
tests/test_team_names.py          name normalization
tests/test_data_loader.py         loading all 6 CSVs
tests/test_match_queries.py       category 1 — match queries
tests/test_team_queries.py        category 2 — team queries
tests/test_player_queries.py      category 3 — player queries
tests/test_competition_queries.py category 4 — standings & champions
tests/test_statistics.py          category 5 — statistical analysis
tests/test_server_tools.py        MCP tool layer + 20+ sample questions
```

```
71 passed in ~3s
```

---

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets are included under `data/kaggle/`:

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv` | [ricardomattos05/jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `Brazilian_Cup_Matches.csv` | same | CC BY 4.0 |
| `Libertadores_Matches.csv` | same | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [cuecacuela/brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | [macedojleo/campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [youssefelbadry10/fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |
