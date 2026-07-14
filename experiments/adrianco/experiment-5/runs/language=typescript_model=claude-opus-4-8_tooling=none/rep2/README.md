# Brazilian Soccer MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that
exposes a **knowledge graph** over Brazilian soccer data. It lets an LLM answer
natural-language questions about players, teams, matches and competitions by
calling structured tools backed by the bundled Kaggle datasets.

Implemented in **TypeScript** against the spec in
[`brazilian-soccer-mcp-guide.md`](brazilian-soccer-mcp-guide.md) /
[`TASK.md`](TASK.md). Tested with **Behaviour-Driven (Given/When/Then)** scenarios.

## What it does

Teams are nodes, matches are edges between two teams, and FIFA players are
linked to their clubs. On startup all six CSV files are parsed into an
in-memory graph (~16k de-duplicated matches, ~18k players, ~360 teams) and
indexed for fast lookup.

### MCP tools

| Tool | Capability | Example question |
|------|-----------|------------------|
| `search_matches` | Match queries | "Show me all Flamengo vs Fluminense matches" |
| `head_to_head` | Match / stats | "Compare Palmeiras and Santos head-to-head" |
| `team_record` | Team queries | "What is Corinthians' home record in 2022?" |
| `team_competitions` | Team queries | "What competitions has Palmeiras played in?" |
| `search_players` | Player queries | "Who are the top Brazilian players?" |
| `standings` | Competition queries | "Who won the 2019 Brasileirão?" |
| `competition_stats` | Statistical analysis | "What's the average goals per match?" |
| `biggest_wins` | Statistical analysis | "Show me the biggest wins in the dataset" |
| `list_competitions` | Discovery | "Which competitions/seasons are available?" |

Every tool returns a human-readable text block **and** structured JSON
(`structuredContent`) for programmatic consumers.

## Quick start

```bash
npm install
npm run build
npm start          # runs the MCP server over stdio
```

During development you can run directly from source:

```bash
npm run dev
```

### Connecting from an MCP client

Add to your client's MCP server config (e.g. Claude Desktop):

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

The data directory defaults to `<repo>/data/kaggle` and can be overridden with
the `SOCCER_DATA_DIR` environment variable.

## Architecture

```
src/
  normalize.ts       Team-name / date / number normalization (data-quality layer)
  loader.ts          One parser per CSV + cross-source de-duplication
  knowledgeGraph.ts  In-memory graph + all query methods
  format.ts          Renders query results as the spec's answer formats
  server.ts          Registers MCP tools on the official SDK McpServer
  config.ts          Resolves the data directory
  index.ts           stdio entry point
tests/               Given/When/Then (BDD) scenarios — one feature per file
```

### Data-quality handling

The datasets are messy, and the implementation normalizes them per the spec:

- **Team name variations** — state suffixes (`Palmeiras-SP`, `América - MG`,
  `Botafogo RJ`), country tags (`Nacional (URU)`), club-type abbreviations
  (`EC Bahia`, `Fortaleza FC`) and accents are all normalized to a single
  matching key. Genuinely distinct clubs that share a base name (Atlético-**MG**
  vs Atlético-**GO**) are kept apart, while the two spellings of Athletico
  Paranaense are unified.
- **Multiple date formats** — ISO (`2023-09-24`), ISO+time
  (`2012-05-19 18:30:00`) and Brazilian (`29/03/2003`) are all parsed.
- **UTF-8 / accents** — handled throughout (São Paulo, Grêmio, Avaí).
- **Overlapping sources** — the five match files overlap heavily (e.g. the 2019
  Brasileirão appears in three files). Records describing the same fixture are
  merged so league points and head-to-head tallies are not multiplied. As a
  ground-truth check, the computed 2019 Série A table has Flamengo champions on
  **90 points (28W 6D 4L)**, matching the real result.

### Data coverage notes

- **Brasileirão Série A**: 2003–2022 (curated files).
- **Série B / Série C**: from the extended-statistics dataset.
- **Copa do Brasil** and **Copa Libertadores**: from their dedicated files.
- **Players**: the FIFA dataset is from FIFA 19, which only licensed some
  Brazilian clubs (Santos, Grêmio, Internacional, Fluminense, Cruzeiro,
  Botafogo, …). Unlicensed clubs such as Flamengo, Palmeiras, Corinthians and
  São Paulo are therefore absent from the player data.

## Testing

```bash
npm test
```

50 BDD scenarios cover all five capability categories, name/date normalization,
the MCP tool interface (driven through an in-memory MCP client) and the spec's
performance budget (simple < 2s, aggregate < 5s).

```gherkin
Feature: Competition Queries
  Scenario: who won the 2019 Brasileirão
    Given the match data is loaded
    When I compute the 2019 Série A standings
    Then Flamengo top the table with 90 points (28W 6D 4L)
```

## Data sources & licenses

The Kaggle datasets are bundled under `data/kaggle/` (Kaggle requires an account
to download, so the freely re-distributable, attributed copies are included):

| File | Source | License |
|------|--------|---------|
| `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv` | [ricardomattos05/jogos-do-campeonato-brasileiro](https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro) | CC BY 4.0 |
| `BR-Football-Dataset.csv` | [cuecacuela/brazilian-football-matches](https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches) | CC0 Public Domain |
| `novo_campeonato_brasileiro.csv` | [macedojleo/campeonato-brasileiro-2003-a-2019](https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019) | CC BY 4.0 |
| `fifa_data.csv` | [youssefelbadry10/fifa-players-data](https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data) | Apache 2.0 |

For demo / non-commercial use.
