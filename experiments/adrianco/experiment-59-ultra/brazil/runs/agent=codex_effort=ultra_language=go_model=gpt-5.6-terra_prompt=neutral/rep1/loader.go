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

// Database keeps immutable records in memory and indexes the common match
// access path. The full supplied corpus is small enough to load eagerly, which
// makes every MCP request deterministic and avoids background database setup.
type Database struct {
	Matches     []Match
	Players     []Player
	Report      LoadReport
	teamIndex   map[string][]int
	teamDisplay map[string]string
	teamKeys    []string
}

type datasetSpec struct {
	name        string
	filename    string
	competition string
	load        func(*Database, [][]string, map[string]int) (loaded, skipped int)
}

// LoadDatabase loads each of the six required CSV files from dataDir. A row
// with a missing result is retained as an unplayed fixture; malformed rows are
// counted in the report and skipped rather than corrupting an aggregate.
func LoadDatabase(dataDir string) (*Database, error) {
	db := &Database{Report: LoadReport{Sources: make(map[string]SourceReport)}}
	specs := []datasetSpec{
		{name: "brasileirao", filename: "Brasileirao_Matches.csv", competition: "Brasileirão Série A", load: loadStandardMatches},
		{name: "brazilian_cup", filename: "Brazilian_Cup_Matches.csv", competition: "Copa do Brasil", load: loadStandardMatches},
		{name: "libertadores", filename: "Libertadores_Matches.csv", competition: "Copa Libertadores", load: loadStandardMatches},
		{name: "extended_statistics", filename: "BR-Football-Dataset.csv", load: loadExtendedMatches},
		{name: "historical_brasileirao", filename: "novo_campeonato_brasileiro.csv", competition: "Brasileirão (Historical 2003-2019)", load: loadHistoricalMatches},
		{name: "fifa_players", filename: "fifa_data.csv", load: loadPlayers},
	}

	for _, spec := range specs {
		path := filepath.Join(dataDir, spec.filename)
		rows, header, err := readCSV(path)
		if err != nil {
			return nil, fmt.Errorf("load %s: %w", spec.filename, err)
		}
		matchStart := len(db.Matches)
		loaded, skipped := spec.load(db, rows, header)
		db.Report.Sources[spec.name] = SourceReport{Path: path, Loaded: loaded, Skipped: skipped}
		for i := matchStart; i < len(db.Matches); i++ {
			db.Matches[i].Source = spec.name
			if db.Matches[i].SourceRow == 0 {
				db.Matches[i].SourceRow = i - matchStart + 2
			}
			db.Matches[i].ID = fmt.Sprintf("%s:%d", spec.name, db.Matches[i].SourceRow)
			if db.Matches[i].Competition == "" {
				db.Matches[i].Competition = spec.competition
			}
		}
	}
	db.rebuildIndexes()
	return db, nil
}

// NewDatabase is useful for callers that construct deterministic fixtures in
// tests while retaining exactly the same indexes as the loaded production data.
func NewDatabase(matches []Match, players []Player) *Database {
	db := &Database{
		Matches: matches,
		Players: players,
		Report:  LoadReport{Sources: make(map[string]SourceReport)},
	}
	for i := range db.Matches {
		if db.Matches[i].HomeKey == "" {
			db.Matches[i].HomeKey = normalizeTeam(db.Matches[i].HomeTeam)
		}
		if db.Matches[i].AwayKey == "" {
			db.Matches[i].AwayKey = normalizeTeam(db.Matches[i].AwayTeam)
		}
		if db.Matches[i].DateText == "" && !db.Matches[i].Date.IsZero() {
			db.Matches[i].DateText = db.Matches[i].Date.Format("2006-01-02")
		}
		if db.Matches[i].ResultStatus == "" {
			if db.Matches[i].ScoreKnown {
				db.Matches[i].ResultStatus = "played"
			} else {
				db.Matches[i].ResultStatus = "unplayed_or_unknown"
			}
		}
	}
	for i := range db.Players {
		if db.Players[i].NameKey == "" {
			db.Players[i].NameKey = normalizeText(db.Players[i].Name)
		}
		if db.Players[i].ClubKey == "" {
			db.Players[i].ClubKey = normalizeTeam(db.Players[i].Club)
		}
	}
	db.rebuildIndexes()
	return db
}

func (db *Database) rebuildIndexes() {
	db.teamIndex = make(map[string][]int)
	db.teamDisplay = make(map[string]string)
	for i := range db.Matches {
		match := &db.Matches[i]
		if match.HomeKey == "" {
			match.HomeKey = normalizeTeam(match.HomeTeam)
		}
		if match.AwayKey == "" {
			match.AwayKey = normalizeTeam(match.AwayTeam)
		}
		if match.DateText == "" && !match.Date.IsZero() {
			match.DateText = match.Date.Format("2006-01-02")
		}
		db.teamIndex[match.HomeKey] = append(db.teamIndex[match.HomeKey], i)
		if match.AwayKey != match.HomeKey {
			db.teamIndex[match.AwayKey] = append(db.teamIndex[match.AwayKey], i)
		}
		if _, exists := db.teamDisplay[match.HomeKey]; !exists {
			db.teamDisplay[match.HomeKey] = displayTeam(match.HomeTeam)
		}
		if _, exists := db.teamDisplay[match.AwayKey]; !exists {
			db.teamDisplay[match.AwayKey] = displayTeam(match.AwayTeam)
		}
	}
	db.teamKeys = db.teamKeys[:0]
	for key := range db.teamIndex {
		db.teamKeys = append(db.teamKeys, key)
	}
}

func readCSV(path string) ([][]string, map[string]int, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.FieldsPerRecord = -1
	reader.TrimLeadingSpace = true
	headerRow, err := reader.Read()
	if err != nil {
		if errors.Is(err, io.EOF) {
			return nil, nil, fmt.Errorf("empty CSV")
		}
		return nil, nil, err
	}
	header := make(map[string]int, len(headerRow))
	for i, field := range headerRow {
		field = strings.TrimPrefix(field, "\ufeff")
		header[normalizeHeader(field)] = i
	}

	var rows [][]string
	for {
		row, err := reader.Read()
		if err == nil {
			rows = append(rows, row)
			continue
		}
		if errors.Is(err, io.EOF) {
			break
		}
		return nil, nil, fmt.Errorf("parse CSV: %w", err)
	}
	return rows, header, nil
}

func normalizeHeader(value string) string { return normalizeText(strings.TrimPrefix(value, "\ufeff")) }

func cell(row []string, header map[string]int, name string) string {
	index, ok := header[normalizeHeader(name)]
	if !ok || index < 0 || index >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[index])
}

func loadStandardMatches(db *Database, rows [][]string, header map[string]int) (loaded, skipped int) {
	for rowIndex, row := range rows {
		home, away := cell(row, header, "home_team"), cell(row, header, "away_team")
		if home == "" || away == "" {
			skipped++
			continue
		}
		match := newMatch(
			cell(row, header, "datetime"),
			cell(row, header, "season"),
			home, away,
			cell(row, header, "home_goal"), cell(row, header, "away_goal"),
		)
		match.HomeState = cell(row, header, "home_team_state")
		match.AwayState = cell(row, header, "away_team_state")
		match.Round = cell(row, header, "round")
		match.Stage = cell(row, header, "stage")
		match.SourceRow = rowIndex + 2
		db.Matches = append(db.Matches, match)
		loaded++
	}
	return loaded, skipped
}

func loadExtendedMatches(db *Database, rows [][]string, header map[string]int) (loaded, skipped int) {
	for rowIndex, row := range rows {
		home, away := cell(row, header, "home"), cell(row, header, "away")
		if home == "" || away == "" {
			skipped++
			continue
		}
		date := strings.TrimSpace(strings.Join([]string{cell(row, header, "date"), cell(row, header, "time")}, " "))
		match := newMatch(date, "", home, away, cell(row, header, "home_goal"), cell(row, header, "away_goal"))
		match.Competition = cell(row, header, "tournament")
		match.Kickoff = cell(row, header, "time")
		match.HomeCorners = optionalInt(cell(row, header, "home_corner"))
		match.AwayCorners = optionalInt(cell(row, header, "away_corner"))
		match.HomeShots = optionalInt(cell(row, header, "home_shots"))
		match.AwayShots = optionalInt(cell(row, header, "away_shots"))
		match.HomeAttacks = optionalInt(cell(row, header, "home_attack"))
		match.AwayAttacks = optionalInt(cell(row, header, "away_attack"))
		match.TotalCorners = optionalInt(cell(row, header, "total_corners"))
		match.HomeGoalDifference = optionalInt(cell(row, header, "ht_diff"))
		match.AwayGoalDifference = optionalInt(cell(row, header, "at_diff"))
		match.HomeResult = cell(row, header, "ht_result")
		match.AwayResult = cell(row, header, "at_result")
		match.SourceRow = rowIndex + 2
		// BR-Football-Dataset has a calendar date but no authoritative season
		// column. Keep Season zero rather than falsely relabelling COVID-era
		// fixtures that occurred in the following calendar year.
		db.Matches = append(db.Matches, match)
		loaded++
	}
	return loaded, skipped
}

func loadHistoricalMatches(db *Database, rows [][]string, header map[string]int) (loaded, skipped int) {
	for rowIndex, row := range rows {
		home, away := cell(row, header, "Equipe_mandante"), cell(row, header, "Equipe_visitante")
		if home == "" || away == "" {
			skipped++
			continue
		}
		match := newMatch(cell(row, header, "Data"), cell(row, header, "Ano"), home, away, cell(row, header, "Gols_mandante"), cell(row, header, "Gols_visitante"))
		match.ExternalID = cell(row, header, "ID")
		match.SourceRow = rowIndex + 2
		match.Round = cell(row, header, "Rodada")
		match.HomeState = cell(row, header, "Mandante_UF")
		match.AwayState = cell(row, header, "Visitante_UF")
		match.Venue = cell(row, header, "Arena")
		db.Matches = append(db.Matches, match)
		loaded++
	}
	return loaded, skipped
}

func loadPlayers(db *Database, rows [][]string, header map[string]int) (loaded, skipped int) {
	for _, row := range rows {
		name := cell(row, header, "Name")
		if name == "" {
			skipped++
			continue
		}
		player := Player{
			ID:          cell(row, header, "ID"),
			Name:        name,
			NameKey:     normalizeText(name),
			Age:         intOrZero(cell(row, header, "Age")),
			Nationality: cell(row, header, "Nationality"),
			Overall:     intOrZero(cell(row, header, "Overall")),
			Potential:   intOrZero(cell(row, header, "Potential")),
			Club:        cell(row, header, "Club"),
			Position:    cell(row, header, "Position"),
			Jersey:      cell(row, header, "Jersey Number"),
			Height:      cell(row, header, "Height"),
			Weight:      cell(row, header, "Weight"),
			Attributes:  playerAttributes(row, header),
		}
		player.ClubKey = normalizeTeam(player.Club)
		db.Players = append(db.Players, player)
		loaded++
	}
	return loaded, skipped
}

func playerAttributes(row []string, header map[string]int) map[string]int {
	columns := map[string]string{
		"crossing": "Crossing", "finishing": "Finishing", "headingAccuracy": "HeadingAccuracy",
		"shortPassing": "ShortPassing", "volleys": "Volleys", "dribbling": "Dribbling", "curve": "Curve",
		"freeKickAccuracy": "FKAccuracy", "longPassing": "LongPassing", "ballControl": "BallControl",
		"acceleration": "Acceleration", "sprintSpeed": "SprintSpeed", "agility": "Agility", "reactions": "Reactions",
		"balance": "Balance", "shotPower": "ShotPower", "jumping": "Jumping", "stamina": "Stamina",
		"strength": "Strength", "longShots": "LongShots", "aggression": "Aggression", "interceptions": "Interceptions",
		"positioning": "Positioning", "vision": "Vision", "penalties": "Penalties", "composure": "Composure",
		"marking": "Marking", "standingTackle": "StandingTackle", "slidingTackle": "SlidingTackle",
	}
	attributes := make(map[string]int, len(columns))
	for name, column := range columns {
		if value, ok := parseScore(cell(row, header, column)); ok {
			attributes[name] = value
		}
	}
	return attributes
}

func newMatch(dateText, seasonText, home, away, homeGoals, awayGoals string) Match {
	date, _ := parseDate(dateText)
	season := intOrZero(seasonText)
	match := Match{
		Date:         date,
		DateText:     formattedDate(date, dateText),
		Season:       season,
		HomeTeam:     displayTeam(home),
		AwayTeam:     displayTeam(away),
		HomeKey:      normalizeTeam(home),
		AwayKey:      normalizeTeam(away),
		ResultStatus: "unplayed_or_unknown",
	}
	homeScore, homeOK := parseScore(homeGoals)
	awayScore, awayOK := parseScore(awayGoals)
	if homeOK && awayOK {
		match.HomeGoals, match.AwayGoals, match.ScoreKnown = homeScore, awayScore, true
		match.ResultStatus = "played"
	}
	return match
}

func parseDate(value string) (time.Time, error) {
	value = strings.TrimSpace(value)
	if value == "" || value == "-" || strings.EqualFold(value, "NA") {
		return time.Time{}, nil
	}
	for _, layout := range []string{
		"2006-01-02 15:04:05", time.RFC3339, "2006-01-02", "02/01/2006", "2/1/2006", "02/01/2006 15:04:05",
	} {
		if parsed, err := time.ParseInLocation(layout, value, time.UTC); err == nil {
			return parsed, nil
		}
	}
	return time.Time{}, fmt.Errorf("unsupported date %q", value)
}

func formattedDate(date time.Time, original string) string {
	if !date.IsZero() {
		return date.Format("2006-01-02")
	}
	return strings.TrimSpace(original)
}

func parseScore(value string) (int, bool) {
	value = strings.TrimSpace(value)
	if value == "" || value == "-" || strings.EqualFold(value, "NA") || strings.EqualFold(value, "N/A") {
		return 0, false
	}
	parsed, err := strconv.ParseFloat(strings.ReplaceAll(value, ",", "."), 64)
	if err != nil || math.IsNaN(parsed) || math.IsInf(parsed, 0) || parsed < 0 || parsed != math.Trunc(parsed) {
		return 0, false
	}
	return int(parsed), true
}

func intOrZero(value string) int {
	parsed, ok := parseScore(value)
	if !ok {
		return 0
	}
	return parsed
}

func optionalInt(value string) *int {
	parsed, ok := parseScore(value)
	if !ok {
		return nil
	}
	return &parsed
}
