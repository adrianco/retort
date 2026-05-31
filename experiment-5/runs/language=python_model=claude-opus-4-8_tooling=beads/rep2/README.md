# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
turns six pre-downloaded Kaggle datasets into a queryable knowledge base for
Brazilian soccer. An LLM (e.g. Claude) can connect to it and answer natural-
language questions about matches, teams, players, competitions and statistics —
spanning the Brasileirão (Série A/B/C), Copa do Brasil, Copa Libertadores and a
FIFA player database.

Built per [`TASK.md`](TASK.md) / [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

---

## What was built

| Layer | File | Responsibility |
|-------|------|----------------|
| Normalisation | `brazilian_soccer_mcp/normalize.py` | Canonical team-name keys (handles `Palmeiras-SP` vs `Palmeiras` vs `São Paulo`) + multi-format date/int parsing |
| Data store | `brazilian_soccer_mcp/data_loader.py` | Loads all 6 CSVs into typed `Match`/`Player` records (stdlib `csv` only — no pandas) and de-duplicates overlapping sources |
| Query engine | `brazilian_soccer_mcp/query_engine.py` | All match / team / player / competition / statistics queries, returning JSON-friendly dicts |
| Formatters | `brazilian_soccer_mcp/formatters.py` | Render result dicts into the readable prose shown in the spec's "Example answer format" blocks |
| MCP server | `brazilian_soccer_mcp/server.py` | Registers 17 tools with the official `mcp` SDK (`FastMCP`) |
| Launcher | `run_server.py` | `python run_server.py` convenience entry point |
| Demo | `demo.py` | Answers 20+ sample questions end-to-end |
| Tests | `tests/` | BDD (Given/When/Then) PyTest suite — 52 scenarios |

Every source file opens with a detailed context-block comment.

### Key design decision: source de-duplication

Série A appears in **three** overlapping files (2003–2011, 2012–2022, 2023) and
Copa do Brasil in **two**. Loading them naively would triple-count games and
inflate standings. The loader tags each fixture with a competition family and
source file, then picks a single **canonical** source per `(competition,
season)` by a fixed priority. Standings and league-wide statistics consume only
canonical rows, so totals are correct; raw match search can opt into all
sources. Result: **23,954 matches loaded → 16,712 canonical**, covering seasons
**2003–2023** with no gaps or double counting.

---

## Capabilities (mapped to the spec)

1. **Match queries** — `find_matches` (by team/opponent/season/competition/date
   range), `last_match`.
2. **Team queries** — `team_record` (overall/home/away), `compare_teams`,
   `competitions_for_team`.
3. **Player queries** — `search_players` (name/nationality/club/position/min
   rating), `get_player`, `brazilian_clubs_summary`.
4. **Competition queries** — `standings` (computed from results),
   `competition_winner`, `relegated_teams`.
5. **Statistical analysis** — `head_to_head`, `league_statistics`,
   `biggest_wins`, `best_record`, `top_scoring_team`.

Plus `data_summary` for an overview. Standings are validated against known
real-world results (e.g. the 2019 Brasileirão correctly returns Flamengo
champions on 90 points; 2017 returns Corinthians).

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # mcp + pytest
```

The datasets are already bundled in `data/kaggle/`. To point at a different
directory, set `BR_SOCCER_DATA_DIR`.

## Running the server

```bash
python run_server.py            # stdio MCP transport
# or
python -m brazilian_soccer_mcp.server
```

### Connecting from Claude Desktop

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/run_server.py"]
    }
  }
}
```

## Quick demo (no MCP client needed)

```bash
python demo.py
```

Sample output:

```
Q: Who won the 2019 Brasileirão?
2019 Brasileirão Série A champion: Flamengo

Q: Show the 2019 Brasileirão final standings
2019 Brasileirão Série A Final Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L, GD +49) - Champion
2. Santos - 74 pts (22W, 8D, 8L, GD +27)
3. Palmeiras - 74 pts (21W, 11D, 6L, GD +29)
...

Q: What's the average goals per match in the Brasileirão?
- Average goals per match: 2.57
- Home win rate: 49.7%
```

Use the engine directly in Python:

```python
from brazilian_soccer_mcp import QueryEngine, load_default_store
engine = QueryEngine(load_default_store())
print(engine.head_to_head("Flamengo", "Fluminense")["total_matches"])
```

---

## Testing (BDD / Given-When-Then)

The suite follows the spec's Behaviour-Driven Development approach: each test is
a `Feature`/`Scenario` expressed as Given/When/Then, asserting on structured
data so results are verifiable.

```bash
pytest                 # 52 scenarios across 6 feature files
```

| File | Feature |
|------|---------|
| `tests/test_normalization.py` | Team-name & date canonicalisation |
| `tests/test_match_queries.py` | Match search |
| `tests/test_team_queries.py` | Team records & head-to-head |
| `tests/test_player_queries.py` | FIFA player search |
| `tests/test_competition_queries.py` | Standings & champions |
| `tests/test_statistics.py` | Aggregate statistics |
| `tests/test_mcp_server.py` | MCP tool layer & server wiring |

---

## Data quality handling

- **Team-name variations** — state suffixes (`-SP`), accents (`São`/`Sao`),
  parenthetical country codes (`Nacional (URU)`) and the three ambiguous
  "Atlético" clubs (MG / PR / GO) all resolve correctly via a canonical-key
  normaliser with a curated alias table for the best-known clubs.
- **Date formats** — ISO, ISO+time and Brazilian `DD/MM/YYYY` are all parsed.
- **Encoding** — files are read as UTF-8 (with BOM handling for `fifa_data.csv`).
- **Overlapping sources** — de-duplicated via canonical-source selection (above).

## Performance

The whole knowledge base loads in well under a second using only the standard
library, and is cached per process. Simple lookups and aggregate queries both
return in milliseconds, comfortably inside the spec's < 2 s / < 5 s targets.

---

## Data sources & licenses

See [`TASK.md`](TASK.md) for full attribution. Datasets: Brasileirão / Copa do
Brasil / Libertadores (CC BY 4.0), BR-Football (CC0), Campeonato Brasileiro
2003–2019 (CC BY 4.0), FIFA players (Apache 2.0). Demo / non-commercial use.

## Project tracking

Subtasks were tracked with [beads](https://github.com/steveyegge/beads) (`bd`);
see `.beads/`.
