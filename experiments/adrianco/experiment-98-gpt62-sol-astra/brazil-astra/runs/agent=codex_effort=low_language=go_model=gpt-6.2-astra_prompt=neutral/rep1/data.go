package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

type Row map[string]string
type Match struct {
	Date, Season, Competition, Round, Stage, Home, Away string
	HomeGoals, AwayGoals                                *int
	Sources                                             map[string]Row
}
type Player struct {
	row                Row
	name, club, nation string
	rating             int
}
type Graph struct {
	Matches []*Match
	Players []Player
}

var files = []string{"novo_campeonato_brasileiro.csv", "Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "fifa_data.csv"}
var accents = strings.NewReplacer("á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "é", "e", "ê", "e", "è", "e", "í", "i", "ï", "i", "ó", "o", "ô", "o", "õ", "o", "ö", "o", "ú", "u", "ü", "u", "ç", "c", "ñ", "n", "-", " ")

func fold(s string) string {
	return strings.Join(strings.Fields(accents.Replace(strings.ToLower(s))), " ")
}

var aliases = map[string]string{"sport club do recife": "sport", "america fc (minas gerais)": "america mg", "ceara sporting club": "ceara", "sport club corinthians paulista": "corinthians",
	"sao paulo fc":                  "sao paulo",
	"sao paulo futebol clube":       "sao paulo",
	"clube de regatas do flamengo":  "flamengo",
	"sociedade esportiva palmeiras": "palmeiras",
	"santos fc":                     "santos",
	"atletico mineiro":              "atletico mg",
	"athletico pr":                  "atletico pr",
	"atletico paranaense":           "atletico pr",
	"athletico paranaense":          "atletico pr",
	"athletico":                     "atletico pr",
	"atletico goianiense":           "atletico go",
	"vasco":                         "vasco da gama",
	"botafogo":                      "botafogo rj",
	"red bull bragantino":           "bragantino",
	"sport recife":                  "sport",
	"nautico capibaribe":            "nautico",
	"ec bahia":                      "bahia",
	"ec juventude":                  "juventude",
	"santa cruz fc":                 "santa cruz",
	"fortaleza fc":                  "fortaleza"}

func team(s string) string {
	k := fold(s)
	idx := strings.LastIndexByte(k, ' ')
	state := k[idx+1:]
	if idx >= 0 && strings.Contains(" ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to ", " "+state+" ") {
		b := strings.TrimSuffix(k, " "+state)
		switch b {
		case "atletico", "athletico", "america", "botafogo", "nacional", "operario", "river", "ferroviario":
		default:
			k = b
		}
	}
	if a := aliases[k]; a != "" {
		return a
	}
	return k
}
func competition(s string) string {
	switch fold(s) {
	case "brasileirao", "brasileirao serie a", "serie a", "campeonato brasileiro":
		return "Serie A"
	case "libertadores", "copa libertadores":
		return "Copa Libertadores"
	case "copa do brasil", "brazilian cup":
		return "Copa do Brasil"
	case "serie b":
		return "Serie B"
	case "serie c":
		return "Serie C"
	}
	return s
}
func day(s string) string {
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006"} {
		if d, e := time.Parse(layout, s); e == nil {
			return d.Format("2006-01-02")
		}
	}
	return ""
}
func goals(s string) *int {
	n, e := strconv.Atoi(strings.TrimSuffix(s, ".0"))
	if e != nil || n < 0 {
		return nil
	}
	return &n
}
func readRows(path string, visit func(Row)) error {
	f, e := os.Open(path)
	if e != nil {
		return e
	}
	defer f.Close()
	r := csv.NewReader(f)
	h, e := r.Read()
	if e != nil {
		return e
	}
	for {
		v, e := r.Read()
		if e == io.EOF {
			return nil
		}
		if e != nil {
			return e
		}
		row := make(Row, len(h))
		for i, k := range h {
			row[strings.TrimPrefix(k, "\ufeff")] = v[i]
		}
		visit(row)
	}
}
func parseMatch(i int, r Row) *Match {
	m := &Match{Date: day(r["datetime"]), Season: r["season"], Competition: "Serie A", Round: r["round"], Stage: r["stage"], Home: r["home_team"], Away: r["away_team"], HomeGoals: goals(r["home_goal"]), AwayGoals: goals(r["away_goal"]), Sources: map[string]Row{files[i]: r}}
	switch i {
	case 0:
		m.Date = day(r["Data"])
		m.Season = r["Ano"]
		m.Round = r["Rodada"]
		m.Home = r["Equipe_mandante"]
		m.Away = r["Equipe_visitante"]
		m.HomeGoals = goals(r["Gols_mandante"])
		m.AwayGoals = goals(r["Gols_visitante"])
	case 2:
		m.Competition = "Copa do Brasil"
		final := map[string]string{"2012": "6", "2016": "7"}[m.Season]
		if final == "" {
			final = "8"
		}
		if m.Round == final {
			m.Stage = "final"
		}
	case 3:
		m.Competition = "Copa Libertadores"
	case 4:
		m.Competition = competition(r["tournament"])
		m.Date = day(r["date"])
		m.Season = strings.Split(m.Date, "-")[0]
		m.Home = r["home"]
		m.Away = r["away"]
	}
	m.Home = team(m.Home)
	m.Away = team(m.Away)
	return m
}
func Load(dir string) (*Graph, error) {
	g := new(Graph)
	pairs := map[[3]string][]*Match{}
	for i, file := range files {
		e := readRows(filepath.Join(dir, file), func(r Row) {
			if i == 5 {
				n, _ := strconv.Atoi(r["Overall"])
				g.Players = append(g.Players, Player{r, fold(r["Name"]), team(r["Club"]), fold(r["Nationality"]), n})
				return
			}
			m := parseMatch(i, r)
			key := [3]string{m.Competition, m.Home, m.Away}
			d, _ := time.Parse("2006-01-02", m.Date)
			for _, old := range pairs[key] {
				if old.Sources[file] != nil {
					continue
				}
				od, _ := time.Parse("2006-01-02", old.Date)
				diff := d.Sub(od).Hours()
				if (m.Date != "" && diff >= -24 && diff <= 24) || (m.Competition == "Serie A" && old.Season == m.Season && (i != 4 || diff > -24*180 && diff < 24*180)) {
					old.Sources[file] = r
					if old.HomeGoals == nil && m.HomeGoals != nil {
						old.HomeGoals = m.HomeGoals
						old.AwayGoals = m.AwayGoals
					}
					return
				}
			}
			pairs[key] = append(pairs[key], m)
			g.Matches = append(g.Matches, m)
		})
		if e != nil {
			return nil, fmt.Errorf("%s: %w", file, e)
		}
	}
	sort.SliceStable(g.Matches, func(i, j int) bool { return g.Matches[i].Date > g.Matches[j].Date })
	// The extended file lacks rounds. In these three cup editions the final
	// consists of the last two fixtures, played with the venues reversed.
	for _, season := range []string{"2021", "2022", "2023"} {
		var legs []*Match
		for _, m := range g.Matches {
			if m.Competition == "Copa do Brasil" && m.Season == season {
				legs = append(legs, m)
				if len(legs) == 2 {
					break
				}
			}
		}
		if len(legs) == 2 && legs[0].Home == legs[1].Away && legs[0].Away == legs[1].Home {
			for _, leg := range legs {
				leg.Stage = "final"
			}
		}
	}
	sort.SliceStable(g.Players, func(i, j int) bool { return g.Players[i].rating > g.Players[j].rating })
	return g, nil
}
