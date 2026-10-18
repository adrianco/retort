// In-memory store for the six Kaggle CSV files.
//
// Every source is converted to rawMatch, de-duplicated across files (the
// Brasileirão files overlap for 2012–2019, and BR-Football overlaps for
// 2014–2023), and assigned stable team IDs. The store is read-only after
// LoadStore returns, so tool handlers can share it without locking.

package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	compBrasileirao  = "Brasileirão Serie A"
	compSerieB       = "Brasileirão Serie B"
	compSerieC       = "Brasileirão Serie C"
	compCup          = "Copa do Brasil"
	compLibertadores = "Copa Libertadores"
)

const (
	fileBrasileirao  = "Brasileirao_Matches.csv"
	fileCup          = "Brazilian_Cup_Matches.csv"
	fileLibertadores = "Libertadores_Matches.csv"
	fileHistorical   = "novo_campeonato_brasileiro.csv"
	fileBRFootball   = "BR-Football-Dataset.csv"
	fileFIFA         = "fifa_data.csv"
)

// Team is one club. ID is the base key, with "|STATE" appended only when the
// base name is shared by several clubs (Atlético-MG, Atlético-PR, ...).
type Team struct {
	ID    string
	Name  string
	Base  string
	State string
}

// Match is one played fixture. Home and Away are Team IDs.
type Match struct {
	Date        time.Time
	Competition string
	Season      int
	Round       string
	Stage       string
	IsFinal     bool
	Home        string
	Away        string
	HomeGoals   int
	AwayGoals   int
}

// Player is one row of the FIFA player table.
type Player struct {
	ID            int
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	Position      string
	JerseyNumber  int
	Value         string
	Wage          string
	PreferredFoot string
	Height        string
	Weight        string
}

// Store holds everything the query layer needs.
type Store struct {
	Teams   map[string]*Team
	Matches []Match
	Players []Player

	// brazilianBases holds base keys of clubs seen in domestic competitions.
	// It is used to decide whether a FIFA club is Brazilian.
	brazilianBases map[string]bool
}

// rawMatch is a source row after parsing and before de-duplication.
type rawMatch struct {
	date        time.Time
	season      int
	competition string
	round       string
	stage       string
	home        teamName
	away        teamName
	homeGoals   int
	awayGoals   int
}

// LoadStore reads all six CSV files from dir.
func LoadStore(dir string) (*Store, error) {
	loaders := []struct {
		file    string
		convert func(map[string]string) (rawMatch, bool)
	}{
		// Order matters: earlier files win when the same match appears twice.
		{fileBrasileirao, brasileiraoRow},
		{fileCup, cupRow},
		{fileLibertadores, libertadoresRow},
		{fileHistorical, historicalRow},
		{fileBRFootball, brFootballRow},
	}

	// Each (competition, season) is taken from the first file that covers it.
	// The files overlap heavily, and the BR-Football "Serie A" label is not
	// reliable for 2014–2022, so row-level de-duplication alone would double
	// count. Later files only fill seasons no earlier file has.
	var raws []rawMatch
	covered := map[string]bool{}
	for _, l := range loaders {
		rows, err := readCSV(filepath.Join(dir, l.file))
		if err != nil {
			return nil, err
		}
		var parsed []rawMatch
		for _, row := range rows {
			if m, ok := l.convert(row); ok {
				parsed = append(parsed, m)
			}
		}
		fromThisFile := map[string]bool{}
		for _, m := range parsed {
			key := seasonKey(m.competition, m.season)
			if !covered[key] {
				raws = append(raws, m)
				fromThisFile[key] = true
			}
		}
		for key := range fromThisFile {
			covered[key] = true
		}
	}

	rows, err := readCSV(filepath.Join(dir, fileFIFA))
	if err != nil {
		return nil, err
	}
	players := make([]Player, 0, len(rows))
	for _, row := range rows {
		players = append(players, playerRow(row))
	}
	return buildStore(raws, players), nil
}

// readCSV returns each row as a map keyed by header. A UTF-8 BOM on the first
// header is removed, because the FIFA export includes one.
func readCSV(path string) ([]map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.FieldsPerRecord = -1
	records, err := r.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	if len(records) == 0 {
		return nil, nil
	}

	header := records[0]
	for i := range header {
		header[i] = strings.TrimSpace(strings.TrimPrefix(header[i], "\ufeff"))
	}
	rows := make([]map[string]string, 0, len(records)-1)
	for _, rec := range records[1:] {
		row := make(map[string]string, len(header))
		for i, h := range header {
			if i < len(rec) {
				row[h] = strings.TrimSpace(rec[i])
			}
		}
		rows = append(rows, row)
	}
	return rows, nil
}

func seasonKey(competition string, season int) string {
	return fmt.Sprintf("%s|%d", competition, season)
}

// seasonYear reads the season column, falling back to the match year when the
// column is missing (BR-Football has none).
func seasonYear(column string, date time.Time) int {
	if n, err := strconv.Atoi(strings.TrimSpace(column)); err == nil {
		return n
	}
	return date.Year()
}

// makeRaw builds a rawMatch from one parsed row. season is the file's own
// season column; it is not derived from the date because Brazilian seasons
// can run into the following calendar year.
func makeRaw(competition, season, dateStr, round, stage string, home, away teamName, homeGoal, awayGoal string) (rawMatch, bool) {
	date, err := parseDate(dateStr)
	if err != nil {
		return rawMatch{}, false
	}
	hg, err := parseGoals(homeGoal)
	if err != nil {
		return rawMatch{}, false
	}
	ag, err := parseGoals(awayGoal)
	if err != nil {
		return rawMatch{}, false
	}
	return rawMatch{
		date: date, season: seasonYear(season, date), competition: competition, round: round, stage: stage,
		home: home, away: away, homeGoals: hg, awayGoals: ag,
	}, true
}

func brasileiraoRow(r map[string]string) (rawMatch, bool) {
	home := parseTeamName(r["home_team"])
	home.State = firstNonEmpty(home.State, r["home_team_state"])
	away := parseTeamName(r["away_team"])
	away.State = firstNonEmpty(away.State, r["away_team_state"])
	return makeRaw(compBrasileirao, r["season"], r["datetime"], r["round"], "", home, away, r["home_goal"], r["away_goal"])
}

func cupRow(r map[string]string) (rawMatch, bool) {
	return makeRaw(compCup, r["season"], r["datetime"], r["round"], "",
		parseTeamName(r["home_team"]), parseTeamName(r["away_team"]), r["home_goal"], r["away_goal"])
}

func libertadoresRow(r map[string]string) (rawMatch, bool) {
	return makeRaw(compLibertadores, r["season"], r["datetime"], "", r["stage"],
		parseTeamName(r["home_team"]), parseTeamName(r["away_team"]), r["home_goal"], r["away_goal"])
}

func historicalRow(r map[string]string) (rawMatch, bool) {
	home := parseTeamName(r["Equipe_mandante"])
	home.State = firstNonEmpty(home.State, r["Mandante_UF"])
	away := parseTeamName(r["Equipe_visitante"])
	away.State = firstNonEmpty(away.State, r["Visitante_UF"])
	return makeRaw(compBrasileirao, r["Ano"], r["Data"], r["Rodada"], "", home, away, r["Gols_mandante"], r["Gols_visitante"])
}

func brFootballRow(r map[string]string) (rawMatch, bool) {
	return makeRaw(competitionFor(r["tournament"]), "", r["date"], "", "",
		parseTeamName(r["home"]), parseTeamName(r["away"]), r["home_goal"], r["away_goal"])
}

// competitionFor maps the BR-Football tournament labels to the names used
// by the other files.
func competitionFor(tournament string) string {
	switch tournament {
	case "Serie A":
		return compBrasileirao
	case "Serie B":
		return compSerieB
	case "Serie C":
		return compSerieC
	case "Copa do Brasil":
		return compCup
	}
	return tournament
}

func playerRow(r map[string]string) Player {
	return Player{
		ID:            atoi(r["ID"]),
		Name:          r["Name"],
		Age:           atoi(r["Age"]),
		Nationality:   r["Nationality"],
		Overall:       atoi(r["Overall"]),
		Potential:     atoi(r["Potential"]),
		Club:          r["Club"],
		Position:      strings.ToUpper(r["Position"]),
		JerseyNumber:  atoi(r["Jersey Number"]),
		Value:         r["Value"],
		Wage:          r["Wage"],
		PreferredFoot: r["Preferred Foot"],
		Height:        r["Height"],
		Weight:        r["Weight"],
	}
}

// buildStore de-duplicates matches, assigns team IDs and derives finals.
func buildStore(raws []rawMatch, players []Player) *Store {
	// Count the states seen for each base name first. A base with more than
	// one state gets state-qualified IDs.
	states := map[string]map[string]int{}
	for _, r := range raws {
		for _, tn := range []teamName{r.home, r.away} {
			if tn.State == "" {
				continue
			}
			if states[tn.Base] == nil {
				states[tn.Base] = map[string]int{}
			}
			states[tn.Base][tn.State]++
		}
	}

	st := &Store{Teams: map[string]*Team{}, Players: players, brazilianBases: map[string]bool{}}
	seen := map[string]bool{}
	for _, r := range raws {
		// Within a file, a pair meets at most once per orientation per competition
		// and season, so the key leaves out the date. The state is included
		// so that Atlético-MG and Atlético-PR stay distinct.
		key := fmt.Sprintf("%d|%s|%s|%s|%s|%s|%d|%d", r.season, r.competition,
			r.home.Base, r.home.State, r.away.Base, r.away.State, r.homeGoals, r.awayGoals)
		if seen[key] {
			continue
		}
		seen[key] = true
		st.Matches = append(st.Matches, Match{
			Date:        r.date,
			Competition: r.competition,
			Season:      r.season,
			Round:       r.round,
			Stage:       r.stage,
			Home:        st.register(r.home, states),
			Away:        st.register(r.away, states),
			HomeGoals:   r.homeGoals,
			AwayGoals:   r.awayGoals,
		})
	}

	markFinals(st.Matches)
	for _, m := range st.Matches {
		if m.Competition == compLibertadores {
			continue
		}
		st.brazilianBases[st.Teams[m.Home].Base] = true
		st.brazilianBases[st.Teams[m.Away].Base] = true
	}
	return st
}

// register returns the ID for tn and creates the Team on first sight.
// Rows without a state, such as BR-Football's "Flamengo", join the team that
// the base name is most often seen with, so that a club's record stays in one
// place. This is a heuristic: a stateless row for a second club with the same
// name is attributed to the dominant one.
func (st *Store) register(tn teamName, states map[string]map[string]int) string {
	id, state, name := tn.Base, tn.State, tn.Display
	if len(states[tn.Base]) > 1 {
		if state == "" {
			state = dominantState(states[tn.Base])
		}
		id = tn.Base + "|" + state
		name = fmt.Sprintf("%s-%s", tn.Display, state)
	}
	if _, ok := st.Teams[id]; !ok {
		st.Teams[id] = &Team{ID: id, Name: name, Base: tn.Base, State: state}
	}
	return id
}

// dominantState returns the most frequent state, breaking ties alphabetically.
func dominantState(counts map[string]int) string {
	best := ""
	for state, n := range counts {
		if best == "" || n > counts[best] || (n == counts[best] && state < best) {
			best = state
		}
	}
	return best
}

// markFinals flags Libertadores rows with stage "final" and the last numbered
// round of each Copa do Brasil season. Other competitions have no final flag.
func markFinals(matches []Match) {
	lastRound := map[int]int{}
	for _, m := range matches {
		if m.Competition != compCup {
			continue
		}
		if n, err := strconv.Atoi(m.Round); err == nil && n > lastRound[m.Season] {
			lastRound[m.Season] = n
		}
	}
	for i := range matches {
		m := &matches[i]
		n, err := strconv.Atoi(m.Round)
		m.IsFinal = strings.EqualFold(m.Stage, "final") ||
			(m.Competition == compCup && err == nil && n == lastRound[m.Season])
	}
}

// teamLabel returns the display name for a team ID, or the ID if unknown.
func (st *Store) teamLabel(id string) string {
	if t, ok := st.Teams[id]; ok {
		return t.Name
	}
	return id
}

// resolveTeams returns the IDs of every team matching a user-supplied name.
// A state in the query narrows the match. Without one, every state matches.
func (st *Store) resolveTeams(query string) []string {
	want := parseTeamName(query)
	var ids []string
	for id, t := range st.Teams {
		if t.Base != want.Base {
			continue
		}
		if want.State != "" && t.State != "" && t.State != want.State {
			continue
		}
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if v != "" {
			return v
		}
	}
	return ""
}

func atoi(s string) int {
	n, _ := strconv.Atoi(strings.TrimSpace(s))
	return n
}
