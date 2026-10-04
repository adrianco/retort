package soccer

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

// The six provided datasets. Match files are loaded in this order, so
// that when several record the same match, the one with round and stage
// information is kept and the others add to it.
const (
	FileSerieA       = "Brasileirao_Matches.csv"
	FileCup          = "Brazilian_Cup_Matches.csv"
	FileLibertadores = "Libertadores_Matches.csv"
	FileHistorical   = "novo_campeonato_brasileiro.csv"
	FileExtended     = "BR-Football-Dataset.csv"
	FilePlayers      = "fifa_data.csv"
)

// Load reads every provided dataset from the data directory. A dataset
// that cannot be read is reported in Datasets rather than stopping the
// others from loading.
func Load(dir string) (*Store, error) {
	if info, err := os.Stat(dir); err != nil || !info.IsDir() {
		return nil, fmt.Errorf("data directory %q not found", dir)
	}
	s := newStore()
	loaders := []struct {
		name, file string
		load       func(*Store, *table, *Dataset)
	}{
		{"Brasileirão Série A matches", FileSerieA, loadSerieA},
		{"Copa do Brasil matches", FileCup, loadCup},
		{"Copa Libertadores matches", FileLibertadores, loadLibertadores},
		{"Historical Brasileirão matches", FileHistorical, loadHistorical},
		{"Extended match statistics", FileExtended, loadExtended},
		{"FIFA players", FilePlayers, loadPlayers},
	}
	for _, l := range loaders {
		ds := Dataset{Name: l.name, File: l.file}
		t, err := readTable(filepath.Join(dir, l.file))
		if err != nil {
			ds.Error = err.Error()
		} else {
			l.load(s, t, &ds)
		}
		s.Datasets = append(s.Datasets, ds)
	}
	s.finish()
	return s, nil
}

// table is a CSV file addressed by column name.
type table struct {
	columns map[string]int
	rows    [][]string
}

func readTable(path string) (*table, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.FieldsPerRecord = -1
	header, err := r.Read()
	if err != nil {
		return nil, fmt.Errorf("%s has no header: %v", filepath.Base(path), err)
	}
	t := &table{columns: map[string]int{}}
	for i, h := range header {
		t.columns[strings.TrimSpace(strings.TrimPrefix(h, "\uFEFF"))] = i
	}
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("%s: %v", filepath.Base(path), err)
		}
		t.rows = append(t.rows, row)
	}
	return t, nil
}

func (t *table) get(row []string, column string) string {
	i, ok := t.columns[column]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

var dateLayouts = []string{"2006-01-02 15:04:05", "2006-01-02T15:04:05", "2006-01-02 15:04", "2006-01-02", "02/01/2006", "2/1/2006"}

// ParseDate understands ISO dates, ISO date-times and Brazilian DD/MM/YYYY dates.
func ParseDate(s string) (time.Time, bool) { return parseDate(s) }

func parseDate(s string) (time.Time, bool) {
	for _, layout := range dateLayouts {
		if d, err := time.Parse(layout, strings.TrimSpace(s)); err == nil {
			return d, true
		}
	}
	return time.Time{}, false
}

// parseCount reads whole numbers, including those written as "2.0".
func parseCount(s string) (int, bool) {
	s = strings.Trim(strings.TrimSpace(s), `"`)
	if n, err := strconv.Atoi(s); err == nil {
		return n, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

func optionalCount(s string) *int {
	if n, ok := parseCount(s); ok {
		return &n
	}
	return nil
}

type seasonRange struct{ first, last int }

func (r *seasonRange) add(season int) {
	if r.first == 0 || season < r.first {
		r.first = season
	}
	r.last = max(r.last, season)
}

func (r seasonRange) String() string {
	if r.first == 0 {
		return ""
	}
	if r.first == r.last {
		return strconv.Itoa(r.first)
	}
	return fmt.Sprintf("%d-%d", r.first, r.last)
}

// matchRow is the part of a row common to every match file.
type matchRow struct {
	date                 string
	home, away           string
	homeGoals, awayGoals string
	season               string
	round                string
	stage                string
	arena                string
	competition          Competition
	stats                *MatchStats
}

func (s *Store) addRow(r matchRow, ds *Dataset, seasons *seasonRange) {
	date, okDate := parseDate(r.date)
	hg, okH := parseCount(r.homeGoals)
	ag, okA := parseCount(r.awayGoals)
	if !okDate || !okH || !okA || r.home == "" || r.away == "" {
		ds.Skipped++
		return
	}
	season, ok := parseCount(r.season)
	if !ok {
		season = date.Year()
	}
	round, _ := parseCount(r.round)
	m := &Match{
		Date: date, Competition: r.competition, Season: season, Round: round,
		Stage: strings.ToLower(strings.TrimSpace(r.stage)), Arena: r.arena,
		HomeKey: s.team(r.home), AwayKey: s.team(r.away), HomeGoals: hg, AwayGoals: ag, Stats: r.stats,
	}
	ds.Records++
	seasons.add(season)
	if s.addMatch(m, ds.Name) {
		ds.Merged++
	} else {
		ds.NewMatches++
	}
}

func loadSerieA(s *Store, t *table, ds *Dataset) {
	var seasons seasonRange
	for _, row := range t.rows {
		s.addRow(matchRow{
			date: t.get(row, "datetime"), home: t.get(row, "home_team"), away: t.get(row, "away_team"),
			homeGoals: t.get(row, "home_goal"), awayGoals: t.get(row, "away_goal"),
			season: t.get(row, "season"), round: t.get(row, "round"), competition: SerieA,
		}, ds, &seasons)
	}
	ds.Seasons = seasons.String()
}

func loadCup(s *Store, t *table, ds *Dataset) {
	var seasons seasonRange
	for _, row := range t.rows {
		s.addRow(matchRow{
			date: t.get(row, "datetime"), home: t.get(row, "home_team"), away: t.get(row, "away_team"),
			homeGoals: t.get(row, "home_goal"), awayGoals: t.get(row, "away_goal"),
			season: t.get(row, "season"), round: t.get(row, "round"), competition: CopaDoBrasil,
		}, ds, &seasons)
	}
	ds.Seasons = seasons.String()
}

func loadLibertadores(s *Store, t *table, ds *Dataset) {
	var seasons seasonRange
	for _, row := range t.rows {
		s.addRow(matchRow{
			date: t.get(row, "datetime"), home: t.get(row, "home_team"), away: t.get(row, "away_team"),
			homeGoals: t.get(row, "home_goal"), awayGoals: t.get(row, "away_goal"),
			season: t.get(row, "season"), stage: t.get(row, "stage"), competition: Libertadores,
		}, ds, &seasons)
	}
	ds.Seasons = seasons.String()
}

func loadHistorical(s *Store, t *table, ds *Dataset) {
	var seasons seasonRange
	for _, row := range t.rows {
		s.addRow(matchRow{
			date: t.get(row, "Data"), home: t.get(row, "Equipe_mandante"), away: t.get(row, "Equipe_visitante"),
			homeGoals: t.get(row, "Gols_mandante"), awayGoals: t.get(row, "Gols_visitante"),
			season: t.get(row, "Ano"), round: t.get(row, "Rodada"), arena: t.get(row, "Arena"), competition: SerieA,
		}, ds, &seasons)
	}
	ds.Seasons = seasons.String()
}

func loadExtended(s *Store, t *table, ds *Dataset) {
	var seasons seasonRange
	for _, row := range t.rows {
		competition, ok := ResolveCompetition(t.get(row, "tournament"))
		if !ok {
			ds.Skipped++
			continue
		}
		stats := &MatchStats{
			HomeCorners: optionalCount(t.get(row, "home_corner")), AwayCorners: optionalCount(t.get(row, "away_corner")),
			HomeShots: optionalCount(t.get(row, "home_shots")), AwayShots: optionalCount(t.get(row, "away_shots")),
			HomeAttacks: optionalCount(t.get(row, "home_attack")), AwayAttacks: optionalCount(t.get(row, "away_attack")),
		}
		if stats.HomeCorners == nil && stats.HomeShots == nil && stats.HomeAttacks == nil {
			stats = nil
		}
		s.addRow(matchRow{
			date: t.get(row, "date"), home: t.get(row, "home"), away: t.get(row, "away"),
			homeGoals: t.get(row, "home_goal"), awayGoals: t.get(row, "away_goal"),
			competition: competition, stats: stats,
		}, ds, &seasons)
	}
	ds.Seasons = seasons.String()
}

var skillColumns = []string{"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
	"Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions",
	"Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions",
	"Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle",
	"GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"}

func loadPlayers(s *Store, t *table, ds *Dataset) {
	for _, row := range t.rows {
		name := t.get(row, "Name")
		if name == "" {
			ds.Skipped++
			continue
		}
		num := func(col string) int { n, _ := parseCount(t.get(row, col)); return n }
		p := &Player{
			ID: num("ID"), Name: name, Age: num("Age"), Nationality: t.get(row, "Nationality"),
			Overall: num("Overall"), Potential: num("Potential"), Club: t.get(row, "Club"),
			Position: t.get(row, "Position"), Jersey: num("Jersey Number"),
			Height: t.get(row, "Height"), Weight: t.get(row, "Weight"),
			Value: t.get(row, "Value"), Wage: t.get(row, "Wage"), PreferredFoot: t.get(row, "Preferred Foot"),
			Joined: t.get(row, "Joined"), ContractUntil: t.get(row, "Contract Valid Until"),
		}
		if p.Club != "" {
			p.ClubKey = NormalizeTeam(p.Club).Key
		}
		for _, col := range skillColumns {
			if v, ok := parseCount(t.get(row, col)); ok {
				p.Skills = append(p.Skills, Skill{Name: col, Rating: v})
			}
		}
		s.Players = append(s.Players, p)
		ds.Records++
	}
}
