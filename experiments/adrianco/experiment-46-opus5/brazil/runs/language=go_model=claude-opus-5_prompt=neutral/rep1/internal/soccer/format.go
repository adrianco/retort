// format.go - human readable rendering of query results.
//
// Context
//
//	Every MCP tool returns two things: structured JSON for programmatic use and
//	a text block for the language model to read. The text block is what the LLM
//	actually quotes back to the user, so it is written the way the specification
//	asks the answers to look:
//
//	    Flamengo vs Fluminense (Fla-Flu):
//	    - 2023-11-11: Flamengo 1-1 Fluminense (Brasileirão Série A 2023)
//	    ...
//	    Head-to-head: Flamengo 18 wins, Fluminense 15 wins, 12 draws
//
//	Formatting is deliberately compact: results are capped, totals are always
//	stated ("showing 10 of 45"), and any caveat the data forces on us - missing
//	scores, incomplete seasons, competitions the club never entered - is spelled
//	out rather than left for the model to infer.
package soccer

import (
	"fmt"
	"strings"
)

// FormatMatchList renders matches as a bulleted list with a "showing N of M"
// header when the list has been truncated.
func FormatMatchList(title string, matches []*Match, total int) string {
	var b strings.Builder
	if title != "" {
		b.WriteString(title)
		b.WriteString("\n")
	}
	if len(matches) == 0 {
		b.WriteString("No matches found.\n")
		return b.String()
	}
	for _, m := range matches {
		fmt.Fprintf(&b, "- %s\n", m.Describe())
	}
	if total > len(matches) {
		fmt.Fprintf(&b, "... (%d more of %d total)\n", total-len(matches), total)
	}
	return b.String()
}

// FormatRecord renders a win/draw/loss record as an indented block.
func FormatRecord(label string, r Record) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", label)
	fmt.Fprintf(&b, "- Matches: %d\n", r.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (GD %+d)\n", r.GoalsFor, r.GoalsAgainst, r.GoalDiff)
	fmt.Fprintf(&b, "- Points: %d (%.1f%% of available)\n", r.Points, r.PointsPct)
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", r.WinRate)
	if r.Unscored > 0 {
		fmt.Fprintf(&b, "- Note: %d further fixture(s) have no score in the source data\n", r.Unscored)
	}
	return b.String()
}

// FormatTeamStats renders the full team statistics answer.
func FormatTeamStats(ts TeamStats) string {
	var b strings.Builder
	scope := ts.Club.Label()
	if ts.Competition != "" {
		scope += " in " + string(ts.Competition)
	}
	if ts.Season != 0 {
		scope += fmt.Sprintf(" %d", ts.Season)
	}
	switch ts.Venue {
	case VenueHome:
		scope += " (home matches only)"
	case VenueAway:
		scope += " (away matches only)"
	}
	b.WriteString(FormatRecord(scope, ts.Overall))

	if ts.Venue == VenueAny && ts.Overall.Played > 0 {
		fmt.Fprintf(&b, "\nHome: %s\n", ts.Home.Summary())
		fmt.Fprintf(&b, "Away: %s\n", ts.Away.Summary())
	}
	if ts.BiggestWin != nil {
		fmt.Fprintf(&b, "\nBiggest win:  %s\n", ts.BiggestWin.Describe())
	}
	if ts.BiggestLoss != nil {
		fmt.Fprintf(&b, "Biggest loss: %s\n", ts.BiggestLoss.Describe())
	}
	if ts.FirstMatch != nil && ts.LastMatch != nil {
		fmt.Fprintf(&b, "Data range: %s to %s\n", ts.FirstMatch.DateString(), ts.LastMatch.DateString())
	}
	if len(ts.ByCompetition) > 0 {
		b.WriteString("\nBy competition:\n")
		for _, cr := range ts.ByCompetition {
			fmt.Fprintf(&b, "- %s (%s): %s\n", cr.Competition,
				formatSeasonRange(cr.Seasons), cr.Record.Summary())
		}
	}
	return b.String()
}

func formatSeasonRange(seasons []int) string {
	if len(seasons) == 0 {
		return "no seasons"
	}
	if len(seasons) == 1 {
		return fmt.Sprint(seasons[0])
	}
	contiguous := true
	for i := 1; i < len(seasons); i++ {
		if seasons[i] != seasons[i-1]+1 {
			contiguous = false
			break
		}
	}
	if contiguous {
		return fmt.Sprintf("%d-%d", seasons[0], seasons[len(seasons)-1])
	}
	return fmt.Sprintf("%d-%d, %d seasons", seasons[0], seasons[len(seasons)-1], len(seasons))
}

// FormatHeadToHead renders the rivalry answer.
func FormatHeadToHead(h HeadToHead) string {
	var b strings.Builder
	title := fmt.Sprintf("%s vs %s", h.ClubA.Name, h.ClubB.Name)
	if h.Nickname != "" {
		title += fmt.Sprintf(" (%s)", h.Nickname)
	}
	if h.Competition != "" {
		title += " in " + string(h.Competition)
	}
	if h.Season != 0 {
		title += fmt.Sprintf(" %d", h.Season)
	}
	b.WriteString(title + ":\n")
	if h.Total == 0 {
		b.WriteString("No meetings between these clubs in the dataset.\n")
		return b.String()
	}
	for _, m := range h.Matches {
		fmt.Fprintf(&b, "- %s\n", m.Describe())
	}
	if h.Total > len(h.Matches) {
		fmt.Fprintf(&b, "... (%d more of %d meetings)\n", h.Total-len(h.Matches), h.Total)
	}
	fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws (%d matches with scores)\n",
		h.ClubA.Name, h.AWins, h.ClubB.Name, h.BWins, h.Draws, h.Played)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n", h.ClubA.Name, h.AGoals, h.ClubB.Name, h.BGoals)
	if len(h.ByCompetition) > 1 {
		parts := make([]string, 0, len(h.ByCompetition))
		for _, c := range AllCompetitions {
			if n, ok := h.ByCompetition[string(c)]; ok {
				parts = append(parts, fmt.Sprintf("%s: %d", c, n))
			}
		}
		fmt.Fprintf(&b, "By competition: %s\n", strings.Join(parts, ", "))
	}
	return b.String()
}

// FormatStandings renders a calculated league table.
func FormatStandings(s Standings) string {
	var b strings.Builder
	suffix := "Final Standings"
	if !s.Complete {
		suffix = "Standings (season incomplete in dataset)"
	}
	fmt.Fprintf(&b, "%d %s %s (calculated from %d matches):\n",
		s.Season, s.Competition, suffix, s.MatchesPlayed)
	fmt.Fprintf(&b, "%-3s %-26s %3s %3s %3s %3s %4s %4s %4s %s\n",
		"#", "Club", "Pts", "P", "W", "D", "L", "GF", "GA", "GD")
	for _, row := range s.Rows {
		r := row.Record
		fmt.Fprintf(&b, "%-3d %-26s %3d %3d %3d %3d %4d %4d %4d %+d",
			row.Position, truncate(r.Club, 26), r.Points, r.Played, r.Wins, r.Draws, r.Losses,
			r.GoalsFor, r.GoalsAgainst, r.GoalDiff)
		if row.Status != "" {
			fmt.Fprintf(&b, "  <- %s", row.Status)
		}
		b.WriteString("\n")
	}
	if s.Note != "" {
		fmt.Fprintf(&b, "\nNote: %s\n", s.Note)
	}
	return b.String()
}

// FormatAggregate renders competition-wide statistics.
func FormatAggregate(a Aggregate) string {
	var b strings.Builder
	scope := "All competitions"
	if a.Competition != "" {
		scope = string(a.Competition)
	}
	if a.Season != 0 {
		scope += fmt.Sprintf(" %d", a.Season)
	}
	fmt.Fprintf(&b, "%s statistics:\n", scope)
	fmt.Fprintf(&b, "- Matches with scores: %d of %d\n", a.Played, a.Matches)
	fmt.Fprintf(&b, "- Total goals: %d\n", a.TotalGoals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", a.GoalsPerMatch)
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), Draws: %d (%.1f%%), Away wins: %d (%.1f%%)\n",
		a.HomeWins, a.HomeWinPct, a.Draws, a.DrawPct, a.AwayWins, a.AwayWinPct)
	fmt.Fprintf(&b, "- Goals by venue: home %d, away %d\n", a.HomeGoals, a.AwayGoals)
	fmt.Fprintf(&b, "- Matches with a clean sheet: %d, goalless draws: %d\n", a.CleanSheets, a.GoallessDraws)
	if a.BiggestWin != nil {
		fmt.Fprintf(&b, "- Biggest win: %s\n", a.BiggestWin.Describe())
	}
	if a.HighestScoring != nil {
		fmt.Fprintf(&b, "- Highest scoring: %s\n", a.HighestScoring.Describe())
	}
	return b.String()
}

// FormatLeaderboard renders a club ranking.
func FormatLeaderboard(l Leaderboard) string {
	var b strings.Builder
	scope := "all competitions"
	if l.Competition != "" {
		scope = string(l.Competition)
	}
	if l.Season != 0 {
		scope += fmt.Sprintf(" %d", l.Season)
	}
	venue := ""
	switch l.Venue {
	case VenueHome:
		venue = ", home matches only"
	case VenueAway:
		venue = ", away matches only"
	}
	fmt.Fprintf(&b, "Clubs ranked by %s in %s%s:\n", l.Metric, scope, venue)
	for i, r := range l.Rows {
		fmt.Fprintf(&b, "%2d. %-26s %s\n", i+1, truncate(r.Club, 26), r.Summary())
	}
	if len(l.Rows) == 0 {
		b.WriteString("No clubs matched (try lowering min_matches).\n")
	}
	return b.String()
}

// FormatPlayerList renders a ranked player list.
func FormatPlayerList(title string, players []*Player, total int) string {
	var b strings.Builder
	if title != "" {
		b.WriteString(title + "\n")
	}
	if len(players) == 0 {
		b.WriteString("No players matched.\n")
		return b.String()
	}
	for i, p := range players {
		fmt.Fprintf(&b, "%2d. %s\n", i+1, p.Describe())
	}
	if total > len(players) {
		fmt.Fprintf(&b, "... (%d more of %d total)\n", total-len(players), total)
	}
	return b.String()
}

// FormatPlayerProfile renders one player in detail.
func FormatPlayerProfile(p *Player, alternatives []*Player) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s (FIFA ID %d)\n", p.Name, p.ID)
	fmt.Fprintf(&b, "- Nationality: %s\n", p.Nationality)
	fmt.Fprintf(&b, "- Age: %d\n", p.Age)
	fmt.Fprintf(&b, "- Club: %s\n", orNone(p.Club))
	fmt.Fprintf(&b, "- Position: %s", orNone(p.Position))
	if p.PositionGroup != "" {
		fmt.Fprintf(&b, " (%s)", p.PositionGroup)
	}
	b.WriteString("\n")
	if p.JerseyNumber > 0 {
		fmt.Fprintf(&b, "- Jersey number: %d\n", p.JerseyNumber)
	}
	fmt.Fprintf(&b, "- Overall: %d, Potential: %d\n", p.Overall, p.Potential)
	if p.Value != "" || p.Wage != "" {
		fmt.Fprintf(&b, "- Value: %s, Wage: %s\n", orNone(p.Value), orNone(p.Wage))
	}
	if p.Height != "" || p.Weight != "" {
		fmt.Fprintf(&b, "- Height: %s, Weight: %s\n", orNone(p.Height), orNone(p.Weight))
	}
	if p.PreferredFoot != "" {
		fmt.Fprintf(&b, "- Preferred foot: %s, work rate: %s\n", p.PreferredFoot, orNone(p.WorkRate))
	}
	if top := TopSkills(p, 6); len(top) > 0 {
		parts := make([]string, 0, len(top))
		for _, k := range top {
			parts = append(parts, fmt.Sprintf("%s %d", k, p.Skills[k]))
		}
		fmt.Fprintf(&b, "- Best attributes: %s\n", strings.Join(parts, ", "))
	}
	if len(alternatives) > 0 {
		names := make([]string, 0, len(alternatives))
		for _, a := range alternatives {
			names = append(names, fmt.Sprintf("%s (%s, %d)", a.Name, orNone(a.Club), a.Overall))
		}
		fmt.Fprintf(&b, "\nOther players matching that name: %s\n", strings.Join(names, "; "))
	}
	return b.String()
}

// FormatClubSummaries renders a per-club player breakdown.
func FormatClubSummaries(title string, rows []ClubPlayerSummary) string {
	var b strings.Builder
	if title != "" {
		b.WriteString(title + "\n")
	}
	if len(rows) == 0 {
		b.WriteString("No clubs matched.\n")
		return b.String()
	}
	for _, r := range rows {
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.1f, avg age: %.1f, best: %s %d)\n",
			r.Club, r.Players, r.AvgOverall, r.AvgAge, r.TopPlayer, r.MaxOverall)
	}
	return b.String()
}

// FormatMatchDetail renders one match with whatever extended statistics exist.
func FormatMatchDetail(m *Match, home, away *Club) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", m.Describe())
	fmt.Fprintf(&b, "- Match ID: %s\n", m.ID)
	fmt.Fprintf(&b, "- Competition: %s, season %d\n", m.Competition, m.Season)
	if m.Round != "" {
		fmt.Fprintf(&b, "- Round: %s\n", m.Round)
	}
	if m.Stage != "" {
		fmt.Fprintf(&b, "- Stage: %s\n", m.Stage)
	}
	if m.Stadium != "" {
		fmt.Fprintf(&b, "- Stadium: %s\n", m.Stadium)
	}
	if home != nil && away != nil {
		fmt.Fprintf(&b, "- Home: %s | Away: %s\n", home.Label(), away.Label())
	}
	if m.HasScore {
		switch m.Outcome() {
		case "home":
			fmt.Fprintf(&b, "- Result: %s won\n", m.HomeTeam)
		case "away":
			fmt.Fprintf(&b, "- Result: %s won\n", m.AwayTeam)
		default:
			b.WriteString("- Result: draw\n")
		}
	} else {
		b.WriteString("- Result: no score recorded in the source data\n")
	}
	if s := m.Stats; s != nil {
		b.WriteString("- Extended statistics (BR-Football-Dataset.csv):\n")
		writeStat(&b, "  - Shots", s.HomeShots, s.AwayShots)
		writeStat(&b, "  - Corners", s.HomeCorners, s.AwayCorners)
		writeStat(&b, "  - Attacks", s.HomeAttacks, s.AwayAttacks)
		if s.KickOff != "" {
			fmt.Fprintf(&b, "  - Kick-off: %s\n", s.KickOff)
		}
		if s.HomeResult != "" {
			fmt.Fprintf(&b, "  - Half-time trend: home %s, away %s\n", s.HomeResult, s.AwayResult)
		}
	}
	fmt.Fprintf(&b, "- Sources: %s\n", strings.Join(m.Sources, ", "))
	return b.String()
}

func writeStat(b *strings.Builder, label string, home, away *int) {
	if home == nil && away == nil {
		return
	}
	fmt.Fprintf(b, "%s: %s-%s\n", label, intOrDash(home), intOrDash(away))
}

func intOrDash(v *int) string {
	if v == nil {
		return "?"
	}
	return fmt.Sprint(*v)
}

func orNone(s string) string {
	if strings.TrimSpace(s) == "" {
		return "(none)"
	}
	return s
}

func truncate(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n-1]) + "…"
}
