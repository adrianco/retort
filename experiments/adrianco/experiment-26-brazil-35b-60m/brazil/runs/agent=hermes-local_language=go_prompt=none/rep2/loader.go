// The CSV loader reads and normalizes team names across all 6 Kaggle datasets,
// parsing dates and numeric fields into Go types for storage in the MCP store.
package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
)

// LoadBrasileirao loads Brasileirao Serie A matches (home_team_state suffix).
func LoadBrasileirao(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open brasileirao: %w", err)
	}
	defer f.Close()

	var matches []Match
	r := csv.NewReader(f)
	r.LazyQuotes = true
	_, err = r.Read() // skip header
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read row: %w", err)
		}
		if len(row) < 9 {
			continue
		}

		season := parseInt(strings.TrimSpace(row[7]))
		round := parseInt(strings.TrimSpace(row[8]))

		matches = append(matches, Match{
			DateTime:    strings.TrimSpace(row[0]),
			HomeTeam:    normalizeTeamName(strings.TrimSpace(row[1])),
			AwayTeam:    normalizeTeamName(strings.TrimSpace(row[4])),
			HomeScore:   parseInt(row[5]),
			AwayScore:   parseInt(row[6]),
			Season:      season,
			Round:       strconv.Itoa(round),
			Competition: "Brasileirao Serie A",
			Source:      "Brasileirao_Matches.csv",
		})
	}
	return matches, nil
}

// LoadCopaBrasil loads Copa do Brasil matches.
func LoadCopaBrasil(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open copa brasil: %w", err)
	}
	defer f.Close()

	var matches []Match
	r := csv.NewReader(f)
	r.LazyQuotes = true
	_, err = r.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read row: %w", err)
		}
		if len(row) < 7 {
			continue
		}

		season := parseInt(strings.TrimSpace(row[6]))
		round := strings.TrimSpace(row[0])

		matches = append(matches, Match{
			DateTime:    strings.TrimSpace(row[1]),
			HomeTeam:    normalizeTeamName(strings.TrimSpace(row[2])),
			AwayTeam:    normalizeTeamName(strings.TrimSpace(row[3])),
			HomeScore:   parseInt(row[4]),
			AwayScore:   parseInt(row[5]),
			Season:      season,
			Round:       round,
			Competition: "Copa do Brasil",
			Source:      "Brazilian_Cup_Matches.csv",
		})
	}
	return matches, nil
}

// LoadLibertadores loads Copa Libertadores matches.
func LoadLibertadores(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open libertadores: %w", err)
	}
	defer f.Close()

	var matches []Match
	r := csv.NewReader(f)
	r.LazyQuotes = true
	_, err = r.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read row: %w", err)
		}
		if len(row) < 7 {
			continue
		}

		season := parseInt(strings.TrimSpace(row[5]))

		matches = append(matches, Match{
			DateTime:    strings.TrimSpace(row[0]),
			HomeTeam:    normalizeTeamName(strings.TrimSpace(row[1])),
			AwayTeam:    normalizeTeamName(strings.TrimSpace(row[2])),
			HomeScore:   parseInt(row[3]),
			AwayScore:   parseInt(row[4]),
			Season:      season,
			Stage:       strings.TrimSpace(row[6]),
			Competition: "Copa Libertadores",
			Source:      "Libertadores_Matches.csv",
		})
	}
	return matches, nil
}

// LoadBRFootball loads the extended match statistics dataset.
func LoadBRFootball(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open br-football: %w", err)
	}
	defer f.Close()

	var matches []Match
	r := csv.NewReader(f)
	r.LazyQuotes = true
	_, err = r.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read row: %w", err)
		}
		if len(row) < 18 {
			continue
		}

		// Extract date from the "date" column (index 12)
		dateStr := strings.TrimSpace(row[12])
		// Extract season from date if possible
		season := 0
		if len(dateStr) >= 4 {
			parts := strings.Split(dateStr, "-")
			if len(parts) >= 1 {
				season = parseInt(parts[0])
			}
		}

		tournament := strings.TrimSpace(row[0])
		competition := tournament
		if competition == "" {
			competition = "Brazilian Football"
		}

		matches = append(matches, Match{
			DateTime:    dateStr,
			HomeTeam:    normalizeTeamName(strings.TrimSpace(row[1])),
			AwayTeam:    normalizeTeamName(strings.TrimSpace(row[4])),
			HomeScore:   parseInt(row[2]),
			AwayScore:   parseInt(row[3]),
			Season:      season,
			Tournament:  tournament,
			Competition: competition,
			Source:      "BR-Football-Dataset.csv",
		})
	}
	return matches, nil
}

// LoadNovoCampeonato loads historical Brasileirao 2003-2019.
func LoadNovoCampeonato(path string) ([]Match, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open novo campeonato: %w", err)
	}
	defer f.Close()

	var matches []Match
	r := csv.NewReader(f)
	r.LazyQuotes = true
	_, err = r.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read row: %w", err)
		}
		if len(row) < 13 {
			continue
		}

		// Date format: DD/MM/YYYY
		dateStr := strings.TrimSpace(row[1])
		year := 0
		if len(dateStr) >= 7 {
			parts := strings.Split(dateStr, "/")
			if len(parts) >= 3 {
				year = parseInt(parts[2])
			}
		}

		round := parseInt(strings.TrimSpace(row[3]))

		matches = append(matches, Match{
			DateTime:    dateStr,
			HomeTeam:    normalizeTeamName(strings.TrimSpace(row[4])),
			AwayTeam:    normalizeTeamName(strings.TrimSpace(row[5])),
			HomeScore:   parseInt(row[6]),
			AwayScore:   parseInt(row[7]),
			Season:      year,
			Round:       strconv.Itoa(round),
			Competition: "Campeonato Brasileiro",
			Source:      "novo_campeonato_brasileiro.csv",
		})
	}
	return matches, nil
}

// LoadFIFAPlayers loads FIFA player database.
func LoadFIFAPlayers(path string) ([]Player, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open fifa: %w", err)
	}
	defer f.Close()

	var players []Player
	r := csv.NewReader(f)
	r.LazyQuotes = true
	header, err := r.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}

	// Find column indices (header[0] may be empty due to BOM)
	colIdx := make(map[string]int)
	for i, name := range header {
		colIdx[strings.TrimSpace(name)] = i
	}

	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("read row: %w", err)
		}
		if len(row) < 10 {
			continue
		}

		id := parseInt(getCol(row, colIdx, "ID"))
		name := strings.TrimSpace(getCol(row, colIdx, "Name"))
		age := parseInt(getCol(row, colIdx, "Age"))
		nationality := strings.TrimSpace(getCol(row, colIdx, "Nationality"))
		overall := parseInt(getCol(row, colIdx, "Overall"))
		potential := parseInt(getCol(row, colIdx, "Potential"))
		club := strings.TrimSpace(getCol(row, colIdx, "Club"))
		position := strings.TrimSpace(getCol(row, colIdx, "Position"))

		players = append(players, Player{
			ID:          id,
			Name:        name,
			Age:         age,
			Nationality: nationality,
			Overall:     overall,
			Potential:   potential,
			Club:        club,
			Position:    position,
		})
	}
	return players, nil
}

// Helper functions
func normalizeTeamName(name string) string {
	// Remove state suffixes like -SP, -RJ, -MG, -PR, -RS, -BA, -CE, -GO, -PE, -AL, -MT, -PA, -PB, -ES, -DF
	for _, suffix := range []string{"-SP", "-RJ", "-MG", "-PR", "-RS", "-BA", "-CE", "-GO", "-PE", "-AL", "-MT", "-PA", "-PB", "-ES", "-DF"} {
		name = strings.TrimSuffix(name, suffix)
	}
	// Trim whitespace and clean up
	name = strings.TrimSpace(name)
	return name
}

func parseInt(s string) int {
	s = strings.TrimSpace(s)
	s = strings.ReplaceAll(s, ".", "")
	val, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return val
}

func getCol(row []string, idx map[string]int, name string) string {
	if i, ok := idx[name]; ok && i < len(row) {
		return row[i]
	}
	if i, ok := idx[""+name]; ok && i < len(row) {
		return row[i]
	}
	return ""
}
