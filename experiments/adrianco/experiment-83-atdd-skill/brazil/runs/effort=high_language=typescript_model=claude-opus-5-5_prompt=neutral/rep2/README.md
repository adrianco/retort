# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server, written in TypeScript, that lets an LLM answer
natural-language questions about Brazilian soccer: matches, teams, competitions, players and statistics.
The specification is in `TASK.md` / `brazilian-soccer-mcp-guide.md`.

## Quick start

```bash
npm install
npm run build
npm test            # 78 tests: unit, query, MCP end-to-end and stdio
npm start           # serve MCP over stdio (node dist/index.js)
```

To use it from an MCP host (Claude Desktop, Claude Code, ...):

```json
{
  "mcpServers": {
    "brazilian-soccer": { "command": "node", "args": ["/absolute/path/to/dist/index.js"] }
  }
}
```

The data directory defaults to `data/kaggle`; override it with `--data-dir <path>` or `BRAZIL_SOCCER_DATA_DIR`.

## Design

All six CSV files are loaded at startup into an in-memory knowledge graph
(Team → Match → Competition/Season, Player → Club → Team). Loading takes about 0.4 s and every query
then runs in a few milliseconds, well inside the 2 s / 5 s limits in the spec.

| File | Purpose |
|------|---------|
| `src/csv.ts` | RFC 4180 CSV parser (quotes, embedded newlines, UTF-8 BOM) |
| `src/dates.ts` | Parses `2023-09-24`, `2012-05-19 18:30:00`, `29/03/2003` into ISO dates |
| `src/teams.ts` | Team-name normalisation, curated table of major clubs, rivalries (clássicos) |
| `src/data.ts` | Loads all files into one `Match`/`Player` model, de-duplicates fixtures across files |
| `src/queries.ts` | Query engine: matches, head-to-head, records, standings, brackets, rankings, stats, players |
| `src/format.ts` | Text formatting of results |
| `src/server.ts` | MCP tool definitions (zod input schemas) |
| `src/index.ts` | stdio entry point |

### Data handling

- **Team names.** `"Palmeiras-SP"`, `"Palmeiras - SP"`, `"Palmeiras"`, `"Sport Club Corinthians Paulista"`,
  `"Atlético Paranaense - PR"`, `"Athletico"`, `"C. R. B. - AL"` and so on all resolve to stable keys.
  Accents are ignored when matching but kept for display. State suffixes keep same-named clubs apart
  (`Flamengo-RJ` and `Flamengo-PI`, `Botafogo-RJ`/`-PB`/`-SP`). Foreign Libertadores clubs never merge with
  Brazilian namesakes (River Plate and River Plate-SE). The `*_UF` state columns in
  `novo_campeonato_brasileiro.csv` are wrong in places (Bahia is tagged "BH", Vitória "ES"), so they are ignored.
- **Duplicates.** Série A 2012–2019 appears in three files. A fixture (same competition and teams, dates within
  3 days) is counted once. The highest-priority file is canonical, and the copies add their extra data to it:
  shots, corners and attacks from BR-Football, stadium from the historical file.
- **Seasons.** The BR-Football file has no season column, so the season comes from the date. The COVID-delayed
  2020 seasons, which finished in early 2021, are handled.
- **Standings** are calculated from results (3 points per win). The table uses the most complete file for the
  season, and gaps are filled from other files only with fixtures between that season's clubs. The champion
  and relegated clubs (4, or 2 in 2003) are marked only when the season is complete. The calculated tables
  match the real ones, e.g. 2019: Flamengo 90 pts (28W 6D 4L), Santos 74, Palmeiras 74.
- **Cup finals.** Copa do Brasil finals are detected as the last round when it holds a single two-legged tie.
  Where round data is missing, the last two matches of the season are used if they are the same pairing.
- Rows with unplayed results (`NA` scores) are skipped: 82 in `Brasileirao_Matches.csv` and 2 in
  `Libertadores_Matches.csv`.

### Tools

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals" (`stage: "final"`), date ranges, home/away |
| `head_to_head` | "Show me all Flamengo vs Fluminense matches", "When did Flamengo last play Corinthians?" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `team_profile` | "What competitions has Palmeiras played in?" Combines match data with the FIFA squad (cross-file) |
| `team_rankings` | "Which team has the best home/away record?", "Which team scored the most goals in 2023?" |
| `find_team` | Resolve an ambiguous name ("Atletico") and show the spelling variants per file |
| `league_standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" (Série A/B/C) |
| `cup_bracket` | "Show the 2018 Copa Libertadores bracket" (ties with legs and aggregates) |
| `cup_finals` | Every Copa do Brasil or Libertadores final in the data |
| `competition_stats` | "Average goals per match in the Brasileirão?", home/draw/away rates, per-season trend, corners and shots |
| `biggest_wins` | "Show me the biggest wins", highest-scoring matches |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `derby_matches` | "Show me all derbies in 2023" (Fla-Flu, Grenal, Derby Paulista, Choque-Rei, ...) |
| `search_players` | "Find all Brazilian players", "Show me all forwards from Grêmio", filters by rating, age and position group |
| `get_player` | "Who is Neymar?" Gives the full profile, and for Brazilian clubs adds the club's match record |
| `players_by_club` | "Brazilian players at Brazilian clubs: count and average rating per club" |
| `list_competitions` | Overview of the competitions, seasons and rows loaded from each file |

Example (`league_standings`, season 2019):

```
2019 Brasileirão Série A Final Standings (calculated from 380 matches; source: Brasileirao_Matches.csv):
1. Flamengo - 90 pts (28W, 6D, 4L) GF 86 GA 37 GD +49 - Champion
2. Santos - 74 pts (22W, 8D, 8L) GF 60 GA 33 GD +27
3. Palmeiras - 74 pts (21W, 11D, 6L) GF 61 GA 32 GD +29
```

### Known data limitations

- The FIFA data is FIFA 19. Several big Brazilian clubs (Flamengo, Palmeiras, Corinthians, São Paulo, Vasco)
  are unlicensed there, and the licensed Brazilian clubs have generated player names. The tools say so when a
  club has no players.
- Two-legged ties that finish level on aggregate are reported as level; penalty results are not in the data.
- The 2023 Série A season has 377 of 380 matches, so its table is shown with a warning and no champion.

## Tests

The `tests/` directory holds 78 tests:

- `csv-dates.test.ts`, `teams.test.ts`: parsing and name-normalisation edge cases.
- `data.test.ts`: all six files load, de-duplication works, dates are ISO, UTF-8 is intact.
- `queries.test.ts`: the query engine checked against known results (champions 2003–2022, 2019 table,
  2020 relegations, Copa do Brasil finals, 2018 Libertadores bracket, player filters).
- `server.test.ts`: end-to-end through an MCP client. It covers 28 sample questions from the spec, cross-file
  queries and error handling, and asserts response times (< 2 s lookups, < 5 s aggregates).
- `stdio.test.ts`: starts the built server as a subprocess and talks MCP over stdio.

## Data Sources

Kaggle data can't be downloaded without an account, so these data sets (freely available with attribution)
have been downloaded for use here:

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
