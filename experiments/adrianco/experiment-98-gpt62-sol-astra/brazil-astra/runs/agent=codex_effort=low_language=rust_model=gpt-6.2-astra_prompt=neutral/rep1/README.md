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

## Running the Rust server

Build with `cargo build --release` and run the tests with `cargo test`.
Configure a stdio MCP client to launch the absolute path to
`target/release/soccer-mcp`. The optional first argument is the directory
containing the six CSVs. By default the server uses this checkout's
`data/kaggle` directory. Loading happens once at startup. No credentials
or external services are needed.

Ask questions in the connected LLM client. Its discovered `query_soccer`
tool describes the SQLite schema, team-name functions, and joins. For
example, “How did Corinthians do at home in 2022?” can use:

```sql
SELECT count(*) AS played, sum(win) AS wins, sum(draw) AS draws,
       sum(loss) AS losses, sum(gf) AS goals_for, sum(ga) AS goals_against
FROM team_results
WHERE team = team_key('Corinthians-SP') AND venue = 'home'
  AND season = 2022 AND competition = 'Serie A';
```

Use `matches` for schedules and results, `team_results` for completed games,
and `standings` for rankings calculated from the available scores. Results
include at most 100 rows per call. Page with a deterministic ORDER BY and
LIMIT/OFFSET when the tool reports truncation.

The five match files overlap. Each original row remains in `records`, with
its filename, fixture link, and original fields in `attributes`. Matching
uses competition, ordered normalized clubs, and dates or league season.
The dedicated competition files take precedence for reported scores.
Extended records without an explicit season use the calendar year unless
linked to an existing fixture. Source coverage and quality vary by season.
Standings omit administrative adjustments and use points, wins, goal
difference, and goals scored. FIFA clubs and ratings reflect the supplied
snapshot. Individual match goalscorers are unavailable.
