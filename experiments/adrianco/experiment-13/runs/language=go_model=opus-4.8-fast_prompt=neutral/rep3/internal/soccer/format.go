// format.go turns query results into the human-readable, LLM-friendly text
// blocks returned by the MCP tools (mirroring the answer formats in the spec).
package soccer

import (
	"fmt"
	"strings"
)

func (db *DB) dateStr(m Match) string {
	if m.HasDate {
		return m.Date.Format("2006-01-02")
	}
	if m.Season != 0 {
		return fmt.Sprintf("%d", m.Season)
	}
	return "unknown date"
}

// context returns the "(Competition, Round/Stage)" suffix for a match line.
func matchContext(m Match) string {
	parts := []string{m.Competition}
	switch {
	case m.Stage != "":
		parts = append(parts, titleCase(m.Stage))
	case m.Round != "":
		parts = append(parts, "Round "+m.Round)
	}
	return strings.Join(parts, ", ")
}

// FormatMatchLine renders one match, e.g.
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)".
func (db *DB) FormatMatchLine(m Match) string {
	home := db.TeamDisplay(m.HomeKey)
	away := db.TeamDisplay(m.AwayKey)
	score := "vs"
	if m.HasScore {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", db.dateStr(m), home, score, away, matchContext(m))
}

// FormatMatches renders a list of matches with a header line. total is the
// number of matches found before any limit was applied.
func (db *DB) FormatMatches(header string, ms []Match, total int) string {
	var b strings.Builder
	if header != "" {
		fmt.Fprintf(&b, "%s\n", header)
	}
	if len(ms) == 0 {
		b.WriteString("No matches found.")
		return b.String()
	}
	for _, m := range ms {
		fmt.Fprintf(&b, "- %s\n", db.FormatMatchLine(m))
	}
	if total > len(ms) {
		fmt.Fprintf(&b, "... (%d more match(es) in dataset)\n", total-len(ms))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatRecord renders a team Record block.
func (db *DB) FormatRecord(title string, r Record) string {
	return fmt.Sprintf(`%s:
- Matches: %d
- Wins: %d, Draws: %d, Losses: %d
- Goals For: %d, Goals Against: %d (diff %+d)
- Points: %d
- Win rate: %.1f%%`,
		title, r.Played, r.Wins, r.Draws, r.Losses,
		r.GoalsFor, r.GoalsAgainst, r.GoalDiff(), r.Points(), r.WinRate())
}

// FormatH2H renders a head-to-head summary plus recent matches.
func (db *DB) FormatH2H(h H2H, maxMatches int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s — head-to-head (provided data):\n", h.TeamA, h.TeamB)
	played := h.AWins + h.BWins + h.Draws
	fmt.Fprintf(&b, "Played: %d | %s %d wins, %s %d wins, %d draws\n",
		played, h.TeamA, h.AWins, h.TeamB, h.BWins, h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n", h.TeamA, h.AGoals, h.TeamB, h.BGoals)
	if len(h.Matches) == 0 {
		b.WriteString("No matches between these teams in the dataset.")
		return strings.TrimRight(b.String(), "\n")
	}
	b.WriteString("\nMatches:\n")
	shown := h.Matches
	if maxMatches > 0 && len(shown) > maxMatches {
		shown = shown[:maxMatches]
	}
	for _, m := range shown {
		fmt.Fprintf(&b, "- %s\n", db.FormatMatchLine(m))
	}
	if len(h.Matches) > len(shown) {
		fmt.Fprintf(&b, "... (%d more)\n", len(h.Matches)-len(shown))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatStandings renders a league table.
func (db *DB) FormatStandings(competition string, season int, table []Record, limit int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s %d — standings (calculated from matches):\n", competition, season)
	if len(table) == 0 {
		b.WriteString("No matches found for this competition/season.")
		return b.String()
	}
	if limit > 0 && len(table) > limit {
		table = table[:limit]
	}
	for i, r := range table {
		tag := ""
		if i == 0 {
			tag = " — Champion"
		}
		fmt.Fprintf(&b, "%d. %s — %d pts (%dW %dD %dL, GD %+d)%s\n",
			i+1, r.Team, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalDiff(), tag)
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatPlayers renders a list of players.
func (db *DB) FormatPlayers(header string, players []Player, total int) string {
	var b strings.Builder
	if header != "" {
		fmt.Fprintf(&b, "%s\n", header)
	}
	if len(players) == 0 {
		b.WriteString("No players found.")
		return b.String()
	}
	for i, p := range players {
		club := p.Club
		if club == "" {
			club = "(no club)"
		}
		fmt.Fprintf(&b, "%d. %s — Overall: %d, Position: %s, Club: %s, Age: %d, Nationality: %s\n",
			i+1, p.Name, p.Overall, orNA(p.Position), club, p.Age, p.Nationality)
	}
	if total > len(players) {
		fmt.Fprintf(&b, "... (%d more player(s) match)\n", total-len(players))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatStats renders aggregate competition statistics.
func (db *DB) FormatStats(s Stats) string {
	var b strings.Builder
	scope := s.Competition
	if scope == "" {
		scope = "All competitions"
	}
	if s.Season != 0 {
		scope = fmt.Sprintf("%s %d", scope, s.Season)
	}
	fmt.Fprintf(&b, "%s — statistics (provided data):\n", scope)
	fmt.Fprintf(&b, "- Matches with scores: %d\n", s.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", s.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", s.AvgGoals())
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), Away wins: %d, Draws: %d\n",
		s.HomeWins, s.HomeWinRate(), s.AwayWins, s.Draws)
	if len(s.BiggestWins) > 0 {
		b.WriteString("Biggest victories:\n")
		for i, m := range s.BiggestWins {
			fmt.Fprintf(&b, "%d. %s\n", i+1, db.FormatMatchLine(m))
		}
	}
	return strings.TrimRight(b.String(), "\n")
}

// titleCase upper-cases the first letter of each word (e.g. "group stage"
// -> "Group Stage") without the Unicode caveats of the deprecated strings.Title.
func titleCase(s string) string {
	words := strings.Fields(s)
	for i, w := range words {
		words[i] = strings.ToUpper(w[:1]) + w[1:]
	}
	return strings.Join(words, " ")
}

func orNA(s string) string {
	if strings.TrimSpace(s) == "" {
		return "N/A"
	}
	return s
}
