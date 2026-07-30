package main

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

// LoadData reads every dataset required by the specification. It fails rather
// than silently omitting a CSV, because incomplete data would yield misleading
// answers from aggregate tools.
func LoadData(dataDir string) (*DataStore, error) {
	d := &DataStore{}
	matchFiles := []struct {
		file, kind string
	}{
		{"Brasileirao_Matches.csv", "brasileirao"},
		{"Brazilian_Cup_Matches.csv", "cup"},
		{"Libertadores_Matches.csv", "libertadores"},
		{"BR-Football-Dataset.csv", "extended"},
		{"novo_campeonato_brasileiro.csv", "historical"},
	}
	for _, spec := range matchFiles {
		matches, err := loadMatches(filepath.Join(dataDir, spec.file), spec.kind)
		if err != nil {
			return nil, err
		}
		d.Matches = append(d.Matches, matches...)
	}
	players, err := loadPlayers(filepath.Join(dataDir, "fifa_data.csv"))
	if err != nil {
		return nil, err
	}
	d.Players = players
	return d, nil
}

func loadMatches(path, kind string) ([]Match, error) {
	records, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	if len(records) == 0 {
		return nil, fmt.Errorf("%s: missing header", path)
	}
	head := csvHeader(records[0])
	var matches []Match
	for _, row := range records[1:] {
		get := func(name string) string { return csvValue(row, head, name) }
		var m Match
		m.Source = filepath.Base(path)
		switch kind {
		case "brasileirao":
			m = matchFromValues(get("datetime"), "Brasileirão", get("season"), get("round"), "", get("home_team"), get("away_team"), get("home_goal"), get("away_goal"))
		case "cup":
			m = matchFromValues(get("datetime"), "Copa do Brasil", get("season"), get("round"), "", get("home_team"), get("away_team"), get("home_goal"), get("away_goal"))
		case "libertadores":
			m = matchFromValues(get("datetime"), "Copa Libertadores", get("season"), "", get("stage"), get("home_team"), get("away_team"), get("home_goal"), get("away_goal"))
		case "extended":
			m = matchFromValues(get("date"), get("tournament"), "", "", "", get("home"), get("away"), get("home_goal"), get("away_goal"))
			m.HomeCorners = optionalInt(get("home_corner"))
			m.AwayCorners = optionalInt(get("away_corner"))
			m.HomeShots = optionalInt(get("home_shots"))
			m.AwayShots = optionalInt(get("away_shots"))
		case "historical":
			m = matchFromValues(get("Data"), "Brasileirão", get("Ano"), get("Rodada"), "", get("Equipe_mandante"), get("Equipe_visitante"), get("Gols_mandante"), get("Gols_visitante"))
			m.Venue = get("Arena")
		}
		m.Source = filepath.Base(path)
		if m.Date.IsZero() || m.HomeTeam == "" || m.AwayTeam == "" {
			// The Libertadores file contains one placeholder final with NA date
			// and '-' scores. It is not a completed match, so it cannot truthfully
			// participate in a result or statistics query.
			continue
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func matchFromValues(dateValue, competition, season, round, stage, home, away, homeGoals, awayGoals string) Match {
	date, _ := parseDate(dateValue)
	seasonNumber := integer(season)
	if seasonNumber == 0 && !date.IsZero() {
		seasonNumber = date.Year()
	}
	return Match{
		Date: date, Competition: displayCompetition(canonicalCompetition(competition)), Season: seasonNumber,
		Round: strings.TrimSpace(round), Stage: strings.TrimSpace(stage), HomeTeam: strings.TrimSpace(home), AwayTeam: strings.TrimSpace(away),
		HomeGoals: integer(homeGoals), AwayGoals: integer(awayGoals),
	}
}

func loadPlayers(path string) ([]Player, error) {
	records, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	if len(records) == 0 {
		return nil, fmt.Errorf("%s: missing header", path)
	}
	head := csvHeader(records[0])
	players := make([]Player, 0, len(records)-1)
	for number, row := range records[1:] {
		get := func(name string) string { return csvValue(row, head, name) }
		p := Player{ID: get("ID"), Name: get("Name"), Age: integer(get("Age")), Nationality: get("Nationality"), Overall: integer(get("Overall")), Potential: integer(get("Potential")), Club: get("Club"), Position: get("Position"), JerseyNo: get("Jersey Number"), Height: get("Height"), Weight: get("Weight")}
		if p.ID == "" || p.Name == "" {
			return nil, fmt.Errorf("%s: row %d has invalid required player data", path, number+2)
		}
		players = append(players, p)
	}
	return players, nil
}

func readCSV(path string) ([][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.TrimLeadingSpace = true
	r.LazyQuotes = true
	var records [][]string
	for {
		record, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("parse %s: %w", path, err)
		}
		records = append(records, record)
	}
	return records, nil
}

func csvHeader(row []string) map[string]int {
	head := make(map[string]int, len(row))
	for i, value := range row {
		value = strings.TrimPrefix(strings.TrimSpace(value), "\ufeff")
		head[strings.ToLower(value)] = i
	}
	return head
}

func csvValue(row []string, header map[string]int, name string) string {
	i, ok := header[strings.ToLower(name)]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func integer(value string) int {
	value = strings.TrimSpace(value)
	if value == "" {
		return 0
	}
	if n, err := strconv.Atoi(value); err == nil {
		return n
	}
	if f, err := strconv.ParseFloat(value, 64); err == nil {
		return int(f)
	}
	return 0
}

func optionalInt(value string) *int {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	n := integer(value)
	return &n
}

func parseDate(value string) (time.Time, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return time.Time{}, fmt.Errorf("empty date")
	}
	layouts := []string{"2006-01-02 15:04:05", time.RFC3339, "2006-01-02", "02/01/2006", "2/1/2006"}
	for _, layout := range layouts {
		if parsed, err := time.ParseInLocation(layout, value, time.UTC); err == nil {
			return parsed, nil
		}
	}
	return time.Time{}, fmt.Errorf("unsupported date %q", value)
}
