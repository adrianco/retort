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

## Implementation (Rust)

A dependency-light Rust MCP server (`csv` + `serde_json` only) that loads all six CSV
files into memory at start-up (~0.2 s in release) and answers queries over stdio using
newline-delimited JSON-RPC 2.0 (MCP `initialize`, `tools/list`, `tools/call`, `ping`).

```bash
cargo build --release
cargo test                      # unit tests + 32 BDD (Given/When/Then) scenarios on the real data

# run as an MCP server (stdio)
./target/release/brazilian-soccer-mcp [--data-dir data/kaggle]

# or ask one question from the shell
./target/release/brazilian-soccer-mcp --call standings '{"season": 2019}'
./target/release/brazilian-soccer-mcp --call head_to_head '{"team_a": "Flamengo", "team_b": "Fluminense"}'
```

MCP client configuration:

```json
{ "mcpServers": { "brazilian-soccer": {
    "command": "/path/to/target/release/brazilian-soccer-mcp",
    "args": ["--data-dir", "/path/to/data/kaggle"] } } }
```

The data directory is `--data-dir`, else `$BRAZILIAN_SOCCER_DATA_DIR`, else `./data/kaggle`.

### Tools

| Tool | Answers |
|------|---------|
| `search_matches` | Matches by team, opponent, venue, competition, season, stage/round, date range (newest first) |
| `head_to_head` | Two-team comparison: wins, draws, goals, home/away split, recent meetings |
| `team_stats` | W/D/L, goals, win rate; home/away and per-competition breakdowns |
| `team_profile` | Cross-file club profile: match record + competitions + derbies + FIFA squad |
| `team_competitions` | Competitions and seasons a team appears in |
| `standings` | League table calculated from results (champion / relegation zone) |
| `competition_bracket` | Round-by-round results of a cup season, with the final's aggregate |
| `league_stats` | Goals per match, home/draw/away rates, corners and shots |
| `biggest_wins` | Largest victories by margin |
| `rank_teams` | Best home/away records, most goals, etc. |
| `compare_seasons` | Side-by-side season aggregates |
| `find_derbies` | Matches between traditional rivals (Fla-Flu, Gre-Nal, ...) |
| `search_players` | FIFA players by name, nationality, club, position (code or group), rating |
| `player_details` | Full player profile by name or FIFA ID |
| `players_by_club` | Player counts and average rating per club |
| `data_summary` | What is loaded |

### Layout

- `src/normalize.rs` – accent folding, team-name keys, date parsing
- `src/data.rs` – data model, CSV loading, cross-file de-duplication
- `src/queries.rs` – filtering, records, standings, statistics, player search, text formatting
- `src/mcp.rs` – tool definitions and the JSON-RPC/MCP server loop
- `tests/bdd.rs` – scenario tests

### Data handling notes

- **Team names** are reduced to one key per club: accents, state suffixes (`-SP`, ` - SP`,
  ` SP`), country suffixes and `FC`/`EC` are dropped and known long forms are aliased
  (`Athletico Paranaense` = `Atlético - PR`). Clubs that share a name keep their state
  (`Atlético-MG` vs `Atlético-GO`, `Santos` vs `Santos-AP`).
- **Overlapping files**: Série A 2012–2019 appears in up to three files and the Copa do
  Brasil in two. A match already loaded from a preferred file is flagged as a duplicate and
  excluded from queries; its corner/shot statistics are merged onto the surviving record.
  Result: 23,854 rows → 16,808 unique matches, exactly 380 per 20-team Série A season.
- **Unplayed fixtures** (scores `NA` or `-`: 82 Série A, 16 cup, 2 Libertadores rows) are skipped.
- `BR-Football-Dataset.csv` has no season column; the year of the date is used, with
  January/February league matches assigned to the previous season.

### Known limitations of the data

- The 2023 Série A in the dataset is three matches short, so that table is labelled
  "Leader (incomplete data)" rather than "Champion".
- Tables are computed from results only; off-field point deductions are not in the data.
- The FIFA file (FIFA 19) has no Flamengo, Palmeiras, Corinthians or São Paulo squads, and
  players at the licensed Brazilian clubs have generated names, so e.g. "Gabriel Barbosa"
  is not found.
- No goal-scorer data exists in any file, so "top scorers" is answered at team level
  (`rank_teams` with `metric: goals_for`).
- A few foreign clubs share a key with a Brazilian one (Guaraní of Paraguay and Guarani-SP).
