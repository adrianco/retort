package loader

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// Match represents a single match from any competition.
type Match struct {
	Competition string
	HomeTeam    string
	AwayTeam    string
	HomeGoal    int
	AwayGoal    int
	Season      int
	Date        time.Time
	Round       string
	Stage       string
}

// Player represents a FIFA dataset player record.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
	JerseyNumber int
}

// Dataset holds all loaded data.
type Dataset struct {
	Matches []Match
	Players []Player
}

// Load reads all CSV files from dir and returns a combined dataset.
func Load(dir string) (*Dataset, error) {
	ds := &Dataset{}

	loaders := []struct {
		file string
		fn   func(*Dataset, string) error
	}{
		{"Brasileirao_Matches.csv", loadBrasileiraoMatches},
		{"Brazilian_Cup_Matches.csv", loadCupMatches},
		{"Libertadores_Matches.csv", loadLibertadoresMatches},
		{"novo_campeonato_brasileiro.csv", loadNovoCampeonato},
		{"BR-Football-Dataset.csv", loadBRFootball},
		{"fifa_data.csv", loadFIFA},
	}

	for _, l := range loaders {
		path := filepath.Join(dir, l.file)
		if err := l.fn(ds, path); err != nil {
			return nil, fmt.Errorf("loading %s: %w", l.file, err)
		}
	}

	return ds, nil
}

func openCSV(path string) (*csv.Reader, *os.File, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.TrimLeadingSpace = true
	return r, f, nil
}

func parseGoals(s string) int {
	s = strings.TrimSpace(s)
	n, _ := strconv.Atoi(s)
	return n
}

func parseSeason(s string) int {
	s = strings.TrimSpace(s)
	n, _ := strconv.Atoi(s)
	return n
}

var dateFormats = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02",
	"02/01/2006",
	"01/02/2006",
}

func parseDate(s string) time.Time {
	s = strings.TrimSpace(s)
	for _, f := range dateFormats {
		if t, err := time.Parse(f, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

// NormalizeTeam strips state suffixes and trims spaces.
func NormalizeTeam(name string) string {
	name = strings.TrimSpace(name)
	// Remove state suffix like "-SP", "-RJ", " - MG", etc.
	if idx := strings.LastIndex(name, "-"); idx > 0 {
		suffix := strings.TrimSpace(name[idx+1:])
		// State abbreviations are 2 uppercase letters
		if len(suffix) == 2 && strings.ToUpper(suffix) == suffix {
			name = strings.TrimSpace(name[:idx])
		}
	}
	// Also handle " - STATE" pattern
	if idx := strings.Index(name, " - "); idx > 0 {
		suffix := strings.TrimSpace(name[idx+3:])
		if len(suffix) == 2 && strings.ToUpper(suffix) == suffix {
			name = strings.TrimSpace(name[:idx])
		}
	}
	return name
}

func loadBrasileiraoMatches(ds *Dataset, path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Competition: "Brasileirao Serie A",
			HomeTeam:    NormalizeTeam(getField(row, idx, "home_team")),
			AwayTeam:    NormalizeTeam(getField(row, idx, "away_team")),
			HomeGoal:    parseGoals(getField(row, idx, "home_goal")),
			AwayGoal:    parseGoals(getField(row, idx, "away_goal")),
			Season:      parseSeason(getField(row, idx, "season")),
			Date:        parseDate(getField(row, idx, "datetime")),
			Round:       getField(row, idx, "round"),
		}
		ds.Matches = append(ds.Matches, m)
	}
	return nil
}

func loadCupMatches(ds *Dataset, path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Competition: "Copa do Brasil",
			HomeTeam:    NormalizeTeam(getField(row, idx, "home_team")),
			AwayTeam:    NormalizeTeam(getField(row, idx, "away_team")),
			HomeGoal:    parseGoals(getField(row, idx, "home_goal")),
			AwayGoal:    parseGoals(getField(row, idx, "away_goal")),
			Season:      parseSeason(getField(row, idx, "season")),
			Date:        parseDate(getField(row, idx, "datetime")),
			Round:       getField(row, idx, "round"),
		}
		ds.Matches = append(ds.Matches, m)
	}
	return nil
}

func loadLibertadoresMatches(ds *Dataset, path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Competition: "Copa Libertadores",
			HomeTeam:    NormalizeTeam(getField(row, idx, "home_team")),
			AwayTeam:    NormalizeTeam(getField(row, idx, "away_team")),
			HomeGoal:    parseGoals(getField(row, idx, "home_goal")),
			AwayGoal:    parseGoals(getField(row, idx, "away_goal")),
			Season:      parseSeason(getField(row, idx, "season")),
			Date:        parseDate(getField(row, idx, "datetime")),
			Stage:       getField(row, idx, "stage"),
		}
		ds.Matches = append(ds.Matches, m)
	}
	return nil
}

func loadNovoCampeonato(ds *Dataset, path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Competition: "Brasileirao Serie A",
			HomeTeam:    NormalizeTeam(getField(row, idx, "Equipe_mandante")),
			AwayTeam:    NormalizeTeam(getField(row, idx, "Equipe_visitante")),
			HomeGoal:    parseGoals(getField(row, idx, "Gols_mandante")),
			AwayGoal:    parseGoals(getField(row, idx, "Gols_visitante")),
			Season:      parseSeason(getField(row, idx, "Ano")),
			Date:        parseDate(getField(row, idx, "Data")),
			Round:       getField(row, idx, "Rodada"),
		}
		// skip rows where we couldn't parse a season (header re-rows etc)
		if m.Season == 0 {
			continue
		}
		ds.Matches = append(ds.Matches, m)
	}
	return nil
}

func loadBRFootball(ds *Dataset, path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(header)

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		dateStr := getField(row, idx, "date")
		t := parseDate(dateStr)
		season := t.Year()
		if season == 0 {
			continue
		}

		tournament := getField(row, idx, "tournament")
		// Map tournament names to our canonical names
		comp := normalizeTournament(tournament)

		homeGoalF := parseGoals(strings.Split(getField(row, idx, "home_goal"), ".")[0])
		awayGoalF := parseGoals(strings.Split(getField(row, idx, "away_goal"), ".")[0])

		m := Match{
			Competition: comp,
			HomeTeam:    NormalizeTeam(getField(row, idx, "home")),
			AwayTeam:    NormalizeTeam(getField(row, idx, "away")),
			HomeGoal:    homeGoalF,
			AwayGoal:    awayGoalF,
			Season:      season,
			Date:        t,
		}
		ds.Matches = append(ds.Matches, m)
	}
	return nil
}

func normalizeTournament(t string) string {
	tl := strings.ToLower(strings.TrimSpace(t))
	switch {
	case strings.Contains(tl, "brasileirao") || strings.Contains(tl, "serie a") || tl == "brasileirão série a":
		return "Brasileirao Serie A"
	case strings.Contains(tl, "copa do brasil"):
		return "Copa do Brasil"
	case strings.Contains(tl, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(tl, "copa sul-americana") || strings.Contains(tl, "sulamericana"):
		return "Copa Sulamericana"
	default:
		return t
	}
}

func loadFIFA(ds *Dataset, path string) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()

	// Skip BOM if present
	r.FieldsPerRecord = -1

	header, err := r.Read()
	if err != nil {
		return err
	}
	// Strip BOM from first header field
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\xef\xbb\xbf")
		header[0] = strings.TrimLeft(header[0], "\x00\xff\xfe ")
	}
	idx := headerIndex(header)

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		idStr := getField(row, idx, "ID")
		id, _ := strconv.Atoi(strings.TrimSpace(idStr))
		age, _ := strconv.Atoi(strings.TrimSpace(getField(row, idx, "Age")))
		overall, _ := strconv.Atoi(strings.TrimSpace(getField(row, idx, "Overall")))
		potential, _ := strconv.Atoi(strings.TrimSpace(getField(row, idx, "Potential")))
		jerseyStr := strings.TrimSpace(getField(row, idx, "Jersey Number"))
		jersey, _ := strconv.Atoi(jerseyStr)

		p := Player{
			ID:           id,
			Name:         strings.TrimSpace(getField(row, idx, "Name")),
			Age:          age,
			Nationality:  strings.TrimSpace(getField(row, idx, "Nationality")),
			Overall:      overall,
			Potential:    potential,
			Club:         strings.TrimSpace(getField(row, idx, "Club")),
			Position:     strings.TrimSpace(getField(row, idx, "Position")),
			JerseyNumber: jersey,
		}
		if p.Name == "" {
			continue
		}
		ds.Players = append(ds.Players, p)
	}
	return nil
}

func headerIndex(header []string) map[string]int {
	m := make(map[string]int, len(header))
	for i, h := range header {
		h = strings.TrimSpace(h)
		h = strings.Trim(h, "\"")
		m[h] = i
	}
	return m
}

func getField(row []string, idx map[string]int, name string) string {
	i, ok := idx[name]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.Trim(strings.TrimSpace(row[i]), "\"")
}
