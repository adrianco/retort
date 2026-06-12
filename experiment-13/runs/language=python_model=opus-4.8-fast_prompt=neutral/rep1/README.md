# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that exposes a
**knowledge graph over Brazilian soccer data** (matches, teams, competitions and
players) so that an LLM can answer natural-language questions such as *"Who won
the 2019 Brasileirão?"*, *"What is Corinthians' home record in 2022?"* or
*"Who are the top Brazilian players in the dataset?"*.

It implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) (also mirrored
in `TASK.md`).

---

## What was built

| Layer | File | Responsibility |
|-------|------|----------------|
| Normalization | `normalization.py` | Reconcile messy team-name variants (accents, `-UF` state suffixes, country codes). |
| Data loading | `data_loader.py` | Load all 6 Kaggle CSVs into **one unified match schema** + a clean player table. |
| Query engine | `knowledge_graph.py` | The knowledge graph: match/team/player/competition/statistics queries. |
| Presentation | `formatting.py` | Turn structured results into the spec's human-readable answer formats. |
| MCP server | `server.py` | 13 MCP tools (FastMCP, stdio) wrapping the engine. |
| Demo | `demo.py` | Answers 21 sample questions without an MCP client. |
| Tests | `test_*.py`, `conftest.py` | 49 pytest tests covering every layer. |

### Architecture

```
        CSV files (data/kaggle/)
                 │
        data_loader.py  ──►  unified `matches` + `players` DataFrames
                 │
        knowledge_graph.py  ──►  KnowledgeGraph  (returns JSON-friendly dicts)
                 │
   ┌─────────────┴─────────────┐
formatting.py              demo.py
   │
server.py  (FastMCP, 13 tools over stdio)  ──►  LLM / MCP client
```

The data is modelled conceptually as a graph —
`(Team) —played→ (Match) ←played— (Team)`, `(Match) —in→ (Competition, Season)`,
`(Player) —plays_for→ (Club)`, `(Player) —from→ (Nationality)` — and backed by
indexed pandas DataFrames for sub-second queries.

---

## MCP Tools

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2021?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `standings` | "Who won the 2019 Brasileirão?", "Show the 2020 Série A table" |
| `top_scoring_teams` | "Which team scored the most goals in Série A 2019?" |
| `average_goals` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `search_players` | "Find all Brazilian players", "Highest-rated players at Santos" |
| `get_player` | "Who is Neymar?" |
| `brazilian_players_by_club` | "Which clubs have the most Brazilian players?" |
| `list_competitions` / `list_seasons` / `list_teams` | discovery / schema introspection |

---

## Setup

```bash
pip install -r requirements.txt        # mcp, pandas, pytest
```

### Run the demo (no MCP client needed)

```bash
python demo.py
```

### Run the test suite

```bash
python -m pytest -q
```

### Run as an MCP server

```bash
python server.py        # speaks MCP over stdio
```

Register it with an MCP client (e.g. Claude Desktop's `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

---

## Key design decisions

### Team-name normalization (the hardest data-quality problem)

The datasets spell the same club many ways: `Palmeiras-SP`, `Palmeiras`,
`São Paulo` vs `Sao Paulo`, `Nacional (URU)`. Naïvely stripping the `-UF` suffix
**merges genuinely different clubs** that are *only* distinguished by state —
`Atlético-MG` vs `Atlético-GO` vs `Athletico-PR`, or `América-MG` vs `América-RN`.

The solution (`normalization.py`):

* **Keep** the state code in the canonical key (`"atletico mg"` ≠ `"atletico go"`),
  so distinct clubs stay distinct.
* Match with **bidirectional whole-word containment**, so a casual query
  `"Flamengo"` still finds the stored `"Flamengo-RJ"`, and vice-versa, without
  ever matching the wrong club.

### Overlapping sources & deduplication

The Brasileirão Série A is described by **three** overlapping files
(`Brasileirao_Matches`, `novo_campeonato_brasileiro`, and the broad
`BR-Football-Dataset`), and the Copa do Brasil by two. Counting all of them would
triple-count fixtures and inflate standings.

`KnowledgeGraph.dedupe_matches` chooses **one source per (competition, season)**:

1. the source with the **most played matches** (so an incomplete mid-season
   capture loses to a complete one — e.g. 2022 Série A), then
2. the most **authoritative / clean-named** dedicated file as a tiebreaker.

This is why the computed **2019 Brasileirão standings exactly reproduce the known
result**: Flamengo champion on **90 pts (28W 6D 4L)**, with Santos and Palmeiras
on 74 — the worked example in the specification.

### Multiple date formats & UTF-8

`data_loader.py` parses ISO timestamps (`2012-05-19 18:30:00`), Brazilian
`DD/MM/YYYY` (`29/03/2003`) and plain ISO dates, and reads everything as UTF-8 so
accented names (São Paulo, Grêmio, Avaí) are preserved in output.

---

## Data coverage

| Competition | Seasons | Source(s) |
|-------------|---------|-----------|
| Brasileirão Série A | 2003–2023 | `novo_…`, `Brasileirao_Matches`, `BR-Football-Dataset` (one chosen per season by the dedup rule) |
| Série B / Série C | 2014–2023 | `BR-Football-Dataset` |
| Copa do Brasil | 2012–2023 | `Brazilian_Cup_Matches`, `BR-Football-Dataset` |
| Copa Libertadores | 2013–2023 | `Libertadores_Matches` |
| Players | FIFA snapshot | `fifa_data.csv` (18,207 players, 827 Brazilians) |

Every computed Série A champion from 2003–2022 matches the real historical
result (e.g. 2003 Cruzeiro, 2009 Flamengo, 2021 Atlético-MG, 2022 Palmeiras),
and the dedup rule correctly rejects the BR-Football-Dataset's calendar-year
grouping that would otherwise inflate the 2021 season to 24 teams.

> **Note on data limitations:** results reflect *only the provided datasets*. The
> most recent Série A season (2023) is missing a handful of fixtures in the source
> file, so a few teams show 37 rather than 38 games — this is a gap in the source
> data, not a calculation error. Cup "final/round" labels are limited to what each
> file provides.

---

## Success criteria checklist

- [x] Search and return match data from all provided CSV files
- [x] Search and return player data
- [x] Calculate basic statistics (wins, losses, goals, standings)
- [x] Compare teams head-to-head
- [x] Handle team name variations correctly (state suffixes, accents, country codes)
- [x] Return properly formatted responses (matches the spec's answer formats)
- [x] Simple lookups < 2 s, aggregate queries < 5 s (data loads once in ~0.4 s; queries are sub-second)
- [x] All 6 CSV files loadable and queryable
- [x] ≥ 20 sample questions answered (`demo.py` answers 21)
- [x] Cross-file queries work (player + match data)

---

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets are included under `data/kaggle/`:

[jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro)
— License: CC BY 4.0
- `data/kaggle/Brasileirao_Matches.csv`
- `data/kaggle/Brazilian_Cup_Matches.csv`
- `data/kaggle/Libertadores_Matches.csv`

[brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches)
— License: CC0 Public Domain
- `data/kaggle/BR-Football-Dataset.csv`

[campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019)
— License: CC BY 4.0
- `data/kaggle/novo_campeonato_brasileiro.csv`

[fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data)
— License: Apache 2.0
- `data/kaggle/fifa_data.csv`
