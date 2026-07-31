// format.go renders query results as compact human readable text. MCP tool
// results are returned as text content, so the wording here is what the LLM
// actually reads back to the user; each renderer therefore states the scope of
// the data it used and never invents facts that are not in the datasets.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// FormatMatch renders one result line, e.g.
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, round 22)".
func FormatMatch(m *Match) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s: %s %d-%d %s", m.DateString, m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam)
	var ctx []string
	if m.Competition != "" {
		ctx = append(ctx, m.Competition)
	}
	if m.Stage != "" {
		ctx = append(ctx, m.Stage)
	} else if m.Round != "" {
		ctx = append(ctx, "round "+m.Round)
	}
	if m.Venue != "" {
		ctx = append(ctx, m.Venue)
	}
	if len(ctx) > 0 {
		fmt.Fprintf(&b, " (%s)", strings.Join(ctx, ", "))
	}
	return b.String()
}

// FormatMatches renders a match list with a heading and a truncation note.
func FormatMatches(title string, matches []*Match, total int) string {
	if len(matches) == 0 {
		return title + "\nNo matches found in the provided datasets."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", title)
	for _, m := range matches {
		fmt.Fprintf(&b, "- %s\n", FormatMatch(m))
	}
	if total > len(matches) {
		fmt.Fprintf(&b, "... (%d more matches in dataset)\n", total-len(matches))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatRecord renders a win/draw/loss block.
func FormatRecord(label string, r Record) string {
	if r.Matches == 0 {
		return fmt.Sprintf("%s: no matches", label)
	}
	return fmt.Sprintf("%s: %d matches, %dW %dD %dL, GF %d, GA %d, %d pts, win rate %.1f%%",
		label, r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.Points, r.WinRate)
}

// FormatTeamReport renders the output of TeamStats.
func FormatTeamReport(rep *TeamReport) string {
	var b strings.Builder
	scope := rep.Filter
	if scope == "" {
		scope = "all competitions and seasons in the datasets"
	}
	fmt.Fprintf(&b, "%s (%s)\n", rep.Team, scope)
	fmt.Fprintf(&b, "%s\n", FormatRecord("Overall", rep.Overall))
	if rep.Home.Matches > 0 {
		fmt.Fprintf(&b, "%s\n", FormatRecord("Home", rep.Home))
	}
	if rep.Away.Matches > 0 {
		fmt.Fprintf(&b, "%s\n", FormatRecord("Away", rep.Away))
	}
	if len(rep.ByCompetition) > 1 {
		b.WriteString("By competition:\n")
		for _, c := range sortedKeys(rep.ByCompetition) {
			fmt.Fprintf(&b, "  %s\n", FormatRecord(c, rep.ByCompetition[c]))
		}
	}
	if len(rep.BySeason) > 1 {
		b.WriteString("By season:\n")
		seasons := make([]int, 0, len(rep.BySeason))
		for y := range rep.BySeason {
			seasons = append(seasons, y)
		}
		sort.Ints(seasons)
		for _, y := range seasons {
			r := rep.BySeason[y]
			fmt.Fprintf(&b, "  %d: %dW %dD %dL (%d pts, GF %d, GA %d)\n",
				y, r.Wins, r.Draws, r.Losses, r.Points, r.GoalsFor, r.GoalsAgainst)
		}
	}
	if rep.BiggestWin != nil {
		fmt.Fprintf(&b, "Biggest win: %s\n", FormatMatch(rep.BiggestWin))
	}
	if rep.BiggestLoss != nil {
		fmt.Fprintf(&b, "Biggest defeat: %s\n", FormatMatch(rep.BiggestLoss))
	}
	return strings.TrimRight(b.String(), "\n")
}

func sortedKeys(m map[string]Record) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// FormatH2H renders a head-to-head summary.
func FormatH2H(h *H2H) string {
	var b strings.Builder
	scope := h.Filter
	if scope == "" {
		scope = "all competitions in the datasets"
	}
	fmt.Fprintf(&b, "%s vs %s (%s)\n", h.TeamA, h.TeamB, scope)
	fmt.Fprintf(&b, "Head-to-head: %s %d wins, %s %d wins, %d draws (%d matches, %d-%d on goals)\n",
		h.TeamA, h.WinsA, h.TeamB, h.WinsB, h.Draws, h.Matches, h.GoalsA, h.GoalsB)
	fmt.Fprintf(&b, "First meeting %s, last meeting %s\n", h.FirstMeeting, h.LastMeeting)
	for _, m := range h.Results {
		fmt.Fprintf(&b, "- %s\n", FormatMatch(m))
	}
	if h.Matches > len(h.Results) {
		fmt.Fprintf(&b, "... (%d more meetings in dataset)\n", h.Matches-len(h.Results))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatStandings renders a computed league table.
func FormatStandings(competition string, season int, rows []StandingRow) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s table (calculated from match results in the datasets)\n", season, competition)
	for _, r := range rows {
		note := ""
		if r.Position == 1 {
			note = " - Champion (by points)"
		}
		fmt.Fprintf(&b, "%2d. %s - %d pts (%dW %dD %dL, GF %d, GA %d, GD %+d)%s\n",
			r.Position, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff, note)
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatStats renders aggregate competition statistics.
func FormatStats(st *CompetitionStats) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics for %s\n", st.Scope)
	fmt.Fprintf(&b, "Matches: %d across %d teams\n", st.Matches, st.Teams)
	fmt.Fprintf(&b, "Goals: %d total, %.2f per match (%d home, %d away)\n",
		st.TotalGoals, st.GoalsPerMatch, st.HomeGoals, st.AwayGoals)
	fmt.Fprintf(&b, "Results: home wins %d (%.1f%%), away wins %d (%.1f%%), draws %d (%.1f%%)\n",
		st.HomeWins, st.HomeWinRate, st.AwayWins, st.AwayWinRate, st.Draws, st.DrawRate)
	fmt.Fprintf(&b, "Matches with a clean sheet: %d\n", st.CleanSheets)
	if len(st.Seasons) > 0 {
		fmt.Fprintf(&b, "Seasons covered: %d-%d\n", st.Seasons[0], st.Seasons[len(st.Seasons)-1])
	}
	if st.HighestScoring != nil {
		fmt.Fprintf(&b, "Highest scoring match: %s\n", FormatMatch(st.HighestScoring))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatPlayer renders a one line player summary.
func FormatPlayer(p *Player) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s - Overall: %d", p.Name, p.Overall)
	if p.Position != "" {
		fmt.Fprintf(&b, ", Position: %s", p.Position)
	}
	if p.Club != "" {
		fmt.Fprintf(&b, ", Club: %s", p.Club)
	}
	if p.Nationality != "" {
		fmt.Fprintf(&b, ", Nationality: %s", p.Nationality)
	}
	if p.Age > 0 {
		fmt.Fprintf(&b, ", Age: %d", p.Age)
	}
	return b.String()
}

// FormatPlayerProfile renders the full detail of one player.
func FormatPlayerProfile(p *Player) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", p.Name)
	fmt.Fprintf(&b, "Nationality: %s | Age: %d | Club: %s | Position: %s\n",
		or(p.Nationality, "unknown"), p.Age, or(p.Club, "unattached"), or(p.Position, "n/a"))
	fmt.Fprintf(&b, "Overall: %d | Potential: %d | Preferred foot: %s\n", p.Overall, p.Potential, or(p.PreferredFoot, "n/a"))
	if p.Value != "" || p.Wage != "" {
		fmt.Fprintf(&b, "Value: %s | Wage: %s\n", or(p.Value, "n/a"), or(p.Wage, "n/a"))
	}
	if p.Height != "" || p.Weight != "" {
		fmt.Fprintf(&b, "Height: %s | Weight: %s | Shirt: %d\n", p.Height, p.Weight, p.JerseyNumber)
	}
	if len(p.Skills) > 0 {
		keys := make([]string, 0, len(p.Skills))
		for k := range p.Skills {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		var parts []string
		for _, k := range keys {
			parts = append(parts, fmt.Sprintf("%s %d", k, p.Skills[k]))
		}
		fmt.Fprintf(&b, "Attributes: %s\n", strings.Join(parts, ", "))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatPlayers renders a numbered player list.
func FormatPlayers(title string, players []*Player, total int) string {
	if len(players) == 0 {
		return title + "\nNo players matched in the FIFA dataset."
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", title)
	for i, p := range players {
		fmt.Fprintf(&b, "%d. %s\n", i+1, FormatPlayer(p))
	}
	if total > len(players) {
		fmt.Fprintf(&b, "... (%d more players matched)\n", total-len(players))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatRankings renders a team ranking table.
func FormatRankings(title string, rows []TeamRanking) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", title)
	for i, r := range rows {
		fmt.Fprintf(&b, "%2d. %s - %d matches, %dW %dD %dL, %d pts, win rate %.1f%%, GF %d, GA %d, GD %+d\n",
			i+1, r.Team, r.Matches, r.Wins, r.Draws, r.Losses, r.Points, r.WinRate, r.GoalsFor, r.GoalsAgainst, r.GoalDiff)
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatSquads renders the club squad summary from the FIFA data.
func FormatSquads(title string, squads []ClubSquad) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", title)
	if len(squads) == 0 {
		b.WriteString("No clubs matched.\n")
	}
	for _, s := range squads {
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.1f)", s.Club, s.Players, s.AvgOverall)
		if len(s.Top) > 0 {
			names := make([]string, 0, len(s.Top))
			for _, p := range s.Top {
				names = append(names, fmt.Sprintf("%s %d", p.Name, p.Overall))
			}
			fmt.Fprintf(&b, " - top: %s", strings.Join(names, ", "))
		}
		b.WriteString("\n")
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatTeams renders the team directory.
func FormatTeams(title string, teams []TeamSummary) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", title)
	for _, t := range teams {
		fmt.Fprintf(&b, "- %s: %d matches, %d-%d, competitions: %s\n",
			t.Team, t.Matches, t.FirstSeason, t.LastSeason, strings.Join(t.Competitions, "; "))
	}
	return strings.TrimRight(b.String(), "\n")
}

// FormatCompetitions renders the competition directory.
func FormatCompetitions(comps []CompetitionSummary) string {
	var b strings.Builder
	b.WriteString("Competitions in the loaded datasets:\n")
	for _, c := range comps {
		fmt.Fprintf(&b, "- %s: %d matches, %d teams, seasons %d-%d\n",
			c.Competition, c.Matches, c.Teams, c.FirstSeason, c.LastSeason)
	}
	return strings.TrimRight(b.String(), "\n")
}
