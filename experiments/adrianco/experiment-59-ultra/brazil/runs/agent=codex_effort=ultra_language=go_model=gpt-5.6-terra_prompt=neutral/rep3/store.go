package main

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

const (
	brasileiraoFile  = "Brasileirao_Matches.csv"
	cupFile          = "Brazilian_Cup_Matches.csv"
	libertadoresFile = "Libertadores_Matches.csv"
	extendedFile     = "BR-Football-Dataset.csv"
	historicalFile   = "novo_campeonato_brasileiro.csv"
	fifaFile         = "fifa_data.csv"
)

type csvRow struct {
	headers map[string]int
	values  []string
}

func (row csvRow) get(name string) string {
	index, ok := row.headers[normalizeHeader(name)]
	if !ok || index >= len(row.values) {
		return ""
	}
	return strings.TrimSpace(row.values[index])
}

func normalizeHeader(value string) string {
	return strings.ToLower(strings.TrimSpace(strings.TrimPrefix(value, "\ufeff")))
}

func eachCSV(path string, required []string, visit func(csvRow) error) (int, error) {
	file, err := os.Open(path)
	if err != nil {
		return 0, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.FieldsPerRecord = -1
	reader.LazyQuotes = true
	headers, err := reader.Read()
	if err != nil {
		return 0, fmt.Errorf("read header: %w", err)
	}
	indexes := make(map[string]int, len(headers))
	for index, header := range headers {
		indexes[normalizeHeader(header)] = index
	}
	if err := requireHeaders(path, indexes, required...); err != nil {
		return 0, err
	}

	count := 0
	for line := 2; ; line++ {
		values, err := reader.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return count, fmt.Errorf("read row %d: %w", line, err)
		}
		if err := visit(csvRow{headers: indexes, values: values}); err != nil {
			return count, fmt.Errorf("parse row %d: %w", line, err)
		}
		count++
	}
	return count, nil
}

func requireHeaders(path string, headers map[string]int, names ...string) error {
	for _, name := range names {
		if _, ok := headers[normalizeHeader(name)]; !ok {
			return fmt.Errorf("%s is missing required column %q", filepath.Base(path), name)
		}
	}
	return nil
}

// LoadData reads all six supplied datasets exactly once. Invalid dates and
// unplayed scores are represented on their records instead of rejecting a valid
// source file, so every provided row remains available to match searches.
func LoadData(dataDir string) (*DataStore, error) {
	store := &DataStore{}
	loaders := []struct {
		file string
		kind string
		load func(*DataStore, string) (int, error)
	}{
		{brasileiraoFile, "matches", loadBrasileirao},
		{cupFile, "matches", loadCup},
		{libertadoresFile, "matches", loadLibertadores},
		{extendedFile, "matches", loadExtended},
		{historicalFile, "matches", loadHistorical},
		{fifaFile, "players", loadPlayers},
	}

	for _, loader := range loaders {
		path := filepath.Join(dataDir, loader.file)
		count, err := loader.load(store, path)
		if err != nil {
			return nil, fmt.Errorf("load %s: %w", loader.file, err)
		}
		store.Datasets = append(store.Datasets, DatasetInfo{File: loader.file, Kind: loader.kind, Records: count})
	}
	return store, nil
}

func loadBrasileirao(store *DataStore, path string) (int, error) {
	return eachCSV(path, []string{"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round"}, func(row csvRow) error {
		date := parseDate(row.get("datetime"))
		store.Matches = append(store.Matches, newMatch(date, "Brasileirão", brasileiraoFile, teamWithState(row.get("home_team"), row.get("home_team_state")), teamWithState(row.get("away_team"), row.get("away_team_state")), row.get("home_goal"), row.get("away_goal"), parseInt(row.get("season")), row.get("round"), "", ""))
		return nil
	})
}

func loadCup(store *DataStore, path string) (int, error) {
	return eachCSV(path, []string{"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "round"}, func(row csvRow) error {
		date := parseDate(row.get("datetime"))
		store.Matches = append(store.Matches, newMatch(date, "Copa do Brasil", cupFile, row.get("home_team"), row.get("away_team"), row.get("home_goal"), row.get("away_goal"), parseInt(row.get("season")), row.get("round"), "", ""))
		return nil
	})
}

func loadLibertadores(store *DataStore, path string) (int, error) {
	return eachCSV(path, []string{"datetime", "home_team", "away_team", "home_goal", "away_goal", "season", "stage"}, func(row csvRow) error {
		date := parseDate(row.get("datetime"))
		store.Matches = append(store.Matches, newMatch(date, "Copa Libertadores", libertadoresFile, row.get("home_team"), row.get("away_team"), row.get("home_goal"), row.get("away_goal"), parseInt(row.get("season")), "", row.get("stage"), ""))
		return nil
	})
}

func loadExtended(store *DataStore, path string) (int, error) {
	return eachCSV(path, []string{"tournament", "home", "away", "home_goal", "away_goal", "date"}, func(row csvRow) error {
		dateValue := row.get("date")
		if clock := row.get("time"); clock != "" && !isMissing(clock) {
			dateValue += " " + clock
		}
		date := parseDate(dateValue)
		season := 0
		if !date.IsZero() {
			season = date.Year()
		}
		competition := canonicalCompetition(row.get("tournament"))
		store.Matches = append(store.Matches, newMatch(date, competition, extendedFile, row.get("home"), row.get("away"), row.get("home_goal"), row.get("away_goal"), season, "", "", ""))
		return nil
	})
}

func loadHistorical(store *DataStore, path string) (int, error) {
	return eachCSV(path, []string{"Data", "Ano", "Rodada", "Equipe_mandante", "Equipe_visitante", "Gols_mandante", "Gols_visitante", "Arena"}, func(row csvRow) error {
		date := parseDate(row.get("Data"))
		// The historical UF columns are not a reliable team identity (for
		// example, Vitória is labelled ES at home and BA away in 2003). Keep
		// the source name intact and let state-qualified queries match its
		// exact base name rather than splitting one club into two standings rows.
		store.Matches = append(store.Matches, newMatch(date, "Brasileirão", historicalFile, row.get("Equipe_mandante"), row.get("Equipe_visitante"), row.get("Gols_mandante"), row.get("Gols_visitante"), parseInt(row.get("Ano")), row.get("Rodada"), "", row.get("Arena")))
		return nil
	})
}

func loadPlayers(store *DataStore, path string) (int, error) {
	return eachCSV(path, []string{"ID", "Name", "Nationality", "Overall", "Club", "Position"}, func(row csvRow) error {
		store.Players = append(store.Players, Player{
			ID:          row.get("ID"),
			Name:        row.get("Name"),
			Age:         parseInt(row.get("Age")),
			Nationality: row.get("Nationality"),
			Overall:     parseInt(row.get("Overall")),
			Potential:   parseInt(row.get("Potential")),
			Club:        row.get("Club"),
			Position:    row.get("Position"),
			Jersey:      row.get("Jersey Number"),
			Height:      row.get("Height"),
			Weight:      row.get("Weight"),
		})
		return nil
	})
}

func newMatch(date time.Time, competition, source, home, away, homeGoals, awayGoals string, season int, round, stage, stadium string) Match {
	return Match{
		Date:        date,
		DateText:    formatDate(date),
		Competition: canonicalCompetition(competition),
		Source:      source,
		HomeTeam:    strings.TrimSpace(home),
		AwayTeam:    strings.TrimSpace(away),
		HomeGoals:   parseScore(homeGoals),
		AwayGoals:   parseScore(awayGoals),
		Season:      season,
		Round:       strings.TrimSpace(round),
		Stage:       strings.TrimSpace(stage),
		Stadium:     strings.TrimSpace(stadium),
	}
}

func teamWithState(team, state string) string {
	team = strings.TrimSpace(team)
	state = strings.ToUpper(strings.TrimSpace(state))
	if team == "" || state == "" || parseTeamName(team).state != "" || !isBrazilianState(state) {
		return team
	}
	return team + "-" + state
}

func isBrazilianState(value string) bool {
	_, ok := map[string]struct{}{
		"AC": {}, "AL": {}, "AP": {}, "AM": {}, "BA": {}, "CE": {}, "DF": {}, "ES": {}, "GO": {}, "MA": {}, "MT": {}, "MS": {}, "MG": {}, "PA": {}, "PB": {}, "PR": {}, "PE": {}, "PI": {}, "RJ": {}, "RN": {}, "RS": {}, "RO": {}, "RR": {}, "SC": {}, "SP": {}, "SE": {}, "TO": {},
	}[value]
	return ok
}

func parseDate(value string) time.Time {
	value = strings.TrimSpace(value)
	if isMissing(value) {
		return time.Time{}
	}
	for _, layout := range []string{
		"2006-01-02 15:04:05",
		"2006-01-02 15:04",
		time.RFC3339,
		"2006-01-02",
		"02/01/2006 15:04:05",
		"02/01/2006 15:04",
		"02/01/2006",
	} {
		if parsed, err := time.ParseInLocation(layout, value, time.Local); err == nil {
			return parsed
		}
	}
	return time.Time{}
}

func formatDate(date time.Time) string {
	if date.IsZero() {
		return ""
	}
	if date.Hour() == 0 && date.Minute() == 0 && date.Second() == 0 {
		return date.Format("2006-01-02")
	}
	return date.Format("2006-01-02 15:04:05")
}

func parseInt(value string) int {
	value = strings.TrimSpace(value)
	if isMissing(value) {
		return 0
	}
	parsed, err := strconv.Atoi(value)
	if err != nil || parsed < 0 {
		return 0
	}
	return parsed
}

func parseScore(value string) *int {
	value = strings.TrimSpace(value)
	if isMissing(value) {
		return nil
	}
	parsed, err := strconv.ParseFloat(strings.ReplaceAll(value, ",", "."), 64)
	if err != nil || math.IsNaN(parsed) || math.IsInf(parsed, 0) {
		return nil
	}
	if parsed < 0 || math.Trunc(parsed) != parsed {
		return nil
	}
	result := int(parsed)
	return &result
}

func isMissing(value string) bool {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "", "na", "n/a", "-", "null", "nan":
		return true
	default:
		return false
	}
}
