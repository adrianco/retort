// load.go reads the six Kaggle CSV files into a Store. Each loader is tolerant
// of the quirks of its own file (quoted numerics, float goal counts, Brazilian
// DD/MM/YYYY dates, UTF-8 BOMs) and rows that cannot be parsed are skipped
// rather than failing the whole load.
package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
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

// dateLayouts covers every date spelling seen in the datasets.
var dateLayouts = []struct {
	layout  string
	hasTime bool
}{
	{"2006-01-02 15:04:05", true},
	{"2006-01-02T15:04:05", true},
	{"2006-01-02", false},
	{"02/01/2006", false},
	{"02/01/2006 15:04", true},
	{"01/02/2006", false}, // last resort for US style dates
}

// ParseDate parses any of the supported date spellings.
func ParseDate(s string) (t time.Time, hasTime bool, err error) {
	s = strings.TrimSpace(strings.Trim(s, `"`))
	if s == "" {
		return time.Time{}, false, fmt.Errorf("empty date")
	}
	for _, l := range dateLayouts {
		if t, err = time.Parse(l.layout, s); err == nil {
			return t, l.hasTime, nil
		}
	}
	return time.Time{}, false, fmt.Errorf("unrecognised date %q", s)
}

// parseInt tolerates quoting, blanks and float-formatted integers ("1.0").
func parseInt(s string) (int, bool) {
	s = strings.TrimSpace(strings.Trim(s, `"`))
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

func clean(s string) string { return strings.TrimSpace(strings.Trim(s, `"`)) }

// Store is the loaded knowledge graph.
type Store struct {
	Matches []*Match
	Players []*Player

	matchesByTeam map[string][]*Match
	teamDisplay   map[string]string
	playersByClub map[string][]*Player
	competitions  []string
	loadErrors    []string
}

// LoadErrors reports rows that were skipped during loading.
func (s *Store) LoadErrors() []string { return s.loadErrors }

// readCSV opens path and returns its header plus all records.
func readCSV(path string) ([]string, [][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	r.ReuseRecord = false

	header, err := r.Read()
	if err != nil {
		return nil, nil, fmt.Errorf("%s: %w", filepath.Base(path), err)
	}
	// Strip a UTF-8 BOM from the first header cell (fifa_data.csv has one).
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\ufeff")
	}
	var rows [][]string
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			// Skip malformed lines but keep going.
			continue
		}
		rows = append(rows, rec)
	}
	return header, rows, nil
}

// colIndex builds a case-insensitive header name to column index map.
func colIndex(header []string) map[string]int {
	m := make(map[string]int, len(header))
	for i, h := range header {
		m[strings.ToLower(strings.TrimSpace(h))] = i
	}
	return m
}

// get safely reads a named column from a record.
func get(rec []string, idx map[string]int, name string) string {
	i, ok := idx[name]
	if !ok || i >= len(rec) {
		return ""
	}
	return clean(rec[i])
}

// Load reads every dataset found in dir and returns the populated store.
// Missing files are reported in LoadErrors but do not abort the load, so the
// server still starts with whatever data is present.
func Load(dir string) (*Store, error) {
	s := &Store{
		matchesByTeam: map[string][]*Match{},
		teamDisplay:   map[string]string{},
		playersByClub: map[string][]*Player{},
	}

	loaders := []struct {
		file string
		fn   func(*Store, string) error
	}{
		{FileBrasileirao, (*Store).loadBrasileirao},
		{FileCup, (*Store).loadCup},
		{FileLibertadores, (*Store).loadLibertadores},
		{FileHistorical, (*Store).loadHistorical},
		{FileBRFootball, (*Store).loadBRFootball},
		{FileFIFA, (*Store).loadFIFA},
	}
	for _, l := range loaders {
		if err := l.fn(s, filepath.Join(dir, l.file)); err != nil {
			s.loadErrors = append(s.loadErrors, err.Error())
		}
	}
	if len(s.Matches) == 0 && len(s.Players) == 0 {
		return nil, fmt.Errorf("no data loaded from %s: %s", dir, strings.Join(s.loadErrors, "; "))
	}
	s.index()
	return s, nil
}

// addMatch registers a match, merging it with an already loaded duplicate of
// the same fixture from another dataset instead of double counting it.
func (s *Store) addMatch(m *Match, dedup map[string]*Match) {
	m.HomeKey = CanonicalTeam(m.HomeTeam)
	m.AwayKey = CanonicalTeam(m.AwayTeam)
	if m.HomeKey == "" || m.AwayKey == "" {
		return
	}
	m.HomeTeam = DisplayTeam(m.HomeTeam)
	m.AwayTeam = DisplayTeam(m.AwayTeam)
	m.DateString = m.Date.Format("2006-01-02")

	// The same fixture appears in several datasets, sometimes recorded a day
	// apart because one source stores the local kick-off and another the UTC
	// date. Look for an already loaded copy within a one day window.
	key := dedupKey(m, 0)
	prev, ok := dedup[key]
	if !ok {
		prev, ok = dedup[dedupKey(m, -1)]
	}
	if !ok {
		prev, ok = dedup[dedupKey(m, 1)]
	}
	if ok {
		prev.Sources = append(prev.Sources, m.Sources...)
		if prev.Stats == nil {
			prev.Stats = m.Stats
		}
		if prev.Round == "" {
			prev.Round = m.Round
		}
		if prev.Stage == "" {
			prev.Stage = m.Stage
		}
		if prev.Venue == "" {
			prev.Venue = m.Venue
		}
		return
	}
	dedup[key] = m
	s.Matches = append(s.Matches, m)
}

// dedupKey identifies a fixture: competition, both clubs and the date shifted
// by dayOffset days.
func dedupKey(m *Match, dayOffset int) string {
	d := m.Date.AddDate(0, 0, dayOffset).Format("2006-01-02")
	return m.Competition + "|" + d + "|" + m.HomeKey + "|" + m.AwayKey
}

// dedupKeys rebuilds the dedup index over already loaded matches so that each
// loader can merge into the results of the previous ones.
func (s *Store) dedupKeys() map[string]*Match {
	m := make(map[string]*Match, len(s.Matches))
	for _, mt := range s.Matches {
		m[dedupKey(mt, 0)] = mt
	}
	return m
}

func (s *Store) loadBrasileirao(path string) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := colIndex(header)
	dedup := s.dedupKeys()
	for _, rec := range rows {
		d, hasTime, err := ParseDate(get(rec, idx, "datetime"))
		if err != nil {
			continue
		}
		hg, ok1 := parseInt(get(rec, idx, "home_goal"))
		ag, ok2 := parseInt(get(rec, idx, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		season, _ := parseInt(get(rec, idx, "season"))
		s.addMatch(&Match{
			Date: d, HasTime: hasTime,
			Competition: CompSerieA,
			Season:      season,
			Round:       get(rec, idx, "round"),
			HomeTeam:    get(rec, idx, "home_team"),
			AwayTeam:    get(rec, idx, "away_team"),
			HomeState:   get(rec, idx, "home_team_state"),
			AwayState:   get(rec, idx, "away_team_state"),
			HomeGoals:   hg, AwayGoals: ag,
			Sources: []string{FileBrasileirao},
		}, dedup)
	}
	return nil
}

func (s *Store) loadCup(path string) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := colIndex(header)
	dedup := s.dedupKeys()
	for _, rec := range rows {
		d, hasTime, err := ParseDate(get(rec, idx, "datetime"))
		if err != nil {
			continue
		}
		hg, ok1 := parseInt(get(rec, idx, "home_goal"))
		ag, ok2 := parseInt(get(rec, idx, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		season, _ := parseInt(get(rec, idx, "season"))
		home, away := get(rec, idx, "home_team"), get(rec, idx, "away_team")
		s.addMatch(&Match{
			Date: d, HasTime: hasTime,
			Competition: CompCopaBrasil,
			Season:      season,
			Round:       get(rec, idx, "round"),
			Stage:       cupStage(get(rec, idx, "round")),
			HomeTeam:    home, AwayTeam: away,
			HomeState: TeamState(home), AwayState: TeamState(away),
			HomeGoals: hg, AwayGoals: ag,
			Sources: []string{FileCup},
		}, dedup)
	}
	return nil
}

// cupStage turns a Copa do Brasil round number into a readable stage name.
// The competition is a straight knockout, so the final round of the season is
// the final; without knowing the season size we name the common late rounds.
func cupStage(round string) string {
	n, ok := parseInt(round)
	if !ok {
		return strings.TrimSpace(round)
	}
	switch n {
	case 8:
		return "final"
	case 7:
		return "semifinals"
	case 6:
		return "quarterfinals"
	case 5:
		return "round of 16"
	default:
		return fmt.Sprintf("round %d", n)
	}
}

func (s *Store) loadLibertadores(path string) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := colIndex(header)
	dedup := s.dedupKeys()
	for _, rec := range rows {
		d, hasTime, err := ParseDate(get(rec, idx, "datetime"))
		if err != nil {
			continue
		}
		hg, ok1 := parseInt(get(rec, idx, "home_goal"))
		ag, ok2 := parseInt(get(rec, idx, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		season, _ := parseInt(get(rec, idx, "season"))
		home, away := get(rec, idx, "home_team"), get(rec, idx, "away_team")
		s.addMatch(&Match{
			Date: d, HasTime: hasTime,
			Competition: CompLibertadores,
			Season:      season,
			Stage:       get(rec, idx, "stage"),
			HomeTeam:    home, AwayTeam: away,
			HomeState: TeamState(home), AwayState: TeamState(away),
			HomeGoals: hg, AwayGoals: ag,
			Sources: []string{FileLibertadores},
		}, dedup)
	}
	return nil
}

func (s *Store) loadHistorical(path string) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := colIndex(header)
	dedup := s.dedupKeys()
	for _, rec := range rows {
		d, hasTime, err := ParseDate(get(rec, idx, "data"))
		if err != nil {
			continue
		}
		hg, ok1 := parseInt(get(rec, idx, "gols_mandante"))
		ag, ok2 := parseInt(get(rec, idx, "gols_visitante"))
		if !ok1 || !ok2 {
			continue
		}
		season, _ := parseInt(get(rec, idx, "ano"))
		s.addMatch(&Match{
			Date: d, HasTime: hasTime,
			Competition: CompSerieA,
			Season:      season,
			Round:       get(rec, idx, "rodada"),
			Venue:       get(rec, idx, "arena"),
			HomeTeam:    get(rec, idx, "equipe_mandante"),
			AwayTeam:    get(rec, idx, "equipe_visitante"),
			HomeState:   get(rec, idx, "mandante_uf"),
			AwayState:   get(rec, idx, "visitante_uf"),
			HomeGoals:   hg, AwayGoals: ag,
			Sources: []string{FileHistorical},
		}, dedup)
	}
	return nil
}

// brTournaments maps the BR-Football tournament column onto canonical names.
var brTournaments = map[string]string{
	"serie a":        CompSerieA,
	"serie b":        CompSerieB,
	"serie c":        CompSerieC,
	"copa do brasil": CompCopaBrasil,
	"libertadores":   CompLibertadores,
}

func (s *Store) loadBRFootball(path string) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := colIndex(header)
	dedup := s.dedupKeys()
	for _, rec := range rows {
		d, hasTime, err := ParseDate(get(rec, idx, "date"))
		if err != nil {
			continue
		}
		hg, ok1 := parseInt(get(rec, idx, "home_goal"))
		ag, ok2 := parseInt(get(rec, idx, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		comp, ok := brTournaments[FoldAccents(get(rec, idx, "tournament"))]
		if !ok {
			comp = get(rec, idx, "tournament")
		}
		stats := &MatchStats{}
		stats.HomeCorners, _ = parseInt(get(rec, idx, "home_corner"))
		stats.AwayCorners, _ = parseInt(get(rec, idx, "away_corner"))
		stats.HomeShots, _ = parseInt(get(rec, idx, "home_shots"))
		stats.AwayShots, _ = parseInt(get(rec, idx, "away_shots"))
		stats.HomeAttacks, _ = parseInt(get(rec, idx, "home_attack"))
		stats.AwayAttacks, _ = parseInt(get(rec, idx, "away_attack"))

		home, away := get(rec, idx, "home"), get(rec, idx, "away")
		s.addMatch(&Match{
			Date: d, HasTime: hasTime,
			Competition: comp,
			Season:      d.Year(),
			HomeTeam:    home, AwayTeam: away,
			HomeState: TeamState(home), AwayState: TeamState(away),
			HomeGoals: hg, AwayGoals: ag,
			Stats:   stats,
			Sources: []string{FileBRFootball},
		}, dedup)
	}
	return nil
}

// fifaSkills are the attribute columns kept for each player.
var fifaSkills = []string{
	"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling",
	"BallControl", "Acceleration", "SprintSpeed", "ShotPower", "Stamina",
	"Strength", "Vision", "Penalties", "Composure", "StandingTackle",
	"GKDiving", "GKReflexes",
}

func (s *Store) loadFIFA(path string) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := colIndex(header)
	for _, rec := range rows {
		name := get(rec, idx, "name")
		if name == "" {
			continue
		}
		p := &Player{Name: name}
		p.ID, _ = parseInt(get(rec, idx, "id"))
		p.Age, _ = parseInt(get(rec, idx, "age"))
		p.Nationality = get(rec, idx, "nationality")
		p.Overall, _ = parseInt(get(rec, idx, "overall"))
		p.Potential, _ = parseInt(get(rec, idx, "potential"))
		p.Club = get(rec, idx, "club")
		p.ClubKey = CanonicalTeam(p.Club)
		p.Position = get(rec, idx, "position")
		p.JerseyNumber, _ = parseInt(get(rec, idx, "jersey number"))
		p.Height = get(rec, idx, "height")
		p.Weight = get(rec, idx, "weight")
		p.Value = get(rec, idx, "value")
		p.Wage = get(rec, idx, "wage")
		p.PreferredFoot = get(rec, idx, "preferred foot")
		p.Skills = map[string]int{}
		for _, sk := range fifaSkills {
			if v, ok := parseInt(get(rec, idx, strings.ToLower(sk))); ok {
				p.Skills[sk] = v
			}
		}
		s.Players = append(s.Players, p)
	}
	return nil
}

// index builds the lookup structures used by the query layer.
func (s *Store) index() {
	sort.SliceStable(s.Matches, func(i, j int) bool {
		return s.Matches[i].Date.Before(s.Matches[j].Date)
	})

	comps := map[string]bool{}
	for _, m := range s.Matches {
		s.matchesByTeam[m.HomeKey] = append(s.matchesByTeam[m.HomeKey], m)
		s.matchesByTeam[m.AwayKey] = append(s.matchesByTeam[m.AwayKey], m)
		s.rememberDisplay(m.HomeKey, m.HomeTeam)
		s.rememberDisplay(m.AwayKey, m.AwayTeam)
		comps[m.Competition] = true
	}
	for _, p := range s.Players {
		if p.ClubKey != "" {
			s.playersByClub[p.ClubKey] = append(s.playersByClub[p.ClubKey], p)
		}
	}
	for c := range comps {
		s.competitions = append(s.competitions, c)
	}
	sort.Strings(s.competitions)
}

// rememberDisplay keeps the shortest display spelling seen for a team, which
// is almost always the most readable one.
func (s *Store) rememberDisplay(key, display string) {
	if key == "" || display == "" {
		return
	}
	cur, ok := s.teamDisplay[key]
	if !ok || len(display) < len(cur) {
		s.teamDisplay[key] = display
	}
}

// DisplayName returns the preferred display spelling for a canonical key.
func (s *Store) DisplayName(key string) string {
	if d, ok := s.teamDisplay[key]; ok {
		return d
	}
	return key
}

// Competitions lists every competition present in the loaded matches.
func (s *Store) Competitions() []string { return append([]string(nil), s.competitions...) }
