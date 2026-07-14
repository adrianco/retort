# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server, written in
Elixir, that answers natural-language questions about Brazilian soccer — matches,
teams, players, competitions and statistics — over the Kaggle datasets in
`data/kaggle/`.

The server exposes a catalogue of tools an LLM can call to search matches, compute
head-to-head records, build league tables, look up FIFA players, and calculate
aggregate statistics. It is implemented against the spec in
[`TASK.md`](TASK.md) / [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md).

## Highlights

- **All six CSV files loaded and queryable** — 16,873 de-duplicated matches and
  18,207 players, parsed at start-up and held in memory for fast (<10 ms) queries.
- **Robust team-name normalisation** — `Flamengo`, `Flamengo-RJ`, `Atlético
  Mineiro` / `Atletico-MG`, `São Paulo` / `Sao Paulo`, `Nacional (URU)` all resolve
  correctly, while genuinely distinct clubs (Atlético-MG vs Atlético-PR) stay apart.
- **Multiple date & encoding formats** — ISO, `DD/MM/YYYY`, with/without time, full
  UTF-8 (accents, cedillas).
- **Computed competition tables** — standings, champions and relegation derived
  directly from match results. The 2019 Brasileirão table reproduces the real
  result (Flamengo, 90 pts).
- **Cross-file queries** — e.g. Brazilian FIFA players grouped by their Brazilian
  club (clubs identified by matching the player's club against teams seen in the
  match data).
- **Zero-dependency CSV/JSON-RPC core** — only `jason` is used for JSON encoding;
  the CSV parser and MCP transport are hand-rolled and unit-tested.

## Requirements

- Elixir ~> 1.16 (tested on Elixir 1.19 / Erlang OTP 29)

## Setup

```sh
mix deps.get
mix compile
```

## Running the MCP server

The server speaks JSON-RPC 2.0 over stdio (newline-delimited messages), the MCP
stdio transport. Build the escript and run it from the repository root (so it can
find `data/kaggle/`):

```sh
mix escript.build
./br_soccer
```

Or without building an escript:

```sh
mix run --no-halt -e 'BrSoccer.MCP.CLI.main()'
```

### Example MCP client configuration

```json
{
  "mcpServers": {
    "br-soccer": {
      "command": "/absolute/path/to/br_soccer",
      "cwd": "/absolute/path/to/this/repo"
    }
  }
}
```

### Quick manual check (no MCP client needed)

A `--ask` flag runs a single tool call with `key=value` arguments:

```sh
./br_soccer --ask league_standings competition=brasileirao season=2019
./br_soccer --ask head_to_head team_a=Flamengo team_b=Fluminense
./br_soccer --ask search_players nationality=Brazil min_overall=85
./br_soccer --ask team_record team=Corinthians season=2022 venue=home
```

## Tool catalogue

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?" |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `last_match` | "When did Flamengo last play Corinthians? What was the score?" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `league_standings` | "Who won the 2019 Brasileirão?" |
| `relegated_teams` | "Which teams were relegated in 2019?" |
| `search_players` | "Find all Brazilian players", "Show me forwards from a club" |
| `player_profile` | "Who is Neymar?" |
| `brazilian_clubs_squads` | "Brazilian players at Brazilian clubs" |
| `competition_stats` | "What's the average goals per match in the Brasileirão?" |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `top_scoring_teams` | "Which team scored the most goals in Serie A 2019?" |
| `team_rankings` | "Which team has the best home/away record?" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |

Each tool returns formatted text designed to be handed straight back to an LLM.

## Architecture

```
lib/br_soccer/
  csv.ex            # dependency-free RFC-4180 CSV parser (quotes, BOM, CRLF, UTF-8)
  team_name.ex      # name normalisation: canonical match keys + display names
  match.ex          # unified Match struct + result helpers
  player.ex         # FIFA Player struct
  loader.ex         # per-file parsing into normalised structs; date/int parsing; dedup
  repo.ex           # in-memory store (persistent_term cache), loaded once at startup
  competition.ex    # competition ids, display names, free-text parsing
  matches.ex        # match search, head-to-head, competition history
  teams.ex          # team records, rankings, top scorers, biggest wins
  players.ex        # player search, Brazilians, Brazilians-at-Brazilian-clubs
  competitions.ex   # league tables, champions, relegation (single-source per season)
  stats.ex          # aggregate stats, season comparison
  format.ex         # renders results as human-readable text
  br_soccer.ex      # thin programmatic facade
  mcp/
    tools.ex        # MCP tool catalogue + dispatch
    server.ex       # JSON-RPC 2.0 stdio server (pure handle_message/1 + serve loop)
    cli.ex          # escript / mix entry point
```

### Data quality handling

- **Overlapping files.** The Brasileirão appears in three files and the Copa do
  Brasil in two. Fixtures are de-duplicated at load time, keeping the most
  authoritative source (priority: `Brasileirao_Matches` → `novo_campeonato` →
  `BR-Football` for Série A). Standings are always computed from a single source
  per season to avoid double-counting.
- **Name variations.** See `BrSoccer.TeamName`. A small set of ambiguous bare
  names (Atlético, América, Botafogo) keep their state in the canonical key;
  everything else collapses so the same club matches across files.
- **FIFA dataset note.** The FIFA 19 data anonymises (or omits) several
  unlicensed Brazilian clubs — e.g. Flamengo is absent and some squads use
  placeholder player names. Queries for those clubs correctly return no results
  rather than guessing.

## Tests

```sh
mix test
```

57 tests cover the CSV parser, name normalisation, date/number parsing, every
query module (against a deterministic fixture), the MCP tools and JSON-RPC server,
and an end-to-end integration suite against the real CSVs (including the
performance budgets from the spec).

## Data sources & licenses

Kaggle data can't be downloaded without an account, so these freely available
(attribution) datasets were pre-downloaded into `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro — CC BY 4.0
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches — CC0 Public Domain
  - `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 — CC BY 4.0
  - `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data — Apache 2.0
  - `fifa_data.csv`
