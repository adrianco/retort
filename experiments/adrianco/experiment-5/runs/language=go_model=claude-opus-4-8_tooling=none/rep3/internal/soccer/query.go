// Context: the query engine. These methods implement the five capability
// categories in TASK.md — match queries, team queries, player queries,
// competition queries and statistical analysis — over the in-memory Store.
package soccer

import (
	"sort"
	"strings"
)

// SearchMatches returns the matches passing the filter, most recent first.
func (s *Store) SearchMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range s.Matches {
		if !f.keepBase(m) {
			continue
		}
		if !teamSideMatches(m, f) {
			continue
		}
		out = append(out, m)
	}
	sortMatchesByDateDesc(out)
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// teamSideMatches applies the Team / Opponent / Venue constraints.
func teamSideMatches(m Match, f MatchFilter) bool {
	if f.Team == "" && f.Opponent == "" {
		return true
	}
	homeT := matchesQuery(m.HomeKey, f.Team)
	awayT := matchesQuery(m.AwayKey, f.Team)

	if f.Team != "" {
		switch f.Venue {
		case "home":
			if !homeT {
				return false
			}
		case "away":
			if !awayT {
				return false
			}
		default:
			if !homeT && !awayT {
				return false
			}
		}
	}
	if f.Opponent != "" {
		// Opponent must be on the side opposite to Team.
		oppHome := matchesQuery(m.HomeKey, f.Opponent)
		oppAway := matchesQuery(m.AwayKey, f.Opponent)
		if f.Team == "" {
			return oppHome || oppAway
		}
		// team home -> opponent away, and vice versa
		if homeT && oppAway {
			return true
		}
		if awayT && oppHome {
			return true
		}
		return false
	}
	return true
}

// TeamStats aggregates a single team's record. Venue ("home"/"away"/"") narrows
// to matches where the team played at that venue.
func (s *Store) TeamStats(team string, f MatchFilter) TeamRecord {
	f.Team = team
	f.ScoredOnly = true
	rec := TeamRecord{
		Team:        s.canonicalTeamName(team),
		Season:      f.Season,
		Competition: f.Competition,
		Venue:       f.Venue,
	}
	for _, m := range s.Matches {
		if !f.keepBase(m) {
			continue
		}
		isHome := matchesQuery(m.HomeKey, team)
		isAway := matchesQuery(m.AwayKey, team)
		if !isHome && !isAway {
			continue
		}
		switch f.Venue {
		case "home":
			if !isHome {
				continue
			}
			isAway = false
		case "away":
			if !isAway {
				continue
			}
			isHome = false
		}
		// A team could in principle appear on both sides only via bad data; treat
		// as home in that case.
		gf, ga, won, lost := 0, 0, false, false
		if isHome {
			gf, ga = m.HomeGoal, m.AwayGoal
		} else {
			gf, ga = m.AwayGoal, m.HomeGoal
		}
		won = gf > ga
		lost = gf < ga
		rec.Matches++
		rec.GoalsFor += gf
		rec.GoalsAgst += ga
		switch {
		case won:
			rec.Wins++
		case lost:
			rec.Losses++
		default:
			rec.Draws++
		}
	}
	return rec
}

// HeadToHead returns the all-time (filtered) record between two teams.
func (s *Store) HeadToHead(teamA, teamB string, f MatchFilter) HeadToHead {
	h := HeadToHead{
		TeamA: s.canonicalTeamName(teamA),
		TeamB: s.canonicalTeamName(teamB),
	}
	f.ScoredOnly = true
	for _, m := range s.Matches {
		if !f.keepBase(m) {
			continue
		}
		aHome := matchesQuery(m.HomeKey, teamA)
		aAway := matchesQuery(m.AwayKey, teamA)
		bHome := matchesQuery(m.HomeKey, teamB)
		bAway := matchesQuery(m.AwayKey, teamB)
		var aGoals, bGoals int
		switch {
		case aHome && bAway:
			aGoals, bGoals = m.HomeGoal, m.AwayGoal
		case aAway && bHome:
			aGoals, bGoals = m.AwayGoal, m.HomeGoal
		default:
			continue
		}
		h.Matches = append(h.Matches, m)
		h.AGoals += aGoals
		h.BGoals += bGoals
		switch {
		case aGoals > bGoals:
			h.AWins++
		case bGoals > aGoals:
			h.BWins++
		default:
			h.Draws++
		}
	}
	sortMatchesByDateDesc(h.Matches)
	return h
}

// SearchPlayers returns players matching the filter, sorted by Overall desc.
func (s *Store) SearchPlayers(f PlayerFilter) []Player {
	nameQ := strings.ToLower(foldAccents(strings.TrimSpace(f.Name)))
	natQ := strings.ToLower(foldAccents(strings.TrimSpace(f.Nationality)))
	posQ := strings.ToLower(strings.TrimSpace(f.Position))

	var out []Player
	for _, p := range s.Players {
		if nameQ != "" && !strings.Contains(strings.ToLower(foldAccents(p.Name)), nameQ) {
			continue
		}
		if natQ != "" && !strings.Contains(strings.ToLower(foldAccents(p.Nationality)), natQ) {
			continue
		}
		if f.Club != "" && !matchesQuery(p.ClubKey, f.Club) {
			continue
		}
		if posQ != "" && !strings.Contains(strings.ToLower(p.Position), posQ) {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
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
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// Standings computes a league table for a competition/season from match
// results. Duplicate fixtures appearing in more than one source file are
// collapsed by (season, home, away) so points are not double counted.
func (s *Store) Standings(f MatchFilter) []TeamRecord {
	f.ScoredOnly = true
	type pairKey struct {
		season     int
		home, away string
	}
	seen := make(map[pairKey]bool)
	records := make(map[string]*TeamRecord)

	get := func(key, display string) *TeamRecord {
		r, ok := records[key]
		if !ok {
			r = &TeamRecord{Team: display, Season: f.Season, Competition: f.Competition}
			records[key] = r
		}
		return r
	}

	for _, m := range s.Matches {
		if !f.keepBase(m) {
			continue
		}
		pk := pairKey{m.Season, m.HomeKey, m.AwayKey}
		if seen[pk] {
			continue
		}
		seen[pk] = true

		home := get(m.HomeKey, m.HomeTeam)
		away := get(m.AwayKey, m.AwayTeam)
		home.Matches++
		away.Matches++
		home.GoalsFor += m.HomeGoal
		home.GoalsAgst += m.AwayGoal
		away.GoalsFor += m.AwayGoal
		away.GoalsAgst += m.HomeGoal
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

	table := make([]TeamRecord, 0, len(records))
	for _, r := range records {
		table = append(table, *r)
	}
	sort.SliceStable(table, func(i, j int) bool {
		if table[i].Points() != table[j].Points() {
			return table[i].Points() > table[j].Points()
		}
		if table[i].Wins != table[j].Wins {
			return table[i].Wins > table[j].Wins
		}
		if table[i].GoalDiff() != table[j].GoalDiff() {
			return table[i].GoalDiff() > table[j].GoalDiff()
		}
		if table[i].GoalsFor != table[j].GoalsFor {
			return table[i].GoalsFor > table[j].GoalsFor
		}
		return table[i].Team < table[j].Team
	})
	return table
}

// CompetitionStats computes aggregate statistics over the filtered matches.
func (s *Store) CompetitionStats(f MatchFilter) CompetitionSummary {
	f.ScoredOnly = true
	c := CompetitionSummary{Competition: f.Competition, Season: f.Season}
	for _, m := range s.Matches {
		if !f.keepBase(m) {
			continue
		}
		if !teamSideMatches(m, f) {
			continue
		}
		c.Matches++
		c.TotalGoals += m.HomeGoal + m.AwayGoal
		switch m.Winner() {
		case "home":
			c.HomeWins++
		case "away":
			c.AwayWins++
		default:
			c.Draws++
		}
	}
	return c
}

// BiggestWins returns the filtered scored matches with the largest goal margin,
// most decisive first.
func (s *Store) BiggestWins(f MatchFilter, limit int) []Match {
	f.ScoredOnly = true
	var out []Match
	for _, m := range s.Matches {
		if !f.keepBase(m) {
			continue
		}
		if !teamSideMatches(m, f) {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool {
		mi := abs(out[i].HomeGoal - out[i].AwayGoal)
		mj := abs(out[j].HomeGoal - out[j].AwayGoal)
		if mi != mj {
			return mi > mj
		}
		ti := out[i].HomeGoal + out[i].AwayGoal
		tj := out[j].HomeGoal + out[j].AwayGoal
		return ti > tj
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// canonicalTeamName returns the best display name we know for a query term.
func (s *Store) canonicalTeamName(query string) string {
	key := normKey(query)
	if n, ok := s.teamNames[key]; ok {
		return n
	}
	// Fall back to the cleaned input.
	display, _ := cleanTeamName(query)
	if display != "" {
		return display
	}
	return query
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
