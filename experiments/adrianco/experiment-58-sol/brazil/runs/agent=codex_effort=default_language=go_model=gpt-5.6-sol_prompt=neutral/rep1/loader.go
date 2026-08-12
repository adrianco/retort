package main

import (
	"encoding/csv"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

type csvTable struct {
	head []string
	rows [][]string
}

func readCSV(path string) (csvTable, error) {
	f, err := os.Open(path)
	if err != nil {
		return csvTable{}, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.ReuseRecord = false
	head, err := r.Read()
	if err != nil {
		return csvTable{}, err
	}
	for i := range head {
		head[i] = strings.TrimSpace(strings.TrimPrefix(head[i], "\ufeff"))
	}
	var rows [][]string
	for line := 2; ; line++ {
		row, err := r.Read()
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return csvTable{}, fmt.Errorf("%s line %d: %w", filepath.Base(path), line, err)
		}
		rows = append(rows, row)
	}
	return csvTable{head: head, rows: rows}, nil
}

func rowMap(head, row []string) map[string]string {
	m := make(map[string]string, len(head))
	for i, name := range head {
		if i < len(row) {
			m[name] = strings.TrimSpace(row[i])
		}
	}
	return m
}

func atoi(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return 0
}

func optionalInt(s string) *int {
	if strings.TrimSpace(s) == "" {
		return nil
	}
	v := atoi(s)
	return &v
}

func LoadStore(dataDir string) (*Store, error) {
	s := &Store{teamNames: map[string]string{}, preferredSources: map[string]string{}, matchIndexes: map[string][]int{}}
	loaders := []struct {
		file string
		fn   func(string) ([]Match, error)
	}{
		{"Brasileirao_Matches.csv", loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", loadBrazilianCup},
		{"Libertadores_Matches.csv", loadLibertadores},
		{"BR-Football-Dataset.csv", loadExtended},
		{"novo_campeonato_brasileiro.csv", loadHistorical},
	}
	for _, loader := range loaders {
		matches, err := loader.fn(filepath.Join(dataDir, loader.file))
		if err != nil {
			return nil, fmt.Errorf("load %s: %w", loader.file, err)
		}
		s.matches = append(s.matches, matches...)
	}
	players, err := loadPlayers(filepath.Join(dataDir, "fifa_data.csv"))
	if err != nil {
		return nil, fmt.Errorf("load fifa_data.csv: %w", err)
	}
	s.players = players
	for i, m := range s.matches {
		for _, name := range []string{m.HomeTeam, m.AwayTeam} {
			key := normalizeTeam(name)
			s.matchIndexes[key] = append(s.matchIndexes[key], i)
			if old, ok := s.teamNames[key]; !ok || len(name) < len(old) {
				s.teamNames[key] = strings.TrimSpace(stateSuffix.ReplaceAllString(name, ""))
			}
		}
	}
	// Aggregate queries select one authoritative feed per competition/season.
	// This avoids double counting when the official, historical, and extended
	// datasets encode the same fixture with slightly different names or dates.
	rank := map[string]int{
		"Brasileirao_Matches.csv":        0,
		"Brazilian_Cup_Matches.csv":      0,
		"Libertadores_Matches.csv":       0,
		"novo_campeonato_brasileiro.csv": 1,
		"BR-Football-Dataset.csv":        2,
	}
	best := map[string]int{}
	for _, m := range s.matches {
		key, r := competitionSeasonKey(m), rank[m.Source]
		if old, ok := best[key]; !ok || r < old {
			best[key], s.preferredSources[key] = r, m.Source
		}
	}
	return s, nil
}

func matchesFrom(path, source string, convert func(map[string]string) (Match, error)) ([]Match, error) {
	t, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	out := make([]Match, 0, len(t.rows))
	for i, row := range t.rows {
		m, err := convert(rowMap(t.head, row))
		if err != nil {
			return nil, fmt.Errorf("row %d: %w", i+2, err)
		}
		m.Source = source
		out = append(out, m)
	}
	return out, nil
}

func loadBrasileirao(path string) ([]Match, error) {
	return matchesFrom(path, "Brasileirao_Matches.csv", func(r map[string]string) (Match, error) {
		d, err := parseDate(r["datetime"])
		return Match{Date: d, HomeTeam: r["home_team"], AwayTeam: r["away_team"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]), Competition: "Brasileirão Serie A", Season: atoi(r["season"]), Round: r["round"]}, err
	})
}

func loadBrazilianCup(path string) ([]Match, error) {
	return matchesFrom(path, "Brazilian_Cup_Matches.csv", func(r map[string]string) (Match, error) {
		d, err := parseDate(r["datetime"])
		return Match{Date: d, HomeTeam: r["home_team"], AwayTeam: r["away_team"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]), Competition: "Copa do Brasil", Season: atoi(r["season"]), Round: r["round"], Stage: r["round"]}, err
	})
}

func loadLibertadores(path string) ([]Match, error) {
	return matchesFrom(path, "Libertadores_Matches.csv", func(r map[string]string) (Match, error) {
		var d time.Time
		var err error
		if r["datetime"] != "NA" && r["datetime"] != "" {
			d, err = parseDate(r["datetime"])
		}
		missing := r["home_goal"] == "-" || r["away_goal"] == "-"
		return Match{Date: d, HomeTeam: r["home_team"], AwayTeam: r["away_team"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]), Competition: "Copa Libertadores", Season: atoi(r["season"]), Stage: r["stage"], ResultMissing: missing}, err
	})
}

func loadExtended(path string) ([]Match, error) {
	return matchesFrom(path, "BR-Football-Dataset.csv", func(r map[string]string) (Match, error) {
		d, err := parseDate(r["date"])
		return Match{Date: d, HomeTeam: r["home"], AwayTeam: r["away"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]), Competition: normalizeCompetition(r["tournament"]), Season: d.Year(), HomeCorners: optionalInt(r["home_corner"]), AwayCorners: optionalInt(r["away_corner"]), HomeShots: optionalInt(r["home_shots"]), AwayShots: optionalInt(r["away_shots"])}, err
	})
}

func loadHistorical(path string) ([]Match, error) {
	return matchesFrom(path, "novo_campeonato_brasileiro.csv", func(r map[string]string) (Match, error) {
		d, err := parseDate(r["Data"])
		return Match{Date: d, HomeTeam: r["Equipe_mandante"], AwayTeam: r["Equipe_visitante"], HomeGoals: atoi(r["Gols_mandante"]), AwayGoals: atoi(r["Gols_visitante"]), Competition: "Brasileirão Serie A", Season: atoi(r["Ano"]), Round: r["Rodada"], Arena: r["Arena"]}, err
	})
}

func loadPlayers(path string) ([]Player, error) {
	t, err := readCSV(path)
	if err != nil {
		return nil, err
	}
	attributeNames := []string{"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling", "BallControl", "Acceleration", "SprintSpeed", "ShotPower", "Stamina", "Strength", "Vision", "StandingTackle", "GKDiving", "GKReflexes"}
	players := make([]Player, 0, len(t.rows))
	for _, row := range t.rows {
		r := rowMap(t.head, row)
		attrs := make(map[string]int, len(attributeNames))
		for _, name := range attributeNames {
			if r[name] != "" {
				attrs[name] = atoi(r[name])
			}
		}
		players = append(players, Player{ID: atoi(r["ID"]), Name: r["Name"], Age: atoi(r["Age"]), Nationality: r["Nationality"], Overall: atoi(r["Overall"]), Potential: atoi(r["Potential"]), Club: r["Club"], Position: r["Position"], Jersey: atoi(r["Jersey Number"]), Height: r["Height"], Weight: r["Weight"], Attributes: attrs})
	}
	return players, nil
}
