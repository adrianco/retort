# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) (Model Context Protocol) server, written
in Rust, that exposes a queryable knowledge interface over the provided Brazilian
soccer datasets. An LLM host connects to it over stdio and answers natural-language
questions about players, teams, matches and competitions by calling its tools.

It implements the specification in [`TASK.md`](TASK.md) /
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## What it does

The server loads all six provided CSV files at startup into memory, unifies the
match data into a single model (de-duplicating the same fixture appearing across
multiple files), normalizes the many team-name spellings onto a single canonical
identity, and serves queries through seven MCP tools.

### Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season, or date range. When two teams are named, includes a head-to-head summary. |
| `team_record` | A team's W/D/L record, goals, points and win rate — optionally by competition, season, and home/away venue. |
| `head_to_head` | Compare two teams: total meetings, each side's wins/draws/goals, and the match list. |
| `search_players` | Search FIFA players by name, nationality, club, position and minimum overall; sort by overall/potential/age. |
| `league_standings` | Compute the final league table for a competition + season from match results. |
| `competition_stats` | Aggregate stats: match count, average goals per match, home/away/draw split, home-win rate, biggest wins. |
| `list_competitions` | List all competitions in the loaded data with match counts and season ranges. |

Every tool returns both human-readable `content` text (for the LLM to read) and a
machine-readable `structuredContent` JSON payload.

### Data handling

The specification calls out three real-world data-quality challenges, all handled:

- **Team-name variations** — "Palmeiras-SP", "Palmeiras", "Atletico Mineiro",
  "Atlético-MG" all resolve to one canonical club via a curated alias table in
  [`src/teams.rs`](src/teams.rs). Crucially, this avoids the naive trap of
  suffix-stripping, which would *merge distinct clubs* (Atlético-**MG** and
  Athletico-**PR**). Fixtures are de-duplicated on this canonical identity, so the
  same Brasileirão game appearing in several source files is counted once.
- **Date formats** — ISO (`2023-09-24`), ISO with time (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) are all parsed to a single ISO form.
- **UTF-8 / accents** — Portuguese accents and cedillas are read correctly and
  folded for matching (so "São Paulo" matches "Sao Paulo").

## Building and running

```sh
cargo build --release
./target/release/brazilian-soccer-mcp        # speaks MCP/JSON-RPC over stdio
```

The data directory defaults to `data/kaggle`; override with `SOCCER_DATA_DIR`.

### Connecting from an MCP client

Configure your MCP host (e.g. Claude Desktop) to launch the binary as a stdio
server:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/target/release/brazilian-soccer-mcp"
    }
  }
}
```

### Quick manual check

```sh
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"league_standings","arguments":{"competition":"Brasileirão","season":2019}}}' \
  | ./target/release/brazilian-soccer-mcp
```

## Tests

Development followed **Acceptance Test-Driven Development**. The acceptance suite in
[`tests/acceptance.rs`](tests/acceptance.rs) is an executable specification: each
test drives the server **only** through the MCP protocol (it spawns the compiled
binary as a child process and speaks JSON-RPC over its stdio), with no back-door
access to internals. Each scenario starts a fresh server process, so tests are
atomic and independent. Finer-grained unit tests cover the normalization internals.

```sh
cargo test
```

This runs the unit tests plus the full acceptance suite covering every required
capability category (match, team, player, competition and statistical queries),
team-name normalization, date-range filtering, and cross-file queries.

## Project layout

```
src/
  main.rs       stdio JSON-RPC event loop + startup data load
  mcp.rs        MCP protocol: initialize, tools/list, tools/call; tool schemas
  tools.rs      the seven query tools
  data.rs       CSV loading + fixture de-duplication
  model.rs      Match and Player domain types
  teams.rs      canonical team-name resolution (alias table)
  normalize.rs  accent folding, date parsing, competition-name normalization
tests/
  acceptance.rs executable acceptance specification (drives the server over MCP)
  common/mod.rs MCP test client harness
```

---

## Data Sources

Kaggle data can't be downloaded without an account so these (freely available with
attribution) data sets have been downloaded for use here:

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
