// Data loading.
//
// Reads the six Kaggle CSV files in data/kaggle/ into a single Dataset:
// a de-duplicated list of matches (five match files, several of which overlap
// in time) and the FIFA player list. Columns are looked up by header name so
// small layout differences between files do not break loading. Rows with
// missing or non-numeric goals are skipped.

package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// Competition names used across all sources.
const (
	CompBrasileirao = "Brasileirão Série A"
	CompSerieB      = "Brasileirão Série B"
	CompSerieC      = "Brasileirão Série C"
	CompCopaBrasil  = "Copa do Brasil"
	CompLibertadore = "Copa Libertadores"
)

// Match is one played fixture.
type Match struct {
	Date        time.Time
	Home        TeamName
	Away        TeamName
	HomeGoals   int
	AwayGoals   int
	Competition string
	Season      int
	Round       string // round number or stage name, may be empty
	Source      string // file the row came from
}

// Result returns "H", "A" or "D" from the home side's perspective.
func (m Match) Result() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return "H"
	case m.HomeGoals < m.AwayGoals:
		return "A"
	default:
		return "D"
	}
}

// Dataset is everything the server queries.
type Dataset struct {
	Matches []Match
	Players []Player
	// BrazilianClubs holds the base name of every club seen in the Brazilian
	// league files. Base names (not Key) because FIFA club names carry no state.
	BrazilianClubs map[string]bool
}

// Source files, loaded in priority order. The files overlap heavily (the
// historical Brasileirão file and the BR-Football extract repeat seasons that
// the curated files already cover, often with different club spellings), so a
// later file only contributes the competition/season pairs no earlier file
// supplied. Fixture de-duplication remains as a safety net within those.
var matchSources = []string{
	"Brasileirao_Matches.csv",
	"novo_campeonato_brasileiro.csv",
	"Brazilian_Cup_Matches.csv",
	"Libertadores_Matches.csv",
	"BR-Football-Dataset.csv",
}

// LoadDataset reads every expected file under dir.
func LoadDataset(dir string) (*Dataset, error) {
	ds := &Dataset{BrazilianClubs: map[string]bool{}}

	seen := map[string]bool{}    // fixtureKey values already added
	covered := map[string]bool{} // competitionSeasonKey values supplied by earlier files
	for _, name := range matchSources {
		rows, err := readCSV(filepath.Join(dir, name))
		if err != nil {
			return nil, err
		}
		var matches []Match
		switch name {
		case "Brasileirao_Matches.csv":
			matches = parseBrasileirao(rows, name)
		case "novo_campeonato_brasileiro.csv":
			matches = parseHistorical(rows, name)
		case "Brazilian_Cup_Matches.csv":
			matches = parseCup(rows, name)
		case "Libertadores_Matches.csv":
			matches = parseLibertadores(rows, name)
		case "BR-Football-Dataset.csv":
			matches = parseBRFootball(rows, name)
		}

		fresh := map[string]bool{}
		for _, m := range matches {
			ck := competitionSeasonKey(m)
			if covered[ck] {
				continue
			}
			fresh[ck] = true
			if seen[fixtureKey(m)] {
				continue
			}
			seen[fixtureKey(m)] = true
			ds.Matches = append(ds.Matches, m)
			if strings.HasPrefix(m.Competition, "Brasileirão") {
				ds.BrazilianClubs[m.Home.Base] = true
				ds.BrazilianClubs[m.Away.Base] = true
			}
		}
		for k := range fresh {
			covered[k] = true
		}
	}

	players, err := readCSV(filepath.Join(dir, "fifa_data.csv"))
	if err != nil {
		return nil, err
	}
	ds.Players = parsePlayers(players)
	return ds, nil
}

// competitionSeasonKey identifies a competition's season, e.g. "Brasileirão Série A|2019".
func competitionSeasonKey(m Match) string {
	return m.Competition + "|" + strconv.Itoa(m.Season)
}

// fixtureKey identifies a fixture regardless of which file it came from.
// It uses the base name only: some files carry state codes and others don't,
// and two clubs with the same base name never meet on the same day.
func fixtureKey(m Match) string {
	return m.Date.Format("2006-01-02") + "|" + m.Home.Base + "|" + m.Away.Base
}

// row is one CSV record keyed by lower-case header name.
type row map[string]string

func (r row) get(col string) string {
	return strings.TrimSpace(r[col])
}

// readCSV loads a file into rows keyed by header. It strips a UTF-8 BOM and
// tolerates ragged rows.
func readCSV(path string) ([]row, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.FieldsPerRecord = -1

	header, err := r.Read()
	if err != nil {
		return nil, fmt.Errorf("read header of %s: %w", path, err)
	}
	for i, h := range header {
		h = strings.TrimPrefix(h, "\ufeff")
		header[i] = strings.ToLower(strings.TrimSpace(h))
	}

	var out []row
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("parse %s: %w", path, err)
		}
		m := make(row, len(header))
		for i, h := range header {
			if i < len(rec) {
				m[h] = rec[i]
			}
		}
		out = append(out, m)
	}
	return out, nil
}

// parseDate accepts the date layouts found in the datasets.
func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// parseGoals accepts "2", "2.0" and rejects empty or non-numeric values.
func parseGoals(s string) (int, bool) {
	f, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if err != nil || f < 0 {
		return 0, false
	}
	return int(f), true
}

// buildMatch assembles a Match, returning false if any required field is bad.
func buildMatch(source, date, homeRaw, homeState, awayRaw, awayState, hg, ag, competition, round string, season int) (Match, bool) {
	t, ok := parseDate(date)
	if !ok {
		return Match{}, false
	}
	home := ParseTeam(homeRaw, homeState)
	away := ParseTeam(awayRaw, awayState)
	hgoals, ok1 := parseGoals(hg)
	agoals, ok2 := parseGoals(ag)
	if !ok1 || !ok2 || home.Empty() || away.Empty() {
		return Match{}, false
	}
	if season == 0 {
		season = t.Year()
	}
	return Match{
		Date: t, Home: home, Away: away,
		HomeGoals: hgoals, AwayGoals: agoals,
		Competition: competition, Season: season,
		Round: round, Source: source,
	}, true
}

func atoi(s string) int {
	n, _ := strconv.Atoi(strings.TrimSpace(s))
	return n
}

// Brasileirao_Matches.csv: datetime, home_team, home_team_state, away_team, away_team_state, home_goal, away_goal, season, round
func parseBrasileirao(rows []row, source string) []Match {
	var out []Match
	for _, r := range rows {
		m, ok := buildMatch(source, r.get("datetime"), r.get("home_team"), r.get("home_team_state"),
			r.get("away_team"), r.get("away_team_state"), r.get("home_goal"), r.get("away_goal"),
			CompBrasileirao, r.get("round"), atoi(r.get("season")))
		if ok {
			out = append(out, m)
		}
	}
	return out
}

// novo_campeonato_brasileiro.csv (2003-2019): Data DD/MM/YYYY, Ano, Rodada, Equipe_mandante, ... Mandante_UF, Visitante_UF
func parseHistorical(rows []row, source string) []Match {
	var out []Match
	for _, r := range rows {
		m, ok := buildMatch(source, r.get("data"), r.get("equipe_mandante"), r.get("mandante_uf"),
			r.get("equipe_visitante"), r.get("visitante_uf"), r.get("gols_mandante"), r.get("gols_visitante"),
			CompBrasileirao, r.get("rodada"), atoi(r.get("ano")))
		if ok {
			out = append(out, m)
		}
	}
	return out
}

// Brazilian_Cup_Matches.csv: round, datetime, home_team, away_team, home_goal, away_goal, season
func parseCup(rows []row, source string) []Match {
	var out []Match
	for _, r := range rows {
		m, ok := buildMatch(source, r.get("datetime"), r.get("home_team"), "",
			r.get("away_team"), "", r.get("home_goal"), r.get("away_goal"),
			CompCopaBrasil, r.get("round"), atoi(r.get("season")))
		if ok {
			out = append(out, m)
		}
	}
	return out
}

// Libertadores_Matches.csv: datetime, home_team, away_team, home_goal, away_goal, season, stage
func parseLibertadores(rows []row, source string) []Match {
	var out []Match
	for _, r := range rows {
		m, ok := buildMatch(source, r.get("datetime"), r.get("home_team"), "",
			r.get("away_team"), "", r.get("home_goal"), r.get("away_goal"),
			CompLibertadore, r.get("stage"), atoi(r.get("season")))
		if ok {
			out = append(out, m)
		}
	}
	return out
}

// BR-Football-Dataset.csv: tournament, home, away, home_goal, away_goal, date, ...
// Tournaments are "Serie A", "Serie B", "Serie C" and "Copa do Brasil".
func parseBRFootball(rows []row, source string) []Match {
	var out []Match
	for _, r := range rows {
		comp := brFootballCompetition(r.get("tournament"))
		m, ok := buildMatch(source, r.get("date"), r.get("home"), "",
			r.get("away"), "", r.get("home_goal"), r.get("away_goal"),
			comp, "", 0)
		if ok {
			out = append(out, m)
		}
	}
	return out
}

func brFootballCompetition(t string) string {
	switch strings.ToLower(strings.TrimSpace(t)) {
	case "serie a":
		return CompBrasileirao
	case "serie b":
		return CompSerieB
	case "serie c":
		return CompSerieC
	case "copa do brasil":
		return CompCopaBrasil
	default:
		return strings.TrimSpace(t)
	}
}
