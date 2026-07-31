package mcpserver

import (
	"fmt"
	"sort"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// The renderers below produce the prose block of each tool result. They aim to
// match the answer shapes in the specification closely enough that an LLM can
// quote them verbatim.

func renderMatch(m soccer.Match) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s: %s %d-%d %s (%s",
		m.Date.Format("2006-01-02"), m.Home.Name, m.HomeGoals, m.AwayGoals, m.Away.Name, m.Competition)
	switch {
	case m.Stage != "":
		fmt.Fprintf(&b, " %s", m.Stage)
	case m.Round != "":
		fmt.Fprintf(&b, " Round %s", m.Round)
	}
	b.WriteString(")")
	if m.Venue != "" {
		fmt.Fprintf(&b, " at %s", m.Venue)
	}
	return b.String()
}

func renderMatches(res *soccer.MatchQueryResult) string {
	var b strings.Builder
	b.WriteString(res.Summary + "\n")
	for _, m := range res.Matches {
		b.WriteString("- " + renderMatch(m) + "\n")
	}
	if res.Returned < res.Total {
		fmt.Fprintf(&b, "... (%d more matches in dataset)\n", res.Total-res.Returned)
	}
	if h := res.HeadToHead; h != nil {
		b.WriteString("\n" + renderH2H(h))
	}
	return b.String()
}

func renderH2H(h *soccer.H2H) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Head-to-head in dataset: %s %d wins, %s %d wins, %d draws (%d meetings)\n",
		h.TeamA, h.WinsA, h.TeamB, h.WinsB, h.Draws, h.Matches)
	if h.Matches == 0 {
		return b.String()
	}
	fmt.Fprintf(&b, "Goals: %s %d, %s %d (%.2f per match)\n", h.TeamA, h.GoalsA, h.TeamB, h.GoalsB, h.AvgGoals)
	fmt.Fprintf(&b, "First meeting: %s, last meeting: %s\n", h.FirstMeet, h.LastMeet)
	if len(h.ByComp) > 0 {
		comps := make([]string, 0, len(h.ByComp))
		for c := range h.ByComp {
			comps = append(comps, c)
		}
		sort.Strings(comps)
		parts := make([]string, 0, len(comps))
		for _, c := range comps {
			parts = append(parts, fmt.Sprintf("%s %d", c, h.ByComp[c]))
		}
		fmt.Fprintf(&b, "By competition: %s\n", strings.Join(parts, ", "))
	}
	if h.BiggestWin != "" {
		fmt.Fprintf(&b, "Biggest margin: %s\n", h.BiggestWin)
	}
	return b.String()
}

func renderRecord(label string, r soccer.Record) string {
	if r.Matches == 0 {
		return ""
	}
	return fmt.Sprintf("%s: %d matches, %dW %dD %dL, GF %d GA %d (%+d), %d pts, win rate %.1f%%\n",
		label, r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst,
		r.GoalDiff, r.Points, r.WinRate)
}

func renderTeamStats(st *soccer.TeamStats) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s record (%s):\n", st.Team, st.Scope)
	b.WriteString(renderRecord("  Overall", st.Overall))
	b.WriteString(renderRecord("  Home", st.Home))
	b.WriteString(renderRecord("  Away", st.Away))
	if len(st.ByCompetition) > 1 {
		comps := make([]string, 0, len(st.ByCompetition))
		for c := range st.ByCompetition {
			comps = append(comps, c)
		}
		sort.Strings(comps)
		b.WriteString("  By competition:\n")
		for _, c := range comps {
			b.WriteString("  " + renderRecord("  "+c, st.ByCompetition[c]))
		}
	}
	if st.BiggestWin != "" {
		fmt.Fprintf(&b, "  Biggest win: %s\n", st.BiggestWin)
	}
	if st.BiggestLoss != "" {
		fmt.Fprintf(&b, "  Heaviest defeat: %s\n", st.BiggestLoss)
	}
	fmt.Fprintf(&b, "  Data spans %s to %s\n", st.FirstMatch, st.LastMatch)
	return b.String()
}

func renderStandings(st *soccer.Standings) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Final Standings (calculated from matches):\n", st.Season, st.Competition)
	for _, r := range st.Table {
		fmt.Fprintf(&b, "%2d. %-26s %3d pts (%2dW, %2dD, %2dL) GF %3d GA %3d GD %+4d",
			r.Position, r.Team, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff)
		if r.Note != "" {
			fmt.Fprintf(&b, " - %s", r.Note)
		}
		b.WriteString("\n")
	}
	b.WriteString("\n" + st.Note + "\n")
	return b.String()
}

func renderStats(st *soccer.CompetitionStats) string {
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics for %s\n", st.Scope)
	fmt.Fprintf(&b, "Matches: %d over %d seasons\n", st.Matches, len(st.Seasons))
	fmt.Fprintf(&b, "Average goals per match: %.2f (%d total)\n", st.AvgGoals, st.Goals)
	fmt.Fprintf(&b, "Home win rate: %.1f%%  Away win rate: %.1f%%  Draw rate: %.1f%%\n",
		st.HomeWinPct, st.AwayWinPct, st.DrawPct)
	fmt.Fprintf(&b, "Goals by venue: home %d, away %d\n", st.HomeGoals, st.AwayGoals)
	fmt.Fprintf(&b, "Matches with a clean sheet: %d, goalless draws: %d\n", st.CleanSheets, st.GoallessDraws)
	if len(st.BiggestWins) > 0 {
		b.WriteString("\nBiggest victories:\n")
		for i, line := range st.BiggestWins {
			fmt.Fprintf(&b, "%d. %s\n", i+1, line)
		}
	}
	if len(st.HighestScoring) > 0 {
		b.WriteString("\nHighest scoring matches:\n")
		for i, line := range st.HighestScoring {
			fmt.Fprintf(&b, "%d. %s\n", i+1, line)
		}
	}
	return b.String()
}

func renderPlayers(res *soccer.PlayerQueryResult) string {
	var b strings.Builder
	b.WriteString(res.Summary + "\n")
	for i, p := range res.Players {
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Potential: %d, Position: %s, Age: %d, Club: %s, Nationality: %s\n",
			i+1, p.Name, p.Overall, p.Potential, p.Position, p.Age, p.Club, p.Nationality)
	}
	if res.Returned < res.Total {
		fmt.Fprintf(&b, "... (%d more players match)\n", res.Total-res.Returned)
	}
	return b.String()
}
