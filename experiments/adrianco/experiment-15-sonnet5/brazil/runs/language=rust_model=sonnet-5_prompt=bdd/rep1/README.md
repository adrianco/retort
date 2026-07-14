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

## Implementation

A Rust MCP server (`brazilian-soccer-mcp`) that loads all six CSVs above into
an in-memory knowledge base and exposes it as MCP tools over stdio.

### Build & run

```sh
cargo build --release
./target/release/brazilian-soccer-mcp        # serves MCP over stdio
```

The data directory defaults to `data/kaggle` next to `Cargo.toml`. Override
with a CLI argument or the `BRAZIL_SOCCER_DATA_DIR` env var.

### Test

```sh
cargo test
```

48 tests: unit tests for date parsing, team-name normalization, CSV loading,
and query logic (`cargo test --lib`), plus an integration suite (`tests/`)
that loads the real, checked-in CSVs and checks row counts and end-to-end
queries.

### Tools

| Tool | Purpose |
|---|---|
| `find_matches` | Matches by team, opponent, competition, season, date range |
| `head_to_head` | Win/draw/loss tally and goals between two teams |
| `team_record` | A team's W/D/L, goals, and win rate (optionally home/away only) |
| `standings` | League table for a competition/season, calculated from results (CBF tiebreak order: points, wins, goal difference, goals scored) |
| `biggest_wins` | Largest-margin results |
| `match_stats` | Average goals and home/draw/away rates |
| `list_teams` / `list_competitions` | Discover exact team names and dataset coverage |
| `search_players` | FIFA player search by name/nationality/club/position/rating |

### Team name normalization

Club names vary across files (`Palmeiras-SP` vs `Palmeiras` vs `Sport Club
Corinthians Paulista`, `Grêmio` vs `Gremio`). Names are normalized to a
lowercase, accent-free key; queries match a candidate if either name
contains the other, so both abbreviated and full-legal-name queries work.

State/country qualifiers (`-MG`, `-PR`, `(URU)`, `(PAR)`) are **kept**, not
discarded: they disambiguate real, distinct clubs that share a base name
(e.g. Atlético-MG vs Atlético-PR, or Nacional (URU) vs Nacional (PAR)).
Dropping them would silently merge two different clubs' match histories.
An unqualified query like "Flamengo" still matches "Flamengo-RJ" via
substring containment.

Rows with no recorded result (goals logged as `NA` or `-`, e.g. the 2016
Chapecoense fixture never played after the team's air disaster) are
skipped rather than fabricating a score.

### Known data limitations

- The provided FIFA player CSV does not include several major Brazilian
  clubs (Flamengo, Corinthians, Palmeiras, São Paulo do not appear as
  `Club` values), so player queries for those clubs correctly return no
  results — this is a gap in the source data, not the query logic.
- Team-name matching is substring-based, not a full entity-resolution
  system; a handful of edge cases (e.g. "Athletico" vs "Atlético" spelling
  variants for the same club) are not unified.
