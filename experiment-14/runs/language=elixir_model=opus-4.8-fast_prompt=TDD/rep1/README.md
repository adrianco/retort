# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server,
written in Elixir, that answers natural-language-style questions about Brazilian
soccer — players, teams, matches and competitions — from the bundled Kaggle
datasets. It implements the specification in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) / [`TASK.md`](TASK.md).

The server speaks JSON-RPC 2.0 over stdio and exposes a set of query tools that
an LLM client (Claude Desktop, etc.) can call. No third-party dependencies are
used: CSV parsing and JSON encoding are handled with the standard library
(Elixir 1.18+ ships a built-in `JSON` module).

## Quick start

```bash
mix deps.get          # no-op, there are no deps
mix test              # run the unit-test suite (91 tests)
mix escript.build     # build the ./brazilian_soccer_mcp executable
./brazilian_soccer_mcp        # start the MCP server on stdio
```

By default the server reads the CSV files from `data/kaggle/`. Override with a
positional argument or the `DATA_DIR` environment variable:

```bash
./brazilian_soccer_mcp /path/to/data
DATA_DIR=/path/to/data ./brazilian_soccer_mcp
```

### Talking to it

Each line of stdin is one JSON-RPC request; each line of stdout is one response.
Diagnostics go to stderr.

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão Série A","season":2019}}}' \
  | ./brazilian_soccer_mcp
```

```
2019 Brasileirão Série A standings:
1. Flamengo - 90 pts (28W, 6D, 4L, GD +49)
2. Santos - 74 pts (22W, 8D, 8L, GD +27)
3. Palmeiras - 74 pts (21W, 11D, 6L, GD +29)
...
```

### Using it from Claude Desktop

Add to your MCP client configuration (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/brazilian_soccer_mcp",
      "args": ["/absolute/path/to/data/kaggle"]
    }
  }
}
```

## Tools

| Tool | Purpose |
|------|---------|
| `search_matches` | Find matches by team, opponent, competition, season or date range (adds a head-to-head summary when two teams are given) |
| `head_to_head` | Win/draw/loss record between two teams |
| `team_record` | A team's record (W/D/L, goals, win rate), optionally by season, competition and venue |
| `compare_teams` | Two teams' records plus their head-to-head |
| `search_players` | Search FIFA players by name, nationality, club, position; `brazilian=true` for Brazilians |
| `standings` | League table for a competition + season, computed from results |
| `list_competitions` | Competitions available and their season ranges |
| `match_stats` | Aggregate stats (avg goals/match, home/away/draw rates) |
| `biggest_wins` | Largest victories by goal margin |
| `best_record` | Teams ranked by win rate at a venue (home/away/all) |

Call `tools/list` on the running server to see the full JSON input schemas.

## Architecture

```
lib/brazilian_soccer/
  csv.ex            RFC-4180 CSV parser (quotes, embedded commas/newlines, BOM)
  team_name.ex      Team-name normalization: identity key + fuzzy base key
  match.ex          Unified Match struct + date/score parsing, result helpers
  player.ex         Player struct from the FIFA columns
  dataset.ex        In-memory {matches, players} collection
  data_loader.ex    Per-source CSV → Match/Player mappers; load!/1
  queries/
    matches.ex      find/2, head_to_head/3
    teams.ex        record/3, compare/3
    players.ex      search/2, by_club/2
    competitions.ex standings/3, champion/3, seasons/2, competitions/1
    stats.ex        summary/2, biggest_wins/2, best_record/3
    source.ex       single-authoritative-source-per-season de-duplication
  mcp/
    tools.ex        tool registry + dispatch (returns formatted text)
    format.ex       human-readable rendering of results
    server.ex       JSON-RPC 2.0 request handling (pure)
    cli.ex          stdio transport + escript entry point
```

The query modules are pure functions over a `Dataset`, which makes them easy to
unit-test. `MCP.Server.handle/2` and `MCP.CLI.process_line/2` are likewise pure,
so the protocol behaviour is tested without spawning a process.

### Data-quality handling

The specification flags several real issues in the data; here is how they are
addressed:

- **Team-name variations** (`Palmeiras-SP` vs `Palmeiras`, `São Paulo` vs
  `Sao Paulo`, `Nacional (URU)`). `TeamName` produces two normalized forms: an
  **identity key** that *preserves* the state/country suffix (so `Atlético-MG`
  and `Atlético-PR` remain distinct clubs in standings) and a **base key** that
  strips it (so a user query for `"Flamengo"` matches `"Flamengo-RJ"`). Both are
  accent- and case-insensitive.
- **Multiple date formats** (`2012-05-19 18:30:00`, `2023-09-24`, `29/03/2003`)
  are all parsed to `Date`.
- **Duplicate fixtures across files.** The same Série A match often appears in
  three files with inconsistent spellings, which would triple-count standings
  and records. For aggregate queries we therefore use a single authoritative
  source per `{competition, season}` (the file contributing the most matches).
  Match *search* still spans every file. With this, the computed 2019 standings
  match the official table (Flamengo champions, 90 pts).
- **UTF-8 / encoding** is preserved throughout; the CSV parser also strips a
  leading byte-order mark.

### Known data limitations

- The **FIFA 19** player dataset omits some Brazilian Série A clubs (e.g.
  Flamengo, Palmeiras) and anonymizes the names of players at clubs it did not
  license, so some name lookups return placeholder names or nothing. Brazilian
  internationals at licensed (mostly European) clubs — Neymar, Casemiro,
  Coutinho, etc. — appear with real names and ratings.
- Standings are computed only for seasons present in the match data and assume
  the standard 3-points-for-a-win system with Brazilian tie-breakers (points,
  then wins, then goal difference, then goals for).

## Datasets

Kaggle data can't be downloaded without an account, so these (freely available,
with attribution) datasets are bundled under `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  - `fifa_data.csv`

## Development

Built test-first. Each module has a focused test file under `test/`; run an
individual one with e.g. `mix test test/brazilian_soccer/queries/teams_test.exs`.
