package main

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode"
)

type Match struct {
	Competition string    `json:"competition"`
	Date        time.Time `json:"date"`
	Round       string    `json:"round,omitempty"`
	Stage       string    `json:"stage,omitempty"`
	Home        string    `json:"home_team"`
	Away        string    `json:"away_team"`
	HomeGoals   int       `json:"home_goals"`
	AwayGoals   int       `json:"away_goals"`
	Season      int       `json:"season"`
	Venue       string    `json:"venue,omitempty"`
}

type Player struct {
	ID          int    `json:"id"`
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	Age         int    `json:"age"`
	Overall     int    `json:"overall"`
	Potential   int    `json:"potential"`
}

type Store struct {
	Matches []Match
	Players []Player
}

func LoadStore(dir string) (*Store, error) {
	s := &Store{}
	files := []struct {
		name, competition    string
		historical, extended bool
	}{
		{"Brasileirao_Matches.csv", "Brasileirão", false, false},
		{"Brazilian_Cup_Matches.csv", "Copa do Brasil", false, false},
		{"Libertadores_Matches.csv", "Copa Libertadores", false, false},
		{"novo_campeonato_brasileiro.csv", "Brasileirão", true, false},
		{"BR-Football-Dataset.csv", "", false, true},
	}
	for _, f := range files {
		p := filepath.Join(dir, f.name)
		file, err := os.Open(p)
		if err != nil {
			if errors.Is(err, os.ErrNotExist) {
				continue
			}
			return nil, err
		}
		var ms []Match
		if f.historical {
			ms, err = readHistorical(file, f.competition)
		} else if f.extended {
			ms, err = readExtended(file)
		} else {
			ms, err = readMatches(file, f.competition)
		}
		file.Close()
		if err != nil {
			return nil, fmt.Errorf("%s: %w", f.name, err)
		}
		s.Matches = append(s.Matches, ms...)
	}
	file, err := os.Open(filepath.Join(dir, "fifa_data.csv"))
	if err == nil {
		s.Players, err = readPlayers(file)
		file.Close()
	}
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}
	for i := range s.Matches {
		// The extended data has no season column. Its date is still useful for
		// season queries and for reconciling the same fixture from another file.
		if s.Matches[i].Season == 0 && !s.Matches[i].Date.IsZero() {
			s.Matches[i].Season = s.Matches[i].Date.Year()
		}
	}
	s.Matches = deduplicateMatches(s.Matches)
	sort.SliceStable(s.Matches, func(i, j int) bool { return s.Matches[i].Date.Before(s.Matches[j].Date) })
	return s, nil
}

func header(r []string) map[string]int {
	m := map[string]int{}
	for i, v := range r {
		m[strings.ToLower(strings.TrimSpace(strings.TrimPrefix(v, "\ufeff")))] = i
	}
	return m
}
func val(row []string, h map[string]int, keys ...string) string {
	for _, k := range keys {
		if i, ok := h[strings.ToLower(k)]; ok && i < len(row) {
			return strings.TrimSpace(row[i])
		}
	}
	return ""
}
func integer(v string) int {
	v = strings.TrimSpace(v)
	if i, err := strconv.Atoi(v); err == nil {
		return i
	}
	if f, err := strconv.ParseFloat(v, 64); err == nil {
		return int(f)
	}
	return 0
}
func parseDate(v string) time.Time {
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", "02/01/2006 15:04:05"} {
		if t, e := time.Parse(layout, strings.TrimSpace(v)); e == nil {
			return t
		}
	}
	return time.Time{}
}
func readAll(r io.Reader) ([][]string, map[string]int, error) {
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1
	rows, err := cr.ReadAll()
	if err != nil {
		return nil, nil, err
	}
	if len(rows) == 0 {
		return rows, map[string]int{}, nil
	}
	return rows, header(rows[0]), nil
}
func readMatches(r io.Reader, comp string) ([]Match, error) {
	rows, h, e := readAll(r)
	if e != nil {
		return nil, e
	}
	out := []Match{}
	for _, x := range rows[1:] {
		if len(x) == 0 {
			continue
		}
		out = append(out, Match{Competition: comp, Date: parseDate(val(x, h, "datetime")), Round: val(x, h, "round"), Home: val(x, h, "home_team"), Away: val(x, h, "away_team"), HomeGoals: integer(val(x, h, "home_goal")), AwayGoals: integer(val(x, h, "away_goal")), Season: integer(val(x, h, "season")), Stage: val(x, h, "stage")})
	}
	return out, nil
}
func readHistorical(r io.Reader, comp string) ([]Match, error) {
	rows, h, e := readAll(r)
	if e != nil {
		return nil, e
	}
	out := []Match{}
	for _, x := range rows[1:] {
		if len(x) == 0 {
			continue
		}
		out = append(out, Match{Competition: comp, Date: parseDate(val(x, h, "data")), Round: val(x, h, "rodada"), Home: val(x, h, "equipe_mandante"), Away: val(x, h, "equipe_visitante"), HomeGoals: integer(val(x, h, "gols_mandante")), AwayGoals: integer(val(x, h, "gols_visitante")), Season: integer(val(x, h, "ano")), Venue: val(x, h, "arena")})
	}
	return out, nil
}
func readExtended(r io.Reader) ([]Match, error) {
	rows, h, e := readAll(r)
	if e != nil {
		return nil, e
	}
	out := []Match{}
	for _, x := range rows[1:] {
		if len(x) == 0 {
			continue
		}
		out = append(out, Match{Competition: val(x, h, "tournament"), Date: parseDate(val(x, h, "date")), Home: val(x, h, "home"), Away: val(x, h, "away"), HomeGoals: integer(val(x, h, "home_goal")), AwayGoals: integer(val(x, h, "away_goal"))})
	}
	return out, nil
}

// deduplicateMatches reconciles the overlapping Kaggle exports. A match can
// have a different local/UTC date in two sources, so dates within 24 hours are
// considered the same fixture when the season, teams, and score agree.
func deduplicateMatches(in []Match) []Match {
	out := make([]Match, 0, len(in))
	for _, m := range in {
		duplicate := false
		for _, prior := range out {
			if m.Season != prior.Season || m.HomeGoals != prior.HomeGoals || m.AwayGoals != prior.AwayGoals ||
				!teamMatch(m.Home, prior.Home) || !teamMatch(m.Away, prior.Away) {
				continue
			}
			if m.Date.IsZero() || prior.Date.IsZero() || absDuration(m.Date.Sub(prior.Date)) <= 24*time.Hour {
				duplicate = true
				break
			}
		}
		if !duplicate {
			out = append(out, m)
		}
	}
	return out
}

func absDuration(d time.Duration) time.Duration {
	if d < 0 {
		return -d
	}
	return d
}
func readPlayers(r io.Reader) ([]Player, error) {
	rows, h, e := readAll(r)
	if e != nil {
		return nil, e
	}
	out := []Player{}
	for _, x := range rows[1:] {
		if len(x) == 0 {
			continue
		}
		out = append(out, Player{ID: integer(val(x, h, "id")), Name: val(x, h, "name"), Age: integer(val(x, h, "age")), Nationality: val(x, h, "nationality"), Overall: integer(val(x, h, "overall")), Potential: integer(val(x, h, "potential")), Club: val(x, h, "club"), Position: val(x, h, "position")})
	}
	return out, nil
}

func clean(s string) string {
	var b strings.Builder
	for _, r := range strings.ToLower(strings.TrimSpace(s)) {
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
		}
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '-' || r == ' ' {
			b.WriteRune(r)
		}
	}
	return strings.Join(strings.Fields(b.String()), " ")
}

func canonicalTeam(s string) string {
	s = clean(s)
	// Avoid a third Atlético row: historical data calls the Paraná club
	// Athletico while the newer export calls it Atletico.
	s = strings.ReplaceAll(s, "athletico", "atletico")
	// The historical export abbreviates this club while the newer export uses
	// its full registered name.
	s = strings.ReplaceAll(s, "vasco da gama", "vasco")
	return s
}

func teamBase(s string) string {
	s = canonicalTeam(s)
	parts := strings.Split(s, "-")
	if len(parts) > 1 && len(parts[len(parts)-1]) == 2 {
		return strings.Join(parts[:len(parts)-1], "-")
	}
	return s
}

func teamKey(s string) string {
	s = canonicalTeam(s)
	base := teamBase(s)
	// Atlético-MG and Atlético-PR are different clubs; their state suffix is
	// identity, unlike the suffixes used to distinguish a bare query from a
	// single club in the other exports.
	if base == "atletico" || base == "athletico" {
		return s
	}
	return base
}

func teamMatch(a, b string) bool {
	a, b = canonicalTeam(a), canonicalTeam(b)
	if a == b {
		return true
	}
	// A bare query such as "Palmeiras" matches Palmeiras-SP, but two
	// state-specific clubs such as Atletico-MG and Atletico-PR remain distinct.
	return !strings.Contains(b, "-") && teamBase(a) == b || !strings.Contains(a, "-") && teamBase(b) == a
}

func displayTeam(s string) string {
	s = strings.TrimSpace(s)
	if strings.HasSuffix(s, "-SP") || strings.HasSuffix(s, "-RJ") || strings.HasSuffix(s, "-MG") || strings.HasSuffix(s, "-PR") || strings.HasSuffix(s, "-RS") || strings.HasSuffix(s, "-BA") || strings.HasSuffix(s, "-SC") || strings.HasSuffix(s, "-GO") || strings.HasSuffix(s, "-CE") || strings.HasSuffix(s, "-PE") || strings.HasSuffix(s, "-PA") || strings.HasSuffix(s, "-ES") || strings.HasSuffix(s, "-AL") {
		base, state := s[:len(s)-3], s[len(s)-2:]
		if canonicalTeam(base) != "atletico" {
			return base
		}
		return "Atletico-" + state
	}
	return s
}
