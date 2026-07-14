package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
)

// Database holds all loaded data
type Database struct {
	Matches []Match
	Players []Player
}

// seasonRange holds the min and max seasons in a dataset
type seasonRange struct{ min, max int }

// LoadAll loads all CSV files from the given data directory
func LoadAll(dataDir string) (*Database, error) {
	db := &Database{}

	var errs []string

	var brasileiraoSeasons seasonRange
	if matches, err := loadBrasileiraoMatches(dataDir + "/Brasileirao_Matches.csv"); err != nil {
		errs = append(errs, "Brasileirao: "+err.Error())
	} else {
		brasileiraoSeasons = seasonRangeOf(matches)
		db.Matches = append(db.Matches, matches...)
	}

	if matches, err := loadCupMatches(dataDir + "/Brazilian_Cup_Matches.csv"); err != nil {
		errs = append(errs, "Cup: "+err.Error())
	} else {
		db.Matches = append(db.Matches, matches...)
	}

	if matches, err := loadLibertadoresMatches(dataDir + "/Libertadores_Matches.csv"); err != nil {
		errs = append(errs, "Libertadores: "+err.Error())
	} else {
		db.Matches = append(db.Matches, matches...)
	}

	if matches, err := loadBRFootballDataset(dataDir + "/BR-Football-Dataset.csv"); err != nil {
		errs = append(errs, "BR-Football: "+err.Error())
	} else {
		// Mark BR-Football-Dataset Serie A entries as primary only for seasons
		// not covered by Brasileirao_Matches.csv (i.e., 2023+)
		for i := range matches {
			m := &matches[i]
			isBrasileiraoComp := strings.Contains(strings.ToLower(m.Competition), "serie a") ||
				strings.Contains(strings.ToLower(m.Competition), "brasileirao")
			if isBrasileiraoComp && m.Season >= brasileiraoSeasons.min && m.Season <= brasileiraoSeasons.max {
				m.IsPrimary = false
			} else if isBrasileiraoComp && m.Season > brasileiraoSeasons.max {
				m.IsPrimary = true // 2023+ data only available here
			}
		}
		db.Matches = append(db.Matches, matches...)
	}

	if matches, err := loadHistoricalBrasileiraoMatches(dataDir + "/novo_campeonato_brasileiro.csv"); err != nil {
		errs = append(errs, "Historical: "+err.Error())
	} else {
		// Historical data overlaps with Brasileirao_Matches.csv for some seasons.
		// Mark overlapping seasons as non-primary to avoid double-counting.
		for i := range matches {
			m := &matches[i]
			if m.Season >= brasileiraoSeasons.min && m.Season <= brasileiraoSeasons.max {
				m.IsPrimary = false
			}
		}
		db.Matches = append(db.Matches, matches...)
	}

	if players, err := loadFIFAPlayers(dataDir + "/fifa_data.csv"); err != nil {
		errs = append(errs, "FIFA: "+err.Error())
	} else {
		db.Players = players
	}

	db.Matches = deduplicateMatches(db.Matches)

	if len(errs) > 0 {
		return db, fmt.Errorf("partial load errors: %s", strings.Join(errs, "; "))
	}
	return db, nil
}

// deduplicateMatches removes duplicate matches by (date, homeNorm, awayNorm).
// When duplicates exist, prefer the entry with extended stats.
func deduplicateMatches(matches []Match) []Match {
	seen := make(map[string]int) // key -> index in result
	result := make([]Match, 0, len(matches))
	for _, m := range matches {
		if m.Date == "" || m.Date == "NA" {
			continue
		}
		key := m.Date + "|" + m.HomeNorm + "|" + m.AwayNorm
		if idx, ok := seen[key]; ok {
			// Prefer the entry with HasStats; merge stats into existing entry
			if m.HasStats && !result[idx].HasStats {
				merged := result[idx]
				merged.HasStats = true
				merged.HomeCorner = m.HomeCorner
				merged.AwayCorner = m.AwayCorner
				merged.HomeAttack = m.HomeAttack
				merged.AwayAttack = m.AwayAttack
				merged.HomeShots = m.HomeShots
				merged.AwayShots = m.AwayShots
				merged.TotalCorners = m.TotalCorners
				result[idx] = merged
			}
			continue
		}
		seen[key] = len(result)
		result = append(result, m)
	}
	return result
}

func seasonRangeOf(matches []Match) seasonRange {
	r := seasonRange{}
	for _, m := range matches {
		if m.Season == 0 {
			continue
		}
		if r.min == 0 || m.Season < r.min {
			r.min = m.Season
		}
		if m.Season > r.max {
			r.max = m.Season
		}
	}
	return r
}

func openCSV(path string) (*csv.Reader, *os.File, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	// Skip BOM if present
	buf := make([]byte, 3)
	n, _ := f.Read(buf)
	if n == 3 && buf[0] == 0xEF && buf[1] == 0xBB && buf[2] == 0xBF {
		// BOM found, already skipped
	} else {
		f.Seek(0, io.SeekStart)
	}
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.TrimLeadingSpace = true
	return r, f, nil
}

func colIndex(headers []string) map[string]int {
	m := make(map[string]int)
	for i, h := range headers {
		h = strings.TrimSpace(h)
		// Remove BOM if present in first header
		h = strings.TrimPrefix(h, "\xef\xbb\xbf")
		h = strings.TrimPrefix(h, string([]byte{0xef, 0xbb, 0xbf}))
		m[h] = i
	}
	return m
}

func getCol(row []string, idx map[string]int, key string) string {
	i, ok := idx[key]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func parseInt(s string) int {
	s = strings.TrimSpace(s)
	v, _ := strconv.Atoi(s)
	return v
}

func parseFloat(s string) float64 {
	s = strings.TrimSpace(s)
	v, _ := strconv.ParseFloat(s, 64)
	return v
}

// parseDate normalizes dates to YYYY-MM-DD
func parseDate(s string) string {
	s = strings.TrimSpace(s)
	if s == "" {
		return ""
	}
	// "2012-05-19 18:30:00" -> "2012-05-19"
	if len(s) >= 10 && s[4] == '-' {
		return s[:10]
	}
	// "29/03/2003" -> "2003-03-29"
	if len(s) == 10 && s[2] == '/' && s[5] == '/' {
		return s[6:10] + "-" + s[3:5] + "-" + s[0:2]
	}
	return s
}

func makeMatch(competition, date, homeTeam, awayTeam string, homeGoal, awayGoal, season int) Match {
	return Match{
		Competition: competition,
		Date:        parseDate(date),
		HomeTeam:    homeTeam,
		AwayTeam:    awayTeam,
		HomeNorm:    normalizeTeam(homeTeam),
		AwayNorm:    normalizeTeam(awayTeam),
		HomeGoal:    homeGoal,
		AwayGoal:    awayGoal,
		Season:      season,
		IsPrimary:   true, // default; overridden for supplemental datasets
	}
}

func loadBrasileiraoMatches(path string) ([]Match, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := colIndex(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := makeMatch(
			"Brasileirao Serie A",
			getCol(row, idx, "datetime"),
			getCol(row, idx, "home_team"),
			getCol(row, idx, "away_team"),
			parseInt(getCol(row, idx, "home_goal")),
			parseInt(getCol(row, idx, "away_goal")),
			parseInt(getCol(row, idx, "season")),
		)
		m.Round = getCol(row, idx, "round")
		m.HomeState = getCol(row, idx, "home_team_state")
		m.AwayState = getCol(row, idx, "away_team_state")
		matches = append(matches, m)
	}
	return matches, nil
}

func loadCupMatches(path string) ([]Match, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := colIndex(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := makeMatch(
			"Copa do Brasil",
			getCol(row, idx, "datetime"),
			getCol(row, idx, "home_team"),
			getCol(row, idx, "away_team"),
			parseInt(getCol(row, idx, "home_goal")),
			parseInt(getCol(row, idx, "away_goal")),
			parseInt(getCol(row, idx, "season")),
		)
		m.Round = getCol(row, idx, "round")
		matches = append(matches, m)
	}
	return matches, nil
}

func loadLibertadoresMatches(path string) ([]Match, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := colIndex(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := makeMatch(
			"Copa Libertadores",
			getCol(row, idx, "datetime"),
			getCol(row, idx, "home_team"),
			getCol(row, idx, "away_team"),
			parseInt(getCol(row, idx, "home_goal")),
			parseInt(getCol(row, idx, "away_goal")),
			parseInt(getCol(row, idx, "season")),
		)
		m.Stage = getCol(row, idx, "stage")
		matches = append(matches, m)
	}
	return matches, nil
}

func loadBRFootballDataset(path string) ([]Match, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := colIndex(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		tournament := getCol(row, idx, "tournament")
		homeGoal := int(parseFloat(getCol(row, idx, "home_goal")))
		awayGoal := int(parseFloat(getCol(row, idx, "away_goal")))
		date := getCol(row, idx, "date")
		homeTeam := getCol(row, idx, "home")
		awayTeam := getCol(row, idx, "away")

		// Parse the date (format: YYYY-MM-DD)
		m := makeMatch(tournament, date, homeTeam, awayTeam, homeGoal, awayGoal, 0)

		// Extract year from date for season
		if len(date) >= 4 {
			m.Season = parseInt(date[:4])
		}

		m.IsPrimary = false // supplemental dataset; primary source may overlap
		m.HasStats = true
		m.HomeCorner = int(parseFloat(getCol(row, idx, "home_corner")))
		m.AwayCorner = int(parseFloat(getCol(row, idx, "away_corner")))
		m.HomeAttack = int(parseFloat(getCol(row, idx, "home_attack")))
		m.AwayAttack = int(parseFloat(getCol(row, idx, "away_attack")))
		m.HomeShots = int(parseFloat(getCol(row, idx, "home_shots")))
		m.AwayShots = int(parseFloat(getCol(row, idx, "away_shots")))
		m.TotalCorners = int(parseFloat(getCol(row, idx, "total_corners")))

		matches = append(matches, m)
	}
	return matches, nil
}

func loadHistoricalBrasileiraoMatches(path string) ([]Match, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := colIndex(headers)

	var matches []Match
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := makeMatch(
			"Brasileirao Serie A",
			getCol(row, idx, "Data"),
			getCol(row, idx, "Equipe_mandante"),
			getCol(row, idx, "Equipe_visitante"),
			parseInt(getCol(row, idx, "Gols_mandante")),
			parseInt(getCol(row, idx, "Gols_visitante")),
			parseInt(getCol(row, idx, "Ano")),
		)
		m.Round = getCol(row, idx, "Rodada")
		m.HomeState = getCol(row, idx, "Mandante_UF")
		m.AwayState = getCol(row, idx, "Visitante_UF")
		m.Arena = getCol(row, idx, "Arena")
		matches = append(matches, m)
	}
	return matches, nil
}

func loadFIFAPlayers(path string) ([]Player, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	headers, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := colIndex(headers)

	var players []Player
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		p := Player{
			ID:          getCol(row, idx, "ID"),
			Name:        getCol(row, idx, "Name"),
			Age:         parseInt(getCol(row, idx, "Age")),
			Nationality: getCol(row, idx, "Nationality"),
			Overall:     parseInt(getCol(row, idx, "Overall")),
			Potential:   parseInt(getCol(row, idx, "Potential")),
			Club:        getCol(row, idx, "Club"),
			Position:    getCol(row, idx, "Position"),
			Height:      getCol(row, idx, "Height"),
			Weight:      getCol(row, idx, "Weight"),
			Value:       getCol(row, idx, "Value"),
			Wage:        getCol(row, idx, "Wage"),
			Crossing:    parseInt(getCol(row, idx, "Crossing")),
			Finishing:   parseInt(getCol(row, idx, "Finishing")),
			Dribbling:   parseInt(getCol(row, idx, "Dribbling")),
			Passing:     parseInt(getCol(row, idx, "ShortPassing")),
		}
		players = append(players, p)
	}
	return players, nil
}
