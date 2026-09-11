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

// SourceRow preserves the exact source record, including extended match/player attributes.
type SourceRow struct {
	File   string            `json:"file"`
	Row    int               `json:"row"`
	Fields map[string]string `json:"fields"`
}
type Match struct {
	ID          string      `json:"id"`
	Date        string      `json:"date"`
	Home        string      `json:"home_team"`
	Away        string      `json:"away_team"`
	Competition string      `json:"competition"`
	Season      int         `json:"season"`
	Round       string      `json:"round,omitempty"`
	Stage       string      `json:"stage,omitempty"`
	HomeGoals   *int        `json:"home_goal"`
	AwayGoals   *int        `json:"away_goal"`
	Stadium     string      `json:"stadium,omitempty"`
	Sources     []SourceRow `json:"sources"`
	day         time.Time
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
type DatasetInfo struct {
	File    string `json:"file"`
	Rows    int    `json:"rows"`
	URL     string `json:"url"`
	License string `json:"license"`
}
type Store struct {
	Matches       []Match
	Players       []Player
	Sources       []DatasetInfo
	Warnings      []string
	teams         map[string][]int
	playersByClub map[string][]int
}

var accent = strings.NewReplacer("á", "a", "à", "a", "ã", "a", "â", "a", "ä", "a", "é", "e", "è", "e", "ê", "e", "ë", "e", "í", "i", "ì", "i", "î", "i", "ï", "i", "ó", "o", "ò", "o", "õ", "o", "ô", "o", "ö", "o", "ú", "u", "ù", "u", "û", "u", "ü", "u", "ç", "c", "ñ", "n")

func fold(s string) string {
	s = accent.Replace(strings.ToLower(strings.TrimSpace(s)))
	return strings.Join(strings.FieldsFunc(s, func(r rune) bool { return !unicode.IsLetter(r) && !unicode.IsDigit(r) }), " ")
}

var stateSuffix = regexp.MustCompile(`(?i)\s*-\s*(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$`)
var aliases = map[string]string{
	"sport club corinthians paulista": "corinthians", "corinthians paulista": "corinthians", "clube de regatas do flamengo": "flamengo", "cr flamengo": "flamengo", "sociedade esportiva palmeiras": "palmeiras", "sao paulo fc": "sao paulo", "sao paulo futebol clube": "sao paulo", "santos fc": "santos", "gremio fbpa": "gremio", "gremio foot ball porto alegrense": "gremio", "sport club internacional": "internacional", "sc internacional": "internacional", "vasco": "vasco da gama", "cr vasco da gama": "vasco da gama", "ec bahia": "bahia", "esporte clube bahia": "bahia", "ec vitoria": "vitoria", "sport recife": "sport", "sport club do recife": "sport", "sport clube do recife": "sport", "nautico capibaribe": "nautico", "ponte preta": "ponte preta", "aa ponte preta": "ponte preta", "abc": "a b c",
	"red bull bragantino": "bragantino", "rb bragantino": "bragantino", "fortaleza fc": "fortaleza", "vasco da gama rj": "vasco da gama", "santa cruz fc": "santa cruz", "athletico": "athletico pr", "ec juventude": "juventude", "ca parana": "parana", "cs alagoano": "csa", "america fc natal": "america rn", "atletico mineiro": "atletico mg", "clube atletico mineiro": "atletico mg", "atletico mg": "atletico mg", "athletico pr": "athletico pr", "atletico pr": "athletico pr", "atletico paranaense": "athletico pr", "athletico paranaense": "athletico pr", "clube atletico paranaense": "athletico pr", "atletico goianiense": "atletico go", "atletico go": "atletico go", "america mineiro": "america mg", "america mg": "america mg", "america rn": "america rn", "america natal": "america rn", "botafogo sp": "botafogo sp", "botafogo rj": "botafogo", "botafogo fr": "botafogo",
}

// Preserve state qualifiers for names that would otherwise conflate distinct clubs.
func NormalizeTeam(s string) string {
	full := fold(s)
	if v, ok := aliases[full]; ok {
		return v
	}
	if strings.HasPrefix(full, "atletico ") || strings.HasPrefix(full, "america ") || strings.HasPrefix(full, "botafogo ") {
		return full
	}
	s = stateSuffix.ReplaceAllString(s, "")
	n := fold(s)
	if v, ok := aliases[n]; ok {
		return v
	}
	return n
}
func competition(s string) string {
	n := fold(s)
	switch n {
	case "brasileirao", "brasileirao serie a", "serie a", "campeonato brasileiro", "brasileirao a":
		return "Brasileirão"
	case "copa do brasil", "brazilian cup":
		return "Copa do Brasil"
	case "libertadores", "copa libertadores", "copa libertadores da america":
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
			return time.Date(t.Year(), t.Month(), t.Day(), 0, 0, 0, 0, time.UTC), nil
		}
	}
	return time.Time{}, fmt.Errorf("invalid date %q", s)
}
func number(s string) (int, error) {
	n, e := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if e != nil || math.IsNaN(n) || math.IsInf(n, 0) || n != math.Trunc(n) || n < 0 || n > 1000000 {
		return 0, fmt.Errorf("invalid nonnegative integer %q", s)
	}
	return int(n), nil
}
func score(s string) (*int, error) {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "", "na", "nan", "null", "-":
		return nil, nil
	}
	n, e := number(s)
	return &n, e
}
func value(r map[string]string, keys ...string) string {
	for _, k := range keys {
		if v := strings.TrimSpace(r[k]); v != "" {
			return v
		}
	}
	return ""
}

var datasetFiles = []string{"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv", "fifa_data.csv"}

func LoadStore(dir string) (*Store, error) {
	s := &Store{Warnings: []string{}, teams: map[string][]int{}, playersByClub: map[string][]int{}}
	fixtures := map[string][]int{}
	datedFixtures := map[string][]int{}
	for _, name := range datasetFiles {
		f, e := os.Open(filepath.Join(dir, name))
		if e != nil {
			return nil, e
		}
		r := csv.NewReader(f)
		header, e := r.Read()
		if e != nil {
			f.Close()
			return nil, fmt.Errorf("%s: %w", name, e)
		}
		for i := range header {
			header[i] = strings.TrimPrefix(strings.TrimSpace(header[i]), "\ufeff")
		}
		required := []string{"datetime", "home_team", "away_team", "home_goal", "away_goal", "season"}
		switch name {
		case "fifa_data.csv":
			required = []string{"ID", "Name", "Nationality", "Club", "Overall", "Potential", "Position"}
		case "novo_campeonato_brasileiro.csv":
			required = []string{"Data", "Ano", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante"}
		case "BR-Football-Dataset.csv":
			required = []string{"date", "tournament", "home", "away", "home_goal", "away_goal"}
		}
		for _, k := range required {
			found := false
			for _, h := range header {
				if h == k {
					found = true
				}
			}
			if !found {
				f.Close()
				return nil, fmt.Errorf("%s: missing column %s", name, k)
			}
		}
		info := DatasetInfo{File: name, URL: "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro", License: "CC BY 4.0"}
		switch name {
		case "BR-Football-Dataset.csv":
			info.URL = "https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches"
			info.License = "CC0 Public Domain"
		case "novo_campeonato_brasileiro.csv":
			info.URL = "https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019"
		case "fifa_data.csv":
			info.URL = "https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data"
			info.License = "Apache 2.0"
		}
		for row := 2; ; row++ {
			fields, err := r.Read()
			if err == io.EOF {
				break
			}
			if err != nil {
				f.Close()
				return nil, fmt.Errorf("%s row %d: %w", name, row, err)
			}
			rec := map[string]string{}
			for i, k := range header {
				rec[k] = fields[i]
			}
			info.Rows++
			if name == "fifa_data.csv" {
				overall, err := number(rec["Overall"])
				if err != nil {
					f.Close()
					return nil, fmt.Errorf("%s row %d: %w", name, row, err)
				}
				potential, err := number(rec["Potential"])
				if err != nil {
					f.Close()
					return nil, fmt.Errorf("%s row %d: %w", name, row, err)
				}
				p := Player{ID: rec["ID"], Name: rec["Name"], Nationality: rec["Nationality"], Club: rec["Club"], Position: rec["Position"], Overall: overall, Potential: potential, Attributes: rec}
				s.Players = append(s.Players, p)
				continue
			}
			m, err := matchFromRow(name, rec)
			if err != nil {
				f.Close()
				return nil, fmt.Errorf("%s row %d: %w", name, row, err)
			}
			if name == "BR-Football-Dataset.csv" {
				for _, i := range datedFixtures[m.Competition+"|"+m.Home+"|"+m.Away] {
					old := s.Matches[i]
					delta := old.day.Sub(m.day)
					if delta < 0 {
						delta = -delta
					}
					if delta <= 24*time.Hour {
						m.Season = old.Season
						break
					}
				}
			}
			src := SourceRow{name, row, rec}
			if m.Date == "" {
				s.Warnings = append(s.Warnings, fmt.Sprintf("%s row %d: unknown date/season retained as unplayed fixture", name, row))
			}
			key := fmt.Sprintf("%s|%d|%s|%s", m.Competition, m.Season, m.Home, m.Away)
			merged := false
			for _, i := range fixtures[key] {
				old := &s.Matches[i]
				delta := old.day.Sub(m.day)
				if delta < 0 {
					delta = -delta
				}
				// Serie A/B have one home fixture per opponent each season.
				// Match them even if a source retained a postponed date.
				if delta > 24*time.Hour && m.Competition != "Brasileirão" && m.Competition != "Serie B" {
					continue
				}
				// Preserve cup double fixtures; league pairs are unique per season.
				already := false
				for _, x := range old.Sources {
					if x.File == name {
						already = true
					}
				}
				if already && m.Competition != "Brasileirão" && m.Competition != "Serie B" {
					continue
				}
				if delta > 24*time.Hour {
					s.Warnings = append(s.Warnings, fmt.Sprintf("Conflicting league dates for %s: retained %s; alternative %s in %s row %d", key, old.Date, m.Date, name, row))
				}
				if old.HomeGoals != nil && m.HomeGoals != nil && (*old.HomeGoals != *m.HomeGoals || *old.AwayGoals != *m.AwayGoals) {
					s.Warnings = append(s.Warnings, fmt.Sprintf("Conflicting scores for %s on %s: retained %s, alternative in %s row %d", key, old.Date, old.Sources[0].File, name, row))
				}
				if old.HomeGoals == nil && m.HomeGoals != nil {
					old.HomeGoals = m.HomeGoals
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
				old.Sources = append(old.Sources, src)
				merged = true
				break
			}
			if !merged {
				m.ID = fmt.Sprintf("match:%d", len(s.Matches)+1)
				m.Sources = []SourceRow{src}
				fixtures[key] = append(fixtures[key], len(s.Matches))
				datedFixtures[m.Competition+"|"+m.Home+"|"+m.Away] = append(datedFixtures[m.Competition+"|"+m.Home+"|"+m.Away], len(s.Matches))
				s.Matches = append(s.Matches, m)
			}
		}
		f.Close()
		s.Sources = append(s.Sources, info)
	}
	// Cup round numbering changes across seasons; the largest round is the final.
	maxRound := map[int]int{}
	for _, m := range s.Matches {
		if m.Competition == "Copa do Brasil" {
			n, _ := strconv.Atoi(m.Round)
			if n > maxRound[m.Season] {
				maxRound[m.Season] = n
			}
		}
	}
	// Only infer terminal rounds when the highest round contains one two-legged tie.
	terminal := map[int][]Match{}
	for _, m := range s.Matches {
		if m.Competition == "Copa do Brasil" {
			n, _ := strconv.Atoi(m.Round)
			if n == maxRound[m.Season] && n > 0 {
				terminal[m.Season] = append(terminal[m.Season], m)
			}
		}
	}
	for y, ms := range terminal {
		if len(ms) != 2 || ms[0].Home != ms[1].Away || ms[0].Away != ms[1].Home {
			delete(maxRound, y)
		}
	}
	for i := range s.Matches {
		m := &s.Matches[i]
		if m.Competition == "Copa do Brasil" && m.Stage == "" {
			n, _ := strconv.Atoi(m.Round)
			if n > 0 && maxRound[m.Season] > 0 {
				switch maxRound[m.Season] - n {
				case 0:
					m.Stage = "final"
				case 1:
					m.Stage = "semifinals"
				case 2:
					m.Stage = "quarterfinals"
				}
			}
		}
		s.teams[m.Home] = append(s.teams[m.Home], i)
		s.teams[m.Away] = append(s.teams[m.Away], i)
	}
	for i, p := range s.Players {
		s.playersByClub[NormalizeTeam(p.Club)] = append(s.playersByClub[NormalizeTeam(p.Club)], i)
	}
	return s, nil
}
func matchFromRow(file string, r map[string]string) (Match, error) {
	m := Match{Home: NormalizeTeam(value(r, "home_team", "home", "Equipe_mandante")), Away: NormalizeTeam(value(r, "away_team", "away", "Equipe_visitante")), Round: value(r, "round", "Rodada"), Stage: r["stage"], Stadium: r["Arena"]}
	if m.Home == "" || m.Away == "" {
		return m, fmt.Errorf("empty team")
	}
	var err error
	dateValue := value(r, "datetime", "date", "Data")
	if dateValue != "" && strings.ToUpper(dateValue) != "NA" {
		m.day, err = parseDate(dateValue)
		if err != nil {
			return m, err
		}
		m.Date = m.day.Format("2006-01-02")
		m.Season = m.day.Year()
	}
	if v := value(r, "season", "Ano"); v != "" && strings.ToUpper(v) != "NA" {
		m.Season, err = number(v)
		if err != nil {
			return m, err
		}
	}
	m.HomeGoals, err = score(value(r, "home_goal", "Gols_mandante"))
	if err != nil {
		return m, err
	}
	m.AwayGoals, err = score(value(r, "away_goal", "Gols_visitante"))
	if err != nil {
		return m, err
	}
	if (m.HomeGoals == nil) != (m.AwayGoals == nil) {
		return m, fmt.Errorf("only one score is present")
	}
	switch file {
	case "Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv":
		m.Competition = "Brasileirão"
	case "Brazilian_Cup_Matches.csv":
		m.Competition = "Copa do Brasil"
	case "Libertadores_Matches.csv":
		m.Competition = "Libertadores"
	default:
		m.Competition = competition(r["tournament"])
	}
	return m, nil
}
func sortedKeys[V any](m map[string]V) []string {
	k := make([]string, 0, len(m))
	for x := range m {
		k = append(k, x)
	}
	sort.Strings(k)
	return k
}
