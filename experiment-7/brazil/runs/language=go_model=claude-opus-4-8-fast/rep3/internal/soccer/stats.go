// stats.go - aggregate statistical analysis over the match corpus.
//
// Context
// -------
// Implements the "Statistical Analysis" capability area: average goals per
// match, home-win rates, biggest victories, and best home/away records, plus
// small introspection helpers (available competitions, season ranges) used to
// make the dataset discoverable through the MCP tools.
package soccer

import "sort"

// GoalStats summarises scoring across a filtered set of matches.
type GoalStats struct {
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
	AvgGoals    float64
	HomeWinRate float64
	AwayWinRate float64
	DrawRate    float64
}

// GoalStatistics aggregates scoring metrics for the matches passing the filter.
// Only scored matches are considered.
func (db *DB) GoalStatistics(f MatchFilter) GoalStats {
	f.OnlyScored = true
	var gs GoalStats
	for _, m := range db.Matches {
		if !matchPasses(m, f) {
			continue
		}
		gs.Matches++
		gs.TotalGoals += m.TotalGoals()
		switch m.Winner() {
		case "home":
			gs.HomeWins++
		case "away":
			gs.AwayWins++
		default:
			gs.Draws++
		}
	}
	if gs.Matches > 0 {
		gs.AvgGoals = float64(gs.TotalGoals) / float64(gs.Matches)
		gs.HomeWinRate = float64(gs.HomeWins) / float64(gs.Matches)
		gs.AwayWinRate = float64(gs.AwayWins) / float64(gs.Matches)
		gs.DrawRate = float64(gs.Draws) / float64(gs.Matches)
	}
	return gs
}

// BiggestWins returns up to limit scored matches with the largest goal margin,
// ordered by margin descending (ties broken by total goals then date).
func (db *DB) BiggestWins(f MatchFilter, limit int) []*Match {
	f.OnlyScored = true
	var out []*Match
	for _, m := range db.Matches {
		if !matchPasses(m, f) {
			continue
		}
		if m.HomeGoals == m.AwayGoals {
			continue
		}
		out = append(out, m)
	}
	sort.SliceStable(out, func(i, j int) bool {
		mi, mj := out[i], out[j]
		gi := abs(mi.HomeGoals - mi.AwayGoals)
		gj := abs(mj.HomeGoals - mj.AwayGoals)
		if gi != gj {
			return gi > gj
		}
		if mi.TotalGoals() != mj.TotalGoals() {
			return mi.TotalGoals() > mj.TotalGoals()
		}
		if mi.HasDate && mj.HasDate {
			return mi.Date.After(mj.Date)
		}
		return false
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// TeamRecords computes per-team aggregates across the filtered matches and
// returns them. venue may be "home", "away" or "all".
func (db *DB) TeamRecords(competition string, season int, venue string) []TeamStats {
	agg := map[string]*TeamStats{}
	order := []string{}
	add := func(name string, gf, ga int) {
		key := MatchKey(name)
		s, ok := agg[key]
		if !ok {
			s = &TeamStats{Team: name, Season: season, Competition: competition, Venue: venue}
			agg[key] = s
			order = append(order, key)
		}
		s.Played++
		s.GoalsFor += gf
		s.GoalsAgainst += ga
		switch {
		case gf > ga:
			s.Wins++
		case ga > gf:
			s.Losses++
		default:
			s.Draws++
		}
	}
	for _, m := range db.Matches {
		if !m.HasScore {
			continue
		}
		if competition != "" && m.Competition != competition {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if venue != "away" {
			add(m.HomeTeam, m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			add(m.AwayTeam, m.AwayGoals, m.HomeGoals)
		}
	}
	out := make([]TeamStats, 0, len(agg))
	for _, k := range order {
		out = append(out, *agg[k])
	}
	return out
}

// BestRecords returns teams sorted by win rate (descending) among those with at
// least minPlayed matches. venue may be "home", "away" or "all".
func (db *DB) BestRecords(competition string, season int, venue string, minPlayed, limit int) []TeamStats {
	recs := db.TeamRecords(competition, season, venue)
	filtered := recs[:0]
	for _, r := range recs {
		if r.Played >= minPlayed {
			filtered = append(filtered, r)
		}
	}
	sort.SliceStable(filtered, func(i, j int) bool {
		if filtered[i].WinRate() != filtered[j].WinRate() {
			return filtered[i].WinRate() > filtered[j].WinRate()
		}
		if filtered[i].Wins != filtered[j].Wins {
			return filtered[i].Wins > filtered[j].Wins
		}
		return filtered[i].GoalDiff() > filtered[j].GoalDiff()
	})
	if limit > 0 && len(filtered) > limit {
		filtered = filtered[:limit]
	}
	return filtered
}

// TopScoringTeams returns teams ranked by goals scored (descending).
func (db *DB) TopScoringTeams(competition string, season int, limit int) []TeamStats {
	recs := db.TeamRecords(competition, season, "all")
	sort.SliceStable(recs, func(i, j int) bool {
		if recs[i].GoalsFor != recs[j].GoalsFor {
			return recs[i].GoalsFor > recs[j].GoalsFor
		}
		return recs[i].GoalDiff() > recs[j].GoalDiff()
	})
	if limit > 0 && len(recs) > limit {
		recs = recs[:limit]
	}
	return recs
}

// CompetitionInfo summarises one competition's coverage in the dataset.
type CompetitionInfo struct {
	Key       string
	Name      string
	Matches   int
	MinSeason int
	MaxSeason int
}

// Competitions returns coverage information for every competition present,
// ordered by match count descending.
func (db *DB) Competitions() []CompetitionInfo {
	agg := map[string]*CompetitionInfo{}
	for _, m := range db.Matches {
		info, ok := agg[m.Competition]
		if !ok {
			info = &CompetitionInfo{Key: m.Competition, Name: CompetitionName(m.Competition)}
			agg[m.Competition] = info
		}
		info.Matches++
		if m.Season != 0 {
			if info.MinSeason == 0 || m.Season < info.MinSeason {
				info.MinSeason = m.Season
			}
			if m.Season > info.MaxSeason {
				info.MaxSeason = m.Season
			}
		}
	}
	out := make([]CompetitionInfo, 0, len(agg))
	for _, info := range agg {
		out = append(out, *info)
	}
	sort.SliceStable(out, func(i, j int) bool {
		return out[i].Matches > out[j].Matches
	})
	return out
}

// Seasons returns the sorted list of distinct seasons for a competition (or all
// competitions when competition is "").
func (db *DB) Seasons(competition string) []int {
	seen := map[int]bool{}
	for _, m := range db.Matches {
		if competition != "" && m.Competition != competition {
			continue
		}
		if m.Season != 0 {
			seen[m.Season] = true
		}
	}
	out := make([]int, 0, len(seen))
	for s := range seen {
		out = append(out, s)
	}
	sort.Ints(out)
	return out
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
