// MCP tool definitions. Each tool parses its arguments, calls the query layer
// and formats the answer as plain text for the LLM to read.

package main

import (
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	defaultMatchLimit  = 20
	defaultPlayerLimit = 10
)

type findMatchesArgs struct {
	Team        string `json:"team"`
	Opponent    string `json:"opponent"`
	Venue       string `json:"venue"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	DateFrom    string `json:"date_from"`
	DateTo      string `json:"date_to"`
	Round       string `json:"round"`
	FinalsOnly  bool   `json:"finals_only"`
	Limit       int    `json:"limit"`
}

type teamStatsArgs struct {
	Team        string `json:"team"`
	Venue       string `json:"venue"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	DateFrom    string `json:"date_from"`
	DateTo      string `json:"date_to"`
}

type teamRankingArgs struct {
	Venue       string `json:"venue"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	MinMatches  int    `json:"min_matches"`
	Limit       int    `json:"limit"`
}

type standingsArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Limit       int    `json:"limit"`
}

type competitionStatsArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Limit       int    `json:"limit"`
}

type searchPlayersArgs struct {
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	MinOverall  int    `json:"min_overall"`
	Limit       int    `json:"limit"`
}

func newTools(st *Store) []Tool {
	return []Tool{
		{
			Name: "find_matches",
			Description: "Find Brazilian soccer matches (Brasileirão Serie A/B/C, Copa do Brasil, Copa Libertadores), newest first. " +
				"Filter by team, opponent (head-to-head), venue, competition, season, date range, round or finals only.",
			InputSchema: objectSchema(nil, map[string]any{
				"team":        stringProp("Team name, e.g. Flamengo, Palmeiras-SP, São Paulo"),
				"opponent":    stringProp("Second team. With team, returns the head-to-head record"),
				"venue":       stringProp("For team: home, away, or empty for either side"),
				"competition": stringProp("Brasileirão, Serie B, Serie C, Copa do Brasil or Libertadores"),
				"season":      intProp("Year, e.g. 2023"),
				"date_from":   stringProp("Start date, YYYY-MM-DD (inclusive)"),
				"date_to":     stringProp("End date, YYYY-MM-DD (inclusive)"),
				"round":       stringProp("Round label, e.g. 8"),
				"finals_only": boolProp("Only finals: last round of each Copa do Brasil season, or Libertadores final"),
				"limit":       intProp("Maximum matches to list (default 20)"),
			}),
			run: func(raw json.RawMessage) (string, error) {
				a, err := decodeArgs[findMatchesArgs](raw)
				if err != nil {
					return "", err
				}
				q, teamLabel, err := st.baseQuery(a.Team, a.Venue, a.Competition, a.Season, a.DateFrom, a.DateTo, a.Round)
				if err != nil {
					return "", err
				}
				q.FinalsOnly = a.FinalsOnly

				oppLabel := ""
				if strings.TrimSpace(a.Opponent) != "" {
					if q.Team == nil {
						return "", fmt.Errorf("opponent requires team")
					}
					if q.Opponent, oppLabel, err = st.teamSet(a.Opponent); err != nil {
						return "", err
					}
				}

				matches := st.selectMatches(q)
				limit := a.Limit
				if limit <= 0 {
					limit = defaultMatchLimit
				}

				var b strings.Builder
				switch {
				case q.Opponent != nil:
					fmt.Fprintf(&b, "%s vs %s (%d matches):\n", teamLabel, oppLabel, len(matches))
				case q.Team != nil:
					fmt.Fprintf(&b, "%s matches (%d):\n", teamLabel, len(matches))
				default:
					fmt.Fprintf(&b, "Matches (%d):\n", len(matches))
				}
				if len(matches) == 0 {
					b.WriteString("No matches found.")
					return b.String(), nil
				}
				for i, m := range matches {
					if i == limit {
						break
					}
					fmt.Fprintf(&b, "- %s\n", st.matchLine(m))
				}
				if len(matches) > limit {
					fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(matches)-limit)
				}
				if q.Opponent != nil {
					a := sideRecord(matches, q.Team, "")
					o := sideRecord(matches, q.Opponent, "")
					fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws",
						teamLabel, a.Wins, oppLabel, o.Wins, a.Draws)
				}
				return strings.TrimRight(b.String(), "\n"), nil
			},
		},
		{
			Name:        "team_stats",
			Description: "Win/draw/loss record, goals for and against, and win rate for a team, optionally by venue, competition, season or date range.",
			InputSchema: objectSchema([]string{"team"}, map[string]any{
				"team":        stringProp("Team name"),
				"venue":       stringProp("home, away, or empty for either side"),
				"competition": stringProp("Brasileirão, Serie B, Serie C, Copa do Brasil or Libertadores"),
				"season":      intProp("Year, e.g. 2022"),
				"date_from":   stringProp("Start date, YYYY-MM-DD (inclusive)"),
				"date_to":     stringProp("End date, YYYY-MM-DD (inclusive)"),
			}),
			run: func(raw json.RawMessage) (string, error) {
				a, err := decodeArgs[teamStatsArgs](raw)
				if err != nil {
					return "", err
				}
				q, label, err := st.baseQuery(a.Team, a.Venue, a.Competition, a.Season, a.DateFrom, a.DateTo, "")
				if err != nil {
					return "", err
				}
				if q.Team == nil {
					return "", fmt.Errorf("team is required")
				}
				scope := scopeLabel(a.Season, q.Competition)
				rec := sideRecord(st.selectMatches(q), q.Team, q.Venue)
				if rec.Played == 0 {
					return fmt.Sprintf("No matches found for %s%s.", label, scope), nil
				}
				venue := ""
				if q.Venue != "" {
					venue = " " + q.Venue
				}
				return fmt.Sprintf("%s%s record%s:\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Win rate: %.1f%%",
					label, venue, scope, rec.Played, rec.Wins, rec.Draws, rec.Losses,
					rec.GoalsFor, rec.GoalsAgainst, rec.WinRate()), nil
			},
		},
		{
			Name:        "team_ranking",
			Description: "Rank every team by win rate, optionally for home or away games only. Use it for questions such as 'best home record'.",
			InputSchema: objectSchema(nil, map[string]any{
				"venue":       stringProp("home, away, or empty for overall"),
				"competition": stringProp("Brasileirão, Serie B, Serie C, Copa do Brasil or Libertadores"),
				"season":      intProp("Year, e.g. 2022"),
				"min_matches": intProp("Minimum matches played to be ranked (default 10)"),
				"limit":       intProp("Number of teams to list (default 10)"),
			}),
			run: func(raw json.RawMessage) (string, error) {
				a, err := decodeArgs[teamRankingArgs](raw)
				if err != nil {
					return "", err
				}
				q, _, err := st.baseQuery("", a.Venue, a.Competition, a.Season, "", "", "")
				if err != nil {
					return "", err
				}
				minMatches, limit := a.MinMatches, a.Limit
				if minMatches <= 0 {
					minMatches = 10
				}
				if limit <= 0 {
					limit = 10
				}

				type ranked struct {
					name string
					rec  record
				}
				var rows []ranked
				for id, r := range teamRecords(st.selectMatches(q), q.Venue) {
					if r.Played >= minMatches {
						rows = append(rows, ranked{st.teamLabel(id), *r})
					}
				}
				sortRanked := func(i, j int) bool {
					if rows[i].rec.WinRate() != rows[j].rec.WinRate() {
						return rows[i].rec.WinRate() > rows[j].rec.WinRate()
					}
					if rows[i].rec.Wins != rows[j].rec.Wins {
						return rows[i].rec.Wins > rows[j].rec.Wins
					}
					return rows[i].name < rows[j].name
				}
				sort.Slice(rows, sortRanked)

				venue := q.Venue
				if venue == "" {
					venue = "overall"
				}
				if len(rows) == 0 {
					return fmt.Sprintf("No teams with at least %d matches.", minMatches), nil
				}
				var b strings.Builder
				fmt.Fprintf(&b, "Team ranking by win rate, %s%s, min %d matches:\n", venue, scopeInner(a.Season, q.Competition), minMatches)
				for i, row := range rows {
					if i == limit {
						break
					}
					fmt.Fprintf(&b, "%d. %s - %.1f%% win rate (%dW in %d matches)\n",
						i+1, row.name, row.rec.WinRate(), row.rec.Wins, row.rec.Played)
				}
				return strings.TrimRight(b.String(), "\n"), nil
			},
		},
		{
			Name:        "standings",
			Description: "League table for a season, calculated from match results. Defaults to the Brasileirão Serie A and the latest season in the data.",
			InputSchema: objectSchema(nil, map[string]any{
				"competition": stringProp("Brasileirão (default), Serie B or Serie C"),
				"season":      intProp("Year, e.g. 2019 (default: latest)"),
				"limit":       intProp("Number of rows (default 20)"),
			}),
			run: func(raw json.RawMessage) (string, error) {
				a, err := decodeArgs[standingsArgs](raw)
				if err != nil {
					return "", err
				}
				comp, err := resolveCompetition(a.Competition)
				if err != nil {
					return "", err
				}
				if comp == "" {
					comp = compBrasileirao
				}
				season := a.Season
				if season == 0 {
					season = st.latestSeason(comp)
				}
				rows := st.standings(comp, season)
				if len(rows) == 0 {
					return fmt.Sprintf("No matches found for %s in %d.", comp, season), nil
				}
				limit := a.Limit
				if limit <= 0 {
					limit = defaultMatchLimit
				}
				var b strings.Builder
				fmt.Fprintf(&b, "%d %s standings (calculated from matches):\n", season, comp)
				for i, row := range rows {
					if i == limit {
						break
					}
					fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL, GD %+d)",
						i+1, row.Name, row.Points(), row.Wins, row.Draws, row.Losses, row.GoalDifference())
					if i == 0 {
						b.WriteString(" - Champion")
					}
					b.WriteString("\n")
				}
				return strings.TrimRight(b.String(), "\n"), nil
			},
		},
		{
			Name:        "competition_stats",
			Description: "Aggregate statistics for a competition and season: match count, goals per match, home/draw/away results and the biggest wins.",
			InputSchema: objectSchema(nil, map[string]any{
				"competition": stringProp("Brasileirão, Serie B, Serie C, Copa do Brasil or Libertadores; empty for all"),
				"season":      intProp("Year; empty for all seasons"),
				"limit":       intProp("Number of biggest wins to list (default 5)"),
			}),
			run: func(raw json.RawMessage) (string, error) {
				a, err := decodeArgs[competitionStatsArgs](raw)
				if err != nil {
					return "", err
				}
				comp, err := resolveCompetition(a.Competition)
				if err != nil {
					return "", err
				}
				matches := st.selectMatches(matchQuery{Competition: comp, Season: a.Season})
				if len(matches) == 0 {
					return "No matches found.", nil
				}
				limit := a.Limit
				if limit <= 0 {
					limit = 5
				}
				s := summarize(matches)
				n := float64(s.Matches)
				var b strings.Builder
				fmt.Fprintf(&b, "Competition stats%s:\n", scopeLabelOrAll(a.Season, comp))
				fmt.Fprintf(&b, "- Matches: %d\n", s.Matches)
				fmt.Fprintf(&b, "- Goals per match: %.2f\n", float64(s.Goals)/n)
				fmt.Fprintf(&b, "- Home win rate: %.1f%%, Draw rate: %.1f%%, Away win rate: %.1f%%\n",
					float64(s.HomeWins)/n*100, float64(s.Draws)/n*100, float64(s.AwayWins)/n*100)
				b.WriteString("Biggest wins:\n")
				for i, m := range biggestWins(matches, limit) {
					fmt.Fprintf(&b, "%d. %s\n", i+1, st.matchLine(m))
				}
				return strings.TrimRight(b.String(), "\n"), nil
			},
		},
		{
			Name:        "search_players",
			Description: "Search the FIFA player database by name, nationality, club, position or minimum overall rating. Results are sorted by overall rating.",
			InputSchema: objectSchema(nil, map[string]any{
				"name":        stringProp("Name or part of a name, e.g. Neymar"),
				"nationality": stringProp("Nationality, e.g. Brazil"),
				"club":        stringProp("Club name, e.g. Flamengo"),
				"position":    stringProp("Position code (ST, CAM, GK) or group (forward, midfielder, defender, goalkeeper)"),
				"min_overall": intProp("Minimum overall rating"),
				"limit":       intProp("Maximum players to list (default 10)"),
			}),
			run: func(raw json.RawMessage) (string, error) {
				a, err := decodeArgs[searchPlayersArgs](raw)
				if err != nil {
					return "", err
				}
				players := st.searchPlayers(a.Name, a.Nationality, a.Club, a.Position, a.MinOverall)
				if len(players) == 0 {
					return "No players found.", nil
				}
				limit := a.Limit
				if limit <= 0 {
					limit = defaultPlayerLimit
				}
				var b strings.Builder
				fmt.Fprintf(&b, "Player search results (%d found, showing %d):\n", len(players), min(limit, len(players)))
				for i, p := range players {
					if i == limit {
						break
					}
					fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s\n",
						i+1, p.Name, p.Overall, p.Position, p.Club)
				}
				return strings.TrimRight(b.String(), "\n"), nil
			},
		},
		{
			Name:        "brazilian_clubs_summary",
			Description: "Top-rated Brazilian-national players, and how many Brazilian players each Brazilian club has with their average rating.",
			InputSchema: objectSchema(nil, map[string]any{}),
			run: func(raw json.RawMessage) (string, error) {
				var b strings.Builder
				b.WriteString("Top-rated Brazilian players in dataset:\n")
				for i, p := range st.searchPlayers("", "Brazil", "", "", 0) {
					if i == defaultPlayerLimit {
						break
					}
					fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s\n",
						i+1, p.Name, p.Overall, p.Position, p.Club)
				}
				b.WriteString("\nBrazilian players at Brazilian clubs:\n")
				for _, c := range st.brazilianClubSummary() {
					fmt.Fprintf(&b, "- %s: %d players (avg rating: %.0f)\n", c.Club, c.Players, c.AvgOverall)
				}
				return strings.TrimRight(b.String(), "\n"), nil
			},
		},
	}
}

// baseQuery builds the shared filter from user arguments. The returned label
// is the display name of the team filter, or "" if none was given.
func (st *Store) baseQuery(team, venue, competition string, season int, dateFrom, dateTo, round string) (matchQuery, string, error) {
	q := matchQuery{Season: season, Round: strings.TrimSpace(round)}
	label := ""
	if strings.TrimSpace(team) != "" {
		ids, name, err := st.teamSet(team)
		if err != nil {
			return q, "", err
		}
		q.Team, label = ids, name
	}

	venue = strings.ToLower(strings.TrimSpace(venue))
	if venue != "" && venue != "home" && venue != "away" {
		return q, "", fmt.Errorf("venue must be home, away or empty, got %q", venue)
	}
	q.Venue = venue

	comp, err := resolveCompetition(competition)
	if err != nil {
		return q, "", err
	}
	q.Competition = comp

	if q.From, err = parseOptionalDate(dateFrom); err != nil {
		return q, "", err
	}
	if to, err := parseOptionalDate(dateTo); err != nil {
		return q, "", err
	} else if !to.IsZero() {
		q.To = to.AddDate(0, 0, 1) // dateTo is inclusive; To is exclusive
	}
	return q, label, nil
}

// teamSet resolves a team name to its IDs and a display label.
func (st *Store) teamSet(name string) (map[string]bool, string, error) {
	ids := st.resolveTeams(name)
	if len(ids) == 0 {
		return nil, "", fmt.Errorf("no team matching %q", name)
	}
	set := make(map[string]bool, len(ids))
	for _, id := range ids {
		set[id] = true
	}
	label := st.teamLabel(ids[0])
	if len(ids) > 1 {
		label = parseTeamName(name).Display // ambiguous: several clubs share the name
	}
	return set, label, nil
}

// resolveCompetition maps the user's wording to a canonical competition name.
// An empty string means all competitions.
func resolveCompetition(s string) (string, error) {
	f := foldKey(s)
	switch {
	case f == "":
		return "", nil
	case strings.Contains(f, "libertadores"):
		return compLibertadores, nil
	case strings.Contains(f, "copadobrasil") || strings.Contains(f, "cup"):
		return compCup, nil
	case strings.Contains(f, "serieb"):
		return compSerieB, nil
	case strings.Contains(f, "seriec"):
		return compSerieC, nil
	case strings.Contains(f, "brasileirao") || strings.Contains(f, "seriea"):
		return compBrasileirao, nil
	}
	return "", fmt.Errorf("unknown competition %q (use Brasileirão, Serie B, Serie C, Copa do Brasil or Libertadores)", s)
}

func parseOptionalDate(s string) (time.Time, error) {
	if strings.TrimSpace(s) == "" {
		return time.Time{}, nil
	}
	return parseDate(s)
}

// matchLine formats one fixture, e.g. "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Serie A, Round 22)".
func (st *Store) matchLine(m Match) string {
	label := m.Competition
	if m.Stage != "" {
		label += ", " + m.Stage
	} else if m.Round != "" {
		label += ", Round " + m.Round
	}
	if m.IsFinal && m.Stage == "" {
		label += ", Final"
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)", m.Date.Format("2006-01-02"),
		st.teamLabel(m.Home), m.HomeGoals, m.AwayGoals, st.teamLabel(m.Away), label)
}

// scopeLabel returns " (2022 Brasileirão Serie A)" or "" when nothing is set.
func scopeLabel(season int, competition string) string {
	var parts []string
	if season != 0 {
		parts = append(parts, strconv.Itoa(season))
	}
	if competition != "" {
		parts = append(parts, competition)
	}
	if len(parts) == 0 {
		return ""
	}
	return " (" + strings.Join(parts, " ") + ")"
}

// scopeInner is scopeLabel without the surrounding parentheses, for use mid-sentence.
func scopeInner(season int, competition string) string {
	s := scopeLabel(season, competition)
	if s == "" {
		return ""
	}
	return " " + strings.TrimSuffix(strings.TrimPrefix(s, " ("), ")")
}

func scopeLabelOrAll(season int, competition string) string {
	if s := scopeLabel(season, competition); s != "" {
		return s
	}
	return " (all competitions, all seasons)"
}

func objectSchema(required []string, props map[string]any) map[string]any {
	if required == nil {
		required = []string{}
	}
	return map[string]any{"type": "object", "properties": props, "required": required}
}

func stringProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}

func intProp(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

func boolProp(desc string) map[string]any {
	return map[string]any{"type": "boolean", "description": desc}
}
