package soccer

// TeamRecord summarizes a team's results over a set of matches.
type TeamRecord struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// Points returns the standard three-points-for-a-win total.
func (r TeamRecord) Points() int { return r.Wins*3 + r.Draws }

// GoalDiff returns goals for minus goals against.
func (r TeamRecord) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// WinRate returns the win percentage (0–100), or 0 when no matches played.
func (r TeamRecord) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return 100 * float64(r.Wins) / float64(r.Matches)
}

// TeamRecord computes a team's record over the matches selected by f. The
// team whose perspective is used is f.Team, or f.HomeTeam / f.AwayTeam when
// Team is empty. Matches without a score are ignored.
func (kb *KB) TeamRecord(f MatchFilter) TeamRecord {
	team := f.Team
	if team == "" {
		team = f.HomeTeam
	}
	if team == "" {
		team = f.AwayTeam
	}
	rec := TeamRecord{Team: team}
	for _, m := range kb.SearchMatches(f) {
		if !m.HasScore {
			continue
		}
		var gf, ga int
		switch {
		case TeamsMatch(m.HomeTeam, team):
			gf, ga = m.HomeGoals, m.AwayGoals
		case TeamsMatch(m.AwayTeam, team):
			gf, ga = m.AwayGoals, m.HomeGoals
		default:
			continue
		}
		rec.Matches++
		rec.GoalsFor += gf
		rec.GoalsAgainst += ga
		switch {
		case gf > ga:
			rec.Wins++
		case gf < ga:
			rec.Losses++
		default:
			rec.Draws++
		}
	}
	return rec
}

// H2H holds a head-to-head record between two teams. Wins are counted from
// each team's own perspective regardless of home/away.
type H2H struct {
	Team1     string
	Team2     string
	Team1Wins int
	Team2Wins int
	Draws     int
	Matches   []Match
}

// HeadToHead returns the head-to-head record between team1 and team2 across
// all competitions and seasons.
func (kb *KB) HeadToHead(team1, team2 string) H2H {
	h := H2H{Team1: team1, Team2: team2}
	h.Matches = kb.SearchMatches(MatchFilter{Team: team1, Opponent: team2})
	for _, m := range h.Matches {
		if !m.HasScore {
			continue
		}
		// Determine team1's goals for/against in this match.
		var g1, g2 int
		if TeamsMatch(m.HomeTeam, team1) {
			g1, g2 = m.HomeGoals, m.AwayGoals
		} else {
			g1, g2 = m.AwayGoals, m.HomeGoals
		}
		switch {
		case g1 > g2:
			h.Team1Wins++
		case g1 < g2:
			h.Team2Wins++
		default:
			h.Draws++
		}
	}
	return h
}
