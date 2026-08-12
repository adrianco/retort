package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

func (db *Database) sort() {
	sort.SliceStable(db.Matches, func(i, j int) bool { return db.Matches[i].Date.After(db.Matches[j].Date) })
	sort.SliceStable(db.Players, func(i, j int) bool {
		if db.Players[i].Overall != db.Players[j].Overall {
			return db.Players[i].Overall > db.Players[j].Overall
		}
		return db.Players[i].Name < db.Players[j].Name
	})
}

func canonicalCompetition(s string) string {
	n := fold(s)
	switch {
	case strings.Contains(n, "libertadores"):
		return "libertadores"
	case strings.Contains(n, "copa do brasil"), strings.Contains(n, "brazilian cup"):
		return "copa do brasil"
	case strings.Contains(n, "brasileir"), n == "serie a", strings.Contains(n, "campeonato brasileiro"):
		return "serie a"
	case n == "serie b", n == "serie c":
		return n
	default:
		return n
	}
}

func competitionMatches(value, query string) bool {
	return query == "" || canonicalCompetition(value) == canonicalCompetition(query) || fuzzyText(value, query)
}

func matchKey(m Match) string {
	return fmt.Sprintf("%s|%s|%s|%s|%d|%d", m.Date.Format("2006-01-02"), canonicalCompetition(m.Competition), normalizeTeam(m.HomeTeam), normalizeTeam(m.AwayTeam), m.HomeGoals, m.AwayGoals)
}

func (db *Database) SearchMatches(f MatchFilter) []Match {
	limit := f.Limit
	if limit <= 0 {
		limit = 100
	}
	seen := make(map[string]struct{})
	finalRounds := map[int]int{}
	if strings.Contains(fold(f.Stage), "final") {
		for _, m := range db.Matches {
			if canonicalCompetition(m.Competition) != "copa do brasil" {
				continue
			}
			if round, ok := parseInt(m.Round); ok && round > finalRounds[m.Season] {
				finalRounds[m.Season] = round
			}
		}
	}
	result := make([]Match, 0, min(limit, 64))
	for _, m := range db.Matches {
		key := matchKey(m)
		if _, ok := seen[key]; ok {
			continue
		}
		seen[key] = struct{}{}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if !f.StartDate.IsZero() && m.Date.Before(f.StartDate) {
			continue
		}
		if !f.EndDate.IsZero() && m.Date.After(endOfDay(f.EndDate)) {
			continue
		}
		if f.Stage != "" && !fuzzyText(m.Stage+" "+m.Round, f.Stage) {
			isCupFinal := false
			if strings.Contains(fold(f.Stage), "final") && canonicalCompetition(m.Competition) == "copa do brasil" {
				round, ok := parseInt(m.Round)
				isCupFinal = ok && round == finalRounds[m.Season]
			}
			if !isCupFinal {
				continue
			}
		}
		if f.Team != "" {
			matchesHome, matchesAway := fuzzyEqual(m.HomeTeam, f.Team), fuzzyEqual(m.AwayTeam, f.Team)
			if f.HomeOnly && !matchesHome {
				continue
			}
			if f.AwayOnly && !matchesAway {
				continue
			}
			if !f.HomeOnly && !f.AwayOnly && !matchesHome && !matchesAway {
				continue
			}
			if f.Opponent != "" {
				if !(matchesHome && fuzzyEqual(m.AwayTeam, f.Opponent)) && !(matchesAway && fuzzyEqual(m.HomeTeam, f.Opponent)) {
					continue
				}
			}
		} else if f.Opponent != "" && !fuzzyEqual(m.HomeTeam, f.Opponent) && !fuzzyEqual(m.AwayTeam, f.Opponent) {
			continue
		}
		result = append(result, m)
		if len(result) >= limit {
			break
		}
	}
	return result
}

func endOfDay(t time.Time) time.Time {
	return time.Date(t.Year(), t.Month(), t.Day(), 23, 59, 59, int(time.Second-time.Nanosecond), t.Location())
}

func (db *Database) SearchPlayers(f PlayerFilter) []Player {
	limit := f.Limit
	if limit <= 0 {
		limit = 100
	}
	result := make([]Player, 0, min(limit, 64))
	for _, p := range db.Players {
		if !fuzzyText(p.Name, f.Name) || !nationalityMatches(p.Nationality, f.Nationality) || !fuzzyText(p.Club, f.Club) || !positionMatches(p.Position, f.Position) || p.Overall < f.MinOverall {
			continue
		}
		result = append(result, p)
		if len(result) >= limit {
			break
		}
	}
	return result
}

func nationalityMatches(value, query string) bool {
	q := fold(query)
	if q == "" {
		return true
	}
	if q == "brasil" || q == "brazilian" || q == "brasileiro" || q == "brasileira" {
		q = "brazil"
	}
	return strings.Contains(fold(value), q)
}

func positionMatches(value, query string) bool {
	q := fold(query)
	if q == "" {
		return true
	}
	v := fold(value)
	switch q {
	case "forward", "forwards", "attacker", "attackers":
		return strings.Contains(" st cf lf rf lw rw ", " "+v+" ")
	case "midfielder", "midfielders":
		return strings.Contains(" cm cdm cam lm rm lcm rcm lam ram ", " "+v+" ")
	case "defender", "defenders":
		return strings.Contains(" cb lb rb lcb rcb lwb rwb ", " "+v+" ")
	case "goalkeeper", "goalkeepers", "keeper", "keepers":
		return v == "gk"
	default:
		return strings.Contains(v, q)
	}
}

func (db *Database) TeamStatistics(team string, filter MatchFilter) TeamStats {
	filter.Team = team
	filter.Limit = len(db.Matches) + 1
	matches := db.analyticalMatches(filter)
	stats := TeamStats{Team: cleanTeamName(team), Competition: filter.Competition, Season: filter.Season}
	for _, m := range matches {
		home := fuzzyEqual(m.HomeTeam, team)
		stats.Matches++
		gf, ga := m.AwayGoals, m.HomeGoals
		if home {
			gf, ga = m.HomeGoals, m.AwayGoals
			stats.HomeMatches++
		} else {
			stats.AwayMatches++
		}
		stats.GoalsFor += gf
		stats.GoalsAgainst += ga
		switch {
		case gf > ga:
			stats.Wins++
			stats.Points += 3
			if home {
				stats.HomeWins++
			} else {
				stats.AwayWins++
			}
		case gf == ga:
			stats.Draws++
			stats.Points++
		default:
			stats.Losses++
		}
	}
	if stats.Matches > 0 {
		stats.WinRate = round1(float64(stats.Wins) * 100 / float64(stats.Matches))
	}
	return stats
}

func (db *Database) HeadToHead(team1, team2 string, filter MatchFilter) HeadToHead {
	filter.Team, filter.Opponent = team1, team2
	if filter.Limit <= 0 {
		filter.Limit = len(db.Matches) + 1
	}
	result := HeadToHead{Team1: cleanTeamName(team1), Team2: cleanTeamName(team2), Results: db.analyticalMatches(filter)}
	result.Matches = len(result.Results)
	for _, m := range result.Results {
		oneHome := fuzzyEqual(m.HomeTeam, team1)
		g1, g2 := m.AwayGoals, m.HomeGoals
		if oneHome {
			g1, g2 = m.HomeGoals, m.AwayGoals
		}
		result.Goals1 += g1
		result.Goals2 += g2
		if g1 > g2 {
			result.Team1Wins++
		} else if g2 > g1 {
			result.Team2Wins++
		} else {
			result.Draws++
		}
	}
	return result
}

func (db *Database) Standings(competition string, season int) []Standing {
	matches := db.analyticalMatches(MatchFilter{Competition: competition, Season: season, Limit: len(db.Matches) + 1})
	table := map[string]*Standing{}
	display := map[string]string{}
	for _, m := range matches {
		hk, ak := normalizeTeam(m.HomeTeam), normalizeTeam(m.AwayTeam)
		if hk == "" || ak == "" {
			continue
		}
		display[hk], display[ak] = displayTeam(m.HomeTeam), displayTeam(m.AwayTeam)
		if table[hk] == nil {
			table[hk] = &Standing{Team: display[hk]}
		}
		if table[ak] == nil {
			table[ak] = &Standing{Team: display[ak]}
		}
		h, a := table[hk], table[ak]
		h.Played++
		a.Played++
		h.GoalsFor += m.HomeGoals
		h.GoalsAgainst += m.AwayGoals
		a.GoalsFor += m.AwayGoals
		a.GoalsAgainst += m.HomeGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			h.Wins++
			h.Points += 3
			a.Losses++
		case m.HomeGoals < m.AwayGoals:
			a.Wins++
			a.Points += 3
			h.Losses++
		default:
			h.Draws++
			a.Draws++
			h.Points++
			a.Points++
		}
	}
	result := make([]Standing, 0, len(table))
	for _, s := range table {
		s.GoalDiff = s.GoalsFor - s.GoalsAgainst
		result = append(result, *s)
	}
	sort.Slice(result, func(i, j int) bool {
		a, b := result[i], result[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDiff != b.GoalDiff {
			return a.GoalDiff > b.GoalDiff
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	for i := range result {
		result[i].Position = i + 1
	}
	return result
}

func (db *Database) AggregateStats(filter MatchFilter) CompetitionStats {
	filter.Limit = len(db.Matches) + 1
	matches := db.analyticalMatches(filter)
	stats := CompetitionStats{Competition: filter.Competition, Season: filter.Season, Matches: len(matches)}
	for _, m := range matches {
		stats.Goals += m.HomeGoals + m.AwayGoals
		if m.HomeGoals > m.AwayGoals {
			stats.HomeWins++
		} else if m.HomeGoals < m.AwayGoals {
			stats.AwayWins++
		} else {
			stats.Draws++
		}
	}
	if stats.Matches > 0 {
		n := float64(stats.Matches)
		stats.GoalsPerMatch = round2(float64(stats.Goals) / n)
		stats.HomeWinRate = round1(float64(stats.HomeWins) * 100 / n)
		stats.AwayWinRate = round1(float64(stats.AwayWins) * 100 / n)
		stats.DrawRate = round1(float64(stats.Draws) * 100 / n)
	}
	return stats
}

func (db *Database) BiggestWins(filter MatchFilter, limit int) []Match {
	filter.Limit = len(db.Matches) + 1
	result := db.SearchMatches(filter)
	sort.SliceStable(result, func(i, j int) bool {
		di, dj := abs(result[i].HomeGoals-result[i].AwayGoals), abs(result[j].HomeGoals-result[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		return result[i].Date.After(result[j].Date)
	})
	if limit <= 0 {
		limit = 10
	}
	if len(result) > limit {
		result = result[:limit]
	}
	return result
}

func (db *Database) CompetitionsForTeam(team string) []string {
	matches := db.SearchMatches(MatchFilter{Team: team, Limit: len(db.Matches) + 1})
	seen := map[string]string{}
	for _, m := range matches {
		seen[canonicalCompetition(m.Competition)] = m.Competition
	}
	result := make([]string, 0, len(seen))
	for _, name := range seen {
		result = append(result, name)
	}
	sort.Strings(result)
	return result
}

// analyticalMatches selects one authoritative source for each competition and
// season. Several supplied CSVs overlap; mixing them would double-count games
// and produce impossible tables. SearchMatches deliberately remains a union so
// every source is queryable, while all calculations use this canonical view.
func (db *Database) analyticalMatches(filter MatchFilter) []Match {
	all := db.SearchMatches(filter)
	best := make(map[string]int)
	for _, m := range all {
		group := fmt.Sprintf("%s|%d", canonicalCompetition(m.Competition), m.Season)
		p := sourcePriority(m)
		if current, ok := best[group]; !ok || p < current {
			best[group] = p
		}
	}
	result := make([]Match, 0, len(all))
	for _, m := range all {
		group := fmt.Sprintf("%s|%d", canonicalCompetition(m.Competition), m.Season)
		if sourcePriority(m) == best[group] {
			result = append(result, m)
		}
	}
	return result
}

func sourcePriority(m Match) int {
	switch canonicalCompetition(m.Competition) {
	case "serie a":
		switch m.Source {
		case "Brasileirao_Matches.csv":
			return 0
		case "novo_campeonato_brasileiro.csv":
			return 1
		default:
			return 2
		}
	case "copa do brasil":
		if m.Source == "Brazilian_Cup_Matches.csv" {
			return 0
		}
		return 1
	case "libertadores":
		if m.Source == "Libertadores_Matches.csv" {
			return 0
		}
		return 1
	default:
		return 0
	}
}

func round1(v float64) float64 { return float64(int(v*10+0.5)) / 10 }
func round2(v float64) float64 { return float64(int(v*100+0.5)) / 100 }
func abs(v int) int {
	if v < 0 {
		return -v
	}
	return v
}
