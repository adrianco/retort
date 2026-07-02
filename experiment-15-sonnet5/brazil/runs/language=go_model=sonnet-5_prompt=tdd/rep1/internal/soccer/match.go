package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"strconv"
	"strings"
	"time"
)

// Match represents a single soccer match normalized from any of the source
// datasets.
type Match struct {
	Date        time.Time
	Season      int
	Round       string
	Stage       string
	Competition string
	Source      string

	HomeTeam string
	AwayTeam string
	HomeKey  string
	AwayKey  string

	HomeGoals int
	AwayGoals int

	HomeState string
	AwayState string
	Stadium   string
}

// Outcome returns "home", "away" or "draw" describing the match result.
func (m Match) Outcome() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return "home"
	case m.AwayGoals > m.HomeGoals:
		return "away"
	default:
		return "draw"
	}
}

func readCSVRecords(r io.Reader) ([]string, [][]string, error) {
	cr := csv.NewReader(r)
	cr.TrimLeadingSpace = true
	rows, err := cr.ReadAll()
	if err != nil {
		return nil, nil, err
	}
	if len(rows) == 0 {
		return nil, nil, fmt.Errorf("soccer: empty CSV")
	}
	header := rows[0]
	// Strip a UTF-8 BOM from the first header cell, if present.
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\ufeff")
	}
	return header, rows[1:], nil
}

// columnIndex builds a lookup from column name to index for a CSV header row.
func columnIndex(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, name := range header {
		idx[name] = i
	}
	return idx
}

func parseIntField(s string) int {
	s = strings.TrimSpace(strings.TrimSuffix(s, ".0"))
	n, _ := strconv.Atoi(s)
	return n
}

// LoadBrasileiraoMatches parses the Brasileirao_Matches.csv dataset.
func LoadBrasileiraoMatches(r io.Reader) ([]Match, error) {
	header, rows, err := readCSVRecords(r)
	if err != nil {
		return nil, err
	}
	col := columnIndex(header)
	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		date, err := ParseDate(row[col["datetime"]])
		if err != nil {
			continue
		}
		home := row[col["home_team"]]
		away := row[col["away_team"]]
		matches = append(matches, Match{
			Date:        date,
			Season:      parseIntField(row[col["season"]]),
			Round:       row[col["round"]],
			Competition: "Brasileirao",
			Source:      "Brasileirao_Matches.csv",
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeamKey(home),
			AwayKey:     NormalizeTeamKey(away),
			HomeGoals:   parseIntField(row[col["home_goal"]]),
			AwayGoals:   parseIntField(row[col["away_goal"]]),
			HomeState:   row[col["home_team_state"]],
			AwayState:   row[col["away_team_state"]],
		})
	}
	return matches, nil
}

// LoadCopaDoBrasilMatches parses the Brazilian_Cup_Matches.csv dataset.
func LoadCopaDoBrasilMatches(r io.Reader) ([]Match, error) {
	header, rows, err := readCSVRecords(r)
	if err != nil {
		return nil, err
	}
	col := columnIndex(header)
	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		date, err := ParseDate(row[col["datetime"]])
		if err != nil {
			continue
		}
		home := row[col["home_team"]]
		away := row[col["away_team"]]
		matches = append(matches, Match{
			Date:        date,
			Season:      parseIntField(row[col["season"]]),
			Round:       row[col["round"]],
			Competition: "Copa do Brasil",
			Source:      "Brazilian_Cup_Matches.csv",
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeamKey(home),
			AwayKey:     NormalizeTeamKey(away),
			HomeGoals:   parseIntField(row[col["home_goal"]]),
			AwayGoals:   parseIntField(row[col["away_goal"]]),
		})
	}
	return matches, nil
}

// LoadLibertadoresMatches parses the Libertadores_Matches.csv dataset.
func LoadLibertadoresMatches(r io.Reader) ([]Match, error) {
	header, rows, err := readCSVRecords(r)
	if err != nil {
		return nil, err
	}
	col := columnIndex(header)
	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		date, err := ParseDate(row[col["datetime"]])
		if err != nil {
			continue
		}
		home := row[col["home_team"]]
		away := row[col["away_team"]]
		matches = append(matches, Match{
			Date:        date,
			Season:      parseIntField(row[col["season"]]),
			Stage:       row[col["stage"]],
			Competition: "Libertadores",
			Source:      "Libertadores_Matches.csv",
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeamKey(home),
			AwayKey:     NormalizeTeamKey(away),
			HomeGoals:   parseIntField(row[col["home_goal"]]),
			AwayGoals:   parseIntField(row[col["away_goal"]]),
		})
	}
	return matches, nil
}

// LoadBRFootballMatches parses the BR-Football-Dataset.csv dataset. This
// dataset spans multiple competitions (recorded per-row in the "tournament"
// column) and includes extended match statistics not used for the core
// Match model.
func LoadBRFootballMatches(r io.Reader) ([]Match, error) {
	header, rows, err := readCSVRecords(r)
	if err != nil {
		return nil, err
	}
	col := columnIndex(header)
	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		dateStr := row[col["date"]]
		if t := row[col["time"]]; t != "" {
			dateStr += " " + t
		}
		date, err := ParseDate(dateStr)
		if err != nil {
			continue
		}
		home := row[col["home"]]
		away := row[col["away"]]
		matches = append(matches, Match{
			Date:        date,
			Season:      date.Year(),
			Competition: row[col["tournament"]],
			Source:      "BR-Football-Dataset.csv",
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeamKey(home),
			AwayKey:     NormalizeTeamKey(away),
			HomeGoals:   parseIntField(row[col["home_goal"]]),
			AwayGoals:   parseIntField(row[col["away_goal"]]),
		})
	}
	return matches, nil
}

// LoadHistoricalBrasileiraoMatches parses the
// novo_campeonato_brasileiro.csv dataset (seasons 2003-2019). It is tagged
// as a distinct competition, "Brasileirao (Historical)", from the
// Brasileirao_Matches.csv dataset because the two sources overlap in
// coverage for 2012-2019 and are not deduplicated against each other.
func LoadHistoricalBrasileiraoMatches(r io.Reader) ([]Match, error) {
	header, rows, err := readCSVRecords(r)
	if err != nil {
		return nil, err
	}
	col := columnIndex(header)
	matches := make([]Match, 0, len(rows))
	for _, row := range rows {
		date, err := ParseDate(row[col["Data"]])
		if err != nil {
			continue
		}
		home := row[col["Equipe_mandante"]]
		away := row[col["Equipe_visitante"]]
		matches = append(matches, Match{
			Date:        date,
			Season:      parseIntField(row[col["Ano"]]),
			Round:       row[col["Rodada"]],
			Competition: "Brasileirao (Historical)",
			Source:      "novo_campeonato_brasileiro.csv",
			HomeTeam:    home,
			AwayTeam:    away,
			HomeKey:     NormalizeTeamKey(home),
			AwayKey:     NormalizeTeamKey(away),
			HomeGoals:   parseIntField(row[col["Gols_mandante"]]),
			AwayGoals:   parseIntField(row[col["Gols_visitante"]]),
			HomeState:   row[col["Mandante_UF"]],
			AwayState:   row[col["Visitante_UF"]],
			Stadium:     row[col["Arena"]],
		})
	}
	return matches, nil
}
