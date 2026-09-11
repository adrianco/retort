package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

type Match struct {
	ID          string              `json:"id"`
	Date        string              `json:"date"`
	Home        string              `json:"home"`
	Away        string              `json:"away"`
	HomeGoals   *int                `json:"home_goals"`
	AwayGoals   *int                `json:"away_goals"`
	Competition string              `json:"competition"`
	Season      int                 `json:"season"`
	Round       string              `json:"round,omitempty"`
	Stage       string              `json:"stage,omitempty"`
	Sources     []string            `json:"sources"`
	Records     []map[string]string `json:"records"`
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
type Graph struct {
	Matches  []Match
	Players  []Player
	Sources  map[string]int
	Warnings []string
}

var accents = strings.NewReplacer("á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "é", "e", "ê", "e", "è", "e", "í", "i", "ó", "o", "ô", "o", "õ", "o", "ö", "o", "ú", "u", "ü", "u", "ç", "c")

func fold(s string) string {
	return strings.Join(strings.Fields(accents.Replace(strings.ToLower(strings.TrimSpace(s)))), " ")
}

var suffix = regexp.MustCompile(`\s*-\s*(ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to)$`)

func team(s string) string {
	s = fold(s)
	special := map[string]string{"atletico-mg": "atletico-mg", "atletico - mg": "atletico-mg", "atletico-pr": "athletico-pr", "atletico - pr": "athletico-pr", "athletico-pr": "athletico-pr", "athletico": "athletico-pr", "america-mg": "america-mg", "america - mg": "america-mg", "america-rn": "america-rn", "america - rn": "america-rn", "botafogo-sp": "botafogo-sp", "botafogo - sp": "botafogo-sp", "atletico-go": "atletico-go", "atletico - go": "atletico-go"}
	if v, ok := special[s]; ok {
		return v
	}
	s = suffix.ReplaceAllString(s, "")
	aliases := map[string]string{"fortaleza fc": "fortaleza", "ec bahia": "bahia", "vasco da gama rj": "vasco", "botafogo rj": "botafogo", "sport recife": "sport", "sport club do recife": "sport", "atletico goianiense": "atletico-go", "gremio porto alegre": "gremio", "sport club corinthians paulista": "corinthians", "sc corinthians": "corinthians", "clube de regatas do flamengo": "flamengo", "sao paulo fc": "sao paulo", "são paulo": "sao paulo", "sociedade esportiva palmeiras": "palmeiras", "santos fc": "santos", "vasco da gama": "vasco", "atletico mineiro": "atletico-mg", "atletico paranaense": "athletico-pr", "athletico paranaense": "athletico-pr", "atletico pr": "athletico-pr", "atletico mg": "atletico-mg", "gremio foot-ball porto alegrense": "gremio", "america mineiro": "america-mg"}
	// Preserve state qualifiers for clubs whose names would otherwise collide.
	original := fold(s)
	if v, ok := aliases[original]; ok {
		return v
	}
	return s
}
func competition(s string) string {
	f := fold(s)
	switch {
	case strings.Contains(f, "libertadores"):
		return "Libertadores"
	case strings.Contains(f, "copa do brasil"):
		return "Copa do Brasil"
	case f == "brasileirao" || strings.Contains(f, "serie a") || f == "brasileirao serie a":
		return "Brasileirão"
	}
	return strings.TrimSpace(s)
}
func parseDate(s string) (string, error) {
	for _, layout := range []string{time.RFC3339, "2006-01-02 15:04:05", "2006-01-02", "02/01/2006", "2006-01-02 15:04", "02/01/2006 15:04:05"} {
		if d, e := time.Parse(layout, strings.TrimSpace(s)); e == nil {
			return d.Format("2006-01-02"), nil
		}
	}
	return "", fmt.Errorf("invalid date %q", s)
}
func score(s string) *int {
	f, e := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if e != nil || math.IsNaN(f) || math.IsInf(f, 0) || f < 0 || math.Trunc(f) != f {
		return nil
	}
	n := int(f)
	return &n
}
func integer(s string) int { n, _ := strconv.Atoi(s); return n }
func Load(dir string) (*Graph, error) {
	g := &Graph{Sources: map[string]int{}, Warnings: []string{}}
	seen := map[string]int{}
	files := []string{"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv", "fifa_data.csv"}
	for _, name := range files {
		err := func() error {
			f, e := os.Open(filepath.Join(dir, name))
			if e != nil {
				return e
			}
			defer f.Close()
			r := csv.NewReader(f)
			header, e := r.Read()
			if e != nil {
				return e
			}
			for i := range header {
				header[i] = strings.TrimPrefix(header[i], "\ufeff")
			}
			g.Sources[name] = 0
			for line := 2; ; line++ {
				cells, e := r.Read()
				if e == io.EOF {
					break
				}
				if e != nil {
					return fmt.Errorf("%s row %d: %w", name, line, e)
				}
				row := map[string]string{}
				for i, k := range header {
					row[k] = cells[i]
				}
				g.Sources[name]++
				if name == "fifa_data.csv" {
					if row["ID"] == "" || row["Name"] == "" {
						return fmt.Errorf("missing player ID/name")
					}
					g.Players = append(g.Players, Player{row["ID"], row["Name"], team(row["Club"]), row["Nationality"], row["Position"], integer(row["Overall"]), row})
					continue
				}
				m := Match{ID: fmt.Sprintf("%s:%d", name, line), Home: team(row["home_team"]), Away: team(row["away_team"]), HomeGoals: score(row["home_goal"]), AwayGoals: score(row["away_goal"]), Season: integer(row["season"]), Round: row["round"], Stage: row["stage"], Sources: []string{name}, Records: []map[string]string{row}}
				date := row["datetime"]
				switch name {
				case files[0]:
					m.Competition = "Brasileirão"
				case files[1]:
					m.Competition = "Copa do Brasil"
				case files[2]:
					m.Competition = "Libertadores"
				case files[3]:
					m.Competition = competition(row["tournament"])
					m.Home = team(row["home"])
					m.Away = team(row["away"])
					date = row["date"]
				case files[4]:
					m.Competition = "Brasileirão"
					m.Home = team(row["Equipe_mandante"])
					m.Away = team(row["Equipe_visitante"])
					m.HomeGoals = score(row["Gols_mandante"])
					m.AwayGoals = score(row["Gols_visitante"])
					m.Season = integer(row["Ano"])
					m.Round = row["Rodada"]
					date = row["Data"]
				}
				m.Date, e = parseDate(date)
				if e != nil {
					if fold(date) == "na" || strings.TrimSpace(date) == "" {
						g.Warnings = append(g.Warnings, "Unknown date: "+m.ID)
						m.Date = ""
					} else {
						return fmt.Errorf("%s row %d: %w", name, line, e)
					}
				}
				if m.Home == "" || m.Away == "" {
					return fmt.Errorf("%s row %d: missing team", name, line)
				}
				if m.Season == 0 && len(m.Date) >= 4 {
					m.Season = integer(m.Date[:4])
				}
				key := m.Competition + "|" + m.Date + "|" + m.Home + "|" + m.Away
				// Serie A is a double round robin: one fixture per ordered pair per season.
				// Sources disagree on dates (UTC versus local dates and rescheduling).
				if m.Competition == "Brasileirão" && m.Season > 0 {
					key = fmt.Sprintf("%s|%d|%s|%s", m.Competition, m.Season, m.Home, m.Away)
				}
				if idx, ok := seen[key]; ok {
					old := &g.Matches[idx]
					old.Sources = append(old.Sources, name)
					old.Records = append(old.Records, row)
					if old.Round == "" {
						old.Round = m.Round
					}
					if old.Stage == "" {
						old.Stage = m.Stage
					}
					if old.HomeGoals == nil || old.AwayGoals == nil {
						old.HomeGoals = m.HomeGoals
						old.AwayGoals = m.AwayGoals
					} else if m.HomeGoals != nil && m.AwayGoals != nil && (*old.HomeGoals != *m.HomeGoals || *old.AwayGoals != *m.AwayGoals) {
						g.Warnings = append(g.Warnings, "Conflicting score: "+key+"; retained first source")
					}
					continue
				}
				seen[key] = len(g.Matches)
				g.Matches = append(g.Matches, m)
			}
			return nil
		}()
		if err != nil {
			return nil, err
		}
	}
	return g, nil
}
