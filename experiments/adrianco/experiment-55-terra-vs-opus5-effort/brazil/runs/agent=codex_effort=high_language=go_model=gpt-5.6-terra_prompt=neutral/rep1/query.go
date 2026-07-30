package main

import (
	"fmt"
	"sort"
	"strings"
	"unicode"
)

type MatchFilter struct {
	Team, Opponent, Competition, Source, DateFrom, DateTo string
	Season, Limit                                         int
}
type PlayerFilter struct {
	Name, Nationality, Club, Position string
	MinOverall, Limit                 int
}
type TeamStats struct {
	Team                                                 string
	Matches, Wins, Draws, Losses, GoalsFor, GoalsAgainst int
}
type Standing struct {
	Team                                                        string
	Played, Wins, Draws, Losses, GoalsFor, GoalsAgainst, Points int
}
type RankedTeam struct {
	TeamStats
	WinRate float64
}

func canonical(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	var b strings.Builder
	for _, r := range s {
		switch r {
		case 'á', 'à', 'ã', 'â', 'ä':
			r = 'a'
		case 'é', 'è', 'ê', 'ë':
			r = 'e'
		case 'í', 'ì', 'î', 'ï':
			r = 'i'
		case 'ó', 'ò', 'õ', 'ô', 'ö':
			r = 'o'
		case 'ú', 'ù', 'û', 'ü':
			r = 'u'
		case 'ç':
			r = 'c'
		case 'ñ':
			r = 'n'
		}
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
		} else {
			b.WriteByte(' ')
		}
	}
	f := strings.Fields(b.String())
	// A few clubs cannot safely lose their state suffix: Atlético-MG and
	// Atlético-GO are different teams, for example.
	withState := strings.Join(f, " ")
	stateAliases := map[string]string{
		"atletico mg": "atletico mineiro", "atletico go": "atletico goianiense",
		"america mg": "america mineiro", "america rn": "america natal",
	}
	if v, ok := stateAliases[withState]; ok {
		return v
	}
	// Dataset state suffixes are identifiers, not part of the club name.
	if len(f) > 1 && len(f[len(f)-1]) == 2 {
		f = f[:len(f)-1]
	}
	for len(f) > 1 && (f[len(f)-1] == "fc" || f[len(f)-1] == "futebol" || f[len(f)-1] == "clube") {
		f = f[:len(f)-1]
	}
	k := strings.Join(f, " ")
	aliases := map[string]string{"sport club corinthians paulista": "corinthians", "sao paulo futebol clube": "sao paulo", "sociedade esportiva palmeiras": "palmeiras", "santos futebol clube": "santos", "clube de regatas flamengo": "flamengo", "clube de regatas do flamengo": "flamengo", "cr flamengo": "flamengo", "fluminense football club": "fluminense", "gremio fbpa": "gremio", "clube atletico mineiro": "atletico mineiro", "clube de regatas vasco da gama": "vasco", "vasco da gama": "vasco", "athletico paranaense": "atletico paranaense"}
	if v, ok := aliases[k]; ok {
		return v
	}
	return k
}
func containsName(value, wanted string) bool {
	v, w := canonical(value), canonical(wanted)
	return w == "" || v == w || strings.Contains(v, w)
}
func competitionMatches(value, wanted string) bool {
	return wanted == "" || containsName(value, wanted) || (canonical(wanted) == "brasileirao" && canonical(value) == "serie a") || (canonical(wanted) == "libertadores" && strings.Contains(canonical(value), "libertadores"))
}

func (r *Repository) SearchMatches(f MatchFilter) []Match {
	limit := f.Limit
	if limit == 0 {
		limit = 100
	}
	if limit > 500 {
		limit = 500
	}
	from, to := parseDate(f.DateFrom), parseDate(f.DateTo)
	result := make([]Match, 0)
	for _, m := range r.Matches {
		if f.Team != "" && !containsName(m.Home, f.Team) && !containsName(m.Away, f.Team) {
			continue
		}
		if f.Opponent != "" && !containsName(m.Home, f.Opponent) && !containsName(m.Away, f.Opponent) {
			continue
		}
		if f.Team != "" && f.Opponent != "" && !((containsName(m.Home, f.Team) && containsName(m.Away, f.Opponent)) || (containsName(m.Home, f.Opponent) && containsName(m.Away, f.Team))) {
			continue
		}
		if !competitionMatches(m.Competition, f.Competition) || !containsName(m.Source, f.Source) || (f.Season != 0 && m.Season != f.Season) || (!from.IsZero() && m.Date.Before(from)) || (!to.IsZero() && m.Date.After(to.AddDate(0, 0, 1))) {
			continue
		}
		result = append(result, m)
	}
	sort.SliceStable(result, func(i, j int) bool { return result[i].Date.After(result[j].Date) })
	// The supplied CSVs overlap. Cross-source searches and calculations should
	// represent a fixture once; callers can use Source to inspect raw rows.
	if f.Source == "" {
		seen := make(map[string]bool, len(result))
		unique := make([]Match, 0, len(result))
		for _, m := range result {
			comp := canonical(m.Competition)
			if comp == "serie a" {
				comp = "brasileirao"
			}
			key := strings.Join([]string{m.Date.Format("2006-01-02"), comp, canonical(m.Home), canonical(m.Away), fmt.Sprint(m.HomeGoals), fmt.Sprint(m.AwayGoals)}, "|")
			if !seen[key] {
				seen[key] = true
				unique = append(unique, m)
			}
		}
		result = unique
	}
	if limit > 0 && len(result) > limit {
		result = result[:limit]
	}
	return result
}

// analyticalMatches selects the canonical dataset for competitions that occur
// in more than one supplied file. This prevents a table from counting the same
// season two or three times. search_matches remains available with source for
// inspecting every raw dataset.
func (r *Repository) analyticalMatches(f MatchFilter) []Match {
	competition := canonical(f.Competition)
	var preferred []string
	switch competition {
	case "brasileirao":
		preferred = []string{"Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"}
	case "copa do brasil":
		preferred = []string{"Brazilian_Cup_Matches.csv", "BR-Football-Dataset.csv"}
	case "copa libertadores", "libertadores":
		preferred = []string{"Libertadores_Matches.csv"}
	default:
		return r.SearchMatches(f)
	}
	for _, source := range preferred {
		candidate := f
		candidate.Source = source
		candidate.Limit = -1
		if matches := r.SearchMatches(candidate); len(matches) > 0 {
			return matches
		}
	}
	return nil
}

func addResult(s *TeamStats, gf, ga int) {
	s.Matches++
	s.GoalsFor += gf
	s.GoalsAgainst += ga
	if gf > ga {
		s.Wins++
	} else if gf == ga {
		s.Draws++
	} else {
		s.Losses++
	}
}
func (r *Repository) TeamStatistics(team, competition string, season int, homeOnly bool) TeamStats {
	s := TeamStats{Team: team}
	for _, m := range r.analyticalMatches(MatchFilter{Team: team, Competition: competition, Season: season, Limit: -1}) {
		if containsName(m.Home, team) {
			addResult(&s, m.HomeGoals, m.AwayGoals)
		} else if !homeOnly && containsName(m.Away, team) {
			addResult(&s, m.AwayGoals, m.HomeGoals)
		}
	}
	return s
}
func (r *Repository) HeadToHead(a, b, competition string, season int) (TeamStats, TeamStats, []Match) {
	ms := r.analyticalMatches(MatchFilter{Team: a, Opponent: b, Competition: competition, Season: season, Limit: -1})
	as, bs := TeamStats{Team: a}, TeamStats{Team: b}
	for _, m := range ms {
		if containsName(m.Home, a) {
			addResult(&as, m.HomeGoals, m.AwayGoals)
			addResult(&bs, m.AwayGoals, m.HomeGoals)
		} else {
			addResult(&as, m.AwayGoals, m.HomeGoals)
			addResult(&bs, m.HomeGoals, m.AwayGoals)
		}
	}
	return as, bs, ms
}
func (r *Repository) SearchPlayers(f PlayerFilter) []Player {
	limit := f.Limit
	if limit <= 0 || limit > 500 {
		limit = 50
	}
	out := make([]Player, 0)
	for _, p := range r.Players {
		if !containsName(p.Name, f.Name) || !containsName(p.Nationality, f.Nationality) || !containsName(p.Club, f.Club) || !containsName(p.Position, f.Position) || p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall == out[j].Overall {
			return out[i].Name < out[j].Name
		}
		return out[i].Overall > out[j].Overall
	})
	if len(out) > limit {
		out = out[:limit]
	}
	return out
}
func (r *Repository) Standings(competition string, season int) []Standing {
	by := map[string]*Standing{}
	display := map[string]string{}
	for _, m := range r.analyticalMatches(MatchFilter{Competition: competition, Season: season, Limit: -1}) {
		for _, x := range []struct {
			name   string
			gf, ga int
		}{{m.Home, m.HomeGoals, m.AwayGoals}, {m.Away, m.AwayGoals, m.HomeGoals}} {
			k := canonical(x.name)
			if by[k] == nil {
				by[k] = &Standing{}
				display[k] = x.name
			}
			s := by[k]
			s.Played++
			s.GoalsFor += x.gf
			s.GoalsAgainst += x.ga
			if x.gf > x.ga {
				s.Wins++
				s.Points += 3
			} else if x.gf == x.ga {
				s.Draws++
				s.Points++
			} else {
				s.Losses++
			}
		}
	}
	out := make([]Standing, 0, len(by))
	for k, s := range by {
		s.Team = display[k]
		out = append(out, *s)
	}
	sort.Slice(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.GoalsFor-a.GoalsAgainst != b.GoalsFor-b.GoalsAgainst {
			return a.GoalsFor-a.GoalsAgainst > b.GoalsFor-b.GoalsAgainst
		}
		return a.GoalsFor > b.GoalsFor
	})
	return out
}
func (r *Repository) Summary(competition string, season int) (matches, goals, homeWins, draws int) {
	for _, m := range r.analyticalMatches(MatchFilter{Competition: competition, Season: season, Limit: -1}) {
		matches++
		goals += m.HomeGoals + m.AwayGoals
		if m.HomeGoals > m.AwayGoals {
			homeWins++
		} else if m.HomeGoals == m.AwayGoals {
			draws++
		}
	}
	return
}
func (r *Repository) RankTeams(competition string, season int, venue string) []RankedTeam {
	stats := map[string]*TeamStats{}
	for _, m := range r.analyticalMatches(MatchFilter{Competition: competition, Season: season, Limit: -1}) {
		if venue != "away" {
			key := canonical(m.Home)
			if stats[key] == nil {
				stats[key] = &TeamStats{Team: m.Home}
			}
			addResult(stats[key], m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			key := canonical(m.Away)
			if stats[key] == nil {
				stats[key] = &TeamStats{Team: m.Away}
			}
			addResult(stats[key], m.AwayGoals, m.HomeGoals)
		}
	}
	out := make([]RankedTeam, 0, len(stats))
	for _, s := range stats {
		rate := 0.0
		if s.Matches > 0 {
			rate = 100 * float64(s.Wins) / float64(s.Matches)
		}
		out = append(out, RankedTeam{TeamStats: *s, WinRate: rate})
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].WinRate != out[j].WinRate {
			return out[i].WinRate > out[j].WinRate
		}
		if out[i].Points() != out[j].Points() {
			return out[i].Points() > out[j].Points()
		}
		return out[i].GoalsFor-out[i].GoalsAgainst > out[j].GoalsFor-out[j].GoalsAgainst
	})
	return out
}
func (s TeamStats) Points() int { return 3*s.Wins + s.Draws }
func (r *Repository) BiggestWins(competition string, season, limit int) []Match {
	ms := r.analyticalMatches(MatchFilter{Competition: competition, Season: season, Limit: -1})
	sort.SliceStable(ms, func(i, j int) bool {
		mi := abs(ms[i].HomeGoals - ms[i].AwayGoals)
		mj := abs(ms[j].HomeGoals - ms[j].AwayGoals)
		if mi != mj {
			return mi > mj
		}
		return ms[i].Date.After(ms[j].Date)
	})
	if limit <= 0 {
		limit = 10
	}
	if len(ms) > limit {
		ms = ms[:limit]
	}
	return ms
}
func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
func formatMatch(m Match) string {
	date := "unknown date"
	if !m.Date.IsZero() {
		date = m.Date.Format("2006-01-02")
	}
	extra := ""
	if m.Round != "" {
		extra = " Round " + m.Round
	} else if m.Stage != "" {
		extra = " " + m.Stage
	}
	return fmt.Sprintf("- %s: %s %d-%d %s (%s%s)", date, m.Home, m.HomeGoals, m.AwayGoals, m.Away, m.Competition, extra)
}
