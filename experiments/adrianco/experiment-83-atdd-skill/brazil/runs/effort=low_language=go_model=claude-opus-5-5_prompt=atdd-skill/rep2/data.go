package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
	"unicode"

	"golang.org/x/text/unicode/norm"
)

// Match is a single played match from any of the provided datasets.
type Match struct {
	Date        time.Time
	Home, Away  string
	HomeGoals   int
	AwayGoals   int
	Competition string
	Season      int
	Round       string
	Stage       string
	Arena       string
	Source      string
}

// Player is a FIFA player record.
type Player struct {
	Name, Nationality, Club, Position string
	Age, Overall, Potential, Jersey   int
	Height, Weight                    string
}

// Store holds all loaded data.
type Store struct {
	Matches []Match
	Players []Player
	Files   map[string]int
}

var (
	suffixRe = regexp.MustCompile(`\s*-\s*[A-Za-z]{2,3}$`)
	parenRe  = regexp.MustCompile(`\s*\([^)]*\)`)
	spaceRe  = regexp.MustCompile(`\s+`)
)

func stripAccents(s string) string {
	var b strings.Builder
	for _, r := range norm.NFD.String(s) {
		if unicode.Is(unicode.Mn, r) {
			continue
		}
		b.WriteRune(r)
	}
	return b.String()
}

var aliases = map[string]string{
	"athletico paranaense": "athletico", "atletico paranaense": "athletico", "atletico pr": "athletico",
	"atletico mineiro": "atletico mg", "sport club corinthians paulista": "corinthians",
	"sao paulo fc": "sao paulo", "vasco da gama": "vasco", "gremio fbpa": "gremio",
	"sociedade esportiva palmeiras": "palmeiras", "clube de regatas do flamengo": "flamengo",
}

// TeamKey normalizes a team name so different datasets' spellings compare equal.
func TeamKey(name string) string {
	s := strings.TrimSpace(name)
	lower := strings.ToLower(stripAccents(s))
	if strings.HasPrefix(lower, "atletico-mg") || strings.HasPrefix(lower, "atletico - mg") {
		return "atletico mg"
	}
	s = parenRe.ReplaceAllString(s, "")
	s = suffixRe.ReplaceAllString(s, "")
	s = strings.ToLower(stripAccents(s))
	s = strings.NewReplacer("-", " ", ".", " ").Replace(s)
	s = strings.TrimSpace(spaceRe.ReplaceAllString(s, " "))
	if a, ok := aliases[s]; ok {
		return a
	}
	return s
}

// DisplayName strips state suffixes for presentation.
func DisplayName(name string) string {
	s := strings.TrimSpace(suffixRe.ReplaceAllString(strings.TrimSpace(name), ""))
	if strings.HasPrefix(strings.ToLower(stripAccents(name)), "atletico-mg") {
		return "Atlético-MG"
	}
	return s
}

// TeamMatches reports whether a team name matches a user query.
func TeamMatches(team, query string) bool {
	t, q := TeamKey(team), TeamKey(query)
	if q == "" {
		return true
	}
	if t == q {
		return true
	}
	return strings.HasPrefix(t, q+" ") || strings.HasSuffix(t, " "+q) || strings.Contains(t, " "+q+" ")
}

func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	for _, f := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", "2006-01-02T15:04:05"} {
		if t, err := time.Parse(f, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

func atoi(s string) int {
	s = strings.TrimSpace(s)
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return 0
}

func readCSV(path string) ([]map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	recs, err := r.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	if len(recs) == 0 {
		return nil, nil
	}
	hdr := recs[0]
	for i := range hdr {
		hdr[i] = strings.TrimSpace(strings.TrimPrefix(hdr[i], "\ufeff"))
	}
	out := make([]map[string]string, 0, len(recs)-1)
	for _, rec := range recs[1:] {
		m := make(map[string]string, len(hdr))
		for i, h := range hdr {
			if i < len(rec) {
				m[h] = rec[i]
			}
		}
		out = append(out, m)
	}
	return out, nil
}

// Load reads all six datasets from dir.
func Load(dir string) (*Store, error) {
	st := &Store{Files: map[string]int{}}
	seen := map[string]bool{}
	covered := map[string]bool{} // competition|season already provided by a richer source
	var fileCovered map[string]bool
	add := func(m Match) {
		if m.Date.IsZero() {
			return
		}
		ck := fmt.Sprintf("%s|%d", m.Competition, m.Season)
		if covered[ck] {
			return
		}
		if m.Source == "BR-Football-Dataset.csv" && m.Date.Month() <= 2 && covered[fmt.Sprintf("%s|%d", m.Competition, m.Season-1)] {
			return
		}
		fileCovered[ck] = true
		key := m.Date.Format("2006-01-02") + "|" + TeamKey(m.Home) + "|" + TeamKey(m.Away)
		if seen[key] {
			return
		}
		seen[key] = true
		st.Matches = append(st.Matches, m)
	}
	type loader struct {
		file string
		fn   func(r map[string]string)
	}
	loaders := []loader{
		{"Brasileirao_Matches.csv", func(r map[string]string) {
			add(Match{Date: parseDate(r["datetime"]), Home: r["home_team"], Away: r["away_team"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]),
				Competition: "Brasileirão", Season: atoi(r["season"]), Round: r["round"], Source: "Brasileirao_Matches.csv"})
		}},
		{"novo_campeonato_brasileiro.csv", func(r map[string]string) {
			add(Match{Date: parseDate(r["Data"]), Home: r["Equipe_mandante"], Away: r["Equipe_visitante"], HomeGoals: atoi(r["Gols_mandante"]), AwayGoals: atoi(r["Gols_visitante"]),
				Competition: "Brasileirão", Season: atoi(r["Ano"]), Round: r["Rodada"], Arena: r["Arena"], Source: "novo_campeonato_brasileiro.csv"})
		}},
		{"Brazilian_Cup_Matches.csv", func(r map[string]string) {
			add(Match{Date: parseDate(r["datetime"]), Home: r["home_team"], Away: r["away_team"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]),
				Competition: "Copa do Brasil", Season: atoi(r["season"]), Round: r["round"], Source: "Brazilian_Cup_Matches.csv"})
		}},
		{"Libertadores_Matches.csv", func(r map[string]string) {
			add(Match{Date: parseDate(r["datetime"]), Home: r["home_team"], Away: r["away_team"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]),
				Competition: "Libertadores", Season: atoi(r["season"]), Stage: r["stage"], Source: "Libertadores_Matches.csv"})
		}},
		{"BR-Football-Dataset.csv", func(r map[string]string) {
			comp := r["tournament"]
			if comp == "Serie A" {
				comp = "Brasileirão"
			}
			d := parseDate(r["date"])
			add(Match{Date: d, Home: r["home"], Away: r["away"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]),
				Competition: comp, Season: d.Year(), Source: "BR-Football-Dataset.csv"})
		}},
	}
	for _, l := range loaders {
		rows, err := readCSV(filepath.Join(dir, l.file))
		if err != nil {
			return nil, err
		}
		st.Files[l.file] = len(rows)
		fileCovered = map[string]bool{}
		for _, r := range rows {
			l.fn(r)
		}
		for k := range fileCovered {
			covered[k] = true
		}
	}
	rows, err := readCSV(filepath.Join(dir, "fifa_data.csv"))
	if err != nil {
		return nil, err
	}
	st.Files["fifa_data.csv"] = len(rows)
	for _, r := range rows {
		st.Players = append(st.Players, Player{Name: r["Name"], Nationality: r["Nationality"], Club: r["Club"], Position: r["Position"],
			Age: atoi(r["Age"]), Overall: atoi(r["Overall"]), Potential: atoi(r["Potential"]), Jersey: atoi(r["Jersey Number"]), Height: r["Height"], Weight: r["Weight"]})
	}
	return st, nil
}
