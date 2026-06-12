package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// LoadStore loads all CSV files from the given directory into a Store.
func LoadStore(dataDir string) (*Store, error) {
	store := &Store{}

	files := []struct {
		name   string
		loader func(*Store, string) error
	}{
		{"Brasileirao_Matches.csv", loadBrasileiraoMatches},
		{"Brazilian_Cup_Matches.csv", loadCupMatches},
		{"Libertadores_Matches.csv", loadLibertadoresMatches},
		{"BR-Football-Dataset.csv", loadBRFootballDataset},
		{"novo_campeonato_brasileiro.csv", loadNovoCampeonato},
		{"fifa_data.csv", loadFIFAData},
	}

	for _, f := range files {
		path := filepath.Join(dataDir, f.name)
		if err := f.loader(store, path); err != nil {
			fmt.Printf("Warning: error loading %s: %v\n", f.name, err)
		}
	}

	return store, nil
}

// parseDate normalises various date formats to "YYYY-MM-DD".
func parseDate(s string) string {
	s = strings.TrimSpace(s)
	// "2012-05-19 18:30:00" -> "2012-05-19"
	if len(s) >= 10 && s[4] == '-' {
		return s[:10]
	}
	// "29/03/2003" -> "2003-03-29"
	if len(s) == 10 && s[2] == '/' {
		parts := strings.Split(s, "/")
		if len(parts) == 3 {
			return parts[2] + "-" + parts[1] + "-" + parts[0]
		}
	}
	return s
}

// parseGoals converts "1", "1.0", "2" etc. to int. Returns 0 on error.
func parseGoals(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	// Handle float strings like "1.0"
	if strings.Contains(s, ".") {
		f, err := strconv.ParseFloat(s, 64)
		if err != nil {
			return 0
		}
		return int(f)
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return n
}

// parseSeason converts a season string to int. Returns 0 on error.
func parseSeason(s string) int {
	s = strings.TrimSpace(s)
	n, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return n
}

// openCSV opens a CSV file and returns a reader plus the closer function.
func openCSV(path string) (*csv.Reader, func(), error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.TrimLeadingSpace = true
	return r, func() { f.Close() }, nil
}

// stripBOM removes a UTF-8 BOM from a string if present.
func stripBOM(s string) string {
	return strings.TrimPrefix(s, "\xef\xbb\xbf")
}

// headerIndex builds a map of column name -> index from a header row.
func headerIndex(headers []string) map[string]int {
	m := make(map[string]int, len(headers))
	for i, h := range headers {
		m[stripBOM(strings.TrimSpace(h))] = i
	}
	return m
}

// safeGet retrieves a CSV field by column name, returning "" if not found.
func safeGet(record []string, idx map[string]int, col string) string {
	i, ok := idx[col]
	if !ok || i >= len(record) {
		return ""
	}
	return strings.TrimSpace(record[i])
}

// -------- Brasileirao_Matches.csv --------
// columns: datetime, home_team, home_team_state, away_team, away_team_state,
//          home_goal, away_goal, season, round

func loadBrasileiraoMatches(store *Store, path string) error {
	r, close, err := openCSV(path)
	if err != nil {
		return err
	}
	defer close()

	headers, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(headers)

	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Date:        parseDate(safeGet(rec, idx, "datetime")),
			HomeTeam:    safeGet(rec, idx, "home_team"),
			AwayTeam:    safeGet(rec, idx, "away_team"),
			HomeGoals:   parseGoals(safeGet(rec, idx, "home_goal")),
			AwayGoals:   parseGoals(safeGet(rec, idx, "away_goal")),
			Season:      parseSeason(safeGet(rec, idx, "season")),
			Round:       safeGet(rec, idx, "round"),
			Competition: "brasileirao",
			Source:      "Brasileirao_Matches.csv",
		}
		if m.HomeTeam == "" || m.AwayTeam == "" {
			continue
		}
		store.Matches = append(store.Matches, m)
	}
	return nil
}

// -------- Brazilian_Cup_Matches.csv --------
// columns: round, datetime, home_team, away_team, home_goal, away_goal, season

func loadCupMatches(store *Store, path string) error {
	r, close, err := openCSV(path)
	if err != nil {
		return err
	}
	defer close()

	headers, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(headers)

	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Date:        parseDate(safeGet(rec, idx, "datetime")),
			HomeTeam:    safeGet(rec, idx, "home_team"),
			AwayTeam:    safeGet(rec, idx, "away_team"),
			HomeGoals:   parseGoals(safeGet(rec, idx, "home_goal")),
			AwayGoals:   parseGoals(safeGet(rec, idx, "away_goal")),
			Season:      parseSeason(safeGet(rec, idx, "season")),
			Round:       safeGet(rec, idx, "round"),
			Competition: "copa_brasil",
			Source:      "Brazilian_Cup_Matches.csv",
		}
		if m.HomeTeam == "" || m.AwayTeam == "" {
			continue
		}
		store.Matches = append(store.Matches, m)
	}
	return nil
}

// -------- Libertadores_Matches.csv --------
// columns: datetime, home_team, away_team, home_goal, away_goal, season, stage

func loadLibertadoresMatches(store *Store, path string) error {
	r, close, err := openCSV(path)
	if err != nil {
		return err
	}
	defer close()

	headers, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(headers)

	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Date:        parseDate(safeGet(rec, idx, "datetime")),
			HomeTeam:    safeGet(rec, idx, "home_team"),
			AwayTeam:    safeGet(rec, idx, "away_team"),
			HomeGoals:   parseGoals(safeGet(rec, idx, "home_goal")),
			AwayGoals:   parseGoals(safeGet(rec, idx, "away_goal")),
			Season:      parseSeason(safeGet(rec, idx, "season")),
			Stage:       safeGet(rec, idx, "stage"),
			Competition: "libertadores",
			Source:      "Libertadores_Matches.csv",
		}
		if m.HomeTeam == "" || m.AwayTeam == "" {
			continue
		}
		store.Matches = append(store.Matches, m)
	}
	return nil
}

// -------- BR-Football-Dataset.csv --------
// columns: tournament, home, home_goal, away_goal, away, ..., date, ...
// competition derived from tournament column

func loadBRFootballDataset(store *Store, path string) error {
	r, close, err := openCSV(path)
	if err != nil {
		return err
	}
	defer close()

	headers, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(headers)

	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		tournament := strings.ToLower(safeGet(rec, idx, "tournament"))
		var competition string
		switch {
		case strings.Contains(tournament, "brasileirao") || strings.Contains(tournament, "brasileiro"):
			competition = "brasileirao"
		case strings.Contains(tournament, "copa do brasil") || strings.Contains(tournament, "copa brasil"):
			competition = "copa_brasil"
		case strings.Contains(tournament, "libertadores"):
			competition = "libertadores"
		default:
			competition = "other"
		}

		dateStr := safeGet(rec, idx, "date")
		m := Match{
			Date:        parseDate(dateStr),
			HomeTeam:    safeGet(rec, idx, "home"),
			AwayTeam:    safeGet(rec, idx, "away"),
			HomeGoals:   parseGoals(safeGet(rec, idx, "home_goal")),
			AwayGoals:   parseGoals(safeGet(rec, idx, "away_goal")),
			Competition: competition,
			Source:      "BR-Football-Dataset.csv",
		}
		if m.HomeTeam == "" || m.AwayTeam == "" {
			continue
		}
		store.Matches = append(store.Matches, m)
	}
	return nil
}

// -------- novo_campeonato_brasileiro.csv --------
// columns: ID, Data, Ano, Rodada, Equipe_mandante, Equipe_visitante,
//          Gols_mandante, Gols_visitante, Mandante_UF, Visitante_UF,
//          Vencedor, Arena, OBS

func loadNovoCampeonato(store *Store, path string) error {
	r, close, err := openCSV(path)
	if err != nil {
		return err
	}
	defer close()

	headers, err := r.Read()
	if err != nil {
		return err
	}
	idx := headerIndex(headers)

	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		m := Match{
			Date:        parseDate(safeGet(rec, idx, "Data")),
			HomeTeam:    safeGet(rec, idx, "Equipe_mandante"),
			AwayTeam:    safeGet(rec, idx, "Equipe_visitante"),
			HomeGoals:   parseGoals(safeGet(rec, idx, "Gols_mandante")),
			AwayGoals:   parseGoals(safeGet(rec, idx, "Gols_visitante")),
			Season:      parseSeason(safeGet(rec, idx, "Ano")),
			Round:       safeGet(rec, idx, "Rodada"),
			Arena:       safeGet(rec, idx, "Arena"),
			Competition: "brasileirao",
			Source:      "novo_campeonato_brasileiro.csv",
		}
		if m.HomeTeam == "" || m.AwayTeam == "" {
			continue
		}
		store.Matches = append(store.Matches, m)
	}
	return nil
}

// -------- fifa_data.csv --------
// Has BOM, columns include: ID, Name, Age, Nationality, Overall, Potential,
//   Club, Position, Jersey Number, Height, Weight

func loadFIFAData(store *Store, path string) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.TrimLeadingSpace = true

	headers, err := r.Read()
	if err != nil {
		return err
	}
	// Strip BOM from first header
	if len(headers) > 0 {
		headers[0] = stripBOM(headers[0])
	}
	idx := headerIndex(headers)

	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		name := safeGet(rec, idx, "Name")
		if name == "" {
			continue
		}
		ageStr := safeGet(rec, idx, "Age")
		age, _ := strconv.Atoi(ageStr)
		overallStr := safeGet(rec, idx, "Overall")
		overall, _ := strconv.Atoi(overallStr)
		potentialStr := safeGet(rec, idx, "Potential")
		potential, _ := strconv.Atoi(potentialStr)

		p := Player{
			ID:           safeGet(rec, idx, "ID"),
			Name:         name,
			Age:          age,
			Nationality:  safeGet(rec, idx, "Nationality"),
			Overall:      overall,
			Potential:    potential,
			Club:         safeGet(rec, idx, "Club"),
			Position:     safeGet(rec, idx, "Position"),
			JerseyNumber: safeGet(rec, idx, "Jersey Number"),
			Height:       safeGet(rec, idx, "Height"),
			Weight:       safeGet(rec, idx, "Weight"),
		}
		store.Players = append(store.Players, p)
	}
	return nil
}
