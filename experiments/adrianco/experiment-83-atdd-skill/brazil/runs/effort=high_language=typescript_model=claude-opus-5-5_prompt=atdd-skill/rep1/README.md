# Brazilian Soccer MCP Server

An [MCP](https://modelcontextprotocol.io) server, written in TypeScript, that answers natural-language questions about Brazilian soccer (via an LLM host such as Claude) using the six provided Kaggle datasets: matches, teams, players, competitions and statistics.

The specification is in [TASK.md](TASK.md) and `brazilian-soccer-mcp-guide.md`. It was built with Dave Farley's Acceptance Test-Driven Development: executable specifications came first, then the DSL, then the protocol driver, then the system (see [How it was built](#how-it-was-built)).

## Quick start

```bash
npm install
npm test          # builds, then runs acceptance + unit tests
npm start         # serves MCP over stdio using data/kaggle
```

Register it with an MCP host, e.g. Claude Code:

```bash
claude mcp add brazilian-soccer -- node /path/to/repo/dist/src/index.js
```

Data directory: `--data-dir <dir>`, else `$BRAZILIAN_SOCCER_DATA_DIR`, else `data/kaggle`. Loading all six files takes about 0.5 s; queries are answered from memory in milliseconds.

## Tools

Every tool returns readable text (formatted like the examples in TASK.md) plus `structuredContent` for precise follow-up. An unknown team returns an error result that suggests similar names.

| Tool | Answers questions like |
|------|------------------------|
| `search_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "When did Flamengo last play Corinthians?" (limit 1). Filters: team, opponent, home/away, competition, season, date range |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `team_rankings` | "Which team scored the most goals in Serie A 2023?", "Which team has the best home/away record?" |
| `team_profile` | Results across all competitions plus the club's FIFA squad (cross-file) |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `cup_finals` | "Find all Copa do Brasil finals" |
| `knockout_bracket` | "Show the 2018 Copa Libertadores bracket" |
| `find_derbies` | "Show me all derbies in 2023" (Fla-Flu, Derby Paulista, Grenal, …) |
| `competition_stats` | "What's the average goals per match in the Brasileirão?", home/draw/away win rates |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `search_players` | "Find all Brazilian players", "Who are the highest-rated players at Grêmio?", "Show me all forwards from Santos" |
| `get_player` | "Who is Neymar?" (accent-insensitive, suggests similar names) |
| `brazilian_club_squads` | "Brazilian players at Brazilian clubs": count and average rating per club |
| `dataset_info` | Which datasets are loaded, record counts, and seasons covered |

## Data handling

- **Team names**: "Palmeiras-SP", "Palmeiras - SP", "Palmeiras", "Sociedade Esportiva Palmeiras", "Atletico Mineiro", "Atlético-MG", "Nacional (URU)" and so on are each resolved to a single team (`src/domain/teams.ts`). A club without a state takes its usual Brazilian state, so "Botafogo" means Botafogo-RJ and "Botafogo-PB" stays separate. International records only inherit a state from top-flight clubs, so the Argentine River Plate is not River Plate-SE.
- **Dates**: ISO, ISO with time, and Brazilian `DD/MM/YYYY` are all accepted.
- **Duplicates**: Brasileirão seasons appear in up to three files. Matches with the same competition, home and away teams, and the same season (or within 3 days) are merged into one, keeping any corners/shots/attacks statistics.
- **Gaps**: matches without a score (`NA`) are skipped. Seasons with missing matches are reported as provisional, with no champion. Stray one-off records are kept out of league tables. See [docs/atdd-findings.md](docs/atdd-findings.md).
- Standings are calculated from results (3/1/0 points; ties broken by wins, goal difference, then goals scored). The calculated champions match history for every complete season, e.g. Flamengo 2019 with 90 pts (28W, 6D, 4L).

## How it was built

The tests follow Dave Farley's four-layer acceptance-test model:

1. **Test cases** (`tests/acceptance/*.spec.ts`) are written only in the language of Brazilian football. For example:
   ```ts
   given.match({ home: 'Flamengo', away: 'Fluminense', score: '2-1', date: '2023-09-03' });
   given.match({ home: 'Fluminense', away: 'Flamengo', score: '1-0', date: '2023-05-28' });
   await matches.findBetween({ team: 'Flamengo', opponent: 'Fluminense' });
   matches.confirmFound(['2023-09-03 Flamengo 2-1 Fluminense', '2023-05-28 Fluminense 1-0 Flamengo']);
   ```
2. **DSL** (`tests/acceptance/dsl/`) has one class per domain area (given, matches, teams, players, competitions, statistics, datasets), with defaults so specs only state what matters.
3. **Protocol driver** (`tests/acceptance/drivers/`) is the only test code that knows the system is an MCP server. It writes each spec's synthetic world into a fresh data directory in the exact Kaggle CSV formats, launches the server over stdio as an LLM host would, calls tools, and makes the assertions.
4. **System under test** (`src/`) is the MCP server.

Each synthetic spec gets its own server and dataset, so specs are isolated and can run in parallel. `provided-datasets.spec.ts` runs against the real Kaggle data. It checks that all six files load with their full record counts, that real results come out right (2019 champion, 2020 Copa do Brasil final, top Brazilian player, a cross-file club profile), and that 23 sample questions are each answered within 2 s (simple lookups) or 5 s (aggregates). Unit tests in `tests/unit/` cover name, date and CSV parsing.

## Project layout

```
src/index.ts              entry point (stdio)
src/server.ts             MCP tool definitions
src/domain/knowledge.ts   answers to every question
src/domain/records.ts     records, league tables, head-to-head, summaries
src/domain/teams.ts       team-name normalisation and identity
src/domain/derbies.ts     traditional rivalries
src/domain/model.ts       matches, players, competitions, positions
src/data/loader.ts        loads and merges the six CSV files
src/data/csv.ts, dates.ts parsing
tests/acceptance/         executable specifications (4-layer)
tests/unit/               parsing unit tests
docs/atdd-findings.md     data issues surfaced by the specs
```

## Data sources and licences

Kaggle data can't be downloaded without an account, so these freely available datasets (used with attribution) are included in `data/kaggle/`:

- https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro (CC BY 4.0): `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`
- https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches (CC0): `BR-Football-Dataset.csv`
- https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019 (CC BY 4.0): `novo_campeonato_brasileiro.csv`
- https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data (Apache 2.0): `fifa_data.csv`
