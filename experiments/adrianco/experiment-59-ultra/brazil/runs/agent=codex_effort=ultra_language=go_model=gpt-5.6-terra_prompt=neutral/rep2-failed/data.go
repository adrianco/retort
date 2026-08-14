package main

import (
	"bufio"
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
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
	playersFile      = "fifa_data.csv"
)

// MatchStatistics contains the extra match-level facts available only in the
// extended football dataset. Nil means the source did not provide that value.
type MatchStatistics struct {
	HomeCorners  *float64 `json:"home_corners,omitempty"`
	AwayCorners  *float64 `json:"away_corners,omitempty"`
	HomeAttacks  *float64 `json:"home_attacks,omitempty"`
	AwayAttacks  *float64 `json:"away_attacks,omitempty"`
	HomeShots    *float64 `json:"home_shots,omitempty"`
	AwayShots    *float64 `json:"away_shots,omitempty"`
	TotalCorners *float64 `json:"total_corners,omitempty"`
}

// Match is the common representation used by every match dataset. Scores are
// nullable because several supplied rows are future, postponed, or unknown.
type Match struct {
	ID          string           `json:"id"`
	SourceFile  string           `json:"source_file"`
	Competition string           `json:"competition"`
	Date        string           `json:"date,omitempty"`
	PlayedAt    time.Time        `json:"-"`
	Season      int              `json:"season,omitempty"`
	Round       string           `json:"round,omitempty"`
	Stage       string           `json:"stage,omitempty"`
	HomeTeam    string           `json:"home_team"`
	HomeState   string           `json:"home_state,omitempty"`
	AwayTeam    string           `json:"away_team"`
	AwayState   string           `json:"away_state,omitempty"`
	HomeGoals   *int             `json:"home_goals"`
	AwayGoals   *int             `json:"away_goals"`
	Statistics  *MatchStatistics `json:"statistics,omitempty"`
	HomeKey     string           `json:"-"`
	AwayKey     string           `json:"-"`
}

func (m Match) HasResult() bool { return m.HomeGoals != nil && m.AwayGoals != nil }

// Player stores the useful FIFA fields and the individual numeric skills that
// can be searched or surfaced without exposing the raw 89-column CSV row.
type Player struct {
	ID            int            `json:"id"`
	Name          string         `json:"name"`
	Age           int            `json:"age,omitempty"`
	Nationality   string         `json:"nationality,omitempty"`
	Overall       int            `json:"overall,omitempty"`
	Potential     int            `json:"potential,omitempty"`
	Club          string         `json:"club,omitempty"`
	Position      string         `json:"position,omitempty"`
	JerseyNumber  string         `json:"jersey_number,omitempty"`
	PreferredFoot string         `json:"preferred_foot,omitempty"`
	Height        string         `json:"height,omitempty"`
	Weight        string         `json:"weight,omitempty"`
	Attributes    map[string]int `json:"attributes,omitempty"`
}

type Store struct {
	Matches    []Match
	Players    []Player
	SourceRows map[string]int
}

// LoadStore loads all six required files once. The resulting Store is immutable
// and safe for concurrent read-only use by multiple MCP requests.
func LoadStore(dataDir string) (*Store, error) {
	store := &Store{SourceRows: make(map[string]int)}
	loaders := []struct {
		file string
		load func(string) error
	}{
		{brasileiraoFile, store.loadBrasileirao},
		{cupFile, store.loadCup},
		{libertadoresFile, store.loadLibertadores},
		{extendedFile, store.loadExtended},
		{historicalFile, store.loadHistorical},
		{playersFile, store.loadPlayers},
	}
	for _, item := range loaders {
		path := filepath.Join(dataDir, item.file)
		if err := item.load(path); err != nil {
			return nil, err
		}
	}
	sort.SliceStable(store.Matches, func(i, j int) bool {
		return store.Matches[i].PlayedAt.After(store.Matches[j].PlayedAt)
	})
	sort.SliceStable(store.Players, func(i, j int) bool {
		if store.Players[i].Overall != store.Players[j].Overall {
			return store.Players[i].Overall > store.Players[j].Overall
		}
		return normalizeText(store.Players[i].Name) < normalizeText(store.Players[j].Name)
	})
	return store, nil
}

func (s *Store) loadBrasileirao(path string) error {
	return readCSV(path, func(row map[string]string, rowNumber int) error {
		match, err := newMatch(
			brasileiraoFile, rowNumber, "Brasileirão Série A", rowValue(row, "datetime"), "",
			rowValue(row, "home_team"), rowValue(row, "home_team_state"),
			rowValue(row, "away_team"), rowValue(row, "away_team_state"),
			rowValue(row, "home_goal"), rowValue(row, "away_goal"), rowValue(row, "season"),
			rowValue(row, "round"), "", nil,
		)
		if err != nil {
			return err
		}
		s.Matches = append(s.Matches, match)
		s.SourceRows[brasileiraoFile]++
		return nil
	})
}

func (s *Store) loadCup(path string) error {
	return readCSV(path, func(row map[string]string, rowNumber int) error {
		match, err := newMatch(
			cupFile, rowNumber, "Copa do Brasil", rowValue(row, "datetime"), "",
			rowValue(row, "home_team"), "", rowValue(row, "away_team"), "",
			rowValue(row, "home_goal"), rowValue(row, "away_goal"), rowValue(row, "season"),
			rowValue(row, "round"), "", nil,
		)
		if err != nil {
			return err
		}
		s.Matches = append(s.Matches, match)
		s.SourceRows[cupFile]++
		return nil
	})
}

func (s *Store) loadLibertadores(path string) error {
	return readCSV(path, func(row map[string]string, rowNumber int) error {
		match, err := newMatch(
			libertadoresFile, rowNumber, "Copa Libertadores", rowValue(row, "datetime"), "",
			rowValue(row, "home_team"), "", rowValue(row, "away_team"), "",
			rowValue(row, "home_goal"), rowValue(row, "away_goal"), rowValue(row, "season"),
			"", rowValue(row, "stage"), nil,
		)
		if err != nil {
			return err
		}
		s.Matches = append(s.Matches, match)
		s.SourceRows[libertadoresFile]++
		return nil
	})
}

func (s *Store) loadExtended(path string) error {
	return readCSV(path, func(row map[string]string, rowNumber int) error {
		stats, err := parseMatchStatistics(row)
		if err != nil {
			return err
		}
		match, err := newMatch(
			extendedFile, rowNumber, canonicalCompetition(rowValue(row, "tournament")), rowValue(row, "date"), rowValue(row, "time"),
			rowValue(row, "home"), "", rowValue(row, "away"), "",
			rowValue(row, "home_goal"), rowValue(row, "away_goal"), "", "", "", stats,
		)
		if err != nil {
			return err
		}
		s.Matches = append(s.Matches, match)
		s.SourceRows[extendedFile]++
		return nil
	})
}

func (s *Store) loadHistorical(path string) error {
	return readCSV(path, func(row map[string]string, rowNumber int) error {
		match, err := newMatch(
			historicalFile, rowNumber, "Brasileirão Série A", rowValue(row, "data"), "",
			rowValue(row, "equipe_mandante"), rowValue(row, "mandante_uf"),
			rowValue(row, "equipe_visitante"), rowValue(row, "visitante_uf"),
			rowValue(row, "gols_mandante"), rowValue(row, "gols_visitante"), rowValue(row, "ano"),
			rowValue(row, "rodada"), "", nil,
		)
		if err != nil {
			return err
		}
		s.Matches = append(s.Matches, match)
		s.SourceRows[historicalFile]++
		return nil
	})
}

func (s *Store) loadPlayers(path string) error {
	return readCSV(path, func(row map[string]string, rowNumber int) error {
		attributes := make(map[string]int)
		for _, field := range playerAttributeFields {
			if value, ok := optionalInt(rowValue(row, field)); ok == nil && value != nil {
				attributes[field] = *value
			}
		}
		id, _ := intValue(rowValue(row, "id"))
		age, _ := intValue(rowValue(row, "age"))
		overall, _ := intValue(rowValue(row, "overall"))
		potential, _ := intValue(rowValue(row, "potential"))
		player := Player{
			ID:            id,
			Name:          strings.TrimSpace(rowValue(row, "name")),
			Age:           age,
			Nationality:   strings.TrimSpace(rowValue(row, "nationality")),
			Overall:       overall,
			Potential:     potential,
			Club:          strings.TrimSpace(rowValue(row, "club")),
			Position:      strings.TrimSpace(rowValue(row, "position")),
			JerseyNumber:  strings.TrimSpace(rowValue(row, "jersey number")),
			PreferredFoot: strings.TrimSpace(rowValue(row, "preferred foot")),
			Height:        strings.TrimSpace(rowValue(row, "height")),
			Weight:        strings.TrimSpace(rowValue(row, "weight")),
			Attributes:    attributes,
		}
		if player.Name == "" {
			return nil
		}
		s.Players = append(s.Players, player)
		s.SourceRows[playersFile]++
		return nil
	})
}

var playerAttributeFields = []string{
	"crossing", "finishing", "headingaccuracy", "shortpassing", "volleys", "dribbling", "curve", "fkaccuracy",
	"longpassing", "ballcontrol", "acceleration", "sprintspeed", "agility", "reactions", "balance", "shotpower",
	"jumping", "stamina", "strength", "longshots", "aggression", "interceptions", "positioning", "vision",
	"penalties", "composure", "marking", "standingtackle", "slidingtackle", "gkdiving", "gkhandling",
	"gkkicking", "gkpositioning", "gkreflexes",
}

func newMatch(source string, rowNumber int, competition, dateValue, clockValue, home, homeState, away, awayState, homeGoals, awayGoals, seasonValue, round, stage string, stats *MatchStatistics) (Match, error) {
	homeScore, err := optionalInt(homeGoals)
	if err != nil {
		return Match{}, fmt.Errorf("%s row %d: invalid home score %q: %w", source, rowNumber, homeGoals, err)
	}
	awayScore, err := optionalInt(awayGoals)
	if err != nil {
		return Match{}, fmt.Errorf("%s row %d: invalid away score %q: %w", source, rowNumber, awayGoals, err)
	}
	season, err := intValue(seasonValue)
	if err != nil {
		return Match{}, fmt.Errorf("%s row %d: invalid season %q: %w", source, rowNumber, seasonValue, err)
	}
	playedAt, hasDate := parseMatchDate(dateValue, clockValue)
	if season == 0 && hasDate {
		season = playedAt.Year()
	}
	match := Match{
		ID:          fmt.Sprintf("%s:%d", strings.TrimSuffix(source, ".csv"), rowNumber),
		SourceFile:  source,
		Competition: canonicalCompetition(competition),
		Season:      season,
		Round:       strings.TrimSpace(round),
		Stage:       strings.TrimSpace(stage),
		HomeTeam:    displayTeam(home),
		HomeState:   strings.TrimSpace(homeState),
		AwayTeam:    displayTeam(away),
		AwayState:   strings.TrimSpace(awayState),
		HomeGoals:   homeScore,
		AwayGoals:   awayScore,
		Statistics:  stats,
		HomeKey:     normalizeTeam(withState(home, homeState)),
		AwayKey:     normalizeTeam(withState(away, awayState)),
	}
	if hasDate {
		match.PlayedAt = playedAt
		match.Date = playedAt.Format(time.RFC3339)
	}
	return match, nil
}

func withState(team, state string) string {
	if strings.TrimSpace(state) == "" {
		return team
	}
	parts := strings.Fields(normalizeText(team))
	if len(parts) > 0 && strings.EqualFold(parts[len(parts)-1], strings.TrimSpace(state)) {
		return team
	}
	return team + " " + state
}

func parseMatchStatistics(row map[string]string) (*MatchStatistics, error) {
	parse := func(key string) (*float64, error) { return optionalFloat(rowValue(row, key)) }
	homeCorners, err := parse("home_corner")
	if err != nil {
		return nil, err
	}
	awayCorners, err := parse("away_corner")
	if err != nil {
		return nil, err
	}
	homeAttacks, err := parse("home_attack")
	if err != nil {
		return nil, err
	}
	awayAttacks, err := parse("away_attack")
	if err != nil {
		return nil, err
	}
	homeShots, err := parse("home_shots")
	if err != nil {
		return nil, err
	}
	awayShots, err := parse("away_shots")
	if err != nil {
		return nil, err
	}
	totalCorners, err := parse("total_corners")
	if err != nil {
		return nil, err
	}
	return &MatchStatistics{homeCorners, awayCorners, homeAttacks, awayAttacks, homeShots, awayShots, totalCorners}, nil
}

func readCSV(path string, handle func(map[string]string, int) error) error {
	file, err := os.Open(path)
	if err != nil {
		return fmt.Errorf("open required dataset %s: %w", path, err)
	}
	defer file.Close()
	reader := csv.NewReader(bufio.NewReader(file))
	reader.FieldsPerRecord = -1
	reader.TrimLeadingSpace = true
	header, err := reader.Read()
	if err != nil {
		return fmt.Errorf("read header from %s: %w", path, err)
	}
	for i := range header {
		header[i] = normalizeText(header[i])
	}
	for rowNumber := 2; ; rowNumber++ {
		record, err := reader.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return fmt.Errorf("read %s row %d: %w", path, rowNumber, err)
		}
		row := make(map[string]string, len(header))
		for i, key := range header {
			if i < len(record) {
				row[key] = strings.TrimSpace(record[i])
			}
		}
		if err := handle(row, rowNumber); err != nil {
			return err
		}
	}
	return nil
}

func rowValue(row map[string]string, name string) string { return row[normalizeText(name)] }

func optionalInt(raw string) (*int, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" || strings.EqualFold(raw, "na") || strings.EqualFold(raw, "n/a") || raw == "-" {
		return nil, nil
	}
	number, err := strconv.ParseFloat(strings.ReplaceAll(raw, ",", "."), 64)
	if err != nil {
		return nil, err
	}
	if math.Abs(number-math.Round(number)) > 1e-9 {
		return nil, fmt.Errorf("score must be an integer, got %s", raw)
	}
	result := int(math.Round(number))
	return &result, nil
}

func intValue(raw string) (int, error) {
	value, err := optionalInt(raw)
	if err != nil || value == nil {
		return 0, err
	}
	return *value, nil
}

func optionalFloat(raw string) (*float64, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" || strings.EqualFold(raw, "na") || strings.EqualFold(raw, "n/a") || raw == "-" {
		return nil, nil
	}
	value, err := strconv.ParseFloat(strings.ReplaceAll(raw, ",", "."), 64)
	if err != nil {
		return nil, err
	}
	return &value, nil
}

func parseMatchDate(dateValue, clockValue string) (time.Time, bool) {
	dateValue = strings.TrimSpace(dateValue)
	clockValue = strings.TrimSpace(clockValue)
	if dateValue == "" || strings.EqualFold(dateValue, "na") || dateValue == "-" {
		return time.Time{}, false
	}
	values := []string{dateValue}
	if clockValue != "" && !strings.EqualFold(clockValue, "na") && clockValue != "-" {
		values = append([]string{dateValue + " " + clockValue}, values...)
	}
	layouts := []string{time.RFC3339, "2006-01-02 15:04:05", "2006-01-02T15:04:05", "2006-01-02", "02/01/2006"}
	for _, value := range values {
		for _, layout := range layouts {
			if parsed, err := time.ParseInLocation(layout, value, time.UTC); err == nil {
				return parsed, true
			}
		}
	}
	return time.Time{}, false
}
