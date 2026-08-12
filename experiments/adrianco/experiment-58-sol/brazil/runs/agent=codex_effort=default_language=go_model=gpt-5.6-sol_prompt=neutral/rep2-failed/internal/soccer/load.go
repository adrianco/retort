package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const (
	sourceBrasileirao  = "Brasileirao_Matches.csv"
	sourceCup          = "Brazilian_Cup_Matches.csv"
	sourceLibertadores = "Libertadores_Matches.csv"
	sourceExtended     = "BR-Football-Dataset.csv"
	sourceHistorical   = "novo_campeonato_brasileiro.csv"
	sourceFIFA         = "fifa_data.csv"
)

// LoadDir loads every required CSV. It fails if any source cannot be loaded so
// a server never starts with a silently incomplete knowledge base.
func LoadDir(dir string) (*Catalog, error) {
	c := &Catalog{Sources: make(map[string]SourceSummary)}
	matchLoaders := []struct {
		file string
		fn   func([]string, map[string]int) (Match, error)
	}{
		{sourceBrasileirao, parseBrasileirao}, {sourceCup, parseCup},
		{sourceLibertadores, parseLibertadores}, {sourceExtended, parseExtended},
		{sourceHistorical, parseHistorical},
	}
	for _, item := range matchLoaders {
		rows, err := readCSV(filepath.Join(dir, item.file))
		if err != nil {
			return nil, err
		}
		head := headerIndex(rows[0])
		start := len(c.Matches)
		for line, row := range rows[1:] {
			m, err := item.fn(row, head)
			if err != nil {
				return nil, fmt.Errorf("%s line %d: %w", item.file, line+2, err)
			}
			m.Source = item.file
			m.homeKey, m.awayKey = NormalizeTeam(m.HomeTeam), NormalizeTeam(m.AwayTeam)
			c.Matches = append(c.Matches, m)
		}
		c.Sources[item.file] = SourceSummary{File: item.file, Kind: "matches", Records: len(c.Matches) - start}
	}
	rows, err := readCSV(filepath.Join(dir, sourceFIFA))
	if err != nil {
		return nil, err
	}
	head := headerIndex(rows[0])
	for line, row := range rows[1:] {
		p, err := parsePlayer(row, head)
		if err != nil {
			return nil, fmt.Errorf("%s line %d: %w", sourceFIFA, line+2, err)
		}
		p.Source, p.nameKey, p.clubKey = sourceFIFA, searchKey(p.Name), NormalizeTeam(p.Club)
		c.Players = append(c.Players, p)
	}
	c.Sources[sourceFIFA] = SourceSummary{File: sourceFIFA, Kind: "players", Records: len(c.Players)}
	return c, nil
}

func readCSV(path string) ([][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.ReuseRecord = false
	rows, err := r.ReadAll()
	if err != nil && err != io.EOF {
		return nil, fmt.Errorf("read %s: %w", path, err)
	}
	if len(rows) < 2 {
		return nil, fmt.Errorf("%s has no data rows", path)
	}
	return rows, nil
}

func headerIndex(header []string) map[string]int {
	m := make(map[string]int, len(header))
	for i, h := range header {
		m[searchKey(h)] = i
	}
	return m
}

func field(row []string, h map[string]int, names ...string) string {
	for _, name := range names {
		if i, ok := h[searchKey(name)]; ok && i < len(row) {
			return strings.TrimSpace(row[i])
		}
	}
	return ""
}

func baseMatch(row []string, h map[string]int, home, away, homeGoals, awayGoals, date string) (Match, error) {
	dateValue := field(row, h, date)
	var t time.Time
	var err error
	if key := searchKey(dateValue); key != "" && key != "na" && key != "n a" && key != "null" {
		t, err = parseDate(dateValue)
		if err != nil {
			return Match{}, err
		}
	}
	hg, homeComplete, err := parseScore(field(row, h, homeGoals))
	if err != nil {
		return Match{}, fmt.Errorf("home goals: %w", err)
	}
	ag, awayComplete, err := parseScore(field(row, h, awayGoals))
	if err != nil {
		return Match{}, fmt.Errorf("away goals: %w", err)
	}
	dateText := ""
	if !t.IsZero() {
		dateText = t.Format("2006-01-02")
	}
	m := Match{Date: dateText, date: t, HomeTeam: field(row, h, home), AwayTeam: field(row, h, away), HomeGoals: hg, AwayGoals: ag, Completed: homeComplete && awayComplete, Season: t.Year()}
	if m.HomeTeam == "" || m.AwayTeam == "" {
		return Match{}, fmt.Errorf("missing team")
	}
	return m, nil
}

func parseScore(value string) (int, bool, error) {
	switch searchKey(value) {
	case "", "na", "n a", "null":
		return 0, false, nil
	}
	n, err := parseInt(value)
	return n, err == nil, err
}

func parseBrasileirao(row []string, h map[string]int) (Match, error) {
	m, err := baseMatch(row, h, "home_team", "away_team", "home_goal", "away_goal", "datetime")
	if err != nil {
		return m, err
	}
	m.Competition, m.Round = "Brasileirão Série A", field(row, h, "round")
	if s, _ := parseInt(field(row, h, "season")); s != 0 {
		m.Season = s
	}
	return m, nil
}

func parseCup(row []string, h map[string]int) (Match, error) {
	m, err := baseMatch(row, h, "home_team", "away_team", "home_goal", "away_goal", "datetime")
	if err != nil {
		return m, err
	}
	m.Competition, m.Round = "Copa do Brasil", field(row, h, "round")
	if s, _ := parseInt(field(row, h, "season")); s != 0 {
		m.Season = s
	}
	return m, nil
}

func parseLibertadores(row []string, h map[string]int) (Match, error) {
	m, err := baseMatch(row, h, "home_team", "away_team", "home_goal", "away_goal", "datetime")
	if err != nil {
		return m, err
	}
	m.Competition, m.Stage = "Copa Libertadores", field(row, h, "stage")
	if s, _ := parseInt(field(row, h, "season")); s != 0 {
		m.Season = s
	}
	return m, nil
}

func parseExtended(row []string, h map[string]int) (Match, error) {
	m, err := baseMatch(row, h, "home", "away", "home_goal", "away_goal", "date")
	if err != nil {
		return m, err
	}
	m.Competition = normalizeCompetition(field(row, h, "tournament"))
	m.Statistics = map[string]int{}
	for out, col := range map[string]string{"home_corners": "home_corner", "away_corners": "away_corner", "home_attacks": "home_attack", "away_attacks": "away_attack", "home_shots": "home_shots", "away_shots": "away_shots", "total_corners": "total_corners"} {
		if v := field(row, h, col); v != "" {
			n, _ := parseInt(v)
			m.Statistics[out] = n
		}
	}
	return m, nil
}

func parseHistorical(row []string, h map[string]int) (Match, error) {
	m, err := baseMatch(row, h, "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante", "Data")
	if err != nil {
		return m, err
	}
	m.Competition, m.Round, m.Stadium = "Brasileirão Série A", field(row, h, "Rodada"), field(row, h, "Arena")
	if s, _ := parseInt(field(row, h, "Ano")); s != 0 {
		m.Season = s
	}
	return m, nil
}

func parsePlayer(row []string, h map[string]int) (Player, error) {
	id, err := parseInt(field(row, h, "ID"))
	if err != nil {
		return Player{}, err
	}
	age, _ := parseInt(field(row, h, "Age"))
	overall, _ := parseInt(field(row, h, "Overall"))
	potential, _ := parseInt(field(row, h, "Potential"))
	p := Player{ID: id, Name: field(row, h, "Name"), Age: age, Nationality: field(row, h, "Nationality"), Overall: overall, Potential: potential, Club: field(row, h, "Club"), Position: field(row, h, "Position"), Jersey: field(row, h, "Jersey Number"), Height: field(row, h, "Height"), Weight: field(row, h, "Weight"), Attributes: map[string]int{}}
	if p.Name == "" {
		return Player{}, fmt.Errorf("missing player name")
	}
	for _, attr := range []string{"Crossing", "Finishing", "Dribbling", "ShortPassing", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Stamina", "Strength", "Vision", "Composure"} {
		if v := field(row, h, attr); v != "" {
			n, _ := parseInt(v)
			p.Attributes[searchKey(attr)] = n
		}
	}
	return p, nil
}
