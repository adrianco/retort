// loader.go - CSV ingestion for the six bundled Kaggle datasets.
//
// Context
//
//	Each dataset has its own column names, date format and team-name
//	convention, so every file gets a small dedicated reader that emits a common
//	rawMatch record. Nothing is resolved or de-duplicated here - that happens in
//	graph.go once every team spelling in the corpus has been seen.
//
//	    Brasileirao_Matches.csv        Série A 2012-2022, ISO datetimes, "-SP" suffixes
//	    novo_campeonato_brasileiro.csv Série A 2003-2019, DD/MM/YYYY dates, stadium names
//	    Brazilian_Cup_Matches.csv      Copa do Brasil 2012-2021, numeric rounds
//	    Libertadores_Matches.csv       Libertadores 2013-2022, named stages, country markers
//	    BR-Football-Dataset.csv        Série A/B/C + Copa do Brasil 2014-2023, shot/corner detail
//	    fifa_data.csv                  18,207 FIFA 19 players with ratings and attributes
//
//	Missing values are pervasive ("NA" scores, blank shot counts, one Libertadores
//	row with no date at all), so every field is parsed defensively and rows are
//	kept even when incomplete - a fixture with no score is still a fixture.
package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"io/fs"
	"strconv"
	"strings"
	"time"
)

// Dataset file names, relative to the data directory.
const (
	FileBrasileirao  = "Brasileirao_Matches.csv"
	FileCup          = "Brazilian_Cup_Matches.csv"
	FileLibertadores = "Libertadores_Matches.csv"
	FileBRFootball   = "BR-Football-Dataset.csv"
	FileHistorical   = "novo_campeonato_brasileiro.csv"
	FileFIFA         = "fifa_data.csv"
)

// rawMatch is the loader-neutral representation of one CSV row.
type rawMatch struct {
	Source      string
	Competition Competition
	Season      int
	Round       string
	Stage       string
	Date        time.Time
	HasDate     bool
	HasTime     bool
	Home        string
	Away        string
	HomeGoals   int
	AwayGoals   int
	HasScore    bool
	Stadium     string
	Stats       *ExtendedStats
}

// table is a CSV file parsed into a header index plus rows.
type table struct {
	index map[string]int
	rows  [][]string
}

func (t *table) get(row []string, col string) string {
	i, ok := t.index[col]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

// readTable parses a CSV file, tolerating the ragged quoting found in these
// exports and stripping any UTF-8 BOM from the first header cell.
func readTable(fsys fs.FS, name string) (*table, error) {
	f, err := fsys.Open(name)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", name, err)
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	r.ReuseRecord = false

	header, err := r.Read()
	if err != nil {
		return nil, fmt.Errorf("read header of %s: %w", name, err)
	}
	index := make(map[string]int, len(header))
	for i, h := range header {
		h = strings.TrimSpace(strings.TrimPrefix(h, "\ufeff"))
		if _, dup := index[h]; !dup {
			index[h] = i
		}
	}
	t := &table{index: index}
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			// A malformed line should not abort a 10,000 row dataset.
			continue
		}
		t.rows = append(t.rows, rec)
	}
	return t, nil
}

// dateLayouts covers every format seen across the datasets.
var dateLayouts = []struct {
	layout  string
	hasTime bool
}{
	{"2006-01-02 15:04:05", true},
	{"2006-01-02T15:04:05", true},
	{"2006-01-02 15:04", true},
	{"2006-01-02", false},
	{"02/01/2006", false},
	{"2006/01/02", false},
	{"01/02/2006 15:04:05", true},
}

// parseDate accepts ISO timestamps, ISO dates and Brazilian DD/MM/YYYY dates.
func parseDate(s string) (time.Time, bool, bool) {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "NA") || s == "-" {
		return time.Time{}, false, false
	}
	for _, l := range dateLayouts {
		if t, err := time.Parse(l.layout, s); err == nil {
			return t, true, l.hasTime
		}
	}
	return time.Time{}, false, false
}

// parseInt parses a goal count or statistic, accepting "3", "3.0" and
// rejecting "NA", "-" and "".
func parseInt(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "NA") || s == "-" {
		return 0, false
	}
	if v, err := strconv.Atoi(s); err == nil {
		return v, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

func parseIntPtr(s string) *int {
	if v, ok := parseInt(s); ok {
		return &v
	}
	return nil
}

// loadBrasileirao reads Brasileirao_Matches.csv (Série A 2012-2022).
func loadBrasileirao(fsys fs.FS) ([]rawMatch, int, error) {
	t, err := readTable(fsys, FileBrasileirao)
	if err != nil {
		return nil, 0, err
	}
	out := make([]rawMatch, 0, len(t.rows))
	for _, row := range t.rows {
		home, away := t.get(row, "home_team"), t.get(row, "away_team")
		if home == "" || away == "" {
			continue
		}
		m := rawMatch{Source: FileBrasileirao, Competition: SerieA, Home: home, Away: away}
		m.Date, m.HasDate, m.HasTime = parseDate(t.get(row, "datetime"))
		m.Season, _ = parseInt(t.get(row, "season"))
		m.Round = t.get(row, "round")
		hg, okH := parseInt(t.get(row, "home_goal"))
		ag, okA := parseInt(t.get(row, "away_goal"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, okH && okA
		if m.Season == 0 && m.HasDate {
			m.Season = m.Date.Year()
		}
		out = append(out, m)
	}
	return out, len(t.rows), nil
}

// loadHistorical reads novo_campeonato_brasileiro.csv (Série A 2003-2019),
// the only source with stadium names.
func loadHistorical(fsys fs.FS) ([]rawMatch, int, error) {
	t, err := readTable(fsys, FileHistorical)
	if err != nil {
		return nil, 0, err
	}
	out := make([]rawMatch, 0, len(t.rows))
	for _, row := range t.rows {
		home, away := t.get(row, "Equipe_mandante"), t.get(row, "Equipe_visitante")
		if home == "" || away == "" {
			continue
		}
		m := rawMatch{Source: FileHistorical, Competition: SerieA, Home: home, Away: away}
		m.Date, m.HasDate, m.HasTime = parseDate(t.get(row, "Data"))
		m.Season, _ = parseInt(t.get(row, "Ano"))
		m.Round = t.get(row, "Rodada")
		m.Stadium = t.get(row, "Arena")
		hg, okH := parseInt(t.get(row, "Gols_mandante"))
		ag, okA := parseInt(t.get(row, "Gols_visitante"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, okH && okA
		if m.Season == 0 && m.HasDate {
			m.Season = m.Date.Year()
		}
		out = append(out, m)
	}
	return out, len(t.rows), nil
}

// cupStageName converts a numeric Copa do Brasil round into a stage label. The
// last round of a season is the final, so the mapping is derived per season
// from the highest round played.
func cupStageName(round, maxRound int) string {
	if round <= 0 || maxRound <= 0 {
		return ""
	}
	switch maxRound - round {
	case 0:
		return "Final"
	case 1:
		return "Semifinals"
	case 2:
		return "Quarterfinals"
	case 3:
		return "Round of 16"
	}
	return ""
}

// loadCup reads Brazilian_Cup_Matches.csv (Copa do Brasil 2012-2021).
func loadCup(fsys fs.FS) ([]rawMatch, int, error) {
	t, err := readTable(fsys, FileCup)
	if err != nil {
		return nil, 0, err
	}
	type pending struct {
		m     rawMatch
		round int
	}
	items := make([]pending, 0, len(t.rows))
	maxRound := map[int]int{}
	for _, row := range t.rows {
		home, away := t.get(row, "home_team"), t.get(row, "away_team")
		if home == "" || away == "" {
			continue
		}
		m := rawMatch{Source: FileCup, Competition: CopaDoBrasil, Home: home, Away: away}
		m.Date, m.HasDate, m.HasTime = parseDate(t.get(row, "datetime"))
		m.Season, _ = parseInt(t.get(row, "season"))
		round, _ := parseInt(t.get(row, "round"))
		m.Round = t.get(row, "round")
		hg, okH := parseInt(t.get(row, "home_goal"))
		ag, okA := parseInt(t.get(row, "away_goal"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, okH && okA
		if m.Season == 0 && m.HasDate {
			m.Season = m.Date.Year()
		}
		if round > maxRound[m.Season] {
			maxRound[m.Season] = round
		}
		items = append(items, pending{m: m, round: round})
	}
	out := make([]rawMatch, 0, len(items))
	for _, it := range items {
		it.m.Stage = cupStageName(it.round, maxRound[it.m.Season])
		out = append(out, it.m)
	}
	return out, len(t.rows), nil
}

// loadLibertadores reads Libertadores_Matches.csv (2013-2022).
func loadLibertadores(fsys fs.FS) ([]rawMatch, int, error) {
	t, err := readTable(fsys, FileLibertadores)
	if err != nil {
		return nil, 0, err
	}
	out := make([]rawMatch, 0, len(t.rows))
	for _, row := range t.rows {
		home, away := t.get(row, "home_team"), t.get(row, "away_team")
		if home == "" || away == "" {
			continue
		}
		m := rawMatch{Source: FileLibertadores, Competition: Libertadores, Home: home, Away: away}
		m.Date, m.HasDate, m.HasTime = parseDate(t.get(row, "datetime"))
		m.Season, _ = parseInt(t.get(row, "season"))
		m.Stage = titleStage(t.get(row, "stage"))
		hg, okH := parseInt(t.get(row, "home_goal"))
		ag, okA := parseInt(t.get(row, "away_goal"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, okH && okA
		if m.Season == 0 && m.HasDate {
			m.Season = m.Date.Year()
		}
		out = append(out, m)
	}
	return out, len(t.rows), nil
}

// titleStage renders "group stage" as "Group Stage".
func titleStage(s string) string {
	s = strings.TrimSpace(s)
	if s == "" || strings.EqualFold(s, "NA") {
		return ""
	}
	words := strings.Fields(s)
	for i, w := range words {
		r := []rune(w)
		words[i] = strings.ToUpper(string(r[:1])) + string(r[1:])
	}
	return strings.Join(words, " ")
}

// brFootballCompetition maps the tournament column of BR-Football-Dataset.csv.
var brFootballCompetition = map[string]Competition{
	"serie a":        SerieA,
	"serie b":        SerieB,
	"serie c":        SerieC,
	"copa do brasil": CopaDoBrasil,
}

// leagueSeasonForDate infers the season a match belongs to. BR-Football-Dataset.csv
// has no season column, and taking the calendar year is wrong for the
// COVID-shifted 2020 championships, which finished in February 2021: those 111
// Série A rows would otherwise become a second, phantom half of the 2021
// season. Brazilian leagues run from April/May to December, so a league match
// played in January or February belongs to the previous season. Cup
// competitions genuinely start in February and are left alone.
func leagueSeasonForDate(comp Competition, d time.Time) int {
	if isLeague(comp) && d.Month() <= time.February {
		return d.Year() - 1
	}
	return d.Year()
}

// loadBRFootball reads BR-Football-Dataset.csv, the only source with corner,
// shot and attack counts.
func loadBRFootball(fsys fs.FS) ([]rawMatch, int, error) {
	t, err := readTable(fsys, FileBRFootball)
	if err != nil {
		return nil, 0, err
	}
	out := make([]rawMatch, 0, len(t.rows))
	for _, row := range t.rows {
		home, away := t.get(row, "home"), t.get(row, "away")
		if home == "" || away == "" {
			continue
		}
		comp, ok := brFootballCompetition[strings.ToLower(t.get(row, "tournament"))]
		if !ok {
			continue
		}
		m := rawMatch{Source: FileBRFootball, Competition: comp, Home: home, Away: away}
		m.Date, m.HasDate, m.HasTime = parseDate(t.get(row, "date"))
		if m.HasDate {
			m.Season = leagueSeasonForDate(comp, m.Date)
		}
		hg, okH := parseInt(t.get(row, "home_goal"))
		ag, okA := parseInt(t.get(row, "away_goal"))
		m.HomeGoals, m.AwayGoals, m.HasScore = hg, ag, okH && okA
		stats := &ExtendedStats{
			HomeCorners:  parseIntPtr(t.get(row, "home_corner")),
			AwayCorners:  parseIntPtr(t.get(row, "away_corner")),
			TotalCorners: parseIntPtr(t.get(row, "total_corners")),
			HomeShots:    parseIntPtr(t.get(row, "home_shots")),
			AwayShots:    parseIntPtr(t.get(row, "away_shots")),
			HomeAttacks:  parseIntPtr(t.get(row, "home_attack")),
			AwayAttacks:  parseIntPtr(t.get(row, "away_attack")),
			HomeResult:   t.get(row, "ht_result"),
			AwayResult:   t.get(row, "at_result"),
			KickOff:      t.get(row, "time"),
		}
		if !stats.empty() {
			m.Stats = stats
		}
		out = append(out, m)
	}
	return out, len(t.rows), nil
}

func (s *ExtendedStats) empty() bool {
	return s.HomeCorners == nil && s.AwayCorners == nil && s.TotalCorners == nil &&
		s.HomeShots == nil && s.AwayShots == nil && s.HomeAttacks == nil &&
		s.AwayAttacks == nil && s.HomeResult == "" && s.AwayResult == "" && s.KickOff == ""
}

// skillColumns are the FIFA attribute columns copied into Player.Skills.
var skillColumns = []string{
	"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
	"Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
	"Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
	"ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression",
	"Interceptions", "Positioning", "Vision", "Penalties", "Composure",
	"Marking", "StandingTackle", "SlidingTackle", "GKDiving", "GKHandling",
	"GKKicking", "GKPositioning", "GKReflexes",
}

// positionGroups classifies the FIFA position codes into the four broad roles
// people actually ask about.
var positionGroups = map[string]string{
	"GK": "Goalkeeper",
	"CB": "Defender", "LCB": "Defender", "RCB": "Defender", "LB": "Defender",
	"RB": "Defender", "LWB": "Defender", "RWB": "Defender",
	"CDM": "Midfielder", "LDM": "Midfielder", "RDM": "Midfielder",
	"CM": "Midfielder", "LCM": "Midfielder", "RCM": "Midfielder",
	"CAM": "Midfielder", "LAM": "Midfielder", "RAM": "Midfielder",
	"LM": "Midfielder", "RM": "Midfielder",
	"ST": "Forward", "LS": "Forward", "RS": "Forward", "CF": "Forward",
	"LF": "Forward", "RF": "Forward", "LW": "Forward", "RW": "Forward",
}

// PositionGroup classifies a FIFA position code.
func PositionGroup(pos string) string {
	if g, ok := positionGroups[strings.ToUpper(strings.TrimSpace(pos))]; ok {
		return g
	}
	return ""
}

// loadPlayers reads fifa_data.csv.
func loadPlayers(fsys fs.FS) ([]*Player, int, error) {
	t, err := readTable(fsys, FileFIFA)
	if err != nil {
		return nil, 0, err
	}
	out := make([]*Player, 0, len(t.rows))
	for _, row := range t.rows {
		name := t.get(row, "Name")
		if name == "" {
			continue
		}
		p := &Player{Name: name}
		p.ID, _ = parseInt(t.get(row, "ID"))
		p.Age, _ = parseInt(t.get(row, "Age"))
		p.Nationality = t.get(row, "Nationality")
		p.Overall, _ = parseInt(t.get(row, "Overall"))
		p.Potential, _ = parseInt(t.get(row, "Potential"))
		p.Club = t.get(row, "Club")
		p.Position = strings.ToUpper(t.get(row, "Position"))
		p.PositionGroup = PositionGroup(p.Position)
		p.JerseyNumber, _ = parseInt(t.get(row, "Jersey Number"))
		p.Height = t.get(row, "Height")
		p.Weight = t.get(row, "Weight")
		p.Value = t.get(row, "Value")
		p.Wage = t.get(row, "Wage")
		p.PreferredFoot = t.get(row, "Preferred Foot")
		p.WorkRate = t.get(row, "Work Rate")
		p.ClubID = fifaClubToClubID[p.Club]
		skills := make(map[string]int, len(skillColumns))
		for _, col := range skillColumns {
			if v, ok := parseInt(t.get(row, col)); ok {
				skills[col] = v
			}
		}
		if len(skills) > 0 {
			p.Skills = skills
		}
		out = append(out, p)
	}
	return out, len(t.rows), nil
}
