# Brazilian Soccer MCP Server (Clojure)

An [MCP](https://modelcontextprotocol.io) server that exposes a **knowledge graph**
over Brazilian soccer data (matches, teams, players, competitions) as a set of
tools an LLM can call to answer natural-language questions. Implemented in pure
Clojure with **no external services required** — the graph is built in-memory from
the bundled Kaggle CSVs at startup (~20k matches + ~18k players load in well under
a second).

See [`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) for the full
specification this implements.

## Quick start

```bash
# Run the MCP server (speaks JSON-RPC 2.0 over stdio)
clojure -M:run

# Run the test suite (23 tests / 100+ assertions)
clojure -M:test
```

The server reads newline-delimited JSON-RPC messages on stdin and writes responses
to stdout; diagnostics go to stderr only, keeping stdout protocol-clean.

### Registering with an MCP host (e.g. Claude Desktop)

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "clojure",
      "args": ["-M:run"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

### Talking to it manually

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirão Série A","season":2019}}}' \
  | clojure -M:run
```

## Architecture

A small, layered, dependency-light design. Each layer is pure and unit-tested in
isolation; only `data` touches the filesystem and only `main` touches stdio.

| Namespace | Responsibility |
|-----------|----------------|
| `brsoccer.normalize` | Team-name / date / number normalization. Owns the canonical matching key and the cross-dataset alias table. |
| `brsoccer.data` | Loads all 6 CSVs into the in-memory knowledge graph (entity tables + adjacency index); de-duplicates overlapping sources; cached in an atom. |
| `brsoccer.query` | Pure analytics over the graph: match search, team records, head-to-head, player search, standings, statistics. Returns plain data. |
| `brsoccer.format` | Renders query results as the human-readable text blocks from the spec. |
| `brsoccer.mcp` | JSON-RPC 2.0 / MCP protocol: tool definitions, `tools/call` dispatch, stdio transport. `handle-request` is pure. |
| `brsoccer.main` | Entry point: eager-loads the graph, then serves the protocol on stdio. |

### The knowledge graph

No graph database is needed — "Neo4j-style" nodes and relationships are plain
Clojure maps and indexes (which keeps the project dependency-free and fast):

* **Match edges** — one normalized map per fixture: competition, season, date,
  round/stage, home/away teams (display + canonical key), goals, computed result.
* **Team nodes** — `team-key → {:key :name}`, the display name being the most
  common spelling seen for that team.
* **Adjacency index** — `team-key → [matches…]` for O(1) team lookups.
* **Player nodes** — normalized FIFA records linked to clubs by the same team key.

## Data normalization (the hard part)

The datasets spell the same real-world team many ways. `brsoccer.normalize/team-key`
produces one canonical key so a user asking about `"flamengo"` matches rows stored
as `"Flamengo-RJ"`:

* **Accents** stripped — `São Paulo` / `Sao Paulo` → `saopaulo`.
* **State/country suffixes** removed — `Palmeiras-SP`, `Nacional (URU)` → base name.
* **Punctuation/case/space** removed.
* **State-ambiguous bases kept qualified** — the three different Atléticos share a
  base name, so the state is retained: `Atletico-GO`/`Atletico-MG`/`Atletico-PR`
  stay distinct (`atleticogo`/`atleticomg`/`atleticopr`).
* **Cross-dataset alias table** — folds long and short spellings of one club onto a
  single key: `Atletico Mineiro`→`Atletico-MG`, `EC Bahia`→`Bahia`,
  `Vasco da Gama RJ`→`Vasco`, `Fortaleza FC`→`Fortaleza`, etc.

Dates are normalized from all three documented formats (ISO, `DD/MM/YYYY`, with or
without a time component) to sortable `yyyy-MM-dd`.

**De-duplication:** the Brasileirão appears in three overlapping files (2012-2019
is in all three). Because each ordered `(home, away)` pairing occurs at most once
per competition+season in these league/knockout formats, overlapping rows are
collapsed on that key. This makes computed standings exact — e.g. **2019 Série A
reproduces the real table: Flamengo champions, 90 pts, 28W 6D 4L**, from 380
deduplicated matches across 20 teams.

> Known limitation: a few lower-division clubs sharing a base name across different
> states (e.g. Botafogo-RJ/PB/SP, América-MG/RN) are only partially disambiguated,
> since the source files spell them inconsistently. Top-flight clubs are exact.

## MCP tools

| Tool | What it answers |
|------|-----------------|
| `find_matches` | Matches by team / opponent / venue / competition / season / date range. Returns head-to-head when two teams are given. |
| `team_record` | W/D/L, goals, points and win rate for a team (filterable by season, competition, home/away). |
| `head_to_head` | Aggregate record between two teams plus the matches. |
| `search_players` | FIFA players by name / nationality / club / position / min overall rating. |
| `brazilian_players_by_club` | Brazilian players grouped by Brazilian club (counts + avg rating). |
| `standings` | League table for a competition+season, computed from results. |
| `biggest_wins` | Largest-margin victories (filterable). |
| `match_statistics` | Total/avg goals per match and home/away/draw rates. |
| `best_record` | Teams ranked by win rate (overall, home-only or away-only). |
| `list_competitions` | Competitions available with season coverage and counts. |

Each tool returns both formatted **text** (for the model to read) and the
underlying **structured data** (under `structuredContent`) for further reasoning.

## Sample questions it can answer

Matches: *"Show me all Flamengo vs Fluminense matches"* · *"What matches did
Palmeiras play in 2023?"* · *"When did Flamengo last play Corinthians?"*

Teams: *"What is Corinthians' home record in 2022?"* · *"Compare Palmeiras and
Santos head-to-head"* · *"Which team has the best away record?"*

Players: *"Find all Brazilian players"* · *"Who are the highest-rated players at
Flamengo?"* · *"Show me all forwards from São Paulo FC"* · *"Who is Neymar?"*

Competitions: *"Who won the 2019 Brasileirão?"* · *"2019 Série A final standings"*

Stats: *"Average goals per match in the Brasileirão"* · *"Biggest wins in the
Libertadores"* · *"Which team scored the most in 2023?"*

## Data sources

Bundled under `data/kaggle/` (Kaggle requires an account to download, so these
freely-redistributable, attributed datasets are included here):

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv` | [ricardomattos05/jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [cuecacuela/brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | [macedojleo/campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [youssefelbadry10/fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

The data directory can be overridden with the `BRSOCCER_DATA_DIR` environment
variable.

## License / use

Demo / non-commercial, per the dataset licenses above.
