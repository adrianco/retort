# Brazilian Soccer MCP Server - Specification

## Overview

This document specifies the requirements for creating an MCP (Model Context Protocol) server that provides a knowledge graph interface for Brazilian soccer data. The server should enable natural language queries about players, teams, matches, and competitions using the provided datasets.

---

## Purpose

- **Use Case**: Demo/Non-commercial use
- **Goal**: Create an MCP server that can answer natural language questions about Brazilian soccer
- **Integration**: MCP server connected to an LLM for query processing

---

## Provided Data

The following datasets are included in `data/kaggle/` and must be used:

### Match Data

#### 1. Brasileirão Serie A Matches
**File**: `Brasileirao_Matches.csv` (4,180 matches)
**Source**: https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
**License**: CC BY 4.0

| Column | Description |
|--------|-------------|
| datetime | Match date and time |
| home_team | Home team name with state suffix (e.g., "Palmeiras-SP") |
| home_team_state | State abbreviation |
| away_team | Away team name with state suffix |
| away_team_state | State abbreviation |
| home_goal | Goals scored by home team |
| away_goal | Goals scored by away team |
| season | Year of the season |
| round | Match round number |

#### 2. Copa do Brasil Matches
**File**: `Brazilian_Cup_Matches.csv` (1,337 matches)
**Source**: https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
**License**: CC BY 4.0

| Column | Description |
|--------|-------------|
| round | Cup round |
| datetime | Match date and time |
| home_team | Home team name |
| away_team | Away team name |
| home_goal | Home team goals |
| away_goal | Away team goals |
| season | Year |

#### 3. Copa Libertadores Matches
**File**: `Libertadores_Matches.csv` (1,255 matches)
**Source**: https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
**License**: CC BY 4.0

| Column | Description |
|--------|-------------|
| datetime | Match date and time |
| home_team | Home team name |
| away_team | Away team name |
| home_goal | Home team goals |
| away_goal | Away team goals |
| season | Year |
| stage | Tournament stage (group stage, knockout, etc.) |

#### 4. Extended Match Statistics
**File**: `BR-Football-Dataset.csv` (10,296 matches)
**Source**: https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
**License**: CC0 Public Domain

| Column | Description |
|--------|-------------|
| tournament | Competition name |
| home | Home team |
| away | Away team |
| home_goal, away_goal | Final scores |
| home_corner, away_corner | Corner kicks |
| home_attack, away_attack | Attacks |
| home_shots, away_shots | Shots |
| time | Kick-off time |
| date | Match date |
| ht_result, at_result | Half-time results |
| total_corners | Total corners in match |

#### 5. Historical Brasileirão (2003-2019)
**File**: `novo_campeonato_brasileiro.csv` (6,886 matches)
**Source**: https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
**License**: CC BY 4.0

| Column | Description |
|--------|-------------|
| ID | Unique match identifier |
| Data | Match date (DD/MM/YYYY format) |
| Ano | Year |
| Rodada | Round number |
| Equipe_mandante | Home team |
| Equipe_visitante | Away team |
| Gols_mandante | Home goals |
| Gols_visitante | Away goals |
| Mandante_UF, Visitante_UF | Team states |
| Vencedor | Winner (Mandante/Visitante/Empate) |
| Arena | Stadium name |

### Player Data

#### 6. FIFA Player Database
**File**: `fifa_data.csv` (18,207 players)
**Source**: https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data
**License**: Apache 2.0

Key columns include:
| Column | Description |
|--------|-------------|
| ID | Unique player identifier |
| Name | Player name |
| Age | Player age |
| Nationality | Country |
| Overall | FIFA overall rating |
| Potential | FIFA potential rating |
| Club | Current club |
| Position | Playing position |
| Jersey Number | Shirt number |
| Height, Weight | Physical attributes |
| Various skill ratings | Crossing, Finishing, Dribbling, etc. |

---

## Additional Data Sources (Optional)

These sources may be used to supplement the provided data:

### API-Football
- **URL**: https://dashboard.api-football.com/
- **Features**: Current season data, live scores
- **Free tier**: Limited daily requests

### TheSportsDB
- **URL**: https://www.thesportsdb.com/documentation
- **Features**: Team logos, player photos, artwork
- **Free tier**: Test key "123", 2 requests/minute limit

### Wikipedia/DBpedia
- Historical context and notable player/team information

---

## Required Capabilities

The MCP server must support queries in these categories:

### 1. Match Queries

**Find matches by criteria:**
- By team (home, away, or either)
- By date range
- By competition (Brasileirão, Copa do Brasil, Libertadores)
- By season

**Example questions:**
- "Show me all Flamengo vs Fluminense matches"
- "What matches did Palmeiras play in 2023?"
- "Find all Copa do Brasil finals"

**Example answer format:**
```
Flamengo vs Fluminense (Fla-Flu derby):
- 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)
- 2023-05-28: Fluminense 1-0 Flamengo (Brasileirão Round 8)
- ... (15 more matches in dataset)

Head-to-head in dataset: Flamengo 12 wins, Fluminense 8 wins, 7 draws
```

### 2. Team Queries

**Find team information:**
- Match history and statistics
- Win/loss/draw records
- Goals scored/conceded
- Performance by competition

**Example questions:**
- "What is Corinthians' home record in 2022?"
- "Which team scored the most goals in Serie A 2023?"
- "Compare Palmeiras and Santos head-to-head"

**Example answer format:**
```
Corinthians home record (2022 Brasileirão):
- Matches: 19
- Wins: 11, Draws: 5, Losses: 3
- Goals For: 28, Goals Against: 15
- Win rate: 57.9%
```

### 3. Player Queries

**Find player information:**
- Search by name
- Filter by nationality (especially Brazilian players)
- Filter by club (especially Brazilian clubs)
- Player ratings and attributes

**Example questions:**
- "Find all Brazilian players in the dataset"
- "Who are the highest-rated players at Flamengo?"
- "Show me all forwards from São Paulo FC"

**Example answer format:**
```
Top-rated Brazilian players in dataset:
1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain
2. Alisson - Overall: 89, Position: GK, Club: Liverpool
3. Casemiro - Overall: 89, Position: CDM, Club: Real Madrid
...

Brazilian players at Brazilian clubs:
- Flamengo: 8 players (avg rating: 74)
- Palmeiras: 7 players (avg rating: 72)
...
```

### 4. Competition Queries

**Find competition information:**
- Standings by season (calculated from match results)
- Top scorers (if inferable from data)
- Match schedules and results

**Example questions:**
- "Who won the 2019 Brasileirão?"
- "Show the 2018 Copa Libertadores bracket"
- "Which teams were relegated in 2020?"

**Example answer format:**
```
2019 Brasileirão Final Standings (calculated from matches):
1. Flamengo - 90 pts (28W, 6D, 4L) - Champion
2. Santos - 74 pts (22W, 8D, 8L)
3. Palmeiras - 74 pts (21W, 11D, 6L)
...
```

### 5. Statistical Analysis

**Calculate aggregated statistics:**
- Goals per match averages
- Team performance trends
- Head-to-head records
- Home vs away performance

**Example questions:**
- "What's the average goals per match in the Brasileirão?"
- "Which team has the best away record?"
- "Show me the biggest wins in the dataset"

**Example answer format:**
```
Biggest victories in Brasileirão (provided data):
1. 2012-05-27: Santos 8-0 Bolivar (Libertadores)
2. 2015-09-13: Palmeiras 6-0 São Paulo
3. 2019-10-27: Flamengo 5-0 Grêmio
...

Average goals per match: 2.47
Home win rate: 47.3%
```

---

## Sample Questions and Expected Behaviors

### Simple Lookups
| Question | Expected Behavior |
|----------|-------------------|
| "When did Flamengo last play Corinthians?" | Search match data for most recent match between these teams |
| "What was the score?" | Return home_goal and away_goal |
| "Who is Gabriel Barbosa?" | Search FIFA player data by name |

### Relationship Queries
| Question | Expected Behavior |
|----------|-------------------|
| "Which players play for Flamengo?" | Filter FIFA data by Club containing "Flamengo" |
| "Show me all derbies in 2023" | Find matches where teams are traditional rivals |
| "What competitions has Palmeiras played in?" | Search all match files for Palmeiras matches |

### Analytical Queries
| Question | Expected Behavior |
|----------|-------------------|
| "Which team has the best home record?" | Calculate win rates from match data |
| "Who are the top Brazilian players?" | Filter and sort FIFA data |
| "Compare the 2018 and 2019 seasons" | Aggregate statistics across seasons |

---

## Data Quality Notes

### Team Name Variations
The datasets use different naming conventions:
- With state suffix: "Palmeiras-SP", "Flamengo-RJ"
- Without suffix: "Palmeiras", "Flamengo"
- Full names: "Sport Club Corinthians Paulista"

**Implementation should normalize team names for consistent matching.**

### Date Formats
- ISO format: "2023-09-24"
- Brazilian format: "29/03/2003"
- With time: "2012-05-19 18:30:00"

**Implementation should handle multiple date formats.**

### Character Encoding
Brazilian Portuguese text includes special characters:
- Accents: São Paulo, Grêmio, Avaí
- Cedilla: Fortaleza Esporte Clube

**Implementation should handle UTF-8 encoding.**

---

## Success Criteria

### Functional Requirements
- [ ] Can search and return match data from all provided CSV files
- [ ] Can search and return player data
- [ ] Can calculate basic statistics (wins, losses, goals)
- [ ] Can compare teams head-to-head
- [ ] Handles team name variations correctly
- [ ] Returns properly formatted responses

### Query Performance
- [ ] Simple lookups respond in < 2 seconds
- [ ] Aggregate queries respond in < 5 seconds
- [ ] No timeout errors

### Data Coverage
- [ ] All 6 CSV files are loadable and queryable
- [ ] At least 20 sample questions can be answered
- [ ] Cross-file queries work (e.g., player + match data)

---

## Testing Approach

Use BDD (Behavior-Driven Development) test scenarios:

```gherkin
Feature: Match Queries

Scenario: Find matches between two teams
  Given the match data is loaded
  When I search for matches between "Flamengo" and "Fluminense"
  Then I should receive a list of matches
  And each match should have date, scores, and competition

Scenario: Get team statistics
  Given the match data is loaded
  When I request statistics for "Palmeiras" in season "2023"
  Then I should receive wins, losses, draws, and goals
```

---

## Document Information
- **Version**: 2.0
- **Purpose**: Specification for Brazilian Soccer MCP Server benchmark
- **Data**: Pre-downloaded Kaggle datasets included in repository
- **Status**: Ready for implementation

---

## References

### MCP Protocol
- Documentation: https://modelcontextprotocol.io

### Data Sources
- Kaggle Brazilian Soccer: https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro
- Brazilian Football Matches: https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches
- Campeonato Brasileiro 2003-2019: https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019
- FIFA Players: https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data

### Optional APIs
- API-Football: https://dashboard.api-football.com/
- TheSportsDB: https://www.thesportsdb.com/documentation
