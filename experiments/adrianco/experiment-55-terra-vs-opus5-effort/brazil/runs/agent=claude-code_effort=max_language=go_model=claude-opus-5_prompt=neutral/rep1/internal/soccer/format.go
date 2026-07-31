// format.go renders query results as the compact prose an LLM can quote
// directly, following the answer shapes in the specification.
package soccer

import (
	"fmt"
	"strings"
)

// CompetitionLabel returns the short display name of a competition id.
func CompetitionLabel(id string) string {
	if c, ok := CompetitionByID(id); ok {
		return c.Short
	}
	return id
}

// CompetitionFullName returns the long display name of a competition id.
func CompetitionFullName(id string) string {
	if c, ok := CompetitionByID(id); ok {
		return c.Name
	}
	return id
}

// MatchLine renders one match as a bullet:
//
//   - 2023-09-03: Flamengo 2-1 Fluminense (Brasileirão 2023, Round 22)
func MatchLine(m *Match) string {
	ctx := fmt.Sprintf("%s %d", CompetitionLabel(m.CompetitionID), m.Season)
	if r := m.RoundLabel(); r != "" {
		ctx += ", " + r
	}
	line := fmt.Sprintf("- %s: %s (%s)", m.DateString(), m.Label(), ctx)
	if m.Venue != "" {
		line += " at " + m.Venue
	}
	return line
}

// FormatMatches renders a match list with a heading and a truncation notice.
//
// offset is how many results the page skipped, so the "N more" line counts
// what is genuinely still to come rather than everything not on the page.
func FormatMatches(title string, ms []*Match, total, offset int) string {
	var b strings.Builder
	if title != "" {
		fmt.Fprintf(&b, "%s\n", title)
	}
	if len(ms) == 0 {
		if total > 0 {
			fmt.Fprintf(&b, "This page is empty: %d matches match these filters, but the offset %d is past the end of them.\n", total, offset)
		} else {
			b.WriteString("No matches found for those filters.\n")
		}
		return b.String()
	}
	for _, m := range ms {
		b.WriteString(MatchLine(m) + "\n")
	}
	if remaining := total - offset - len(ms); remaining > 0 {
		fmt.Fprintf(&b, "... (%d more matches match these filters; raise `limit` or narrow the query)\n", remaining)
	}
	return b.String()
}

// FormatHeadToHead renders the head-to-head answer shape from the spec.
func FormatHeadToHead(h *HeadToHead, showMatches int) string {
	var b strings.Builder
	title := fmt.Sprintf("%s vs %s", h.TeamA.Name, h.TeamB.Name)
	if h.Rivalry != "" {
		title += fmt.Sprintf(" (%s derby)", h.Rivalry)
	}
	fmt.Fprintf(&b, "%s:\n", title)
	if h.Total == 0 {
		b.WriteString("No meetings between these clubs in the provided data.\n")
		return b.String()
	}
	shown := h.Matches
	if showMatches > 0 && len(shown) > showMatches {
		shown = shown[:showMatches]
	}
	for _, m := range shown {
		b.WriteString(MatchLine(m) + "\n")
	}
	if h.Total > len(shown) {
		fmt.Fprintf(&b, "... (%d more meetings in the dataset)\n", h.Total-len(shown))
	}
	fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws (goals %d-%d)\n",
		h.TeamA.Name, h.AWins, h.TeamB.Name, h.BWins, h.Draws, h.AGoals, h.BGoals)
	if len(h.ByComp) > 0 {
		b.WriteString("By competition: ")
		parts := make([]string, 0, len(h.ByComp))
		for _, c := range h.ByComp {
			parts = append(parts, fmt.Sprintf("%s %dW-%dD-%dL in %d matches",
				CompetitionLabel(c.CompetitionID), c.Record.Wins, c.Record.Draws, c.Record.Losses, c.Record.Matches))
		}
		b.WriteString(strings.Join(parts, "; ") + " (from " + h.TeamA.Name + "'s point of view)\n")
	}
	if h.BiggestA != nil {
		fmt.Fprintf(&b, "Biggest %s win: %s on %s\n", h.TeamA.Name, h.BiggestA.Label(), h.BiggestA.DateString())
	}
	if h.BiggestB != nil {
		fmt.Fprintf(&b, "Biggest %s win: %s on %s\n", h.TeamB.Name, h.BiggestB.Label(), h.BiggestB.DateString())
	}
	return b.String()
}

// FormatRecord renders a club record block.
func FormatRecord(title string, r Record) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", title)
	fmt.Fprintf(&b, "- Matches: %d\n", r.Matches)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Wins, r.Draws, r.Losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (difference %+d)\n", r.GoalsFor, r.GoalsAgainst, r.GoalDiff())
	fmt.Fprintf(&b, "- Points: %d (%.2f per match)\n", r.Points(), r.PointsPerMatch())
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", r.WinRate())
	return b.String()
}

// FormatStandings renders a computed league table.
func FormatStandings(t *Standings, limit int) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (calculated from %d matches in the provided data):\n",
		t.Season, CompetitionLabel(t.CompetitionID), t.Matches)
	rows := t.Rows
	if limit > 0 && len(rows) > limit {
		rows = rows[:limit]
	}
	for _, r := range rows {
		line := fmt.Sprintf("%2d. %-22s %3d pts (%2dW, %2dD, %2dL) GF %3d GA %3d GD %+4d",
			r.Position, r.TeamName, r.Points, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff)
		if r.Note != "" {
			line += " - " + r.Note
		}
		b.WriteString(line + "\n")
	}
	if len(t.Rows) > len(rows) {
		fmt.Fprintf(&b, "... (%d more clubs)\n", len(t.Rows)-len(rows))
	}
	if t.Note != "" {
		fmt.Fprintf(&b, "Note: %s.\n", t.Note)
	}
	if !t.Complete && t.Note == "" {
		b.WriteString("Note: this is a partial table, not a final standing.\n")
	}
	return b.String()
}

// FormatPlayers renders a ranked player list, offset aware like FormatMatches.
func FormatPlayers(title string, ps []*Player, total, offset int) string {
	var b strings.Builder
	if title != "" {
		fmt.Fprintf(&b, "%s\n", title)
	}
	if len(ps) == 0 {
		if total > 0 {
			fmt.Fprintf(&b, "This page is empty: %d players match these filters, but the offset %d is past the end of them.\n", total, offset)
		} else {
			b.WriteString("No players match those filters.\n")
		}
		return b.String()
	}
	for i, p := range ps {
		club := p.Club
		if club == "" {
			club = "no club"
		}
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Age: %d, %s\n",
			i+1, p.Name, p.Overall, orDash(p.Position), club, p.Age, p.Nationality)
	}
	if remaining := total - offset - len(ps); remaining > 0 {
		fmt.Fprintf(&b, "... (%d more players match; raise `limit` to see more)\n", remaining)
	}
	return b.String()
}

// FormatPlayerProfile renders one player in detail.
func FormatPlayerProfile(p *Player, team *Team) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s (FIFA id %d)\n", p.Name, p.ID)
	fmt.Fprintf(&b, "- Overall: %d, Potential: %d\n", p.Overall, p.Potential)
	fmt.Fprintf(&b, "- Position: %s (%s), Jersey: %s\n", orDash(p.Position), p.PositionGroup(), orDashInt(p.Jersey))
	fmt.Fprintf(&b, "- Age: %d, Nationality: %s\n", p.Age, orDash(p.Nationality))
	club := orDash(p.Club)
	if team != nil {
		club += fmt.Sprintf(" (linked to %s in the match data)", team.Name)
	}
	fmt.Fprintf(&b, "- Club: %s\n", club)
	if p.Height != "" || p.Weight != "" {
		fmt.Fprintf(&b, "- Height: %s, Weight: %s, Preferred foot: %s\n", orDash(p.Height), orDash(p.Weight), orDash(p.Foot))
	}
	if p.Value != "" || p.Wage != "" {
		fmt.Fprintf(&b, "- Value: %s, Wage: %s, Release clause: %s\n", orDash(p.Value), orDash(p.Wage), orDash(p.ReleaseCl))
	}
	if p.Joined != "" || p.ContractEnd != "" {
		fmt.Fprintf(&b, "- Joined: %s, Contract until: %s\n", orDash(p.Joined), orDash(p.ContractEnd))
	}
	if top := p.TopSkills(8); len(top) > 0 {
		parts := make([]string, 0, len(top))
		for _, s := range top {
			parts = append(parts, fmt.Sprintf("%s %d", s.Name, s.Value))
		}
		fmt.Fprintf(&b, "- Best attributes: %s\n", strings.Join(parts, ", "))
	}
	return b.String()
}

// FormatAggregate renders the statistical summary of a set of matches.
func FormatAggregate(title string, a Aggregate) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", title)
	if a.Matches == 0 {
		b.WriteString("No matches match those filters.\n")
		return b.String()
	}
	fmt.Fprintf(&b, "- Matches: %d (%s to %s)\n", a.Matches, a.FirstDate, a.LastDate)
	fmt.Fprintf(&b, "- Goals: %d, average goals per match: %.2f\n", a.Goals, a.AvgGoals)
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), draws: %d (%.1f%%), away wins: %d (%.1f%%)\n",
		a.HomeWins, a.HomeWinRate, a.Draws, a.DrawRate, a.AwayWins, a.AwayWinRate)
	fmt.Fprintf(&b, "- Average home goals: %.2f, average away goals: %.2f\n", a.AvgHomeGoals, a.AvgAwayGoals)
	fmt.Fprintf(&b, "- Both teams scored: %.1f%%, over 2.5 goals: %.1f%%\n", a.BothScoredRate, a.Over25Rate)
	fmt.Fprintf(&b, "- Biggest winning margin: %d goals; highest scoring match: %d goals\n", a.BiggestMargin, a.HighestScoring)
	return b.String()
}

// FormatTeamRecords renders a ranked table of club records.
func FormatTeamRecords(title string, rs []Record) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", title)
	if len(rs) == 0 {
		b.WriteString("No clubs match those filters.\n")
		return b.String()
	}
	for i, r := range rs {
		fmt.Fprintf(&b, "%2d. %-22s %3d pts from %3d matches (%dW %dD %dL), GF %d GA %d, win rate %.1f%%\n",
			i+1, r.TeamName, r.Points(), r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate())
	}
	return b.String()
}

// FormatTeamProfile renders the full club dossier.
func FormatTeamProfile(p *TeamProfile) string {
	var b strings.Builder
	t := p.Team
	where := t.State
	if where == "" {
		where = t.Country
	} else if name, ok := BrazilianStates[t.State]; ok {
		where = name + " (" + t.State + ")"
	}
	fmt.Fprintf(&b, "%s [%s]\n", t.Name, t.ID)
	if where != "" {
		fmt.Fprintf(&b, "- Based in: %s\n", where)
	}
	fmt.Fprintf(&b, "- Spellings in the data: %s\n", strings.Join(t.Aliases, ", "))
	if len(t.Seasons) > 0 {
		fmt.Fprintf(&b, "- Seasons covered: %d-%d\n", t.Seasons[0], t.Seasons[len(t.Seasons)-1])
	}
	b.WriteString("\n" + FormatRecord("Overall record in the provided data", p.Record))
	fmt.Fprintf(&b, "- Home: %dW %dD %dL, Away: %dW %dD %dL\n",
		p.Home.Wins, p.Home.Draws, p.Home.Losses, p.Away.Wins, p.Away.Draws, p.Away.Losses)
	if len(p.ByCompetition) > 0 {
		b.WriteString("\nBy competition:\n")
		for _, c := range p.ByCompetition {
			r := c.Record
			fmt.Fprintf(&b, "- %-16s %3d matches: %dW %dD %dL, GF %d GA %d\n",
				CompetitionLabel(c.CompetitionID), r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst)
		}
	}
	if len(p.Titles) > 0 {
		parts := make([]string, 0, len(p.Titles))
		for _, t := range p.Titles {
			parts = append(parts, fmt.Sprintf("%s %d", CompetitionLabel(t.Competition), t.Season))
		}
		fmt.Fprintf(&b, "\nLeague titles inside the data window: %s\n", strings.Join(parts, ", "))
	}
	if p.BiggestWin != nil {
		fmt.Fprintf(&b, "\nBiggest win: %s (%s)\n", p.BiggestWin.Label(), p.BiggestWin.DateString())
	}
	if p.HeaviestLoss != nil {
		fmt.Fprintf(&b, "Heaviest defeat: %s (%s)\n", p.HeaviestLoss.Label(), p.HeaviestLoss.DateString())
	}
	if len(p.Stadiums) > 0 {
		parts := make([]string, 0, len(p.Stadiums))
		for _, s := range p.Stadiums {
			parts = append(parts, fmt.Sprintf("%s (%d)", s.Name, s.Count))
		}
		fmt.Fprintf(&b, "Home grounds recorded: %s\n", strings.Join(parts, ", "))
	}
	if len(p.Rivals) > 0 {
		parts := make([]string, 0, len(p.Rivals))
		for _, r := range p.Rivals {
			other := r.TeamA
			if other == t.ID {
				other = r.TeamB
			}
			if name, ok := p.RivalNames[other]; ok {
				other = name
			}
			parts = append(parts, fmt.Sprintf("%s (against %s)", r.Name, other))
		}
		fmt.Fprintf(&b, "Derbies: %s\n", strings.Join(parts, ", "))
	}
	if len(p.Squad) > 0 {
		fmt.Fprintf(&b, "\nFIFA squad in the player dataset (%d players):\n", len(p.Squad))
		for i, pl := range p.Squad {
			if i == 8 {
				fmt.Fprintf(&b, "... (%d more)\n", len(p.Squad)-8)
				break
			}
			fmt.Fprintf(&b, "- %s (%s, overall %d)\n", pl.Name, orDash(pl.Position), pl.Overall)
		}
	}
	return b.String()
}

// FormatClubSummaries renders per-club squad aggregates.
func FormatClubSummaries(title string, cs []ClubSummary) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", title)
	if len(cs) == 0 {
		b.WriteString("No clubs match those filters.\n")
		return b.String()
	}
	for _, c := range cs {
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.1f, best: %s at %d)\n",
			c.Club, c.Players, c.AvgOverall, c.TopPlayer, c.MaxOverall)
	}
	return b.String()
}

// FormatMatchDetail renders one match with its extended statistics.
func FormatMatchDetail(m *Match) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s: %s\n", m.DateString(), m.Label())
	fmt.Fprintf(&b, "- Competition: %s %d", CompetitionFullName(m.CompetitionID), m.Season)
	if r := m.RoundLabel(); r != "" {
		fmt.Fprintf(&b, " (%s)", r)
	}
	b.WriteString("\n")
	if m.Venue != "" {
		fmt.Fprintf(&b, "- Venue: %s\n", m.Venue)
	}
	fmt.Fprintf(&b, "- Result: %s\n", outcomeText(m))
	if m.Stats != nil {
		s := m.Stats
		fmt.Fprintf(&b, "- Shots: %s-%s, corners: %s-%s, attacks: %s-%s\n",
			s.HomeShots, s.AwayShots, s.HomeCorners, s.AwayCorners, s.HomeAttacks, s.AwayAttacks)
		if s.HTHomeResult != "" {
			fmt.Fprintf(&b, "- Half-time trend: %s / %s\n", s.HTHomeResult, s.HTAwayResult)
		}
	}
	fmt.Fprintf(&b, "- Sources: %s\n", strings.Join(m.Sources, ", "))
	fmt.Fprintf(&b, "- Match id: %s\n", m.ID)
	return b.String()
}

func outcomeText(m *Match) string {
	switch m.Outcome() {
	case HomeWin:
		return m.HomeName + " won at home"
	case AwayWin:
		return m.AwayName + " won away"
	}
	return "draw"
}

func orDash(s string) string {
	if strings.TrimSpace(s) == "" {
		return "-"
	}
	return s
}

func orDashInt(v int) string {
	if v == 0 {
		return "-"
	}
	return fmt.Sprint(v)
}
