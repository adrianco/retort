# Brazilian Soccer MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server, written in
TypeScript, that exposes a queryable knowledge interface over Brazilian soccer
datasets (matches, teams, players, competitions). Connect it to any MCP-capable
LLM client to answer natural-language questions like *"Who won the 2019
Brasileirão?"*, *"Compare Palmeiras and Santos head-to-head"*, or *"Show me the
top-rated Brazilian players."*

The full requirements are in [`brazilian-soccer-mcp-guide.md`](./brazilian-soccer-mcp-guide.md)
(identical to `TASK.md`).

---

## What was built

An in-memory analytical store loaded from the six provided Kaggle CSV files,
fronted by seven MCP tools. The design separates concerns so the analytical core
is pure and fully unit-testable independent of the MCP transport:

| Layer | File | Responsibility |
|-------|------|----------------|
| Domain model | `src/types.ts` | Normalized `Match` / `Player` shapes |
| Normalization | `src/normalize.ts` | Canonical team names, date & number parsing |
| Loaders | `src/loader.ts` | Parse each CSV + **cross-source de-duplication** |
| Query store | `src/store.ts` | Match search, head-to-head, records, standings, stats, player search |
| Formatting | `src/format.ts` | Renders results into the spec's answer formats |
| Tools | `src/tools.ts` | MCP tool schemas + `callTool` dispatcher (pure) |
| Server | `src/server.ts` | MCP protocol adapter (`ListTools` / `CallTool`) |
| Entrypoint | `src/index.ts` | Boots the store and serves over stdio |

Every source file opens with a context comment explaining its role.

### MCP tools

1. **`find_matches`** — search matches by team, opponent, competition, season, date range, home/away venue.
2. **`head_to_head`** — full head-to-head record between two teams (wins/draws/goals + recent meetings).
3. **`team_record`** — a team's W/D/L, goals for/against, points and win rate, optionally scoped by season/competition/venue.
4. **`league_standings`** — a league table **computed from match results** (3 pts win, 1 pt draw) for a competition + season.
5. **`competition_stats`** — average goals per match, home/away win rates, biggest-margin victories.
6. **`search_players`** — FIFA player search by name, nationality, club, position; filter by min rating; sortable.
7. **`list_competitions`** — discover available competitions and the seasons covered.

### Data-quality handling

The datasets describe the same clubs and matches inconsistently; the
implementation reconciles this:

- **Team-name normalization** (`canonicalTeam`): strips state suffixes
  (`Palmeiras-SP` → `Palmeiras`), removes accents for matching (`Grêmio` =
  `Gremio`), drops generic club tokens (`Fortaleza FC` = `Fortaleza`,
  `EC Bahia` = `Bahia`), unifies spelling variants (`Athletico-PR` =
  `Atlético-PR`, `Vasco` = `Vasco da Gama`, all `Sport`/`Sport-PE`/`Sport
  Recife`), while keeping genuinely-distinct ambiguous clubs apart by state
  (`Atlético-MG` ≠ `Atlético-GO` ≠ `Athletico-PR`). Accent-correct display
  names are restored for well-known clubs.
- **Date parsing**: ISO (`2023-09-24`), datetime (`2012-05-19 18:30:00`) and
  Brazilian (`29/03/2003`) formats all normalize to ISO `YYYY-MM-DD`.
- **Cross-source de-duplication**: Série A 2012–2019 appears in up to three
  files. Matches are de-duplicated by competition + season + ordered team pair
  (immune to the ~1-day local-vs-UTC date disagreement between sources), keeping
  the richest record. The COVID-delayed 2020 season — which finished in February
  2021 — is correctly bucketed via a Jan/Feb season-rollover rule.

The de-duplication is verified against history: the computed **2019 Brasileirão
standings reproduce the real result exactly** — Flamengo champion with 90 points
(28W 6D 4L) — and each 20-team season resolves to its expected 380 matches. A
handful of seasons differ by 1–3 matches purely because of gaps/strays in the
source CSVs themselves; these are preserved faithfully rather than fabricated.

---

## Usage

### Install & build

```bash
npm install
npm run build
```

### Run the tests

```bash
npm test
```

44 tests cover normalization, loading/de-duplication, every store query, the
tool dispatch layer, and a full end-to-end MCP client↔server round-trip over an
in-memory transport.

### Run the server (stdio)

```bash
npm start          # node dist/index.js
# or, without building:
npm run dev        # tsx src/index.ts
```

By default the server locates `data/kaggle/` relative to the package. Override
with `SOCCER_DATA_DIR=/path/to/kaggle`.

### Connect from an MCP client

Example `claude_desktop_config.json` (or any MCP client) entry:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/dist/index.js"]
    }
  }
}
```

Then ask natural-language questions; the client will call the tools above.

### Quick manual check

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"c","version":"1"}}}' \
 '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"league_standings","arguments":{"season":2019,"limit":5}}}' \
 | node dist/index.js
```

---

## Example answers

**`league_standings { season: 2019 }`**
```
Brasileirão Série A 2019 — Final Standings (computed from matches):
 1. Flamengo — 90 pts (28W 6D 4L, GF 86 GA 37, GD +49) — Champion
 2. Palmeiras — 74 pts (21W 11D 6L, GF 61 GA 32, GD +29)
 3. Santos — 74 pts (22W 8D 8L, GF 60 GA 33, GD +27)
 ...
```

**`head_to_head { teamA: "Flamengo", teamB: "Fluminense" }`**
```
Flamengo vs Fluminense — head-to-head
Played: 48 | Flamengo 20 wins, Fluminense 15 wins, 13 draws | Goals: Flamengo 67, Fluminense 53
Most recent meetings:
- 2023-11-11: Flamengo 1-1 Fluminense (Brasileirão Série A)
 ...
```

**`search_players { nationality: "Brazil", limit: 3 }`**
```
Players — Brazil (827 found):
1. Neymar Jr — Overall: 92, Position: LW, Club: Paris Saint-Germain (Brazil, age 26)
2. Casemiro — Overall: 88, Position: CDM, Club: Real Madrid (Brazil, age 26)
3. Coutinho — Overall: 88, Position: LW, Club: FC Barcelona (Brazil, age 26)
```

---

## Data sources & licenses

Kaggle data cannot be downloaded without an account, so these freely-available
datasets are bundled under `data/kaggle/` with attribution:

- [jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) — **CC BY 4.0**
  - `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- [brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) — **CC0 Public Domain**
  - `BR-Football-Dataset.csv`
- [campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) — **CC BY 4.0**
  - `novo_campeonato_brasileiro.csv`
- [fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) — **Apache 2.0**
  - `fifa_data.csv`

Use case: demo / non-commercial.
