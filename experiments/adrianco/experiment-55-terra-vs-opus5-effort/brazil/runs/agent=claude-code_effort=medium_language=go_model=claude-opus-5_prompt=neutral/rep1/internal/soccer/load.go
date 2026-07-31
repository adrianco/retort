package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/normalize"
)

// Data file names, relative to the data directory.
const (
	FileBrasileirao  = "Brasileirao_Matches.csv"
	FileCup          = "Brazilian_Cup_Matches.csv"
	FileLibertadores = "Libertadores_Matches.csv"
	FileHistorical   = "novo_campeonato_brasileiro.csv"
	FileExtended     = "BR-Football-Dataset.csv"
	FilePlayers      = "fifa_data.csv"
)

// MatchFiles lists the CSV files that contribute fixtures, in merge priority
// order: earlier files win on conflicting scalar fields, later files fill gaps.
var MatchFiles = []string{FileBrasileirao, FileHistorical, FileCup, FileLibertadores, FileExtended}

// dateLayouts covers every format seen in the datasets.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2006-01-02T15:04:05",
	"01/02/2006",
}

// parseDate accepts ISO, ISO+time and Brazilian DD/MM/YYYY dates. The second
// return value is the kick-off time when the source carried one.
func parseDate(s string) (time.Time, string, error) {
	s = strings.TrimSpace(strings.Trim(strings.TrimSpace(s), `"`))
	if s == "" {
		return time.Time{}, "", fmt.Errorf("empty date")
	}
	for _, layout := range dateLayouts[:4] {
		if t, err := time.Parse(layout, s); err == nil {
			clock := ""
			if strings.Contains(layout, "15:04") && !(t.Hour() == 0 && t.Minute() == 0) {
				clock = t.Format("15:04")
			}
			return time.Date(t.Year(), t.Month(), t.Day(), 0, 0, 0, 0, time.UTC), clock, nil
		}
	}
	return time.Time{}, "", fmt.Errorf("unrecognised date %q", s)
}

// parseInt tolerates quoting, blanks and the float notation ("2.0") used by
// the BR-Football dataset.
func parseInt(s string) (int, bool) {
	s = strings.TrimSpace(strings.Trim(strings.TrimSpace(s), `"`))
	if s == "" {
		return 0, false
	}
	if n, err := strconv.Atoi(s); err == nil {
		return n, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil && !math.IsNaN(f) {
		return int(math.Round(f)), true
	}
	return 0, false
}

func intOr(s string, def int) int {
	if n, ok := parseInt(s); ok {
		return n
	}
	return def
}

// readCSV parses a UTF-8 (optionally BOM-prefixed) CSV into a header index and
// row slices. It tolerates ragged rows, which fifa_data.csv contains.
func readCSV(path string) (map[string]int, [][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	r := csv.NewReader(newBOMReader(f))
	r.FieldsPerRecord = -1
	r.LazyQuotes = true

	header, err := r.Read()
	if err != nil {
		return nil, nil, fmt.Errorf("%s: reading header: %w", filepath.Base(path), err)
	}
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(strings.Trim(strings.TrimSpace(h), `"`))] = i
	}

	var rows [][]string
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			// Skip malformed lines rather than abandoning the whole file.
			if _, ok := err.(*csv.ParseError); ok {
				continue
			}
			return nil, nil, fmt.Errorf("%s: %w", filepath.Base(path), err)
		}
		rows = append(rows, rec)
	}
	return idx, rows, nil
}

// bomReader strips a leading UTF-8 byte order mark.
type bomReader struct {
	r       io.Reader
	checked bool
	buf     []byte
}

func newBOMReader(r io.Reader) io.Reader { return &bomReader{r: r} }

func (b *bomReader) Read(p []byte) (int, error) {
	if !b.checked {
		b.checked = true
		head := make([]byte, 3)
		n, err := io.ReadFull(b.r, head)
		if n == 3 && head[0] == 0xEF && head[1] == 0xBB && head[2] == 0xBF {
			head = nil
		} else {
			head = head[:n]
		}
		b.buf = head
		if err != nil && err != io.ErrUnexpectedEOF && err != io.EOF {
			return 0, err
		}
	}
	if len(b.buf) > 0 {
		n := copy(p, b.buf)
		b.buf = b.buf[n:]
		return n, nil
	}
	return b.r.Read(p)
}

type row struct {
	idx  map[string]int
	rec  []string
	file string
}

func (r row) get(col string) string {
	i, ok := r.idx[col]
	if !ok || i >= len(r.rec) {
		return ""
	}
	return strings.TrimSpace(strings.Trim(strings.TrimSpace(r.rec[i]), `"`))
}

// loadMatchFile parses one fixture CSV into Match values. Rows that carry no
// usable score (the datasets write "NA" for abandoned and never-played
// fixtures) are skipped and counted, so that computed league tables are not
// distorted by phantom 0-0 results.
func loadMatchFile(dir, file string) ([]Match, int, error) {
	path := filepath.Join(dir, file)
	idx, rows, err := readCSV(path)
	if err != nil {
		return nil, 0, err
	}

	skipped := 0
	out := make([]Match, 0, len(rows))
	for _, rec := range rows {
		r := row{idx: idx, rec: rec, file: file}
		var m Match
		var ok bool
		switch file {
		case FileBrasileirao:
			m, ok = parseBrasileirao(r)
		case FileCup:
			m, ok = parseCup(r)
		case FileLibertadores:
			m, ok = parseLibertadores(r)
		case FileHistorical:
			m, ok = parseHistorical(r)
		case FileExtended:
			m, ok = parseExtended(r)
		default:
			return nil, 0, fmt.Errorf("unknown match file %q", file)
		}
		if !ok {
			skipped++
			continue
		}
		m.Sources = []string{file}
		out = append(out, m)
	}
	if file == FileCup {
		labelCupStages(out)
	}
	return out, skipped, nil
}

func baseMatch(r row, homeRaw, awayRaw string) (Match, bool) {
	if homeRaw == "" || awayRaw == "" {
		return Match{}, false
	}
	home := normalize.Resolve(homeRaw)
	away := normalize.Resolve(awayRaw)
	if home.ID == "" || away.ID == "" || home.ID == away.ID {
		return Match{}, false
	}
	return Match{
		Home: teamRef(home, homeRaw),
		Away: teamRef(away, awayRaw),
	}, true
}

func parseBrasileirao(r row) (Match, bool) {
	m, ok := baseMatch(r, r.get("home_team"), r.get("away_team"))
	if !ok {
		return m, false
	}
	d, clock, err := parseDate(r.get("datetime"))
	if err != nil {
		return m, false
	}
	hg, okH := parseInt(r.get("home_goal"))
	ag, okA := parseInt(r.get("away_goal"))
	if !okH || !okA {
		return m, false
	}
	m.Competition, m.Season, m.Date, m.KickOff = SerieA, intOr(r.get("season"), d.Year()), d, clock
	m.HomeGoals, m.AwayGoals = hg, ag
	if rd := r.get("round"); rd != "" {
		m.Round = rd
	}
	if m.Home.State == "" {
		m.Home.State = r.get("home_team_state")
	}
	if m.Away.State == "" {
		m.Away.State = r.get("away_team_state")
	}
	return m, true
}

func parseCup(r row) (Match, bool) {
	m, ok := baseMatch(r, r.get("home_team"), r.get("away_team"))
	if !ok {
		return m, false
	}
	d, clock, err := parseDate(r.get("datetime"))
	if err != nil {
		return m, false
	}
	hg, okH := parseInt(r.get("home_goal"))
	ag, okA := parseInt(r.get("away_goal"))
	if !okH || !okA {
		return m, false
	}
	m.Competition, m.Season, m.Date, m.KickOff = CopaDoBrasil, intOr(r.get("season"), d.Year()), d, clock
	m.HomeGoals, m.AwayGoals = hg, ag
	m.Round = r.get("round")
	return m, true
}

// labelCupStages names the Copa do Brasil knockout rounds.
//
// The round column is a bare number whose meaning shifts between seasons: the
// competition was restructured repeatedly, so the final is round 6 in 2012,
// round 7 in 2016 and round 8 in 2013-2020. The only stable fact is that the
// final is the last round of the season and is a two-legged tie, so stages are
// named backwards from there — and only when the season actually reached a
// final (2021 in this file stops at the round of 16).
func labelCupStages(matches []Match) {
	type seasonInfo struct {
		maxRound   int
		countByRnd map[int]int
	}
	seasons := map[int]*seasonInfo{}
	for i := range matches {
		n, ok := parseInt(matches[i].Round)
		if !ok {
			continue
		}
		si := seasons[matches[i].Season]
		if si == nil {
			si = &seasonInfo{countByRnd: map[int]int{}}
			seasons[matches[i].Season] = si
		}
		si.countByRnd[n]++
		if n > si.maxRound {
			si.maxRound = n
		}
	}

	// knockoutNames[k] is the stage k rounds before the final.
	knockoutNames := []string{"Final", "Semi-final", "Quarter-final", "Round of 16"}

	for i := range matches {
		n, ok := parseInt(matches[i].Round)
		if !ok {
			matches[i].Stage = matches[i].Round
			continue
		}
		si := seasons[matches[i].Season]
		stage := fmt.Sprintf("Round %d", n)
		// A completed season ends in a two-legged (or single) final.
		if si != nil && si.countByRnd[si.maxRound] <= 2 {
			if back := si.maxRound - n; back < len(knockoutNames) {
				stage = knockoutNames[back]
			}
		}
		matches[i].Stage = stage
		matches[i].Round = stage
	}
}

func parseLibertadores(r row) (Match, bool) {
	m, ok := baseMatch(r, r.get("home_team"), r.get("away_team"))
	if !ok {
		return m, false
	}
	d, clock, err := parseDate(r.get("datetime"))
	if err != nil {
		return m, false
	}
	hg, okH := parseInt(r.get("home_goal"))
	ag, okA := parseInt(r.get("away_goal"))
	if !okH || !okA {
		return m, false
	}
	m.Competition, m.Season, m.Date, m.KickOff = Libertadores, intOr(r.get("season"), d.Year()), d, clock
	m.HomeGoals, m.AwayGoals = hg, ag
	m.Stage = r.get("stage")
	m.Round = m.Stage
	return m, true
}

func parseHistorical(r row) (Match, bool) {
	m, ok := baseMatch(r, r.get("Equipe_mandante"), r.get("Equipe_visitante"))
	if !ok {
		return m, false
	}
	d, _, err := parseDate(r.get("Data"))
	if err != nil {
		return m, false
	}
	hg, okH := parseInt(r.get("Gols_mandante"))
	ag, okA := parseInt(r.get("Gols_visitante"))
	if !okH || !okA {
		return m, false
	}
	m.Competition, m.Season, m.Date = SerieA, intOr(r.get("Ano"), d.Year()), d
	m.HomeGoals, m.AwayGoals = hg, ag
	m.Round = r.get("Rodada")
	m.Venue = r.get("Arena")
	if m.Home.State == "" {
		m.Home.State = r.get("Mandante_UF")
	}
	if m.Away.State == "" {
		m.Away.State = r.get("Visitante_UF")
	}
	return m, true
}

// extendedCompetitions maps the tournament column of BR-Football-Dataset onto
// canonical competition names.
var extendedCompetitions = map[string]string{
	"Serie A":        SerieA,
	"Serie B":        SerieB,
	"Serie C":        SerieC,
	"Copa do Brasil": CopaDoBrasil,
}

func parseExtended(r row) (Match, bool) {
	m, ok := baseMatch(r, r.get("home"), r.get("away"))
	if !ok {
		return m, false
	}
	d, _, err := parseDate(r.get("date"))
	if err != nil {
		return m, false
	}
	hg, okH := parseInt(r.get("home_goal"))
	ag, okA := parseInt(r.get("away_goal"))
	if !okH || !okA {
		return m, false
	}
	comp, known := extendedCompetitions[r.get("tournament")]
	if !known {
		comp = r.get("tournament")
	}
	m.Competition, m.Season, m.Date = comp, d.Year(), d
	m.HomeGoals, m.AwayGoals = hg, ag
	if t := r.get("time"); len(t) >= 5 {
		m.KickOff = t[:5]
	}
	m.Stats = &MatchStats{
		HomeCorners:  intOr(r.get("home_corner"), 0),
		AwayCorners:  intOr(r.get("away_corner"), 0),
		HomeShots:    intOr(r.get("home_shots"), 0),
		AwayShots:    intOr(r.get("away_shots"), 0),
		HomeAttacks:  intOr(r.get("home_attack"), 0),
		AwayAttacks:  intOr(r.get("away_attack"), 0),
		TotalCorners: intOr(r.get("total_corners"), 0),
		HalfTimeHome: r.get("ht_result"),
		HalfTimeAway: r.get("at_result"),
	}
	return m, true
}

// skillColumns are the FIFA attribute columns kept on each player.
var skillColumns = []string{
	"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
	"Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
	"Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
	"ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
	"Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
	"Composure", "Marking", "StandingTackle", "SlidingTackle",
	"GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
}

func loadPlayers(dir string) ([]Player, error) {
	idx, rows, err := readCSV(filepath.Join(dir, FilePlayers))
	if err != nil {
		return nil, err
	}
	out := make([]Player, 0, len(rows))
	for _, rec := range rows {
		r := row{idx: idx, rec: rec, file: FilePlayers}
		name := r.get("Name")
		if name == "" {
			continue
		}
		p := Player{
			ID:          intOr(r.get("ID"), 0),
			Name:        name,
			Age:         intOr(r.get("Age"), 0),
			Nationality: r.get("Nationality"),
			Overall:     intOr(r.get("Overall"), 0),
			Potential:   intOr(r.get("Potential"), 0),
			Club:        r.get("Club"),
			Position:    r.get("Position"),
			Jersey:      intOr(r.get("Jersey Number"), 0),
			Value:       r.get("Value"),
			Wage:        r.get("Wage"),
			Foot:        r.get("Preferred Foot"),
			Height:      r.get("Height"),
			Weight:      r.get("Weight"),
			WorkRate:    r.get("Work Rate"),
		}
		if p.Club != "" {
			p.ClubID = normalize.Resolve(p.Club).ID
		}
		skills := make(map[string]int, len(skillColumns))
		for _, c := range skillColumns {
			if v, ok := parseInt(r.get(c)); ok {
				skills[c] = v
			}
		}
		if len(skills) > 0 {
			p.Skills = skills
		}
		out = append(out, p)
	}
	return out, nil
}
