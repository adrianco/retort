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

A TypeScript MCP server (`src/`) that loads all six datasets at startup and answers questions over stdio.

### Running

```bash
npm install
npm run build
npm start                      # serves MCP on stdio, reading data/kaggle
SOCCER_DATA_DIR=/path npm start  # or point it at another copy of the datasets
```

Claude Desktop / Claude Code configuration:

```json
{
  "mcpServers": {
    "brazilian-soccer": {
      "command": "node",
      "args": ["/absolute/path/to/dist/src/server.js"]
    }
  }
}
```

### Tools

| Tool | Answers questions like |
|------|------------------------|
| `find_matches` | "Show me all Flamengo vs Fluminense matches", "What matches did Palmeiras play in 2023?", "Find all Copa do Brasil finals", "When did Flamengo last play Corinthians?" (limit 1) |
| `head_to_head` | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | "What is Corinthians' home record in 2022?" |
| `team_competitions` | "What competitions has Palmeiras played in?" |
| `team_rankings` | "Which team scored the most goals in 2019?", "Which team has the best home/away record?" |
| `team_profile` | Cross-file: a club's match record plus its squad from the FIFA data |
| `standings` | "Who won the 2019 Brasileirão?", "Which teams were relegated in 2020?" |
| `knockout_bracket` | "Show the 2018 Copa Libertadores bracket" |
| `derbies` | "Show me all derbies in 2023" (Fla-Flu, Grenal, Derby Paulista, Choque-Rei, ...) |
| `match_statistics` | "What's the average goals per match in the Brasileirão?", home win rate, corners and shots |
| `biggest_wins` | "Show me the biggest wins in the dataset" |
| `compare_seasons` | "Compare the 2018 and 2019 seasons" |
| `search_players` | "Find all Brazilian players", "Who are the highest-rated players at Cruzeiro?", "Show me all forwards from São Paulo" |
| `player_profile` | "Who is Neymar?" (suggests similar names when a player is not in the data) |
| `players_by_club` | "Brazilian players at Brazilian clubs" |
| `dataset_overview` | What is loaded and how much |

Every tool returns readable text (in the answer formats from the specification) plus the same answer as `structuredContent`.

### Data handling

- **Team names**: `src/teams.ts` reduces every spelling (`Palmeiras-SP`, `Palmeiras - SP`, `Sociedade Esportiva Palmeiras`, `Sao Paulo`, `Atlético - MG`, `America FC (Minas Gerais)`, ...) to one identity. Clubs that share a name but come from different states (Atlético-MG/PR/GO, Botafogo-RJ/PB) stay apart. Accented display names are preferred.
- **Duplicates**: the same Série A match can appear in three files. A record from another file with the same competition, home and away teams within three days is merged into the existing match, adding its corners, shots or stadium. Without this, standings would be double counted.
- **Dates**: ISO, ISO with time and Brazilian `DD/MM/YYYY` are all read. League matches played in January–March belong to the previous season (the 2020 Brasileirão finished in February 2021).
- **Copa do Brasil stages**: the cup file only numbers rounds. When a season's last round is a single two-legged tie, it is labelled the final, with the semi-finals, quarter-finals and round of 16 before it.
- **Standings**: 3 points for a win, ranked by points, wins, goal difference, then goals scored. Relegation is the bottom four (two in 2003).

### Known data limitations

- FIFA 19 has no licensed squads for Flamengo, Palmeiras, Corinthians or São Paulo, and no Gabriel Barbosa. Queries for them correctly answer "none found".
- The 2023 Série A in `BR-Football-Dataset.csv` is missing 3 matches, so the 2023 table is incomplete.
- Some smaller clubs with very different spellings in different files may not be merged.

## How it was built: Acceptance Test-Driven Development

The project was built using Dave Farley's ATDD approach and four-layer test architecture. The specifications were written first, in the language of the problem domain, then the DSL, then the protocol driver, then the system.

```
acceptance/specs/    1. Test cases: executable specifications ("should name the champion of a league season")
acceptance/dsl/      2. DSL: domain vocabulary with defaults and test-scoped sequences (given.brasileiraoMatch, competitions.confirmChampion)
acceptance/drivers/  3. Protocol drivers:
                        - mcp-soccer-driver.ts: launches the real server and talks MCP over stdio, as an LLM client would
                        - dataset-stub.ts: stub for the external Kaggle data, which writes synthetic CSVs in each file's native format
src/                 4. The system under test
test/                Unit tests for the fine-grained cases (team-name variants, dates, competition names)
```

- Most specs create their own synthetic data in a private directory and start their own server, so tests are isolated from each other and from the real files.
- `acceptance/specs/provided-datasets.spec.ts` runs against the real datasets. It checks data coverage, the sample questions from the brief (using well-known results such as Flamengo's 90-point 2019 title) and the response-time criteria (< 2 s for lookups, < 5 s for aggregates).

```bash
npm test                 # builds, then runs acceptance specs and unit tests
npm run test:acceptance  # acceptance specs only
npm run test:unit        # unit tests only
```
