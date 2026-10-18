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

type Match struct {
	ID          string            `json:"id"`
	Date        string            `json:"date"`
	Competition string            `json:"competition"`
	Season      int               `json:"season"`
	Round       string            `json:"round,omitempty"`
	Stage       string            `json:"stage,omitempty"`
	Home        string            `json:"home"`
	Away        string            `json:"away"`
	HomeGoals   *int              `json:"home_goals"`
	AwayGoals   *int              `json:"away_goals"`
	Stadium     string            `json:"stadium,omitempty"`
	Sources     []string          `json:"sources"`
	Attributes  map[string]string `json:"attributes,omitempty"`
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
type Store struct {
	Matches  []Match
	Players  []Player
	Counts   map[string]int
	Warnings []string
}

var files = []string{"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv", "fifa_data.csv"}
var accents = strings.NewReplacer("á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "é", "e", "ê", "e", "è", "e", "ë", "e", "í", "i", "ì", "i", "ï", "i", "ó", "o", "ô", "o", "õ", "o", "ö", "o", "ú", "u", "ü", "u", "ç", "c", "ñ", "n")

func fold(s string) string {
	s = accents.Replace(strings.ToLower(strings.TrimSpace(s)))
	s = strings.Map(func(r rune) rune {
		if unicode.Is(unicode.Mn, r) {
			return -1
		}
		return r
	}, s)
	return strings.Join(strings.FieldsFunc(s, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	}), " ")
}

var suffix = regexp.MustCompile(`(?i)\s*-\s*(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$`)
var aliases = map[string]string{
	"america fc minas gerais": "america mg", "ceara sporting club": "ceara",
	"botafogo rj": "botafogo", "vasco da gama rj": "vasco", "ec bahia": "bahia", "fortaleza fc": "fortaleza", "guarani sp": "guarani", "ec juventude": "juventude", "nautico capibaribe": "nautico", "santa cruz fc": "santa cruz", "clube do remo": "remo", "ad confianca": "confianca", "tombense mg": "tombense", "america mg": "america mg", "atletico mg": "atletico mg", "atletico pr": "atletico pr",

	"sport club corinthians paulista": "corinthians", "corinthians paulista": "corinthians", "clube de regatas do flamengo": "flamengo", "sociedade esportiva palmeiras": "palmeiras", "sao paulo fc": "sao paulo", "sao paulo futebol clube": "sao paulo", "santos fc": "santos", "gremio fbpa": "gremio", "gremio foot ball porto alegrense": "gremio", "sport club internacional": "internacional", "sport club do recife": "sport", "sport recife": "sport", "vasco da gama": "vasco", "cr vasco da gama": "vasco", "clube de regatas vasco da gama": "vasco", "botafogo de futebol e regatas": "botafogo", "fluminense football club": "fluminense", "cruzeiro esporte clube": "cruzeiro", "atletico mineiro": "atletico mg", "clube atletico mineiro": "atletico mg", "athletico pr": "atletico pr", "atletico paranaense": "atletico pr", "athletico paranaense": "atletico pr", "clube atletico paranaense": "atletico pr", "atletico goianiense": "atletico go", "america mineiro": "america mg", "america futebol clube mg": "america mg", "red bull bragantino": "bragantino", "rb bragantino": "bragantino", "ec vitoria": "vitoria", "esporte clube vitoria": "vitoria", "esporte clube bahia": "bahia", "figueirense fc": "figueirense", "chapecoense af": "chapecoense", "associacao chapecoense de futebol": "chapecoense"}

func team(s string) string {
	s = strings.TrimSpace(s)
	base := suffix.ReplaceAllString(s, "")
	k := fold(base)
	// These names are shared by distinct clubs; retain their state identity.
	if k == "america" || k == "atletico" || k == "athletico" || k == "botafogo" && strings.HasSuffix(fold(s), "sp") {
		k = fold(s)
	}
	if a, ok := aliases[k]; ok {
		return a
	}
	return k
}
func competition(s string) string {
	switch fold(s) {
	case "serie a", "brasileirao", "brasileirao serie a", "campeonato brasileiro", "brazil serie a":
		return "Brasileirão"
	case "copa do brasil", "brazilian cup":
		return "Copa do Brasil"
	case "libertadores", "copa libertadores":
		return "Libertadores"
	case "serie b":
		return "Série B"
	case "serie c":
		return "Série C"
	}
	return strings.TrimSpace(s)
}
func date(s string) (string, error) {
	s = strings.TrimSpace(s)
	for _, layout := range []string{time.RFC3339, "2006-01-02 15:04:05", "2006-01-02 15:04", "2006-01-02", "02/01/2006", "2/1/2006", "02/01/2006 15:04:05"} {
		if d, e := time.Parse(layout, s); e == nil {
			return d.Format("2006-01-02"), nil
		}
	}
	return "", fmt.Errorf("invalid date %q", s)
}
func number(s string) (*int, error) {
	if s == "" || s == "-" || s == "NA" || s == "NaN" || s == "nan" {
		return nil, nil
	}
	f, e := strconv.ParseFloat(s, 64)
	if e != nil || math.IsNaN(f) || math.IsInf(f, 0) || f < 0 || f != math.Trunc(f) || f > 1000000 {
		return nil, fmt.Errorf("invalid nonnegative integer %q", s)
	}
	n := int(f)
	return &n, nil
}
func integer(s string) int {
	n, _ := number(s)
	if n == nil {
		return 0
	}
	return *n
}
func Load(dir string) (*Store, error) {
	s := &Store{Counts: map[string]int{}, Warnings: []string{}}
	seen := map[string]int{}
	fixtureSeasons := map[string]int{}
	for fi, fn := range files {
		err := func() error {
			f, e := os.Open(filepath.Join(dir, fn))
			if e != nil {
				return e
			}
			defer f.Close()
			r := csv.NewReader(f)
			header, e := r.Read()
			if e != nil {
				return e
			}
			header[0] = strings.TrimPrefix(header[0], "\ufeff")
			required := [][]string{{"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round"}, {"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round"}, {"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "stage"}, {"tournament", "home", "away", "home_goal", "away_goal", "date"}, {"Data", "Ano", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante"}, {"ID", "Name", "Nationality", "Club", "Overall", "Potential", "Position"}}
			for _, key := range required[fi] {
				found := false
				for _, h := range header {
					if key == h {
						found = true
					}
				}
				if !found {
					return fmt.Errorf("missing column %s", key)
				}
			}
			for line := 2; ; line++ {
				row, e := r.Read()
				if e == io.EOF {
					break
				}
				if e != nil {
					return fmt.Errorf("row %d: %w", line, e)
				}
				a := map[string]string{}
				for i, h := range header {
					a[h] = strings.TrimSpace(row[i])
				}
				s.Counts[fn]++
				if fi == 5 {
					if a["ID"] == "" || a["Name"] == "" {
						return fmt.Errorf("row %d: missing player identity", line)
					}
					s.Players = append(s.Players, Player{a["ID"], a["Name"], a["Nationality"], team(a["Club"]), a["Position"], integer(a["Overall"]), integer(a["Potential"]), a})
					continue
				}
				m := Match{Sources: []string{fn}, Attributes: a, Round: a["round"], Stage: a["stage"]}
				ds, hg, ag := a["datetime"], a["home_goal"], a["away_goal"]
				m.Home, m.Away = team(a["home_team"]), team(a["away_team"])
				m.Season = integer(a["season"])
				switch fi {
				case 0:
					m.Competition = "Brasileirão"
				case 1:
					m.Competition = "Copa do Brasil"
				case 2:
					m.Competition = "Libertadores"
				case 3:
					m.Competition = competition(a["tournament"])
					m.Home, m.Away = team(a["home"]), team(a["away"])
					ds = a["date"]
				case 4:
					m.Competition = "Brasileirão"
					m.Home, m.Away = team(a["Equipe_mandante"]), team(a["Equipe_visitante"])
					ds = a["Data"]
					hg, ag = a["Gols_mandante"], a["Gols_visitante"]
					m.Season = integer(a["Ano"])
					m.Round = a["Rodada"]
					m.Stadium = a["Arena"]
				}
				if m.Home == "" || m.Away == "" {
					return fmt.Errorf("row %d: missing team", line)
				}
				if ds == "NA" || ds == "-" || ds == "" {
					m.Date = ""
					s.Warnings = append(s.Warnings, fmt.Sprintf("%s row %d: unknown match date", fn, line))
				} else {
					m.Date, e = date(ds)
				}
				if e != nil {
					return fmt.Errorf("row %d: %w", line, e)
				}
				if m.Season == 0 && len(m.Date) >= 4 {
					m.Season = integer(m.Date[:4])
				}
				m.HomeGoals, e = number(hg)
				if e != nil {
					return fmt.Errorf("row %d: %w", line, e)
				}
				m.AwayGoals, e = number(ag)
				if e != nil {
					return fmt.Errorf("row %d: %w", line, e)
				}
				// Extended statistics omit season; a calendar year is not always the
				// season year (the 2020 leagues continued into 2021). Prefer known
				// fixture season, tolerating a one-day timezone shift.
				if fi == 3 && m.Date != "" {
					day, _ := time.Parse("2006-01-02", m.Date)
					for _, delta := range []int{0, -1, 1} {
						dk := fmt.Sprintf("%s|%s|%s|%s", m.Competition, day.AddDate(0, 0, delta).Format("2006-01-02"), m.Home, m.Away)
						if season, ok := fixtureSeasons[dk]; ok {
							m.Season = season
							break
						}
					}
				}
				key := fmt.Sprintf("%s|%s|%s|%s", m.Competition, m.Date, m.Home, m.Away)
				fixtureSeasons[key] = m.Season
				// Serie A and B play each directed pairing once per season. Sources
				// disagree on dates (including UTC day shifts and rescheduling).
				if m.Competition == "Brasileirão" || m.Competition == "Série B" {
					key = fmt.Sprintf("%s|%d|%s|%s", m.Competition, m.Season, m.Home, m.Away)
				}
				if idx, ok := seen[key]; ok {
					old := &s.Matches[idx]
					old.Sources = append(old.Sources, fn)
					if old.HomeGoals != nil && old.AwayGoals != nil && m.HomeGoals != nil && m.AwayGoals != nil && (*old.HomeGoals != *m.HomeGoals || *old.AwayGoals != *m.AwayGoals) {
						s.Warnings = append(s.Warnings, "Conflicting scores: "+key+"; retained first source")
					}
					if old.HomeGoals == nil {
						old.HomeGoals = m.HomeGoals
					}
					if old.AwayGoals == nil {
						old.AwayGoals = m.AwayGoals
					}
					if old.Stadium == "" {
						old.Stadium = m.Stadium
					}
					if old.Round == "" {
						old.Round = m.Round
					}
					if old.Stage == "" {
						old.Stage = m.Stage
					}
					for k, v := range a {
						if old.Attributes[k] == "" {
							old.Attributes[k] = v
						}
					}
				} else {
					m.ID = fmt.Sprintf("match:%d", len(s.Matches)+1)
					seen[key] = len(s.Matches)
					s.Matches = append(s.Matches, m)
				}
			}
			return nil
		}()
		if err != nil {
			return nil, fmt.Errorf("%s: %w", fn, err)
		}
	}
	// The dedicated cup source numbers rounds differently across seasons.
	cupFinal := map[int]int{}
	for _, m := range s.Matches {
		if m.Competition == "Copa do Brasil" && contains(m.Sources, "Brazilian_Cup_Matches.csv") {
			if n := integer(m.Round); n > cupFinal[m.Season] {
				cupFinal[m.Season] = n
			}
		}
	}
	for i := range s.Matches {
		m := &s.Matches[i]
		if m.Competition == "Copa do Brasil" && contains(m.Sources, "Brazilian_Cup_Matches.csv") && integer(m.Round) == cupFinal[m.Season] {
			m.Stage = "final"
		}
	}
	sort.Slice(s.Matches, func(i, j int) bool {
		a, b := s.Matches[i], s.Matches[j]
		if a.Date != b.Date {
			return a.Date > b.Date
		}
		return a.ID < b.ID
	})
	sort.Slice(s.Players, func(i, j int) bool {
		a, b := s.Players[i], s.Players[j]
		if a.Overall != b.Overall {
			return a.Overall > b.Overall
		}
		return a.ID < b.ID
	})
	return s, nil
}
