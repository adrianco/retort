// Context: The in-memory data store for the Brazilian Soccer MCP server. It
// loads each of the bundled Kaggle CSV files (matches across four competition
// datasets plus the FIFA player database) into normalized Match/Player slices,
// then answers the domain queries that the MCP tools expose: find matches,
// compute a team's record, head-to-head tallies, competition standings,
// aggregate statistics, and player search. Each CSV file is parsed by a
// dedicated reader that maps columns by header name (so it is tolerant of the
// real files' many extra columns) and tags every match with a canonical
// competition label and its source file. The store is read-only after loading.
package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Store holds all loaded matches and players.
type Store struct {
	Matches []Match
	Players []Player
}

// NewStore returns an empty store.
func NewStore() *Store { return &Store{} }

// loaderFor maps a known CSV filename to the parser that understands it.
var loaderFor = map[string]func(*Store, [][]string) error{
	"Brasileirao_Matches.csv":        (*Store).loadBrasileirao,
	"novo_campeonato_brasileiro.csv": (*Store).loadNovo,
	"Brazilian_Cup_Matches.csv":      (*Store).loadCup,
	"Libertadores_Matches.csv":       (*Store).loadLibertadores,
	"BR-Football-Dataset.csv":        (*Store).loadBRFootball,
	"fifa_data.csv":                  (*Store).loadPlayers,
}

// LoadDir loads every recognized CSV file present in dir. Files that are not
// present are simply skipped, which lets tests load small fixtures containing
// only the datasets they need.
func (s *Store) LoadDir(dir string) error {
	loaded := 0
	for name, loader := range loaderFor {
		path := filepath.Join(dir, name)
		f, err := os.Open(path)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return fmt.Errorf("opening %s: %w", name, err)
		}
		rows, err := readCSV(f)
		f.Close()
		if err != nil {
			return fmt.Errorf("reading %s: %w", name, err)
		}
		if err := loader(s, rows); err != nil {
			return fmt.Errorf("parsing %s: %w", name, err)
		}
		loaded++
	}
	if loaded == 0 {
		return fmt.Errorf("no recognized datasets found in %s", dir)
	}
	s.canonicalize()
	return nil
}

// sourcePriority ranks the datasets so that, where several files cover the same
// competition and season, the cleanest/most authoritative one wins. The
// dedicated competition datasets (consistent state suffixes) outrank the
// historical archive, which outranks the broad extended-statistics dump.
func sourcePriority(source string) int {
	switch source {
	case "Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv":
		return 0
	case "novo_campeonato_brasileiro.csv":
		return 1
	default: // BR-Football-Dataset.csv
		return 2
	}
}

// canonicalize selects a single authoritative source for each (competition,
// season) and keeps only that source's matches for it. The bundled files
// overlap heavily — e.g. the 2012–2019 Brasileirão appears in three datasets —
// and they disagree on club spellings ("Athletico-PR" vs "Atletico-PR"), so
// merging them fixture-by-fixture would leave phantom duplicate teams in the
// standings. Picking one consistent source per competition-season keeps every
// real game once and every club spelled one way, while still letting lower-
// priority files fill in competition-seasons the authoritative files lack
// (Série B/C, and recent seasons beyond the dedicated files' range).
func (s *Store) canonicalize() {
	bestPri := make(map[string]int, len(s.Matches))
	for _, m := range s.Matches {
		k := m.Competition + "|" + itoa(m.Season)
		p := sourcePriority(m.Source)
		if cur, ok := bestPri[k]; !ok || p < cur {
			bestPri[k] = p
		}
	}
	deduped := make([]Match, 0, len(s.Matches))
	seen := make(map[string]bool, len(s.Matches))
	for _, m := range s.Matches {
		k := m.Competition + "|" + itoa(m.Season)
		if sourcePriority(m.Source) != bestPri[k] {
			continue
		}
		dk := m.dedupKey()
		if seen[dk] {
			continue
		}
		seen[dk] = true
		deduped = append(deduped, m)
	}
	s.Matches = deduped
}

func readCSV(r io.Reader) ([][]string, error) {
	cr := csv.NewReader(r)
	cr.FieldsPerRecord = -1 // tolerate ragged rows
	cr.LazyQuotes = true
	return cr.ReadAll()
}

// headerIndex builds a name->column index map, stripping a leading UTF-8 BOM.
func headerIndex(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, h := range header {
		h = strings.TrimPrefix(h, "\ufeff")
		idx[strings.TrimSpace(h)] = i
	}
	return idx
}

func cell(row []string, i int) string {
	if i < 0 || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

// --- CSV parsers -----------------------------------------------------------

func (s *Store) loadBrasileirao(rows [][]string) error {
	if len(rows) < 1 {
		return nil
	}
	h := headerIndex(rows[0])
	for _, row := range rows[1:] {
		hg, ag, ok := parseScore(cell(row, h["home_goal"]), cell(row, h["away_goal"]))
		s.Matches = append(s.Matches, buildMatch(
			cell(row, h["datetime"]),
			cell(row, h["home_team"]), cell(row, h["away_team"]),
			hg, ag, ok,
			cell(row, h["season"]), cell(row, h["round"]), "",
			"Brasileirão", "Brasileirao_Matches.csv"))
	}
	return nil
}

func (s *Store) loadNovo(rows [][]string) error {
	if len(rows) < 1 {
		return nil
	}
	h := headerIndex(rows[0])
	for _, row := range rows[1:] {
		hg, ag, ok := parseScore(cell(row, h["Gols_mandante"]), cell(row, h["Gols_visitante"]))
		s.Matches = append(s.Matches, buildMatch(
			cell(row, h["Data"]),
			cell(row, h["Equipe_mandante"]), cell(row, h["Equipe_visitante"]),
			hg, ag, ok,
			cell(row, h["Ano"]), cell(row, h["Rodada"]), "",
			"Brasileirão", "novo_campeonato_brasileiro.csv"))
	}
	return nil
}

func (s *Store) loadCup(rows [][]string) error {
	if len(rows) < 1 {
		return nil
	}
	h := headerIndex(rows[0])
	for _, row := range rows[1:] {
		hg, ag, ok := parseScore(cell(row, h["home_goal"]), cell(row, h["away_goal"]))
		s.Matches = append(s.Matches, buildMatch(
			cell(row, h["datetime"]),
			cell(row, h["home_team"]), cell(row, h["away_team"]),
			hg, ag, ok,
			cell(row, h["season"]), cell(row, h["round"]), "",
			"Copa do Brasil", "Brazilian_Cup_Matches.csv"))
	}
	return nil
}

func (s *Store) loadLibertadores(rows [][]string) error {
	if len(rows) < 1 {
		return nil
	}
	h := headerIndex(rows[0])
	for _, row := range rows[1:] {
		hg, ag, ok := parseScore(cell(row, h["home_goal"]), cell(row, h["away_goal"]))
		s.Matches = append(s.Matches, buildMatch(
			cell(row, h["datetime"]),
			cell(row, h["home_team"]), cell(row, h["away_team"]),
			hg, ag, ok,
			cell(row, h["season"]), "", cell(row, h["stage"]),
			"Copa Libertadores", "Libertadores_Matches.csv"))
	}
	return nil
}

func (s *Store) loadBRFootball(rows [][]string) error {
	if len(rows) < 1 {
		return nil
	}
	h := headerIndex(rows[0])
	for _, row := range rows[1:] {
		hg, ag, ok := parseScore(cell(row, h["home_goal"]), cell(row, h["away_goal"]))
		comp := canonBRFootball(cell(row, h["tournament"]))
		date := cell(row, h["date"])
		s.Matches = append(s.Matches, buildMatch(
			date,
			cell(row, h["home"]), cell(row, h["away"]),
			hg, ag, ok,
			seasonFromDate(date), "", "",
			comp, "BR-Football-Dataset.csv"))
	}
	return nil
}

// canonBRFootball maps the BR-Football tournament column onto canonical labels.
func canonBRFootball(t string) string {
	switch normText(t) {
	case "serie a":
		return "Brasileirão"
	case "copa do brasil":
		return "Copa do Brasil"
	case "serie b":
		return "Serie B"
	case "serie c":
		return "Serie C"
	default:
		if t == "" {
			return "Brasileirão"
		}
		return t
	}
}

func (s *Store) loadPlayers(rows [][]string) error {
	if len(rows) < 1 {
		return nil
	}
	h := headerIndex(rows[0])
	for _, row := range rows[1:] {
		name := cell(row, h["Name"])
		if name == "" {
			continue
		}
		p := Player{
			ID:          cell(row, h["ID"]),
			Name:        name,
			Age:         atoiSafe(cell(row, h["Age"])),
			Nationality: cell(row, h["Nationality"]),
			Overall:     atoiSafe(cell(row, h["Overall"])),
			Potential:   atoiSafe(cell(row, h["Potential"])),
			Club:        cell(row, h["Club"]),
			Position:    cell(row, h["Position"]),
		}
		p.NameNorm = normText(p.Name)
		p.ClubNorm = normText(p.Club)
		p.NationalityNorm = normText(p.Nationality)
		s.Players = append(s.Players, p)
	}
	return nil
}

// buildMatch normalizes raw fields into a Match.
func buildMatch(date, home, away string, hg, ag int, hasScore bool, season, round, stage, comp, source string) Match {
	d, hasDate := parseDate(date)
	return Match{
		Date:         d,
		HasDate:      hasDate,
		Season:       atoiSafe(season),
		Round:        strings.TrimSpace(round),
		Competition:  comp,
		Stage:        strings.TrimSpace(stage),
		Source:       source,
		HomeTeam:     displayTeam(home),
		AwayTeam:     displayTeam(away),
		HomeTeamNorm: normTeam(home),
		AwayTeamNorm: normTeam(away),
		HomeState:    teamState(home),
		AwayState:    teamState(away),
		HomeGoals:    hg,
		AwayGoals:    ag,
		HasScore:     hasScore,
	}
}

// --- field parsing helpers -------------------------------------------------

func parseScore(h, a string) (int, int, bool) {
	hg, ok1 := parseGoal(h)
	ag, ok2 := parseGoal(a)
	return hg, ag, ok1 && ok2
}

func parseGoal(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if i, err := strconv.Atoi(s); err == nil {
		return i, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2006/01/02",
}

func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	// Fall back to the date portion before any space.
	if i := strings.IndexByte(s, ' '); i > 0 {
		return parseDate(s[:i])
	}
	return time.Time{}, false
}

func seasonFromDate(s string) string {
	if t, ok := parseDate(s); ok {
		return strconv.Itoa(t.Year())
	}
	return ""
}

func atoiSafe(s string) int {
	s = strings.TrimSpace(s)
	if i, err := strconv.Atoi(s); err == nil {
		return i
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return 0
}

func itoa(i int) string { return strconv.Itoa(i) }

// --- queries ---------------------------------------------------------------

// MatchFilter expresses the criteria for selecting matches.
type MatchFilter struct {
	Team        teamQuery
	Opponent    teamQuery
	HasTeam     bool
	HasOpponent bool
	Competition string // canonical label, or "" for any
	Season      int
	HasSeason   bool
	Start       time.Time
	End         time.Time
	HasStart    bool
	HasEnd      bool
	Venue       string // "home", "away", or "" (any)
}

// teamIsHome reports whether the filter's team is the home side of the match.
func (f MatchFilter) teamIsHome(m Match) bool {
	return f.Team.matchesSide(m.HomeTeamNorm, m.HomeState)
}

func (f MatchFilter) accepts(m Match) bool {
	if f.Competition != "" && m.Competition != f.Competition {
		return false
	}
	if f.HasSeason && m.Season != f.Season {
		return false
	}
	if f.HasStart && (!m.HasDate || m.Date.Before(f.Start)) {
		return false
	}
	if f.HasEnd && (!m.HasDate || m.Date.After(f.End)) {
		return false
	}
	if f.HasTeam {
		switch f.Venue {
		case "home":
			if !f.Team.matchesSide(m.HomeTeamNorm, m.HomeState) {
				return false
			}
		case "away":
			if !f.Team.matchesSide(m.AwayTeamNorm, m.AwayState) {
				return false
			}
		default:
			if !m.involves(f.Team) {
				return false
			}
		}
	}
	if f.HasOpponent {
		// The opponent must be on the side opposite the team.
		homeIsTeam := f.Team.matchesSide(m.HomeTeamNorm, m.HomeState)
		awayIsTeam := f.Team.matchesSide(m.AwayTeamNorm, m.AwayState)
		homeIsOpp := f.Opponent.matchesSide(m.HomeTeamNorm, m.HomeState)
		awayIsOpp := f.Opponent.matchesSide(m.AwayTeamNorm, m.AwayState)
		if !((homeIsTeam && awayIsOpp) || (awayIsTeam && homeIsOpp)) {
			return false
		}
	}
	return true
}

// FindMatches returns matches satisfying the filter, most recent first.
func (s *Store) FindMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range s.Matches {
		if f.accepts(m) {
			out = append(out, m)
		}
	}
	sortMatchesByDateDesc(out)
	return out
}

func sortMatchesByDateDesc(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		if ms[i].HasDate != ms[j].HasDate {
			return ms[i].HasDate // dated matches first
		}
		return ms[i].Date.After(ms[j].Date)
	})
}

// TeamRecord aggregates a team's wins/draws/losses and goals for the filter.
type TeamRecord struct {
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

func (r TeamRecord) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Matches) * 100
}

// ComputeTeamRecord returns the record for the team named by the filter.
func (s *Store) ComputeTeamRecord(f MatchFilter) TeamRecord {
	var r TeamRecord
	for _, m := range s.FindMatches(f) {
		if !m.HasScore {
			continue
		}
		var gf, ga int
		if f.teamIsHome(m) {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		r.Matches++
		r.GoalsFor += gf
		r.GoalsAgainst += ga
		switch {
		case gf > ga:
			r.Wins++
		case gf < ga:
			r.Losses++
		default:
			r.Draws++
		}
	}
	return r
}

// HeadToHead summarizes results between two teams.
type HeadToHead struct {
	Matches []Match
	AWins   int
	BWins   int
	Draws   int
	AGoals  int
	BGoals  int
}

func (s *Store) ComputeHeadToHead(a, b teamQuery, f MatchFilter) HeadToHead {
	f.HasTeam = true
	f.Team = a
	f.HasOpponent = true
	f.Opponent = b
	f.Venue = ""
	var h HeadToHead
	h.Matches = s.FindMatches(f)
	for _, m := range h.Matches {
		if !m.HasScore {
			continue
		}
		var ag, bg int
		if a.matchesSide(m.HomeTeamNorm, m.HomeState) {
			ag, bg = m.HomeGoals, m.AwayGoals
		} else {
			ag, bg = m.AwayGoals, m.HomeGoals
		}
		h.AGoals += ag
		h.BGoals += bg
		switch {
		case ag > bg:
			h.AWins++
		case ag < bg:
			h.BWins++
		default:
			h.Draws++
		}
	}
	return h
}

// Standing is one row of a computed competition table.
type Standing struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int
}

func (st Standing) GoalDiff() int { return st.GoalsFor - st.GoalsAgainst }

// ComputeStandings builds a league table for a competition and season from
// match results, counting each fixture once even if it appears in overlapping
// source files.
func (s *Store) ComputeStandings(competition string, season int) []Standing {
	f := MatchFilter{Competition: competition, Season: season, HasSeason: true}
	table := map[string]*Standing{}
	get := func(identity, display string) *Standing {
		st, ok := table[identity]
		if !ok {
			st = &Standing{Team: display}
			table[identity] = st
		}
		return st
	}
	for _, m := range s.Matches {
		if !f.accepts(m) || !m.HasScore {
			continue
		}
		home := get(m.homeIdentity(), m.HomeTeam)
		away := get(m.awayIdentity(), m.AwayTeam)
		home.Played++
		away.Played++
		home.GoalsFor += m.HomeGoals
		home.GoalsAgainst += m.AwayGoals
		away.GoalsFor += m.AwayGoals
		away.GoalsAgainst += m.HomeGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			home.Wins++
			away.Losses++
			home.Points += 3
		case m.HomeGoals < m.AwayGoals:
			away.Wins++
			home.Losses++
			away.Points += 3
		default:
			home.Draws++
			away.Draws++
			home.Points++
			away.Points++
		}
	}
	out := make([]Standing, 0, len(table))
	for _, st := range table {
		out = append(out, *st)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
		}
		if out[i].GoalDiff() != out[j].GoalDiff() {
			return out[i].GoalDiff() > out[j].GoalDiff()
		}
		if out[i].GoalsFor != out[j].GoalsFor {
			return out[i].GoalsFor > out[j].GoalsFor
		}
		return out[i].Team < out[j].Team
	})
	return out
}

// Statistics holds aggregate figures over a set of matches.
type Statistics struct {
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
	BiggestWins []Match
}

func (s Statistics) AvgGoals() float64 {
	if s.Matches == 0 {
		return 0
	}
	return float64(s.TotalGoals) / float64(s.Matches)
}

func (s Statistics) rate(n int) float64 {
	if s.Matches == 0 {
		return 0
	}
	return float64(n) / float64(s.Matches) * 100
}

func (s Statistics) HomeWinRate() float64 { return s.rate(s.HomeWins) }
func (s Statistics) AwayWinRate() float64 { return s.rate(s.AwayWins) }
func (s Statistics) DrawRate() float64    { return s.rate(s.Draws) }

// ComputeStatistics aggregates over matches matching the filter and surfaces
// the biggest victories by winning margin. The match corpus is already
// canonicalized at load time, so each real fixture is counted once.
func (s *Store) ComputeStatistics(f MatchFilter, topN int) Statistics {
	var stat Statistics
	var scored []Match
	for _, m := range s.Matches {
		if !f.accepts(m) || !m.HasScore {
			continue
		}
		stat.Matches++
		stat.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			stat.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			stat.AwayWins++
		default:
			stat.Draws++
		}
		scored = append(scored, m)
	}
	sort.SliceStable(scored, func(i, j int) bool {
		mi := abs(scored[i].HomeGoals - scored[i].AwayGoals)
		mj := abs(scored[j].HomeGoals - scored[j].AwayGoals)
		if mi != mj {
			return mi > mj
		}
		ti := scored[i].HomeGoals + scored[i].AwayGoals
		tj := scored[j].HomeGoals + scored[j].AwayGoals
		return ti > tj
	})
	if topN > len(scored) {
		topN = len(scored)
	}
	stat.BiggestWins = scored[:topN]
	return stat
}

func abs(i int) int {
	if i < 0 {
		return -i
	}
	return i
}

// PlayerFilter expresses player search criteria.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
}

// SearchPlayers returns players matching the filter, highest overall first.
func (s *Store) SearchPlayers(f PlayerFilter) []Player {
	name := normText(f.Name)
	nat := normText(f.Nationality)
	club := normText(f.Club)
	pos := normText(f.Position)
	var out []Player
	for _, p := range s.Players {
		if name != "" && !strings.Contains(p.NameNorm, name) {
			continue
		}
		if nat != "" && !strings.Contains(p.NationalityNorm, nat) {
			continue
		}
		if club != "" && !strings.Contains(p.ClubNorm, club) {
			continue
		}
		if pos != "" && !strings.Contains(normText(p.Position), pos) {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Name < out[j].Name
	})
	return out
}
