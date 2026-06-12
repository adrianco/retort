// Tool definitions and handlers. Each tool maps the soccer domain queries onto
// the MCP tools/call surface, validating arguments and rendering answers in the
// language of the problem domain (matches, head-to-head records, standings,
// player ratings) rather than raw data structures.
package mcp

import (
	"fmt"
	"strings"
	"time"

	"brazilian-soccer-mcp/soccer"
)

const defaultMatchLimit = 50

func (s *Server) registerTools() {
	s.register(tool{
		descriptor: toolDescriptor{
			Name: "find_matches",
			Description: "Find soccer matches by team, opponent, competition, season, or date range. " +
				"When both a team and an opponent are given, includes their head-to-head record.",
			InputSchema: object(props{
				"team":        strProp("Team name (matches home or away). Variations like 'Palmeiras-SP' are normalized."),
				"opponent":    strProp("Restrict to matches against this opponent and report head-to-head."),
				"home_team":   strProp("Restrict to matches where this team played at home."),
				"away_team":   strProp("Restrict to matches where this team played away."),
				"competition": strProp("Competition name, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."),
				"season":      intProp("Season year, e.g. 2019."),
				"start_date":  strProp("Inclusive start date (YYYY-MM-DD)."),
				"end_date":    strProp("Inclusive end date (YYYY-MM-DD)."),
				"limit":       intProp("Maximum matches to list (default 50)."),
			}, nil),
		},
		handler: handleFindMatches,
	})

	s.register(tool{
		descriptor: toolDescriptor{
			Name:        "get_team_stats",
			Description: "Get a team's record (wins, draws, losses, goals for/against, win rate), optionally filtered by competition, season, and venue (home/away/all).",
			InputSchema: object(props{
				"team":        strProp("Team name."),
				"competition": strProp("Optional competition filter."),
				"season":      intProp("Optional season year filter."),
				"venue":       strProp("One of 'home', 'away', or 'all' (default)."),
			}, []string{"team"}),
		},
		handler: handleTeamStats,
	})

	s.register(tool{
		descriptor: toolDescriptor{
			Name:        "compare_teams",
			Description: "Compare two teams head-to-head: wins for each, draws, and the list of matches between them.",
			InputSchema: object(props{
				"team1": strProp("First team."),
				"team2": strProp("Second team."),
			}, []string{"team1", "team2"}),
		},
		handler: handleCompareTeams,
	})

	s.register(tool{
		descriptor: toolDescriptor{
			Name:        "search_players",
			Description: "Search FIFA players by name, nationality (e.g. 'Brazil'), club, or position, with an optional minimum overall rating. Results are sorted by overall rating.",
			InputSchema: object(props{
				"name":        strProp("Full or partial player name."),
				"nationality": strProp("Nationality, e.g. 'Brazil'."),
				"club":        strProp("Club name, e.g. 'Flamengo'."),
				"position":    strProp("Position code, e.g. 'ST', 'GK', 'CDM'."),
				"min_overall": intProp("Minimum FIFA overall rating."),
				"limit":       intProp("Maximum players to return (default 10)."),
			}, nil),
		},
		handler: handleSearchPlayers,
	})

	s.register(tool{
		descriptor: toolDescriptor{
			Name:        "get_standings",
			Description: "Calculate a league standings table from match results for a competition and season (3 points per win, 1 per draw).",
			InputSchema: object(props{
				"competition": strProp("Competition name, e.g. 'Brasileirão'."),
				"season":      intProp("Season year, e.g. 2019."),
			}, []string{"season"}),
		},
		handler: handleStandings,
	})

	s.register(tool{
		descriptor: toolDescriptor{
			Name:        "league_statistics",
			Description: "Aggregate statistics for a competition/season: total matches, average goals per match, home win rate, and the biggest victories.",
			InputSchema: object(props{
				"competition": strProp("Optional competition filter."),
				"season":      intProp("Optional season year filter."),
			}, nil),
		},
		handler: handleLeagueStats,
	})
}

// --- handlers ---

func handleFindMatches(store *soccer.Store, args map[string]any) (string, error) {
	q := soccer.MatchQuery{
		Team:        getString(args, "team"),
		Opponent:    getString(args, "opponent"),
		HomeTeam:    getString(args, "home_team"),
		AwayTeam:    getString(args, "away_team"),
		Competition: getString(args, "competition"),
		Season:      getInt(args, "season"),
		Limit:       getInt(args, "limit"),
	}
	if sd := getString(args, "start_date"); sd != "" {
		t, ok := parseQueryDate(sd)
		if !ok {
			return "", fmt.Errorf("invalid start_date %q (use YYYY-MM-DD)", sd)
		}
		q.Start, q.HasStart = t, true
	}
	if ed := getString(args, "end_date"); ed != "" {
		t, ok := parseQueryDate(ed)
		if !ok {
			return "", fmt.Errorf("invalid end_date %q (use YYYY-MM-DD)", ed)
		}
		q.End, q.HasEnd = t, true
	}
	if q.Team == "" && q.Opponent == "" && q.HomeTeam == "" && q.AwayTeam == "" &&
		q.Competition == "" && q.Season == 0 && !q.HasStart && !q.HasEnd {
		return "", fmt.Errorf("provide at least one filter (team, competition, season, or date range)")
	}

	limit := q.Limit
	if limit == 0 {
		limit = defaultMatchLimit
		q.Limit = 0 // count all, trim for display below
	}
	all := store.FindMatches(q)
	total := len(all)
	shown := all
	if len(shown) > limit {
		shown = shown[:limit]
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", describeMatchQuery(q))
	if total == 0 {
		b.WriteString("No matches found.\n")
		return b.String(), nil
	}
	for _, m := range shown {
		b.WriteString("- " + formatMatch(m) + "\n")
	}
	if total > len(shown) {
		fmt.Fprintf(&b, "... (%d more matches in dataset)\n", total-len(shown))
	}
	fmt.Fprintf(&b, "Total matches in dataset: %d\n", total)

	// Head-to-head when two teams are named.
	if q.Team != "" && q.Opponent != "" {
		h := store.HeadToHead(q.Team, q.Opponent)
		fmt.Fprintf(&b, "head-to-head: %s %d win(s), %s %d win(s), %d draw(s)\n",
			h.Team1, h.Team1Wins, h.Team2, h.Team2Wins, h.Draws)
	}
	return b.String(), nil
}

func handleTeamStats(store *soccer.Store, args map[string]any) (string, error) {
	team := getString(args, "team")
	if team == "" {
		return "", fmt.Errorf("team is required")
	}
	competition := getString(args, "competition")
	season := getInt(args, "season")
	venue, venueLabel := parseVenue(getString(args, "venue"))

	rec := store.TeamStats(team, competition, season, venue)

	var scope []string
	if season != 0 {
		scope = append(scope, fmt.Sprintf("%d", season))
	}
	if competition != "" {
		scope = append(scope, competition)
	}
	scopeStr := ""
	if len(scope) > 0 {
		scopeStr = " (" + strings.Join(scope, " ") + ")"
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s %s record%s:\n", rec.Team, venueLabel, scopeStr)
	fmt.Fprintf(&b, "- Matches: %d\n", rec.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", rec.Wins, rec.Draws, rec.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d\n", rec.GoalsFor, rec.GoalsAgainst)
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", rec.WinRate())
	return b.String(), nil
}

func handleCompareTeams(store *soccer.Store, args map[string]any) (string, error) {
	team1 := getString(args, "team1")
	team2 := getString(args, "team2")
	if team1 == "" || team2 == "" {
		return "", fmt.Errorf("both team1 and team2 are required")
	}
	h := store.HeadToHead(team1, team2)

	var b strings.Builder
	fmt.Fprintf(&b, "Head-to-head: %s vs %s\n", h.Team1, h.Team2)
	fmt.Fprintf(&b, "- Matches: %d\n", len(h.Matches))
	fmt.Fprintf(&b, "- %s wins: %d\n", h.Team1, h.Team1Wins)
	fmt.Fprintf(&b, "- %s wins: %d\n", h.Team2, h.Team2Wins)
	fmt.Fprintf(&b, "- Draws (draw): %d\n", h.Draws)
	if len(h.Matches) > 0 {
		b.WriteString("Matches:\n")
		limit := h.Matches
		if len(limit) > defaultMatchLimit {
			limit = limit[:defaultMatchLimit]
		}
		for _, m := range limit {
			b.WriteString("- " + formatMatch(m) + "\n")
		}
	}
	return b.String(), nil
}

func handleSearchPlayers(store *soccer.Store, args map[string]any) (string, error) {
	q := soccer.PlayerQuery{
		Name:        getString(args, "name"),
		Nationality: getString(args, "nationality"),
		Club:        getString(args, "club"),
		Position:    getString(args, "position"),
		MinOverall:  getInt(args, "min_overall"),
		Limit:       getInt(args, "limit"),
	}
	if q.Limit == 0 {
		q.Limit = 10
	}
	if q.Name == "" && q.Nationality == "" && q.Club == "" && q.Position == "" && q.MinOverall == 0 {
		return "", fmt.Errorf("provide at least one search criterion (name, nationality, club, position, or min_overall)")
	}
	players := store.SearchPlayers(q)

	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", describePlayerQuery(q))
	if len(players) == 0 {
		b.WriteString("No players found.\n")
		return b.String(), nil
	}
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Nationality: %s\n",
			i+1, p.Name, p.Overall, dash(p.Position), dash(p.Club), dash(p.Nationality))
	}
	return b.String(), nil
}

func handleStandings(store *soccer.Store, args map[string]any) (string, error) {
	competition := getString(args, "competition")
	season := getInt(args, "season")
	if season == 0 {
		return "", fmt.Errorf("season is required to calculate standings")
	}
	if competition == "" {
		competition = "Brasileirão"
	}
	rows := store.Standings(competition, season)

	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Standings (calculated from matches):\n", season, competition)
	if len(rows) == 0 {
		b.WriteString("No matches found for this competition and season.\n")
		return b.String(), nil
	}
	for i, r := range rows {
		label := ""
		if i == 0 {
			label = " - Champion"
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d, GD %+d)%s\n",
			i+1, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff(), label)
	}
	return b.String(), nil
}

func handleLeagueStats(store *soccer.Store, args map[string]any) (string, error) {
	competition := getString(args, "competition")
	season := getInt(args, "season")
	stats := store.LeagueStats(competition, season, 5)

	scope := "All competitions"
	if competition != "" {
		scope = competition
	}
	if season != 0 {
		scope = fmt.Sprintf("%s %d", scope, season)
	}

	var b strings.Builder
	fmt.Fprintf(&b, "%s statistics (calculated from %d matches):\n", scope, stats.Matches)
	if stats.Matches == 0 {
		b.WriteString("No matches found for this filter.\n")
		return b.String(), nil
	}
	fmt.Fprintf(&b, "- Matches: %d\n", stats.Matches)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", stats.AvgGoals)
	fmt.Fprintf(&b, "- Home win rate: %.1f%%\n", stats.HomeWinRate)
	fmt.Fprintf(&b, "- Home wins: %d, Away wins: %d, Draws: %d\n", stats.HomeWins, stats.AwayWins, stats.Draws)
	b.WriteString("Biggest victories:\n")
	for i, m := range stats.BiggestWins {
		fmt.Fprintf(&b, "%d. %s\n", i+1, formatMatch(m))
	}
	return b.String(), nil
}

// --- formatting helpers ---

func formatMatch(m soccer.Match) string {
	when := "(no date)"
	if m.HasDate {
		when = m.Date.Format("2006-01-02")
	} else if m.Season != 0 {
		when = fmt.Sprintf("Season %d", m.Season)
	}
	context := m.Competition
	switch {
	case m.Round != "":
		context += " Round " + m.Round
	case m.Stage != "":
		context += " " + m.Stage
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)", when, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, context)
}

func describeMatchQuery(q soccer.MatchQuery) string {
	var parts []string
	if q.Team != "" && q.Opponent != "" {
		parts = append(parts, fmt.Sprintf("%s vs %s", q.Team, q.Opponent))
	} else if q.Team != "" {
		parts = append(parts, q.Team)
	}
	if q.HomeTeam != "" {
		parts = append(parts, "home: "+q.HomeTeam)
	}
	if q.AwayTeam != "" {
		parts = append(parts, "away: "+q.AwayTeam)
	}
	if q.Competition != "" {
		parts = append(parts, q.Competition)
	}
	if q.Season != 0 {
		parts = append(parts, fmt.Sprintf("%d", q.Season))
	}
	if q.HasStart {
		parts = append(parts, "from "+q.Start.Format("2006-01-02"))
	}
	if q.HasEnd {
		parts = append(parts, "to "+q.End.Format("2006-01-02"))
	}
	if len(parts) == 0 {
		return "Matches:"
	}
	return "Matches (" + strings.Join(parts, ", ") + "):"
}

func describePlayerQuery(q soccer.PlayerQuery) string {
	var parts []string
	if q.Name != "" {
		parts = append(parts, "name~"+q.Name)
	}
	if q.Nationality != "" {
		parts = append(parts, "nationality="+q.Nationality)
	}
	if q.Club != "" {
		parts = append(parts, "club="+q.Club)
	}
	if q.Position != "" {
		parts = append(parts, "position="+q.Position)
	}
	if q.MinOverall != 0 {
		parts = append(parts, fmt.Sprintf("min overall %d", q.MinOverall))
	}
	return "Players (" + strings.Join(parts, ", ") + "):"
}

func parseVenue(v string) (soccer.Venue, string) {
	switch strings.ToLower(strings.TrimSpace(v)) {
	case "home":
		return soccer.VenueHome, "home"
	case "away":
		return soccer.VenueAway, "away"
	default:
		return soccer.VenueAll, "overall"
	}
}

func parseQueryDate(s string) (time.Time, bool) {
	for _, l := range []string{"2006-01-02", "02/01/2006", "2006-01-02 15:04:05"} {
		if t, err := time.Parse(l, strings.TrimSpace(s)); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

func dash(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}
