# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server, written in
Rust, that answers natural-language questions about Brazilian soccer over the
pre-downloaded Kaggle datasets in `data/kaggle/`. It loads the match and player
data into an in-memory store and exposes eight tools covering match, team,
player, competition and statistical queries, as specified in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) / [`TASK.md`](TASK.md).

The implementation was built test-first (TDD); see [Testing](#testing).

## Quick start

```bash
# Build
cargo build --release

# Run the MCP server (speaks JSON-RPC 2.0 over stdio)
./target/release/brazilian-soccer-mcp
```

On startup it loads the CSVs (about 0.1 s) and logs readiness to **stderr**,
keeping **stdout** reserved for the JSON-RPC stream:

```
[brazilian-soccer-mcp] loading data from data/kaggle
[brazilian-soccer-mcp] ready: 16505 matches, 18207 players. Listening on stdio.
```

### Data directory resolution

The server finds `data/kaggle` via, in order: a CLI argument
(`brazilian-soccer-mcp <dir>`), the `BSMCP_DATA_DIR` env var, `./data/kaggle`,
then the in-repo copy next to the crate.

### Connecting from an MCP client

Register it as a stdio server. For example, in a Claude Desktop
`mcpServers` config:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "/absolute/path/to/target/release/brazilian-soccer-mcp"
    }
  }
}
```

### Talking to it directly

Each line is one JSON-RPC message:

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
 '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"competition":"Brasileirao","season":2019}}}' \
 | ./target/release/brazilian-soccer-mcp
```

## Tools

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| `find_matches` | Matches involving a team, optionally vs an opponent; adds a head-to-head summary | `team`*, `opponent`, `season`, `competition`, `limit` |
| `team_record` | Win/draw/loss + goals record | `team`*, `season`, `competition`, `venue` (`home`/`away`/`all`) |
| `head_to_head` | Head-to-head between two teams | `team_a`*, `team_b`*, `season`, `competition` |
| `standings` | League table calculated from results (3 pts/win) | `season`*, `competition` (default Brasileirão) |
| `search_players` | FIFA players by name / nationality / club / position | any of `name`, `nationality`, `club`, `position`, `limit` |
| `top_players` | Highest-rated players, optionally filtered | `nationality`, `club`, `limit` |
| `competition_stats` | Avg goals, home-win rate, top scorer, biggest wins | `competition`, `season` |
| `last_match` | Most recent meeting between two teams | `team_a`*, `team_b`* |

`*` = required. Competition names are matched loosely
("Brasileirao"/"Serie A", "Copa do Brasil", "Libertadores").

### Example

`standings` for 2019 reproduces the real Brasileirão exactly:

```
2019 Brasileirão final standings (calculated from matches):
1. Flamengo-RJ - 90 pts (28W 6D 4L, GF 86 GA 37, GD +49)
2. Palmeiras-SP - 74 pts (21W 11D 6L, GF 61 GA 32, GD +29)
3. Santos-SP - 74 pts (22W 8D 8L, GF 60 GA 33, GD +27)
...
```

## Architecture

A small, layered library (`src/`) with a thin binary on top:

| Module | Responsibility |
|--------|----------------|
| `normalize` | Team-name canonicalization. Two keys: a **loose** `normalize_team` (suffix/accent-stripped, so a user's "Flamengo" matches stored "Flamengo-RJ") and a **strict** `canonical_id` (keeps the state code, so Atlético-**MG** and Athletico-**PR** stay distinct). |
| `model` | Core types — `Match`, `Player`, `Competition`, `MatchResult` — and multi-format date parsing (ISO, `DD/MM/YYYY`, datetimes). |
| `data` | CSV loaders for all six files, resolving columns by header name (tolerating the FIFA file's BOM and the mixed quoting/float styles). |
| `query` | The in-memory `Database`: match search, team records, head-to-head, calculated standings, player search and aggregate statistics. |
| `mcp` | The MCP server: `initialize` / `tools/list` / `tools/call`, tool schemas, and answer formatting. Pure `handle_message` and `call_tool` seams. |
| `main` | Wires `mcp` to real stdin/stdout. |

### Data-quality handling

The datasets overlap heavily and disagree in ways that, taken naively, corrupt
results. The query layer addresses this explicitly:

- **Unplayed fixtures** (scores `NA` or `-`) are skipped so they cannot create
  phantom 0-0 draws. (This is why the in-progress 2022 Brasileirão has 299
  played matches rather than a full 380.)
- **Cross-source duplication.** The same game appears in several files with
  different spellings ("Atletico-MG" vs "Atletico Mineiro", "Bahia" vs "EC
  Bahia") and even off-by-one dates, so naive matching multiplied standings
  several-fold. For each *(competition, season)* the loader keeps the single
  most authoritative source and drops the others — Brasileirão comes from
  `Brasileirao_Matches` (2012–2022), the historical file (2003–2011), and the
  extended file (2023) — so coverage is complete without double-counting.
- **Name normalization** distinguishes user-facing matching (loose) from
  fixture identity (strict), which is what keeps 20-team seasons at 20 teams.
- **UTF-8 / accents** are handled throughout (São Paulo, Grêmio, Avaí…).

## Testing

Built with Test-Driven Development. 60 unit + integration tests covering
normalization, date parsing, every loader (against the real CSVs), all query
and statistics operations, the de-duplication logic, and the MCP protocol /
tool dispatch — including an end-to-end check that the loaded 2019 Brasileirão
matches the historical record (Flamengo champions, 90 pts, 38 games).

```bash
cargo test          # run everything
cargo clippy        # lint (clean)
```

## Data Sources

Kaggle data can't be downloaded without an account, so these (freely available
with attribution) datasets have been included under `data/kaggle/`:

https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/Brasileirao_Matches.csv` — Brasileirão Série A (4,180 rows)
- `data/kaggle/Brazilian_Cup_Matches.csv` — Copa do Brasil (1,337 rows)
- `data/kaggle/Libertadores_Matches.csv` — Copa Libertadores (1,255 rows)

https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- License: CC0: Public Domain
- `data/kaggle/BR-Football-Dataset.csv` — extended match stats (10,296 rows)

https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- License: Attribution 4.0 International (CC BY 4.0)
- `data/kaggle/novo_campeonato_brasileiro.csv` — historical Brasileirão 2003–2019 (6,886 rows)

https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
- License: Apache 2.0
- `data/kaggle/fifa_data.csv` — FIFA player database (18,207 players)

## License

Demo / non-commercial use. Code released under the MIT License; the bundled
datasets retain their respective licenses listed above.
