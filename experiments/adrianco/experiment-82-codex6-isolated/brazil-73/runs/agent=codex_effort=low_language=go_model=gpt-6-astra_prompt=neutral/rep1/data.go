package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode"
)

// Match is a graph edge between two teams and a competition-season.
// Attributes retains source-specific statistics without inventing missing values.
type Match struct {
	ID          string                       `json:"id"`
	Date        string                       `json:"date"`
	Home        string                       `json:"home"`
	Away        string                       `json:"away"`
	HomeGoals   *int                         `json:"home_goals"`
	AwayGoals   *int                         `json:"away_goals"`
	Competition string                       `json:"competition"`
	Season      int                          `json:"season"`
	Round       string                       `json:"round,omitempty"`
	Stage       string                       `json:"stage,omitempty"`
	Stadium     string                       `json:"stadium,omitempty"`
	Sources     []string                     `json:"sources"`
	Attributes  map[string]map[string]string `json:"attributes"`
}
type Player struct {
	ID          string            `json:"id"`
	Name        string            `json:"name"`
	Nationality string            `json:"nationality"`
	Club        string            `json:"club"`
	Position    string            `json:"position"`
	Overall     int               `json:"overall"`
	Potential   int               `json:"potential"`
	Attributes  map[string]string `json:"attributes"`
}
type Source struct {
	File    string `json:"file"`
	Rows    int    `json:"rows"`
	License string `json:"license"`
	URL     string `json:"url"`
}
type Graph struct {
	Matches  []*Match
	Players  []Player
	Teams    map[string][]*Match
	Rosters  map[string][]Player
	Sources  []Source
	Warnings []string
}

var accents = strings.NewReplacer("á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "é", "e", "è", "e", "ê", "e", "ë", "e", "í", "i", "ì", "i", "î", "i", "ï", "i", "ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o", "ú", "u", "ù", "u", "û", "u", "ü", "u", "ç", "c", "ñ", "n")

func fold(s string) string {
	return strings.Join(strings.Fields(strings.Map(func(r rune) rune {
		if unicode.Is(unicode.Mn, r) {
			return -1
		}
		return r
	}, accents.Replace(strings.ToLower(strings.TrimSpace(s))))), " ")
}

var stateSuffix = regexp.MustCompile(`\s*-\s*(ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to)$`)
var aliases = map[string]string{
	"ec juventude": "juventude", "santa cruz fc": "santa cruz",
	"america fc (minas gerais)": "america-mg", "ceara sporting club": "ceara", "clube atletico mineiro": "atletico-mg", "gremio foot-ball porto alegrense": "gremio",
	"ec bahia": "bahia", "fortaleza fc": "fortaleza", "vasco da gama rj": "vasco da gama", "athletico": "athletico-pr", "athletico-pr": "athletico-pr", "atletico-pr": "athletico-pr",
	"sport club corinthians paulista": "corinthians", "corinthians paulista": "corinthians", "clube de regatas do flamengo": "flamengo", "sao paulo fc": "sao paulo", "sao paulo futebol clube": "sao paulo", "santos fc": "santos", "sociedade esportiva palmeiras": "palmeiras",
	"atletico mineiro": "atletico-mg", "atletico mg": "atletico-mg", "athletico paranaense": "athletico-pr", "atletico paranaense": "athletico-pr", "athletico pr": "athletico-pr", "atletico pr": "athletico-pr", "atletico goianiense": "atletico-go", "atletico go": "atletico-go",
	"america mineiro": "america-mg", "america mg": "america-mg", "america rn": "america-rn", "botafogo pb": "botafogo-pb", "botafogo sp": "botafogo-sp", "botafogo rj": "botafogo", "vasco": "vasco da gama", "cr vasco da gama": "vasco da gama", "sport recife": "sport", "sport club do recife": "sport", "red bull bragantino": "bragantino", "rb bragantino": "bragantino", "brasil de pelotas": "brasil-rs", "nautico capibaribe": "nautico", "gremio porto alegre": "gremio", "flamengo do piaui": "flamengo-pi", "boavista sport club (antigo esporte clube barreira)": "boavista",
}

func teamKey(s string) string {
	s = fold(s)
	if a, ok := aliases[s]; ok {
		return a
	}
	loc := stateSuffix.FindStringSubmatch(s)
	if len(loc) > 0 {
		base := strings.TrimSpace(s[:len(s)-len(loc[0])])
		state := loc[1]
		if a, ok := aliases[base]; ok {
			return a
		}
		switch base {
		case "atletico", "america", "botafogo", "flamengo", "bragantino", "brasil":
			if base == "botafogo" && state == "rj" || base == "flamengo" && state == "rj" || base == "bragantino" && state == "sp" {
				return base
			}
			if base == "atletico" && state == "pr" {
				return "athletico-pr"
			}
			return base + "-" + state
		}
		s = base
	}
	// Normalize dotted club abbreviations while preserving meaningful country suffixes.
	if strings.Contains(s, ".") {
		s = strings.ReplaceAll(s, ".", "")
		if len(strings.ReplaceAll(s, " ", "")) <= 4 {
			s = strings.ReplaceAll(s, " ", "")
		}
	}
	return s
}
func competitionKey(s string) string {
	switch fold(s) {
	case "brasileirao", "brasileirao serie a", "campeonato brasileiro", "serie a", "brazil serie a":
		return "Brasileirão"
	case "copa do brasil", "brazilian cup":
		return "Copa do Brasil"
	case "libertadores", "copa libertadores":
		return "Libertadores"
	case "serie b":
		return "Serie B"
	case "serie c":
		return "Serie C"
	}
	return strings.TrimSpace(s)
}
func parseDate(s string) (time.Time, error) {
	for _, layout := range []string{time.RFC3339, "2006-01-02 15:04:05", "2006-01-02 15:04", "2006-01-02", "02/01/2006", "02/01/2006 15:04:05"} {
		if t, e := time.Parse(layout, strings.TrimSpace(s)); e == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("invalid date %q", s)
}
func number(s string) (int, error) {
	f, e := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if e != nil || math.IsNaN(f) || math.IsInf(f, 0) || f < 0 || f != math.Trunc(f) || f > 1e9 {
		return 0, fmt.Errorf("invalid nonnegative integer %q", s)
	}
	return int(f), nil
}
func missing(s string) bool {
	return s == "" || strings.EqualFold(s, "na") || strings.EqualFold(s, "nan") || s == "-" || strings.EqualFold(s, "null")
}
func score(s string) (*int, error) {
	if s == "" || strings.EqualFold(s, "nan") || strings.EqualFold(s, "na") || strings.EqualFold(s, "null") || s == "-" {
		return nil, nil
	}
	n, e := number(s)
	return &n, e
}
func first(r map[string]string, keys ...string) string {
	for _, k := range keys {
		if v := r[k]; v != "" {
			return v
		}
	}
	return ""
}
func LoadGraph(dir string) (*Graph, error) {
	g := &Graph{Teams: map[string][]*Match{}, Rosters: map[string][]Player{}, Warnings: []string{}}
	files := []string{"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv", "fifa_data.csv"}
	seen := map[string]*Match{}
	byDay := map[string][]*Match{}
	pendingLeague := map[string]*Match{}
	for _, file := range files {
		source := Source{File: file, License: "CC BY 4.0", URL: "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro"}
		if file == files[3] {
			source.License = "CC0 Public Domain"
			source.URL = "https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches"
		}
		if file == files[4] {
			source.URL = "https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019"
		}
		if file == files[5] {
			source.License = "Apache 2.0"
			source.URL = "https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data"
		}
		err := readCSV(filepath.Join(dir, file), func(r map[string]string) error {
			source.Rows++
			if file == "fifa_data.csv" {
				rating, e := number(r["Overall"])
				if e != nil {
					return e
				}
				potential, e := number(r["Potential"])
				if e != nil {
					return e
				}
				if r["ID"] == "" || r["Name"] == "" {
					return fmt.Errorf("missing player ID or Name")
				}
				p := Player{r["ID"], r["Name"], r["Nationality"], r["Club"], r["Position"], rating, potential, r}
				g.Players = append(g.Players, p)
				g.Rosters[teamKey(p.Club)] = append(g.Rosters[teamKey(p.Club)], p)
				return nil
			}
			rawDate := first(r, "datetime", "date", "Data")
			var date time.Time
			var e error
			dateText := ""
			if !missing(rawDate) {
				date, e = parseDate(rawDate)
				if e != nil {
					return e
				}
				dateText = date.Format("2006-01-02")
			} else {
				g.Warnings = append(g.Warnings, file+": match with unknown date retained")
			}
			home, away := first(r, "home_team", "home", "Equipe_mandante"), first(r, "away_team", "away", "Equipe_visitante")
			if home == "" || away == "" {
				return fmt.Errorf("missing team")
			}
			// Historical state columns disambiguate clubs sharing a name.
			if file == "novo_campeonato_brasileiro.csv" {
				if r["Mandante_UF"] != "" && !stateSuffix.MatchString(fold(home)) {
					home += "-" + r["Mandante_UF"]
				}
				if r["Visitante_UF"] != "" && !stateSuffix.MatchString(fold(away)) {
					away += "-" + r["Visitante_UF"]
				}
			}
			hg, e := score(first(r, "home_goal", "Gols_mandante"))
			if e != nil {
				return e
			}
			ag, e := score(first(r, "away_goal", "Gols_visitante"))
			if e != nil {
				return e
			}
			comp := "Brasileirão"
			switch file {
			case "Brazilian_Cup_Matches.csv":
				comp = "Copa do Brasil"
			case "Libertadores_Matches.csv":
				comp = "Libertadores"
			case "BR-Football-Dataset.csv":
				comp = competitionKey(r["tournament"])
				if comp == "" {
					return fmt.Errorf("missing tournament")
				}
			}
			season := 0
			if !date.IsZero() {
				season = date.Year()
			}
			if s := first(r, "season", "Ano"); !missing(s) {
				season, e = number(s)
				if e != nil {
					return e
				}
			}
			m := &Match{Date: dateText, Home: teamKey(home), Away: teamKey(away), HomeGoals: hg, AwayGoals: ag, Competition: comp, Season: season, Round: first(r, "round", "Rodada"), Stage: r["stage"], Stadium: r["Arena"], Sources: []string{file}, Attributes: map[string]map[string]string{file: r}}
			key := fmt.Sprintf("%s|%d|%s|%s|%s", comp, season, m.Date, m.Home, m.Away)
			old := seen[key]
			// Some sources record UTC dates, others local dates. Merge adjacent-day
			// cross-source fixtures only with identical scores, teams and competition.
			// Extended data has no season column: prefer the explicit season of a
			// matching authoritative fixture (not its calendar year).
			if old == nil && dateText != "" {
				for _, delta := range []int{0, -1, 1} {
					dayKey := comp + "|" + date.AddDate(0, 0, delta).Format("2006-01-02") + "|" + m.Home + "|" + m.Away
					for _, candidate := range byDay[dayKey] {
						_, sameSource := candidate.Attributes[file]
						if !sameSource && (candidate.Season == season || file == "BR-Football-Dataset.csv") && sameScore(candidate, m) {
							old = candidate
							break
						}
					}
					if old != nil {
						break
					}
				}
			}
			fixtureKey := fmt.Sprintf("%s|%d|%s|%s", comp, season, m.Home, m.Away)
			if old == nil && comp == "Brasileirão" && completed(m) {
				if pending := pendingLeague[fixtureKey]; pending != nil {
					if _, sameSource := pending.Attributes[file]; !sameSource {
						old = pending
					}
				}
			}
			if old != nil {
				if !completed(old) && completed(m) {
					old.Date = m.Date
					delete(pendingLeague, fixtureKey)
				}
				if old.HomeGoals != nil && hg != nil && (*old.HomeGoals != *hg || old.AwayGoals != nil && ag != nil && *old.AwayGoals != *ag) {
					g.Warnings = append(g.Warnings, "conflicting scores: "+key+"; retained "+old.Sources[0])
				}
				if old.HomeGoals == nil {
					old.HomeGoals = hg
				}
				if old.AwayGoals == nil {
					old.AwayGoals = ag
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
				if _, ok := old.Attributes[file]; !ok {
					old.Sources = append(old.Sources, file)
				}
				old.Attributes[file] = r
				return nil
			}
			m.ID = key
			if comp == "Brasileirão" && !completed(m) {
				pendingLeague[fixtureKey] = m
			}
			seen[key] = m
			dayKey := comp + "|" + m.Date + "|" + m.Home + "|" + m.Away
			byDay[dayKey] = append(byDay[dayKey], m)
			g.Matches = append(g.Matches, m)
			return nil
		})
		if err != nil {
			return nil, err
		}
		g.Sources = append(g.Sources, source)
	}
	sort.Slice(g.Matches, func(i, j int) bool {
		if g.Matches[i].Date == g.Matches[j].Date {
			return g.Matches[i].ID < g.Matches[j].ID
		}
		return g.Matches[i].Date > g.Matches[j].Date
	})
	for _, m := range g.Matches {
		g.Teams[m.Home] = append(g.Teams[m.Home], m)
		g.Teams[m.Away] = append(g.Teams[m.Away], m)
	}
	return g, nil
}
func readCSV(path string, visit func(map[string]string) error) error {
	f, e := os.Open(path)
	if e != nil {
		return e
	}
	defer f.Close()
	r := csv.NewReader(f)
	header, e := r.Read()
	if e != nil {
		return fmt.Errorf("%s: %w", path, e)
	}
	for i := range header {
		header[i] = strings.TrimPrefix(header[i], "\ufeff")
	}
	for row := 2; ; row++ {
		cells, e := r.Read()
		if e == io.EOF {
			return nil
		}
		if e != nil {
			return fmt.Errorf("%s row %d: %w", path, row, e)
		}
		record := map[string]string{}
		for i, k := range header {
			record[k] = strings.TrimSpace(cells[i])
		}
		if e = visit(record); e != nil {
			return fmt.Errorf("%s row %d: %w", path, row, e)
		}
	}
}

func sameScore(a, b *Match) bool {
	return completed(a) && completed(b) && *a.HomeGoals == *b.HomeGoals && *a.AwayGoals == *b.AwayGoals
}
