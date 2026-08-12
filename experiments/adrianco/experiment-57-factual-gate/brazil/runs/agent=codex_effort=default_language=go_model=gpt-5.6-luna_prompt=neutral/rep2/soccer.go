package main

import (
	"encoding/csv"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

type Match struct {
	Competition, Home, Away, Round, Stage, Date string
	Season, HomeGoals, AwayGoals                int
}

type Player struct {
	ID, Name, Nationality, Club, Position string
	Age, Overall, Potential               int
}

type Store struct {
	Matches []Match
	Players []Player
}

func LoadStore(dir string) (*Store, error) {
	s := &Store{}
	loaders := []struct{ file, competition string }{
		{"Brasileirao_Matches.csv", "Brasileirão"}, {"Brazilian_Cup_Matches.csv", "Copa do Brasil"}, {"Libertadores_Matches.csv", "Copa Libertadores"},
	}
	for _, l := range loaders {
		if err := loadMatchCSV(filepath.Join(dir, l.file), l.competition, &s.Matches); err != nil {
			return nil, err
		}
	}
	if err := loadExtended(filepath.Join(dir, "BR-Football-Dataset.csv"), &s.Matches); err != nil {
		return nil, err
	}
	if err := loadHistorical(filepath.Join(dir, "novo_campeonato_brasileiro.csv"), &s.Matches); err != nil {
		return nil, err
	}
	if err := loadPlayers(filepath.Join(dir, "fifa_data.csv"), &s.Players); err != nil {
		return nil, err
	}
	s.Matches = deduplicateMatches(s.Matches)
	return s, nil
}

func csvRows(path string) ([]map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.FieldsPerRecord = -1
	head, err := r.Read()
	if err != nil {
		return nil, err
	}
	for i := range head {
		head[i] = strings.TrimPrefix(strings.TrimSpace(head[i]), "\ufeff")
	}
	var out []map[string]string
	for {
		row, e := r.Read()
		if errors.Is(e, io.EOF) {
			break
		}
		if e != nil {
			return nil, fmt.Errorf("read %s: %w", path, e)
		}
		m := map[string]string{}
		for i, k := range head {
			if i < len(row) {
				m[k] = strings.TrimSpace(row[i])
			}
		}
		out = append(out, m)
	}
	return out, nil
}
func atoi(s string) int { n, _ := strconv.Atoi(strings.TrimSpace(strings.Split(s, ".")[0])); return n }
func dateOnly(s string) string {
	if t, e := time.Parse("2006-01-02 15:04:05", s); e == nil {
		return t.Format("2006-01-02")
	}
	if t, e := time.Parse("02/01/2006", s); e == nil {
		return t.Format("2006-01-02")
	}
	return s
}

func canonicalCompetition(s string) string {
	k := norm(s)
	switch {
	case strings.Contains(k, "copa do brasil"):
		return "Copa do Brasil"
	case strings.Contains(k, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(k, "brasileirao"), strings.Contains(k, "brasileiro"):
		return "Brasileirão"
	default:
		return strings.TrimSpace(s)
	}
}

func deduplicateMatches(matches []Match) []Match {
	seen := make(map[string]bool, len(matches))
	out := make([]Match, 0, len(matches))
	for _, m := range matches {
		m.Competition = canonicalCompetition(m.Competition)
		if m.Season == 0 && len(m.Date) >= 4 {
			m.Season = atoi(m.Date[:4])
		}
		// The extended and historical files overlap the competition-specific
		// files. Team keys deliberately ignore state suffixes and accents here.
		key := fmt.Sprintf("%s|%d|%s|%s|%d-%d", m.Competition, m.Season, norm(m.Home), norm(m.Away), m.HomeGoals, m.AwayGoals)
		if m.Date != "" {
			key += "|" + m.Date
		}
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, m)
	}
	return out
}
func loadMatchCSV(path, comp string, dst *[]Match) error {
	rows, err := csvRows(path)
	if err != nil {
		return err
	}
	for _, r := range rows {
		*dst = append(*dst, Match{Competition: comp, Home: r["home_team"], Away: r["away_team"], Date: dateOnly(r["datetime"]), Season: atoi(r["season"]), Round: r["round"], Stage: r["stage"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"])})
	}
	return nil
}
func loadExtended(path string, dst *[]Match) error {
	rows, err := csvRows(path)
	if err != nil {
		return err
	}
	for _, r := range rows {
		*dst = append(*dst, Match{Competition: r["tournament"], Home: r["home"], Away: r["away"], Date: dateOnly(r["date"]), HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"])})
	}
	return nil
}
func loadHistorical(path string, dst *[]Match) error {
	rows, err := csvRows(path)
	if err != nil {
		return err
	}
	for _, r := range rows {
		*dst = append(*dst, Match{Competition: "Brasileirão", Home: r["Equipe_mandante"], Away: r["Equipe_visitante"], Date: dateOnly(r["Data"]), Season: atoi(r["Ano"]), Round: r["Rodada"], HomeGoals: atoi(r["Gols_mandante"]), AwayGoals: atoi(r["Gols_visitante"])})
	}
	return nil
}
func loadPlayers(path string, dst *[]Player) error {
	rows, err := csvRows(path)
	if err != nil {
		return err
	}
	for _, r := range rows {
		*dst = append(*dst, Player{ID: r["ID"], Name: r["Name"], Nationality: r["Nationality"], Club: r["Club"], Position: r["Position"], Age: atoi(r["Age"]), Overall: atoi(r["Overall"]), Potential: atoi(r["Potential"])})
	}
	return nil
}

func norm(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	s = strings.NewReplacer("á", "a", "à", "a", "ã", "a", "â", "a", "é", "e", "ê", "e", "í", "i", "ó", "o", "ô", "o", "õ", "o", "ú", "u", "ç", "c").Replace(s)
	if i := strings.LastIndexByte(s, '-'); i >= 0 && len(s)-i-1 == 2 {
		s = s[:i]
	}
	s = strings.Join(strings.Fields(s), " ")
	return strings.ReplaceAll(s, "atletico", "athletico")
}
func contains(a, b string) bool { return b == "" || strings.Contains(norm(a), norm(b)) }
func (s *Store) SearchMatches(team, competition, from, to string, season, limit int) []Match {
	var out []Match
	for _, m := range s.Matches {
		if team != "" && !contains(m.Home, team) && !contains(m.Away, team) {
			continue
		}
		if competition != "" && !contains(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if (from != "" && m.Date < from) || (to != "" && m.Date > to) {
			continue
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Date > out[j].Date })
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

type TeamStats struct {
	Team                                                 string `json:"team"`
	Matches, Wins, Draws, Losses, GoalsFor, GoalsAgainst int
	WinRate                                              float64 `json:"win_rate"`
}

type Standing struct {
	Team                                                        string `json:"team"`
	Played, Wins, Draws, Losses, GoalsFor, GoalsAgainst, Points int
}

func (s *Store) Standings(competition string, season int) []Standing {
	table := map[string]*Standing{}
	for _, m := range s.Matches {
		if competition != "" && !contains(m.Competition, competition) || season != 0 && m.Season != season {
			continue
		}
		hKey, aKey := norm(m.Home), norm(m.Away)
		h := table[hKey]
		if h == nil {
			h = &Standing{Team: m.Home}
			table[hKey] = h
		}
		a := table[aKey]
		if a == nil {
			a = &Standing{Team: m.Away}
			table[aKey] = a
		}
		h.Played++
		a.Played++
		h.GoalsFor += m.HomeGoals
		h.GoalsAgainst += m.AwayGoals
		a.GoalsFor += m.AwayGoals
		a.GoalsAgainst += m.HomeGoals
		if m.HomeGoals > m.AwayGoals {
			h.Wins++
			h.Points += 3
			a.Losses++
		} else if m.HomeGoals < m.AwayGoals {
			a.Wins++
			a.Points += 3
			h.Losses++
		} else {
			h.Draws++
			a.Draws++
			h.Points++
			a.Points++
		}
	}
	out := make([]Standing, 0, len(table))
	for _, v := range table {
		out = append(out, *v)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
		}
		gdI := out[i].GoalsFor - out[i].GoalsAgainst
		gdJ := out[j].GoalsFor - out[j].GoalsAgainst
		if gdI != gdJ {
			return gdI > gdJ
		}
		return out[i].Team < out[j].Team
	})
	return out
}

func (s *Store) Stats(team, competition string, season int, homeOnly, awayOnly bool) TeamStats {
	st := TeamStats{Team: team}
	for _, m := range s.Matches {
		if season != 0 && m.Season != season || competition != "" && !contains(m.Competition, competition) {
			continue
		}
		isHome, isAway := contains(m.Home, team), contains(m.Away, team)
		if !isHome && !isAway || homeOnly && !isHome || awayOnly && !isAway {
			continue
		}
		st.Matches++
		if isHome {
			st.GoalsFor += m.HomeGoals
			st.GoalsAgainst += m.AwayGoals
			if m.HomeGoals > m.AwayGoals {
				st.Wins++
			} else if m.HomeGoals == m.AwayGoals {
				st.Draws++
			} else {
				st.Losses++
			}
		} else {
			st.GoalsFor += m.AwayGoals
			st.GoalsAgainst += m.HomeGoals
			if m.AwayGoals > m.HomeGoals {
				st.Wins++
			} else if m.HomeGoals == m.AwayGoals {
				st.Draws++
			} else {
				st.Losses++
			}
		}
	}
	if st.Matches > 0 {
		st.WinRate = float64(st.Wins) * 100 / float64(st.Matches)
	}
	return st
}

func (s *Store) SearchPlayers(name, nationality, club, position string, minOverall, limit int) []Player {
	var out []Player
	for _, p := range s.Players {
		if !contains(p.Name, name) || !contains(p.Nationality, nationality) || !contains(p.Club, club) || !contains(p.Position, position) || p.Overall < minOverall {
			continue
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Overall > out[j].Overall })
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

func (s *Store) Average(competition string, season int) map[string]any {
	n, g := 0, 0
	for _, m := range s.Matches {
		if competition != "" && !contains(m.Competition, competition) || season != 0 && m.Season != season {
			continue
		}
		n++
		g += m.HomeGoals + m.AwayGoals
	}
	avg := 0.0
	if n > 0 {
		avg = float64(g) / float64(n)
	}
	return map[string]any{"competition": competition, "season": season, "matches": n, "goals": g, "average_goals_per_match": avg}
}

type HeadToHead struct {
	TeamA   string `json:"team_a"`
	TeamB   string `json:"team_b"`
	Matches int    `json:"matches"`
	AWins   int    `json:"a_wins"`
	BWins   int    `json:"b_wins"`
	Draws   int    `json:"draws"`
}

func (s *Store) HeadToHead(teamA, teamB, competition string, season int) HeadToHead {
	out := HeadToHead{TeamA: teamA, TeamB: teamB}
	aKey, bKey := norm(teamA), norm(teamB)
	for _, m := range s.Matches {
		if competition != "" && !contains(m.Competition, competition) || season != 0 && m.Season != season {
			continue
		}
		h, a := norm(m.Home), norm(m.Away)
		if !((h == aKey && a == bKey) || (h == bKey && a == aKey)) {
			continue
		}
		out.Matches++
		if m.HomeGoals == m.AwayGoals {
			out.Draws++
		} else if (h == aKey && m.HomeGoals > m.AwayGoals) || (a == aKey && m.AwayGoals > m.HomeGoals) {
			out.AWins++
		} else {
			out.BWins++
		}
	}
	return out
}

func jsonResult(v any) map[string]any {
	b, _ := json.Marshal(v)
	return map[string]any{"content": []map[string]string{{"type": "text", "text": string(b)}}, "structuredContent": v}
}
