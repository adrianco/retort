// Context
// -------
// The query layer: pure functions over a populated Graph implementing the
// capabilities required by the specification (match search, head-to-head,
// team statistics, league standings, player search and competition-wide
// statistics). Each function returns plain structs; human-readable formatting
// lives in format.go so the same results can also be consumed programmatically.
package soccer

import (
	"sort"
	"strings"
	"time"
)

// MatchQuery describes filters for SearchMatches. Zero-valued fields are
// ignored. Team/Team2 are matched fuzzily against home and away sides.
type MatchQuery struct {
	Team        string    // matches either side
	Team2       string    // when set, restrict to fixtures involving both teams
	Competition string    // canonical or fuzzy competition name
	Season      int       // exact season year
	From        time.Time // inclusive lower date bound
	To          time.Time // inclusive upper date bound
	Limit       int       // max results (<=0 means no limit)
}

// SearchMatches returns matches satisfying the query, sorted most recent first.
// It operates on the source-deduplicated primary set so the same fixture is not
// reported twice from overlapping datasets.
func (g *Graph) SearchMatches(q MatchQuery) []Match {
	var out []Match
	for _, m := range g.primary {
		if !matchPasses(m, q) {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	if q.Limit > 0 && len(out) > q.Limit {
		out = out[:q.Limit]
	}
	return out
}

func matchPasses(m Match, q MatchQuery) bool {
	if q.Team != "" {
		if !(teamMatchesQuery(q.Team, m.HomeTeam) || teamMatchesQuery(q.Team, m.AwayTeam)) {
			return false
		}
	}
	if q.Team2 != "" {
		inHome := teamMatchesQuery(q.Team2, m.HomeTeam) || teamMatchesQuery(q.Team2, m.AwayTeam)
		if !inHome {
			return false
		}
		// Ensure the two queried teams are on opposite sides.
		t1Home := teamMatchesQuery(q.Team, m.HomeTeam)
		t1Away := teamMatchesQuery(q.Team, m.AwayTeam)
		t2Home := teamMatchesQuery(q.Team2, m.HomeTeam)
		t2Away := teamMatchesQuery(q.Team2, m.AwayTeam)
		if !((t1Home && t2Away) || (t1Away && t2Home)) {
			return false
		}
	}
	if q.Competition != "" && !competitionMatches(q.Competition, m.Competition) {
		return false
	}
	if q.Season != 0 && m.Season != q.Season {
		return false
	}
	if !q.From.IsZero() && m.Date.Before(q.From) {
		return false
	}
	if !q.To.IsZero() && m.Date.After(q.To) {
		return false
	}
	return true
}

// competitionMatches fuzzily compares a competition query to a stored name.
func competitionMatches(query, stored string) bool {
	q := strings.ToLower(stripDiacritics(query))
	s := strings.ToLower(stripDiacritics(stored))
	if strings.Contains(s, q) || strings.Contains(q, s) {
		return true
	}
	// Map common synonyms onto the canonical names.
	return strings.ToLower(stripDiacritics(canonicalCompetition(query))) == s
}

// H2H is a head-to-head record between two teams.
type H2H struct {
	TeamA, TeamB        string
	WinsA, WinsB, Draws int
	GoalsA, GoalsB      int
	Matches             []Match
}

// HeadToHead computes the all-competition head-to-head record between two teams.
func (g *Graph) HeadToHead(teamA, teamB string) H2H {
	dispA, _ := g.ResolveTeam(teamA)
	dispB, _ := g.ResolveTeam(teamB)
	res := H2H{TeamA: dispA, TeamB: dispB}
	matches := g.SearchMatches(MatchQuery{Team: teamA, Team2: teamB})
	res.Matches = matches
	for _, m := range matches {
		aHome := teamMatchesQuery(teamA, m.HomeTeam)
		var ga, gb int
		if aHome {
			ga, gb = m.HomeGoals, m.AwayGoals
		} else {
			ga, gb = m.AwayGoals, m.HomeGoals
		}
		res.GoalsA += ga
		res.GoalsB += gb
		switch {
		case ga > gb:
			res.WinsA++
		case gb > ga:
			res.WinsB++
		default:
			res.Draws++
		}
	}
	return res
}

// TeamRecord holds aggregate statistics for a team over a filtered match set.
type TeamRecord struct {
	Team                   string
	Competition            string
	Season                 int
	Filter                 string // "all", "home" or "away"
	Played                 int
	Wins, Draws, Losses    int
	GoalsFor, GoalsAgainst int
}

// Points returns league points (3 for a win, 1 for a draw).
func (r TeamRecord) Points() int { return r.Wins*3 + r.Draws }

// GoalDiff returns goals for minus goals against.
func (r TeamRecord) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// WinRate returns the win percentage (0-100).
func (r TeamRecord) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return 100 * float64(r.Wins) / float64(r.Played)
}

// TeamStatsOptions configures TeamStats.
type TeamStatsOptions struct {
	Season      int
	Competition string
	Filter      string // "", "all", "home", "away"
}

// TeamStats aggregates a team's record, optionally restricted to home or away
// matches, a season and/or a competition.
func (g *Graph) TeamStats(team string, opts TeamStatsOptions) TeamRecord {
	disp, _ := g.ResolveTeam(team)
	filter := opts.Filter
	if filter == "" {
		filter = "all"
	}
	rec := TeamRecord{Team: disp, Competition: opts.Competition, Season: opts.Season, Filter: filter}

	matches := g.SearchMatches(MatchQuery{Team: team, Competition: opts.Competition, Season: opts.Season})
	for _, m := range matches {
		isHome := teamMatchesQuery(team, m.HomeTeam)
		if filter == "home" && !isHome {
			continue
		}
		if filter == "away" && isHome {
			continue
		}
		var gf, ga int
		if isHome {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		rec.Played++
		rec.GoalsFor += gf
		rec.GoalsAgainst += ga
		switch {
		case gf > ga:
			rec.Wins++
		case ga > gf:
			rec.Losses++
		default:
			rec.Draws++
		}
	}
	return rec
}

// Standings computes a league table for a competition + season from results.
func (g *Graph) Standings(competition string, season int) []TeamRecord {
	table := map[string]*TeamRecord{}
	for _, m := range g.primary {
		if season != 0 && m.Season != season {
			continue
		}
		if competition != "" && !competitionMatches(competition, m.Competition) {
			continue
		}
		hk, ak := g.teamID(m.HomeTeam, m.HomeState), g.teamID(m.AwayTeam, m.AwayState)
		home := table[hk]
		if home == nil {
			home = &TeamRecord{Team: g.displayFor(hk, m.HomeTeam), Competition: m.Competition, Season: season, Filter: "all"}
			table[hk] = home
		}
		away := table[ak]
		if away == nil {
			away = &TeamRecord{Team: g.displayFor(ak, m.AwayTeam), Competition: m.Competition, Season: season, Filter: "all"}
			table[ak] = away
		}
		home.Played++
		away.Played++
		home.GoalsFor += m.HomeGoals
		home.GoalsAgainst += m.AwayGoals
		away.GoalsFor += m.AwayGoals
		away.GoalsAgainst += m.HomeGoals
		switch m.Winner() {
		case "home":
			home.Wins++
			away.Losses++
		case "away":
			away.Wins++
			home.Losses++
		default:
			home.Draws++
			away.Draws++
		}
	}

	out := make([]TeamRecord, 0, len(table))
	for _, r := range table {
		out = append(out, *r)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Points() != out[j].Points() {
			return out[i].Points() > out[j].Points()
		}
		if out[i].Wins != out[j].Wins {
			return out[i].Wins > out[j].Wins
		}
		if out[i].GoalDiff() != out[j].GoalDiff() {
			return out[i].GoalDiff() > out[j].GoalDiff()
		}
		return out[i].Team < out[j].Team
	})
	return out
}

// PlayerQuery describes filters for SearchPlayers. Zero values are ignored.
type PlayerQuery struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// SearchPlayers returns players matching the query, sorted by Overall desc.
func (g *Graph) SearchPlayers(q PlayerQuery) []Player {
	var out []Player
	for _, p := range g.Players {
		if q.Name != "" && !containsFold(p.Name, q.Name) {
			continue
		}
		if q.Nationality != "" && !containsFold(p.Nationality, q.Nationality) {
			continue
		}
		if q.Club != "" && !teamMatchesQuery(q.Club, p.Club) && !containsFold(p.Club, q.Club) {
			continue
		}
		if q.Position != "" && !strings.EqualFold(strings.TrimSpace(p.Position), strings.TrimSpace(q.Position)) {
			continue
		}
		if q.MinOverall > 0 && p.Overall < q.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Name < out[j].Name
	})
	if q.Limit > 0 && len(out) > q.Limit {
		out = out[:q.Limit]
	}
	return out
}

func containsFold(haystack, needle string) bool {
	return strings.Contains(
		strings.ToLower(stripDiacritics(haystack)),
		strings.ToLower(stripDiacritics(needle)),
	)
}

// CompetitionStats holds aggregate statistics over a filtered match set.
type CompetitionStats struct {
	Competition string
	Season      int
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
	BiggestWins []Match // sorted by goal margin desc
}

// AvgGoals returns the average goals per match.
func (c CompetitionStats) AvgGoals() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.TotalGoals) / float64(c.Matches)
}

// HomeWinRate returns the home-win percentage (0-100).
func (c CompetitionStats) HomeWinRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return 100 * float64(c.HomeWins) / float64(c.Matches)
}

// Statistics computes aggregate statistics, optionally filtered by competition
// and/or season. topWins controls how many biggest victories to retain.
func (g *Graph) Statistics(competition string, season int, topWins int) CompetitionStats {
	cs := CompetitionStats{Competition: competition, Season: season}
	var filtered []Match
	for _, m := range g.primary {
		if season != 0 && m.Season != season {
			continue
		}
		if competition != "" && !competitionMatches(competition, m.Competition) {
			continue
		}
		filtered = append(filtered, m)
		cs.Matches++
		cs.TotalGoals += m.TotalGoals()
		switch m.Winner() {
		case "home":
			cs.HomeWins++
		case "away":
			cs.AwayWins++
		default:
			cs.Draws++
		}
	}
	if topWins <= 0 {
		topWins = 10
	}
	sort.SliceStable(filtered, func(i, j int) bool {
		mi := abs(filtered[i].HomeGoals - filtered[i].AwayGoals)
		mj := abs(filtered[j].HomeGoals - filtered[j].AwayGoals)
		if mi != mj {
			return mi > mj
		}
		return filtered[i].TotalGoals() > filtered[j].TotalGoals()
	})
	if len(filtered) > topWins {
		filtered = filtered[:topWins]
	}
	cs.BiggestWins = filtered
	return cs
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
