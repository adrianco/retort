package loader

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
	"time"
)

// parseDateTime tries multiple date formats.
func parseDateTime(s string) (time.Time, error) {
	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02",
		"02/01/2006",
	}
	s = strings.TrimSpace(s)
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("cannot parse date %q", s)
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

// indexCols returns a map from column name to index.
func indexCols(header []string) map[string]int {
	m := make(map[string]int, len(header))
	for i, h := range header {
		// Strip BOM and quotes
		h = strings.TrimLeft(h, "\xef\xbb\xbf")
		h = strings.Trim(h, "\"")
		m[h] = i
	}
	return m
}

func col(row []string, idx map[string]int, name string) string {
	i, ok := idx[name]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func LoadBrasileiraoMatches(path string) ([]BrasileiraoMatch, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexCols(header)

	var matches []BrasileiraoMatch
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		dt, _ := parseDateTime(col(row, idx, "datetime"))
		m := BrasileiraoMatch{
			Datetime:      dt,
			HomeTeam:      col(row, idx, "home_team"),
			HomeTeamState: col(row, idx, "home_team_state"),
			AwayTeam:      col(row, idx, "away_team"),
			AwayTeamState: col(row, idx, "away_team_state"),
			HomeGoal:      parseInt(col(row, idx, "home_goal")),
			AwayGoal:      parseInt(col(row, idx, "away_goal")),
			Season:        parseInt(col(row, idx, "season")),
			Round:         parseInt(col(row, idx, "round")),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func LoadCupMatches(path string) ([]CupMatch, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexCols(header)

	var matches []CupMatch
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		dt, _ := parseDateTime(col(row, idx, "datetime"))
		m := CupMatch{
			Round:    col(row, idx, "round"),
			Datetime: dt,
			HomeTeam: col(row, idx, "home_team"),
			AwayTeam: col(row, idx, "away_team"),
			HomeGoal: parseInt(col(row, idx, "home_goal")),
			AwayGoal: parseInt(col(row, idx, "away_goal")),
			Season:   parseInt(col(row, idx, "season")),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func LoadLibertadoresMatches(path string) ([]LibertadoresMatch, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexCols(header)

	var matches []LibertadoresMatch
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		dt, _ := parseDateTime(col(row, idx, "datetime"))
		m := LibertadoresMatch{
			Datetime: dt,
			HomeTeam: col(row, idx, "home_team"),
			AwayTeam: col(row, idx, "away_team"),
			HomeGoal: parseInt(col(row, idx, "home_goal")),
			AwayGoal: parseInt(col(row, idx, "away_goal")),
			Season:   parseInt(col(row, idx, "season")),
			Stage:    col(row, idx, "stage"),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func LoadExtendedMatches(path string) ([]ExtendedMatch, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexCols(header)

	var matches []ExtendedMatch
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		dt, _ := parseDateTime(col(row, idx, "date"))
		m := ExtendedMatch{
			Tournament:   col(row, idx, "tournament"),
			HomeTeam:     col(row, idx, "home"),
			AwayTeam:     col(row, idx, "away"),
			HomeGoal:     parseFloat(col(row, idx, "home_goal")),
			AwayGoal:     parseFloat(col(row, idx, "away_goal")),
			HomeCorner:   parseFloat(col(row, idx, "home_corner")),
			AwayCorner:   parseFloat(col(row, idx, "away_corner")),
			HomeAttack:   parseFloat(col(row, idx, "home_attack")),
			AwayAttack:   parseFloat(col(row, idx, "away_attack")),
			HomeShots:    parseFloat(col(row, idx, "home_shots")),
			AwayShots:    parseFloat(col(row, idx, "away_shots")),
			Time:         col(row, idx, "time"),
			Date:         dt,
			TotalCorners: parseFloat(col(row, idx, "total_corners")),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func LoadHistoricalMatches(path string) ([]HistoricalMatch, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexCols(header)

	var matches []HistoricalMatch
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		dt, _ := parseDateTime(col(row, idx, "Data"))
		m := HistoricalMatch{
			ID:        col(row, idx, "ID"),
			Date:      dt,
			Year:      parseInt(col(row, idx, "Ano")),
			Round:     parseInt(col(row, idx, "Rodada")),
			HomeTeam:  col(row, idx, "Equipe_mandante"),
			AwayTeam:  col(row, idx, "Equipe_visitante"),
			HomeGoals: parseInt(col(row, idx, "Gols_mandante")),
			AwayGoals: parseInt(col(row, idx, "Gols_visitante")),
			HomeState: col(row, idx, "Mandante_UF"),
			AwayState: col(row, idx, "Visitante_UF"),
			Winner:    col(row, idx, "Vencedor"),
			Arena:     col(row, idx, "Arena"),
		}
		matches = append(matches, m)
	}
	return matches, nil
}

func LoadPlayers(path string) ([]Player, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	idx := indexCols(header)

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
			ID:          parseInt(col(row, idx, "ID")),
			Name:        col(row, idx, "Name"),
			Age:         parseInt(col(row, idx, "Age")),
			Nationality: col(row, idx, "Nationality"),
			Overall:     parseInt(col(row, idx, "Overall")),
			Potential:   parseInt(col(row, idx, "Potential")),
			Club:        col(row, idx, "Club"),
			Position:    col(row, idx, "Position"),
			JerseyNumber: parseInt(col(row, idx, "Jersey Number")),
			Height:      col(row, idx, "Height"),
			Weight:      col(row, idx, "Weight"),
			Crossing:    parseInt(col(row, idx, "Crossing")),
			Finishing:   parseInt(col(row, idx, "Finishing")),
			Dribbling:   parseInt(col(row, idx, "Dribbling")),
			SprintSpeed: parseInt(col(row, idx, "SprintSpeed")),
			Reactions:   parseInt(col(row, idx, "Reactions")),
			Stamina:     parseInt(col(row, idx, "Stamina")),
		}
		players = append(players, p)
	}
	return players, nil
}
