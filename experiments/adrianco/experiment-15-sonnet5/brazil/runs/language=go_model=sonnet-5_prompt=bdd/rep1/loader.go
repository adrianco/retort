package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// openCSV opens a CSV file and returns a reader configured to tolerate the
// quirks seen across the provided datasets (UTF-8 BOM, quoted fields
// containing commas, occasional ragged rows).
func openCSV(path string) (*csv.Reader, *os.File, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	return r, f, nil
}

// readHeaderedRows reads a CSV file and invokes fn for every data row with a
// map from header name to cell value. The first row is treated as the
// header. A UTF-8 BOM on the first header cell is stripped.
func readHeaderedRows(path string, fn func(row map[string]string) error) error {
	r, f, err := openCSV(path)
	if err != nil {
		return err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return fmt.Errorf("reading header of %s: %w", path, err)
	}
	for i, h := range header {
		header[i] = strings.TrimPrefix(strings.TrimSpace(h), "\ufeff")
	}

	for {
		record, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return fmt.Errorf("reading %s: %w", path, err)
		}
		row := make(map[string]string, len(header))
		for i, h := range header {
			if i < len(record) {
				row[h] = strings.TrimSpace(record[i])
			}
		}
		if err := fn(row); err != nil {
			return err
		}
	}
	return nil
}

func atoiOr(s string, def int) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return def
	}
	v, err := strconv.Atoi(s)
	if err != nil {
		f, ferr := strconv.ParseFloat(s, 64)
		if ferr == nil {
			return int(f)
		}
		return def
	}
	return v
}

func makeTeam(raw string) (key, display string) {
	return NormalizeTeamName(raw)
}

// LoadAll reads all six provided CSV datasets from dataDir and returns a
// populated Store. It returns an error if any required file is missing or
// malformed.
func LoadAll(dataDir string) (*Store, error) {
	store := &Store{}

	loaders := []struct {
		file string
		fn   func(string, *Store) error
	}{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadCopaDoBrasil},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"BR-Football-Dataset.csv", loadBRFootballDataset},
		{"novo_campeonato_brasileiro.csv", loadNovoCampeonato},
		{"fifa_data.csv", loadFifaPlayers},
	}

	for _, l := range loaders {
		path := filepath.Join(dataDir, l.file)
		if err := l.fn(path, store); err != nil {
			return nil, fmt.Errorf("loading %s: %w", l.file, err)
		}
	}

	store.Matches = dedupeMatches(store.Matches)
	store.BuildIndexes()
	return store, nil
}

// dedupeMatches removes duplicate fixtures that appear in more than one
// source file. Several of the provided datasets have overlapping coverage
// for the same real-world seasons - e.g. Brasileirao 2012-2019 is present in
// Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv, AND (as "Serie A")
// BR-Football-Dataset.csv - so aggregating across all matches without
// deduplication would triple-count standings, records, and statistics.
//
// A fixture is identified by (competition, season, home team, away team,
// score): in a round-robin league each ordered pair of teams meets at most
// once per season, so this key is safe without needing to reconcile
// differing date formats across sources. Matches are loaded in source
// priority order (dedicated competition files before the catch-all
// BR-Football-Dataset.csv), so keeping the first occurrence of each key
// keeps the more structured, purpose-built source.
func dedupeMatches(matches []Match) []Match {
	seen := make(map[string]bool, len(matches))
	result := make([]Match, 0, len(matches))
	for _, m := range matches {
		key := fmt.Sprintf("%s|%d|%s|%s|%d|%d",
			strings.ToLower(m.Competition), m.Season, m.HomeTeamKey, m.AwayTeamKey, m.HomeGoals, m.AwayGoals)
		if seen[key] {
			continue
		}
		seen[key] = true
		result = append(result, m)
	}
	return result
}

func loadBrasileirao(path string, store *Store) error {
	return readHeaderedRows(path, func(row map[string]string) error {
		homeKey, homeDisp := makeTeam(row["home_team"])
		awayKey, awayDisp := makeTeam(row["away_team"])
		m := Match{
			Competition: "Brasileirao",
			Source:      "Brasileirao_Matches.csv",
			Round:       row["round"],
			HomeTeam:    homeDisp,
			AwayTeam:    awayDisp,
			HomeTeamKey: homeKey,
			AwayTeamKey: awayKey,
			HomeGoals:   atoiOr(row["home_goal"], 0),
			AwayGoals:   atoiOr(row["away_goal"], 0),
			HomeState:   row["home_team_state"],
			AwayState:   row["away_team_state"],
			Season:      atoiOr(row["season"], 0),
		}
		if t, err := ParseFlexibleDate(row["datetime"]); err == nil {
			m.Date = t
			m.HasDate = true
			if m.Season == 0 {
				m.Season = t.Year()
			}
		}
		store.Matches = append(store.Matches, m)
		return nil
	})
}

func loadCopaDoBrasil(path string, store *Store) error {
	return readHeaderedRows(path, func(row map[string]string) error {
		homeKey, homeDisp := makeTeam(row["home_team"])
		awayKey, awayDisp := makeTeam(row["away_team"])
		m := Match{
			Competition: "Copa do Brasil",
			Source:      "Brazilian_Cup_Matches.csv",
			Round:       row["round"],
			HomeTeam:    homeDisp,
			AwayTeam:    awayDisp,
			HomeTeamKey: homeKey,
			AwayTeamKey: awayKey,
			HomeGoals:   atoiOr(row["home_goal"], 0),
			AwayGoals:   atoiOr(row["away_goal"], 0),
			Season:      atoiOr(row["season"], 0),
		}
		if t, err := ParseFlexibleDate(row["datetime"]); err == nil {
			m.Date = t
			m.HasDate = true
			if m.Season == 0 {
				m.Season = t.Year()
			}
		}
		store.Matches = append(store.Matches, m)
		return nil
	})
}

func loadLibertadores(path string, store *Store) error {
	return readHeaderedRows(path, func(row map[string]string) error {
		homeKey, homeDisp := makeTeam(row["home_team"])
		awayKey, awayDisp := makeTeam(row["away_team"])
		m := Match{
			Competition: "Copa Libertadores",
			Source:      "Libertadores_Matches.csv",
			Stage:       row["stage"],
			HomeTeam:    homeDisp,
			AwayTeam:    awayDisp,
			HomeTeamKey: homeKey,
			AwayTeamKey: awayKey,
			HomeGoals:   atoiOr(row["home_goal"], 0),
			AwayGoals:   atoiOr(row["away_goal"], 0),
			Season:      atoiOr(row["season"], 0),
		}
		if t, err := ParseFlexibleDate(row["datetime"]); err == nil {
			m.Date = t
			m.HasDate = true
			if m.Season == 0 {
				m.Season = t.Year()
			}
		}
		store.Matches = append(store.Matches, m)
		return nil
	})
}

var tournamentToCompetition = map[string]string{
	"copa do brasil": "Copa do Brasil",
	"serie a":        "Brasileirao",
	"serie b":        "Brasileirao Serie B",
	"serie c":        "Brasileirao Serie C",
}

func loadBRFootballDataset(path string, store *Store) error {
	return readHeaderedRows(path, func(row map[string]string) error {
		homeKey, homeDisp := makeTeam(row["home"])
		awayKey, awayDisp := makeTeam(row["away"])
		competition, ok := tournamentToCompetition[strings.ToLower(strings.TrimSpace(row["tournament"]))]
		if !ok {
			competition = row["tournament"]
		}
		m := Match{
			Competition: competition,
			Source:      "BR-Football-Dataset.csv",
			HomeTeam:    homeDisp,
			AwayTeam:    awayDisp,
			HomeTeamKey: homeKey,
			AwayTeamKey: awayKey,
			HomeGoals:   atoiOr(row["home_goal"], 0),
			AwayGoals:   atoiOr(row["away_goal"], 0),
		}
		dateStr := strings.TrimSpace(row["date"])
		if timeStr := strings.TrimSpace(row["time"]); timeStr != "" && dateStr != "" {
			if t, err := ParseFlexibleDate(dateStr + " " + timeStr); err == nil {
				m.Date = t
				m.HasDate = true
			}
		}
		if !m.HasDate && dateStr != "" {
			if t, err := ParseFlexibleDate(dateStr); err == nil {
				m.Date = t
				m.HasDate = true
			}
		}
		if m.HasDate {
			m.Season = m.Date.Year()
		}
		store.Matches = append(store.Matches, m)
		return nil
	})
}

var vencedorMap = map[string]string{
	"mandante":  "home",
	"visitante": "away",
	"empate":    "draw",
}

func loadNovoCampeonato(path string, store *Store) error {
	return readHeaderedRows(path, func(row map[string]string) error {
		homeKey, homeDisp := makeTeam(row["Equipe_mandante"])
		awayKey, awayDisp := makeTeam(row["Equipe_visitante"])
		m := Match{
			Competition: "Brasileirao",
			Source:      "novo_campeonato_brasileiro.csv",
			Round:       row["Rodada"],
			HomeTeam:    homeDisp,
			AwayTeam:    awayDisp,
			HomeTeamKey: homeKey,
			AwayTeamKey: awayKey,
			HomeGoals:   atoiOr(row["Gols_mandante"], 0),
			AwayGoals:   atoiOr(row["Gols_visitante"], 0),
			HomeState:   row["Mandante_UF"],
			AwayState:   row["Visitante_UF"],
			Season:      atoiOr(row["Ano"], 0),
			Arena:       row["Arena"],
		}
		if t, err := ParseFlexibleDate(row["Data"]); err == nil {
			m.Date = t
			m.HasDate = true
		}
		store.Matches = append(store.Matches, m)
		return nil
	})
}

func loadFifaPlayers(path string, store *Store) error {
	return readHeaderedRows(path, func(row map[string]string) error {
		clubKey, clubDisp := NormalizeTeamName(row["Club"])
		p := Player{
			ID:           atoiOr(row["ID"], 0),
			Name:         row["Name"],
			Age:          atoiOr(row["Age"], 0),
			Nationality:  row["Nationality"],
			Overall:      atoiOr(row["Overall"], 0),
			Potential:    atoiOr(row["Potential"], 0),
			Club:         clubDisp,
			ClubKey:      clubKey,
			Position:     row["Position"],
			JerseyNumber: atoiOr(row["Jersey Number"], 0),
			Height:       row["Height"],
			Weight:       row["Weight"],
		}
		if p.Name == "" {
			return nil
		}
		store.Players = append(store.Players, p)
		return nil
	})
}
