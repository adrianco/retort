package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode"
)

type Match struct {
	ID          string            `json:"id"`
	Date        string            `json:"date"`
	Home        string            `json:"home"`
	Away        string            `json:"away"`
	Competition string            `json:"competition"`
	Season      int               `json:"season"`
	Round       string            `json:"round,omitempty"`
	Stage       string            `json:"stage,omitempty"`
	Stadium     string            `json:"stadium,omitempty"`
	HomeGoals   *int              `json:"home_goals"`
	AwayGoals   *int              `json:"away_goals"`
	Sources     []string          `json:"sources"`
	Attributes  map[string]string `json:"attributes,omitempty"`
}
type Player struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Club        string            `json:"club"`
	Nationality string            `json:"nationality"`
	Position    string            `json:"position"`
	Overall     int               `json:"overall"`
	Attributes  map[string]string `json:"attributes"`
}
type Store struct {
	Matches  []Match
	Players  []Player
	Sources  map[string]int
	Warnings []string
	Teams    map[string][]int
}

var files = []string{"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv", "fifa_data.csv"}

func fold(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	from, to := []rune("áàâãäéèêëíìîïóòôõöúùûüçñ"), []rune("aaaaaeeeeiiiiooooouuuucn")
	return strings.Map(func(r rune) rune {
		for i, c := range from {
			if r == c {
				return to[i]
			}
		}
		if unicode.Is(unicode.Mn, r) {
			return -1
		}
		return r
	}, s)
}

var states = strings.Fields("ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to")

func team(s string) string {
	s = fold(s)
	// State disambiguation must precede generic suffix removal.
	compact := strings.ReplaceAll(s, " - ", "-")
	switch compact {
	case "atletico-mg", "atletico mg", "atletico mineiro":
		return "atletico mg"
	case "atletico-pr", "atletico pr", "athletico-pr", "athletico pr", "atletico paranaense", "athletico paranaense":
		return "athletico pr"
	case "atletico-go", "atletico go", "atletico goianiense":
		return "atletico go"
	case "america-mg", "america mg", "america mineiro":
		return "america mg"
	case "america-rn", "america rn":
		return "america rn"
	case "botafogo-sp", "botafogo sp":
		return "botafogo sp"
	case "bragantino-pa", "bragantino pa":
		return "bragantino pa"
	case "botafogo-pb", "botafogo pb":
		return "botafogo pb"
	}
	for _, st := range states {
		for _, suffix := range []string{"-" + st, " - " + st, " (" + st + ")"} {
			s = strings.TrimSpace(strings.TrimSuffix(s, suffix))
		}
	}
	s = strings.Join(strings.Fields(s), " ")
	aliases := map[string]string{
		"fortaleza ec": "fortaleza", "nautico capibaribe": "nautico", "guarani sp": "guarani", "ec juventude": "juventude", "santa cruz fc": "santa cruz", "ad confianca": "confianca", "clube do remo": "remo", "tombense mg": "tombense", "tupi mg": "tupi", "portuguesa desportos": "portuguesa", "gremio novorizontino": "novorizontino", "sampaio correa": "sampaio correia", "brasil de pelotas": "brasil", "a.s.a.": "asa",

		"sport club corinthians paulista": "corinthians", "corinthians paulista": "corinthians", "clube de regatas do flamengo": "flamengo", "sociedade esportiva palmeiras": "palmeiras", "sao paulo fc": "sao paulo", "sao paulo futebol clube": "sao paulo", "santos fc": "santos", "gremio foot-ball porto alegrense": "gremio", "vasco da gama": "vasco", "cr vasco da gama": "vasco", "atletico paranaense": "athletico pr", "athletico paranaense": "athletico pr", "atletico-pr": "athletico pr", "athletico-pr": "athletico pr", "atletico mineiro": "atletico mg", "atletico-mg": "atletico mg", "america mineiro": "america mg", "america-mg": "america mg", "botafogo-rj": "botafogo", "sport recife": "sport", "sport club do recife": "sport", "red bull bragantino": "bragantino", "fortaleza fc": "fortaleza", "ec bahia": "bahia", "vasco da gama rj": "vasco", "botafogo rj": "botafogo", "athletico": "athletico pr", "atletico mineiro mg": "atletico mg", "sport club internacional": "internacional"}
	// Preserve distinctions between clubs sharing a base name.
	original := fold(strings.TrimSpace(s))
	if v, ok := aliases[original]; ok {
		return v
	}
	return s
}
func competition(s string) string {
	switch fold(s) {
	case "serie a", "brasileirao", "brasileirao serie a", "campeonato brasileiro":
		return "Brasileirão Série A"
	case "copa do brasil":
		return "Copa do Brasil"
	case "libertadores", "copa libertadores":
		return "Copa Libertadores"
	case "serie b":
		return "Brasileirão Série B"
	case "serie c":
		return "Brasileirão Série C"
	}
	return s
}
func parseDate(s string) (string, error) {
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02 15:04", "2006-01-02", time.RFC3339, "02/01/2006", "02/01/2006 15:04", "02/01/2006 15:04:05"} {
		if t, e := time.Parse(layout, strings.TrimSpace(s)); e == nil {
			return t.Format("2006-01-02"), nil
		}
	}
	return "", fmt.Errorf("invalid date %q", s)
}
func score(s string) (*int, error) {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "nan") || strings.EqualFold(s, "na") || strings.EqualFold(s, "null") || s == "-" {
		return nil, nil
	}
	v, e := strconv.ParseFloat(s, 64)
	if e != nil || math.IsNaN(v) || math.IsInf(v, 0) || v < 0 || v != math.Trunc(v) || v > 1000 {
		return nil, fmt.Errorf("invalid score %q", s)
	}
	n := int(v)
	return &n, nil
}
func number(s string) int { f, _ := strconv.ParseFloat(s, 64); return int(f) }
func Load(dir string) (*Store, error) {
	db := &Store{Sources: map[string]int{}, Teams: map[string][]int{}, Warnings: []string{}}
	seen := map[string]int{}
	for _, name := range files {
		if err := db.loadFile(filepath.Join(dir, name), name, seen); err != nil {
			return nil, err
		}
	}
	// Numeric cup rounds vary with tournament format. Last observed round is labeled as inferred.
	last := map[int]int{}
	for _, m := range db.Matches {
		if m.Competition == "Copa do Brasil" && number(m.Round) > last[m.Season] {
			last[m.Season] = number(m.Round)
		}
	}
	for i := range db.Matches {
		m := &db.Matches[i]
		if m.Competition == "Copa do Brasil" && number(m.Round) > 0 && number(m.Round) == last[m.Season] {
			m.Stage = "final (inferred from maximum recorded round)"
		}
		m.ID = fmt.Sprintf("match:%d", i+1)
		db.Teams[m.Home] = append(db.Teams[m.Home], i)
		db.Teams[m.Away] = append(db.Teams[m.Away], i)
	}
	return db, nil
}
func (db *Store) loadFile(path, name string, seen map[string]int) error {
	f, e := os.Open(path)
	if e != nil {
		return e
	}
	defer f.Close()
	r := csv.NewReader(f)
	header, e := r.Read()
	if e != nil {
		return fmt.Errorf("%s: %w", name, e)
	}
	header[0] = strings.TrimPrefix(header[0], "\ufeff")
	required := map[string][]string{
		files[0]: {"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round"}, files[1]: {"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round"}, files[2]: {"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "stage"}, files[3]: {"date", "home", "away", "home_goal", "away_goal", "tournament"}, files[4]: {"Data", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante", "Ano"}, files[5]: {"ID", "Name", "Club", "Nationality", "Position", "Overall"}}
	for _, key := range required[name] {
		found := false
		for _, h := range header {
			if h == key {
				found = true
			}
		}
		if !found {
			return fmt.Errorf("%s: missing column %s", name, key)
		}
	}
	for row := 2; ; row++ {
		values, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return fmt.Errorf("%s row %d: %w", name, row, err)
		}
		a := map[string]string{}
		for i, k := range header {
			a[k] = values[i]
		}
		db.Sources[name]++
		if name == files[5] {
			db.Players = append(db.Players, Player{a["ID"], a["Name"], team(a["Club"]), a["Nationality"], a["Position"], number(a["Overall"]), a})
			continue
		}
		m := Match{Home: team(a["home_team"]), Away: team(a["away_team"]), Season: number(a["season"]), Round: a["round"], Stage: a["stage"], Sources: []string{name}, Attributes: a}
		date, hg, ag := a["datetime"], a["home_goal"], a["away_goal"]
		switch name {
		case files[0]:
			m.Competition = competition("serie a")
		case files[1]:
			m.Competition = competition("copa do brasil")
		case files[2]:
			m.Competition = competition("libertadores")
		case files[3]:
			m.Competition = competition(a["tournament"])
			m.Home = team(a["home"])
			m.Away = team(a["away"])
			date = a["date"]
		case files[4]:
			m.Competition = competition("serie a")
			m.Home = team(a["Equipe_mandante"])
			m.Away = team(a["Equipe_visitante"])
			date = a["Data"]
			hg = a["Gols_mandante"]
			ag = a["Gols_visitante"]
			m.Season = number(a["Ano"])
			m.Round = a["Rodada"]
			m.Stadium = a["Arena"]
		}
		if date == "NA" || date == "" || strings.EqualFold(date, "nan") {
			db.Warnings = append(db.Warnings, fmt.Sprintf("%s row %d: missing date", name, row))
		} else {
			m.Date, err = parseDate(date)
		}
		if err != nil {
			return fmt.Errorf("%s row %d: %w", name, row, err)
		}
		if m.Season == 0 && len(m.Date) >= 4 {
			m.Season = number(m.Date[:4])
		}
		m.HomeGoals, err = score(hg)
		if err != nil {
			return fmt.Errorf("%s row %d: %w", name, row, err)
		}
		m.AwayGoals, err = score(ag)
		if err != nil {
			return fmt.Errorf("%s row %d: %w", name, row, err)
		}
		if m.Home == "" || m.Away == "" {
			return fmt.Errorf("%s row %d: empty team", name, row)
		}
		key := fmt.Sprintf("%s|%s|%s|%s", m.Competition, m.Date, m.Home, m.Away)
		// Serie A and B are double round-robin: a directed fixture occurs once per season.
		// This also reconciles timezone/date disagreements across overlapping sources.
		if m.Competition == competition("serie a") || m.Competition == competition("serie b") {
			key = fmt.Sprintf("%s|%d|%s|%s", m.Competition, m.Season, m.Home, m.Away)
		}
		if i, ok := seen[key]; ok {
			old := &db.Matches[i]
			old.Sources = appendUnique(old.Sources, name)
			if old.HomeGoals != nil && m.HomeGoals != nil && (*old.HomeGoals != *m.HomeGoals || old.AwayGoals != nil && m.AwayGoals != nil && *old.AwayGoals != *m.AwayGoals) {
				db.Warnings = append(db.Warnings, "Conflicting scores: "+key+"; retained first source")
			}
			if old.HomeGoals == nil {
				old.HomeGoals = m.HomeGoals
			}
			if old.AwayGoals == nil {
				old.AwayGoals = m.AwayGoals
			}
			if old.Round == "" {
				old.Round = m.Round
			}
			if old.Stage == "" {
				old.Stage = m.Stage
			}
			if old.Stadium == "" {
				old.Stadium = m.Stadium
			}
			for k, v := range a {
				if old.Attributes[k] == "" {
					old.Attributes[k] = v
				}
			}
			continue
		}
		seen[key] = len(db.Matches)
		db.Matches = append(db.Matches, m)
	}
	return nil
}
func appendUnique(s []string, v string) []string {
	for _, x := range s {
		if x == v {
			return s
		}
	}
	return append(s, v)
}
func sortedKeys[V any](m map[string]V) []string {
	r := []string{}
	for k := range m {
		r = append(r, k)
	}
	sort.Strings(r)
	return r
}
