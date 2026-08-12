package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

type Store struct {
	matches          []Match
	players          []Player
	teamNames        map[string]string
	preferredSources map[string]string
	matchIndexes     map[string][]int
}

type MatchFilter struct {
	Team, Opponent, HomeTeam, AwayTeam string
	Competition, Stage, Source         string
	Season                             int
	DateFrom, DateTo                   time.Time
	Limit                              int
}

func (s *Store) Matches(f MatchFilter) []Match {
	limit := f.Limit
	if limit <= 0 || limit > 200 {
		limit = 20
	}
	var found []Match
	seen := map[string]bool{}
	candidates := s.matches
	for _, query := range []string{f.Team, f.HomeTeam, f.AwayTeam, f.Opponent} {
		if indexes := s.matchIndexes[normalizeTeam(query)]; query != "" && len(indexes) > 0 {
			candidates = make([]Match, 0, len(indexes))
			for _, i := range indexes {
				candidates = append(candidates, s.matches[i])
			}
			break
		}
	}
	for _, m := range candidates {
		if f.Team != "" && !teamMatches(m.HomeTeam, f.Team) && !teamMatches(m.AwayTeam, f.Team) {
			continue
		}
		if f.Opponent != "" && !teamMatches(m.HomeTeam, f.Opponent) && !teamMatches(m.AwayTeam, f.Opponent) {
			continue
		}
		if f.HomeTeam != "" && !teamMatches(m.HomeTeam, f.HomeTeam) {
			continue
		}
		if f.AwayTeam != "" && !teamMatches(m.AwayTeam, f.AwayTeam) {
			continue
		}
		if !competitionMatches(m.Competition, f.Competition) || (f.Season != 0 && m.Season != f.Season) {
			continue
		}
		if f.Stage != "" && !strings.Contains(fold(m.Stage+" "+m.Round), fold(f.Stage)) {
			continue
		}
		if f.Source != "" && !strings.EqualFold(m.Source, f.Source) {
			continue
		}
		if !f.DateFrom.IsZero() && m.Date.Before(f.DateFrom) || !f.DateTo.IsZero() && m.Date.After(f.DateTo) {
			continue
		}
		key := matchKey(m)
		// A source filter asks for raw provenance. Other queries merge overlapping feeds.
		if f.Source == "" && seen[key] {
			continue
		}
		seen[key] = true
		found = append(found, m)
	}
	sort.Slice(found, func(i, j int) bool { return found[i].Date.After(found[j].Date) })
	if len(found) > limit {
		found = found[:limit]
	}
	return found
}

func matchKey(m Match) string {
	return fmt.Sprintf("%s|%s|%s|%d|%d|%s", m.Date.Format("2006-01-02"), normalizeTeam(m.HomeTeam), normalizeTeam(m.AwayTeam), m.HomeGoals, m.AwayGoals, fold(normalizeCompetition(m.Competition)))
}

func (s *Store) allFilteredMatches(team, competition, venue string, season int) []Match {
	var out []Match
	seen := map[string]bool{}
	for _, m := range s.matches {
		if m.ResultMissing {
			continue
		}
		if preferred := s.preferredSources[competitionSeasonKey(m)]; preferred != "" && m.Source != preferred {
			continue
		}
		isHome, isAway := teamMatches(m.HomeTeam, team), teamMatches(m.AwayTeam, team)
		if team != "" && !isHome && !isAway || venue == "home" && !isHome || venue == "away" && !isAway {
			continue
		}
		if season != 0 && m.Season != season || !competitionMatches(m.Competition, competition) {
			continue
		}
		key := matchKey(m)
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, m)
	}
	return out
}

func competitionSeasonKey(m Match) string {
	return fmt.Sprintf("%s|%d", fold(normalizeCompetition(m.Competition)), m.Season)
}

func (s *Store) TeamStatistics(team, competition, venue string, season int) TeamRecord {
	record := TeamRecord{Team: s.displayTeam(team)}
	for _, m := range s.allFilteredMatches(team, competition, venue, season) {
		home := teamMatches(m.HomeTeam, team)
		gf, ga := m.AwayGoals, m.HomeGoals
		if home {
			gf, ga = m.HomeGoals, m.AwayGoals
		}
		record.Matches++
		record.GoalsFor += gf
		record.GoalsAgainst += ga
		switch {
		case gf > ga:
			record.Wins++
			record.Points += 3
		case gf == ga:
			record.Draws++
			record.Points++
		default:
			record.Losses++
		}
	}
	record.GoalDiff = record.GoalsFor - record.GoalsAgainst
	if record.Matches > 0 {
		record.WinRate = round1(100 * float64(record.Wins) / float64(record.Matches))
	}
	return record
}

func (s *Store) HeadToHead(team1, team2, competition string, season int) map[string]any {
	matches := s.Matches(MatchFilter{Team: team1, Opponent: team2, Competition: competition, Season: season, Limit: 200})
	r1, r2, draws := 0, 0, 0
	for _, m := range matches {
		if m.HomeGoals == m.AwayGoals {
			draws++
		} else if (teamMatches(m.HomeTeam, team1) && m.HomeGoals > m.AwayGoals) || (teamMatches(m.AwayTeam, team1) && m.AwayGoals > m.HomeGoals) {
			r1++
		} else {
			r2++
		}
	}
	return map[string]any{"team_1": s.displayTeam(team1), "team_2": s.displayTeam(team2), "matches": len(matches), "team_1_wins": r1, "team_2_wins": r2, "draws": draws, "results": matches}
}

type PlayerFilter struct {
	Name, Nationality, Club, Position string
	MinOverall                        int
	Limit                             int
}

func (s *Store) Players(f PlayerFilter) []Player {
	limit := f.Limit
	if limit <= 0 || limit > 200 {
		limit = 20
	}
	var out []Player
	for _, p := range s.players {
		if f.Name != "" && !strings.Contains(fold(p.Name), fold(f.Name)) || f.Nationality != "" && !nationalityMatches(p.Nationality, f.Nationality) || f.Club != "" && !teamMatches(p.Club, f.Club) || f.Position != "" && !strings.Contains(fold(p.Position), fold(f.Position)) || p.Overall < f.MinOverall {
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

func (s *Store) Standings(competition string, season, limit int) []Standing {
	records := map[string]*TeamRecord{}
	for _, m := range s.allFilteredMatches("", competition, "", season) {
		for _, side := range []struct {
			name   string
			gf, ga int
		}{{m.HomeTeam, m.HomeGoals, m.AwayGoals}, {m.AwayTeam, m.AwayGoals, m.HomeGoals}} {
			key := normalizeTeam(side.name)
			r := records[key]
			if r == nil {
				r = &TeamRecord{Team: s.displayTeam(side.name)}
				records[key] = r
			}
			r.Matches++
			r.GoalsFor += side.gf
			r.GoalsAgainst += side.ga
			switch {
			case side.gf > side.ga:
				r.Wins++
				r.Points += 3
			case side.gf == side.ga:
				r.Draws++
				r.Points++
			default:
				r.Losses++
			}
		}
	}
	standing := make([]Standing, 0, len(records))
	for _, r := range records {
		r.GoalDiff = r.GoalsFor - r.GoalsAgainst
		if r.Matches > 0 {
			r.WinRate = round1(100 * float64(r.Wins) / float64(r.Matches))
		}
		standing = append(standing, Standing{TeamRecord: *r})
	}
	sort.Slice(standing, func(i, j int) bool {
		a, b := standing[i], standing[j]
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
	for i := range standing {
		standing[i].Position = i + 1
	}
	if limit <= 0 || limit > len(standing) {
		limit = len(standing)
	}
	return standing[:limit]
}

func (s *Store) CompetitionStatistics(competition string, season int) map[string]any {
	matches := s.allFilteredMatches("", competition, "", season)
	goals, homeWins, awayWins, draws := 0, 0, 0, 0
	teams := map[string]bool{}
	for _, m := range matches {
		goals += m.HomeGoals + m.AwayGoals
		teams[normalizeTeam(m.HomeTeam)] = true
		teams[normalizeTeam(m.AwayTeam)] = true
		switch {
		case m.HomeGoals > m.AwayGoals:
			homeWins++
		case m.HomeGoals < m.AwayGoals:
			awayWins++
		default:
			draws++
		}
	}
	avg, homeRate := 0.0, 0.0
	if len(matches) > 0 {
		avg = round2(float64(goals) / float64(len(matches)))
		homeRate = round1(100 * float64(homeWins) / float64(len(matches)))
	}
	return map[string]any{"competition": normalizeCompetition(competition), "season": season, "matches": len(matches), "teams": len(teams), "goals": goals, "goals_per_match": avg, "home_wins": homeWins, "away_wins": awayWins, "draws": draws, "home_win_rate_percent": homeRate}
}

func (s *Store) BiggestWins(team, competition string, season, limit int) []Match {
	matches := s.allFilteredMatches(team, competition, "", season)
	sort.Slice(matches, func(i, j int) bool {
		di := abs(matches[i].HomeGoals - matches[i].AwayGoals)
		dj := abs(matches[j].HomeGoals - matches[j].AwayGoals)
		if di == dj {
			return matches[i].Date.After(matches[j].Date)
		}
		return di > dj
	})
	if limit <= 0 {
		limit = 10
	}
	if limit > 100 {
		limit = 100
	}
	if len(matches) > limit {
		matches = matches[:limit]
	}
	return matches
}

func (s *Store) TeamProfile(team string, season int) map[string]any {
	competitionSet := map[string]bool{}
	for _, m := range s.allFilteredMatches(team, "", "", season) {
		competitionSet[m.Competition] = true
	}
	competitions := make([]string, 0, len(competitionSet))
	for c := range competitionSet {
		competitions = append(competitions, c)
	}
	sort.Strings(competitions)
	players := s.Players(PlayerFilter{Club: team, Limit: 100})
	return map[string]any{"team": s.displayTeam(team), "season": season, "record": s.TeamStatistics(team, "", "", season), "competitions": competitions, "players_in_fifa_dataset": players}
}

var derbyPairs = map[string]string{
	"botafogo|flamengo":         "Clássico da Rivalidade",
	"botafogo|fluminense":       "Clássico Vovô",
	"botafogo|vasco":            "Clássico da Amizade",
	"flamengo|fluminense":       "Fla-Flu",
	"flamengo|vasco":            "Clássico dos Milhões",
	"fluminense|vasco":          "Clássico dos Gigantes",
	"corinthians|palmeiras":     "Dérbi Paulista",
	"corinthians|santos":        "Clássico Alvinegro",
	"corinthians|sao paulo":     "Majestoso",
	"palmeiras|santos":          "Clássico da Saudade",
	"palmeiras|sao paulo":       "Choque-Rei",
	"santos|sao paulo":          "San-São",
	"gremio|internacional":      "Gre-Nal",
	"atletico mineiro|cruzeiro": "Clássico Mineiro",
	"athletico pr|coritiba":     "Atletiba",
	"bahia|vitoria":             "Ba-Vi",
	"ceara|fortaleza":           "Clássico-Rei",
	"goias|vila nova":           "Clássico Goiano",
	"nautico|sport":             "Clássico dos Clássicos",
	"santa cruz|sport":          "Clássico das Multidões",
}

func (s *Store) Derbies(season int, competition string, limit int) []DerbyResult {
	matches := s.allFilteredMatches("", competition, "", season)
	var out []DerbyResult
	for _, m := range matches {
		a, b := normalizeTeam(m.HomeTeam), normalizeTeam(m.AwayTeam)
		if a > b {
			a, b = b, a
		}
		if name := derbyPairs[a+"|"+b]; name != "" {
			out = append(out, DerbyResult{Derby: name, Match: m})
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	if limit <= 0 {
		limit = 20
	}
	if limit > 200 {
		limit = 200
	}
	if len(out) > limit {
		out = out[:limit]
	}
	return out
}

func (s *Store) displayTeam(team string) string {
	if n := s.teamNames[normalizeTeam(team)]; n != "" {
		return n
	}
	return strings.TrimSpace(team)
}

func round1(v float64) float64 { return float64(int(v*10+0.5)) / 10 }
func round2(v float64) float64 { return float64(int(v*100+0.5)) / 100 }
func abs(v int) int {
	if v < 0 {
		return -v
	}
	return v
}
