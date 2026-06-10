// Human-readable formatting for query results.
//
// Context: the MCP tools return plain text blocks that an LLM relays to the
// user, so these formatters follow the example answer formats in TASK.md
// (match lists with date/score/competition, win-draw-loss records with
// percentages, numbered standings and player rankings).
package query

import (
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/data"
)

// FormatMatch renders one match as a single line.
func FormatMatch(m *data.Match) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s: %s %d-%d %s (%s",
		m.Date.Format("2006-01-02"), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, m.Competition)
	if m.Round != "" {
		fmt.Fprintf(&b, " round %s", m.Round)
	}
	fmt.Fprintf(&b, ", season %d)", m.Season)
	if m.Stadium != "" {
		fmt.Fprintf(&b, " @ %s", m.Stadium)
	}
	return b.String()
}

// FormatMatches renders a list of matches, capped at limit with a count of
// the remainder.
func FormatMatches(matches []*data.Match, limit int) string {
	if len(matches) == 0 {
		return "No matches found."
	}
	if limit <= 0 {
		limit = 20
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d match(es):\n", len(matches))
	for i, m := range matches {
		if i == limit {
			fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(matches)-limit)
			break
		}
		fmt.Fprintf(&b, "- %s\n", FormatMatch(m))
	}
	return b.String()
}

// FormatRecord renders a team record in the TASK.md example style.
func FormatRecord(r *TeamRecord, season int, competition, venue string) string {
	var b strings.Builder
	scope := ""
	if venue != "" && venue != "all" {
		scope = " " + venue
	}
	fmt.Fprintf(&b, "%s%s record", r.Team, scope)
	if season != 0 {
		fmt.Fprintf(&b, " (%d", season)
		if competition != "" {
			fmt.Fprintf(&b, " %s", competition)
		}
		b.WriteString(")")
	} else if competition != "" {
		fmt.Fprintf(&b, " (%s)", competition)
	}
	fmt.Fprintf(&b, ":\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Win rate: %.1f%%\n",
		r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate())
	return b.String()
}

// FormatHeadToHead renders a head-to-head summary plus recent matches.
func FormatHeadToHead(h *HeadToHead, limit int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s head-to-head (%d matches in dataset):\n", h.Team1, h.Team2, len(h.Matches))
	fmt.Fprintf(&b, "- %s: %d wins\n- %s: %d wins\n- Draws: %d\n- Goals: %s %d, %s %d\n",
		h.Team1, h.Team1Wins, h.Team2, h.Team2Wins, h.Draws, h.Team1, h.Team1Goals, h.Team2, h.Team2Goals)
	if len(h.Matches) > 0 {
		b.WriteString("\nMatches (most recent first):\n")
		if limit <= 0 {
			limit = 10
		}
		for i, m := range h.Matches {
			if i == limit {
				fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(h.Matches)-limit)
				break
			}
			fmt.Fprintf(&b, "- %s\n", FormatMatch(m))
		}
	}
	return b.String()
}

// FormatStandings renders a calculated league table.
func FormatStandings(table []*TeamRecord, season int, competition string) string {
	if len(table) == 0 {
		return fmt.Sprintf("No matches found for %s season %d.", competition, season)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (calculated from %d teams' match results):\n", season, competition, len(table))
	for i, r := range table {
		fmt.Fprintf(&b, "%2d. %s - %d pts (%dW %dD %dL, GF %d GA %d, GD %+d)",
			i+1, r.Team, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff())
		if i == 0 {
			b.WriteString(" - Champion")
		}
		b.WriteString("\n")
	}
	return b.String()
}

// FormatPlayers renders a ranked player list.
func FormatPlayers(players []*data.Player, limit int) string {
	if len(players) == 0 {
		return "No players found."
	}
	if limit <= 0 {
		limit = 20
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d player(s):\n", len(players))
	for i, p := range players {
		if i == limit {
			fmt.Fprintf(&b, "... (%d more players in dataset)\n", len(players)-limit)
			break
		}
		club := p.Club
		if club == "" {
			club = "no club"
		}
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s\n",
			i+1, p.Name, p.Overall, p.Potential, p.Position, p.Age, p.Nationality, club)
	}
	return b.String()
}

// FormatPlayerDetail renders one player with full attributes.
func FormatPlayerDetail(p *data.Player) string {
	return fmt.Sprintf(
		"%s\n- Age: %d\n- Nationality: %s\n- Club: %s\n- Position: %s, Jersey: %d\n- Overall: %d, Potential: %d\n- Height: %s, Weight: %s, Preferred foot: %s\n- Value: %s, Wage: %s\n",
		p.Name, p.Age, p.Nationality, p.Club, p.Position, p.JerseyNumber,
		p.Overall, p.Potential, p.Height, p.Weight, p.PreferredFoot, p.Value, p.Wage)
}

// FormatCompetitionStats renders aggregate goal statistics.
func FormatCompetitionStats(s *CompetitionStats) string {
	scope := "all competitions"
	if s.Competition != "" {
		scope = s.Competition
	}
	if s.Season != 0 {
		scope = fmt.Sprintf("%s, season %d", scope, s.Season)
	}
	if s.Matches == 0 {
		return fmt.Sprintf("No matches found for %s.", scope)
	}
	return fmt.Sprintf(
		"Statistics for %s:\n- Matches: %d\n- Total goals: %d\n- Average goals per match: %.2f\n- Home wins: %d (%.1f%%)\n- Away wins: %d (%.1f%%)\n- Draws: %d (%.1f%%)\n",
		scope, s.Matches, s.TotalGoals, s.AvgGoals(),
		s.HomeWins, s.HomeWinRate(),
		s.AwayWins, float64(s.AwayWins)/float64(s.Matches)*100,
		s.Draws, float64(s.Draws)/float64(s.Matches)*100)
}
