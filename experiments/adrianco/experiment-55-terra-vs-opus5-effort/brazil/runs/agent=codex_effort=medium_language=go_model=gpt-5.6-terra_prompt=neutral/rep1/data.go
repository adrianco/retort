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
	"unicode"
)

type Match struct {
	Date                 time.Time `json:"date"`
	Home, Away           string    `json:"home_team","away_team"`
	HomeGoals, AwayGoals int       `json:"home_goals","away_goals"`
	Competition          string    `json:"competition"`
	Season               int       `json:"season"`
	Round, Stage, Source string    `json:"round,omitempty","stage,omitempty","source"`
}
type Player struct {
	ID, Name, Nationality, Club, Position string
	Age, Overall, Potential               int
}
type Database struct {
	Matches []Match
	Players []Player
}

func LoadDatabase(dir string) (*Database, error) {
	db := &Database{}
	loaders := []struct {
		file string
		fn   func(*Database, map[string]string) error
	}{
		{"Brasileirao_Matches.csv", loadStandard("Brasileirao", "home_team", "away_team", "datetime", "round", "")},
		{"Brazilian_Cup_Matches.csv", loadStandard("Copa do Brasil", "home_team", "away_team", "datetime", "round", "")},
		{"Libertadores_Matches.csv", loadStandard("Libertadores", "home_team", "away_team", "datetime", "", "stage")},
		{"BR-Football-Dataset.csv", loadStandard("", "home", "away", "date", "", "")},
		{"novo_campeonato_brasileiro.csv", loadHistorical},
		{"fifa_data.csv", loadPlayers},
	}
	for _, l := range loaders {
		rows, err := csvRows(filepath.Join(dir, l.file))
		if err != nil {
			return nil, fmt.Errorf("load %s: %w", l.file, err)
		}
		start := len(db.Matches)
		for _, row := range rows {
			if err := l.fn(db, row); err != nil {
				return nil, fmt.Errorf("load %s: %w", l.file, err)
			}
		}
		for i := start; i < len(db.Matches); i++ {
			db.Matches[i].Source = l.file
		}
	}
	sort.Slice(db.Matches, func(i, j int) bool { return db.Matches[i].Date.After(db.Matches[j].Date) })
	sort.Slice(db.Players, func(i, j int) bool { return db.Players[i].Overall > db.Players[j].Overall })
	return db, nil
}
func csvRows(path string) ([]map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
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
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		row := map[string]string{}
		for i, v := range rec {
			if i < len(head) {
				row[head[i]] = strings.TrimSpace(v)
			}
		}
		out = append(out, row)
	}
	return out, nil
}
func loadStandard(defaultComp, homeKey, awayKey, dateKey, roundKey, stageKey string) func(*Database, map[string]string) error {
	return func(db *Database, r map[string]string) error {
		if isMissing(r[dateKey]) || isMissing(r[homeKey]) || isMissing(r[awayKey]) {
			return nil // A few Kaggle rows are explicit NA placeholders, not matches.
		}
		date, err := parseDate(r[dateKey])
		if err != nil {
			return err
		}
		comp := defaultComp
		if comp == "" {
			comp = r["tournament"]
		}
		if comp == "" {
			comp = "Unknown"
		}
		m := Match{Date: date, Home: r[homeKey], Away: r[awayKey], HomeGoals: parseNumber(r["home_goal"]), AwayGoals: parseNumber(r["away_goal"]), Competition: comp, Season: parseNumber(r["season"]), Round: r[roundKey], Stage: r[stageKey], Source: ""}
		if m.Season == 0 {
			m.Season = date.Year()
		}
		db.Matches = append(db.Matches, m)
		return nil
	}
}
func isMissing(s string) bool {
	s = strings.TrimSpace(strings.ToLower(s))
	return s == "" || s == "na" || s == "n/a" || s == "null"
}
func loadHistorical(db *Database, r map[string]string) error {
	d, err := parseDate(r["Data"])
	if err != nil {
		return err
	}
	db.Matches = append(db.Matches, Match{Date: d, Home: r["Equipe_mandante"], Away: r["Equipe_visitante"], HomeGoals: parseNumber(r["Gols_mandante"]), AwayGoals: parseNumber(r["Gols_visitante"]), Competition: "Brasileirao", Season: parseNumber(r["Ano"]), Round: r["Rodada"], Source: "historical"})
	return nil
}
func loadPlayers(db *Database, r map[string]string) error {
	db.Players = append(db.Players, Player{ID: r["ID"], Name: r["Name"], Nationality: r["Nationality"], Club: r["Club"], Position: r["Position"], Age: parseNumber(r["Age"]), Overall: parseNumber(r["Overall"]), Potential: parseNumber(r["Potential"])})
	return nil
}
func parseNumber(s string) int { f, _ := strconv.ParseFloat(strings.TrimSpace(s), 64); return int(f) }
func parseDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	for _, l := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", time.RFC3339} {
		if d, e := time.Parse(l, s); e == nil {
			return d, nil
		}
	}
	return time.Time{}, fmt.Errorf("invalid date %q", s)
}

var aliases = map[string]string{"sao paulo fc": "sao paulo", "sport club corinthians paulista": "corinthians", "cr flamengo": "flamengo", "gremio fbpa": "gremio", "atletico paranaense": "athletico pr", "atletico pr": "athletico pr"}

func normalize(s string) string {
	s = strings.ToLower(strings.TrimSpace(s))
	var b strings.Builder
	for _, r := range s {
		if unicode.Is(unicode.Mn, r) {
			continue
		} // decomposed accents
		// common precomposed Brazilian characters
		switch r {
		case 'á', 'à', 'â', 'ã', 'ä':
			r = 'a'
		case 'é', 'ê', 'ë':
			r = 'e'
		case 'í', 'ï':
			r = 'i'
		case 'ó', 'ô', 'õ', 'ö':
			r = 'o'
		case 'ú', 'ü':
			r = 'u'
		case 'ç':
			r = 'c'
		}
		if unicode.IsLetter(r) || unicode.IsDigit(r) || unicode.IsSpace(r) {
			b.WriteRune(r)
		} else {
			b.WriteByte(' ')
		}
	}
	s = strings.Join(strings.Fields(b.String()), " ")
	if a, ok := aliases[s]; ok {
		return a
	}
	return s
}
func teamMatches(query, name string) bool {
	q, n := matchTeamKey(query), matchTeamKey(name)
	return q != "" && (q == n || strings.Contains(n, q) || strings.Contains(q, n))
}

// Match names leniently without making standings conflate distinct teams such
// as Atlético-MG and Atlético-PR (normalization itself intentionally preserves
// state suffixes for that reason).
func matchTeamKey(s string) string {
	s = normalize(s)
	parts := strings.Fields(s)
	if len(parts) > 1 && len(parts[len(parts)-1]) == 2 {
		parts = parts[:len(parts)-1]
	}
	if len(parts) > 1 && parts[len(parts)-1] == "fc" {
		parts = parts[:len(parts)-1]
	}
	return strings.Join(parts, " ")
}
