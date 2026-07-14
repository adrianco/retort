// store.go - Data layer for the Brazilian Soccer MCP server.
//
// Context: Loads the six Kaggle CSV datasets (Brasileirão Serie A matches,
// Copa do Brasil, Copa Libertadores, extended BR-Football stats, historical
// Brasileirão 2003-2019, and FIFA player data) into an in-memory Store.
// Handles UTF-8/accents, multiple date formats, team-name variations
// ("Palmeiras-SP" vs "Palmeiras" vs "Sociedade Esportiva Palmeiras"), and
// cross-dataset deduplication so overlapping seasons are not double counted.
package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Competition canonical names.
const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Série B"
	CompSerieC       = "Série C"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Source identifiers, in dedup priority order (earlier wins).
const (
	SrcSerieA       = "brasileirao-matches"
	SrcSerieAHist   = "historical-brasileirao"
	SrcCopaDoBrasil = "copa-do-brasil"
	SrcLibertadores = "libertadores"
	SrcExtended     = "br-football-extended"
)

// Team holds a display name plus normalized matching keys.
type Team struct {
	Name  string // display name, e.g. "Palmeiras"
	Base  string // normalized key, e.g. "palmeiras"
	State string // lowercase state code when known, e.g. "sp"
}

// Match is one match row, unified across all datasets.
type Match struct {
	Date        time.Time
	Home, Away  Team
	HomeGoals   int
	AwayGoals   int
	Competition string
	Season      int
	Round       string // league/cup round when known
	Stage       string // Libertadores stage when known
	Arena       string
	Source      string
	// Extended stats from BR-Football-Dataset (-1 when unknown).
	HomeShots, AwayShots     int
	HomeCorners, AwayCorners int
}

// Skill is one named FIFA attribute rating.
type Skill struct {
	Name  string
	Value int
}

// Player is one FIFA database entry.
type Player struct {
	ID            string
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	Position      string
	Jersey        int
	Height        string
	Weight        string
	PreferredFoot string
	Value         string
	Wage          string
	Skills        []Skill
}

// Store holds all loaded data.
type Store struct {
	Matches []Match
	Players []Player

	dedupRound map[string]bool // comp|season|round|home|away
	dedupDate  map[string]bool // date|home|away
}

// ---------- normalization ----------

var accentReplacer = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "å", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ç", "c", "ñ", "n", "ý", "y",
	"Á", "a", "À", "a", "Â", "a", "Ã", "a", "Ä", "a",
	"É", "e", "È", "e", "Ê", "e", "Ë", "e",
	"Í", "i", "Ì", "i", "Î", "i", "Ï", "i",
	"Ó", "o", "Ò", "o", "Ô", "o", "Õ", "o", "Ö", "o",
	"Ú", "u", "Ù", "u", "Û", "u", "Ü", "u",
	"Ç", "c", "Ñ", "n",
)

var brStates = map[string]bool{
	"AC": true, "AL": true, "AP": true, "AM": true, "BA": true, "CE": true,
	"DF": true, "ES": true, "GO": true, "MA": true, "MT": true, "MS": true,
	"MG": true, "PA": true, "PB": true, "PR": true, "PE": true, "PI": true,
	"RJ": true, "RN": true, "RS": true, "RO": true, "RR": true, "SC": true,
	"SP": true, "SE": true, "TO": true,
}

var (
	parenRe      = regexp.MustCompile(`\s*\([^)]*\)`)
	dashSuffixRe = regexp.MustCompile(`\s*-\s*([A-Za-z]{2,3})$`)
	spaceSuffix  = regexp.MustCompile(`\s+([A-Z]{2})$`)
	multiSpaceRe = regexp.MustCompile(`\s+`)
)

// aliases maps a normalized base name to its canonical base (and state when
// the alias implies one). Built from observed cross-dataset variations.
var aliases = map[string]struct{ base, state string }{
	"vasco da gama":        {"vasco", "rj"},
	"atletico mineiro":     {"atletico", "mg"},
	"atletico paranaense":  {"atletico", "pr"},
	"atletico goianiense":  {"atletico", "go"},
	"sport recife":         {"sport", "pe"},
	"sport club do recife": {"sport", "pe"},
	"red bull bragantino":  {"bragantino", "sp"},
	"fortaleza ec":         {"fortaleza", "ce"},
}

func normalizeText(s string) string {
	s = accentReplacer.Replace(s)
	s = strings.ToLower(s)
	s = multiSpaceRe.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// parseTeam turns a raw dataset team string into a Team with normalized keys.
// state, when supplied from a dedicated CSV column, takes precedence.
func parseTeam(raw, state string) Team {
	name := parenRe.ReplaceAllString(raw, "")
	name = strings.TrimSpace(name)

	st := strings.ToLower(strings.TrimSpace(state))
	// Trailing "-SP" / " - MG" style suffix (2-letter state or 3-letter country).
	if m := dashSuffixRe.FindStringSubmatch(name); m != nil {
		tok := strings.ToUpper(m[1])
		if len(tok) == 2 && brStates[tok] {
			if st == "" {
				st = strings.ToLower(tok)
			}
			name = strings.TrimSpace(dashSuffixRe.ReplaceAllString(name, ""))
		} else if len(tok) == 3 && tok == m[1] {
			// Country code like "Barcelona-EQU": strip, no Brazilian state.
			name = strings.TrimSpace(dashSuffixRe.ReplaceAllString(name, ""))
		}
	}
	// Trailing bare state token like "Botafogo RJ" (uppercase in source).
	if m := spaceSuffix.FindStringSubmatch(name); m != nil && brStates[m[1]] {
		if st == "" {
			st = strings.ToLower(m[1])
		}
		name = strings.TrimSpace(spaceSuffix.ReplaceAllString(name, ""))
	}

	base := normalizeText(name)
	base = strings.ReplaceAll(base, "athletico", "atletico")
	base = strings.TrimPrefix(base, "ec ")
	base = strings.TrimSuffix(base, " fc")
	base = strings.TrimSpace(base)
	if a, ok := aliases[base]; ok {
		base = a.base
		if st == "" {
			st = a.state
		}
	}
	return Team{Name: name, Base: base, State: st}
}

// teamQueryMatches reports whether team t satisfies the user query q
// (itself parsed via parseTeam). Matching is bidirectional substring on the
// normalized base, with state compatibility when both sides declare one.
func teamQueryMatches(t, q Team) bool {
	if q.Base == "" {
		return false
	}
	if t.State != "" && q.State != "" && t.State != q.State {
		return false
	}
	return strings.Contains(t.Base, q.Base) || strings.Contains(q.Base, t.Base)
}

// ---------- date parsing ----------

var dateFormats = []string{
	"2006-01-02 15:04:05",
	"2006-01-02T15:04:05",
	"2006-01-02 15:04",
	"2006-01-02",
	"02/01/2006 15:04",
	"02/01/2006",
}

func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	for _, f := range dateFormats {
		if t, err := time.Parse(f, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// ---------- CSV helpers ----------

type csvTable struct {
	cols map[string]int
	rows [][]string
}

func (t *csvTable) get(row []string, col string) string {
	i, ok := t.cols[col]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func readCSV(path string) (*csvTable, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.LazyQuotes = true
	r.FieldsPerRecord = -1
	all, err := r.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	if len(all) == 0 {
		return nil, fmt.Errorf("%s: empty file", path)
	}
	header := all[0]
	if len(header) > 0 {
		header[0] = strings.TrimPrefix(header[0], "\ufeff")
	}
	cols := map[string]int{}
	for i, h := range header {
		cols[strings.ToLower(strings.TrimSpace(h))] = i
	}
	return &csvTable{cols: cols, rows: all[1:]}, nil
}

func parseGoals(s string) (int, bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0, false
	}
	if n, err := strconv.Atoi(s); err == nil {
		return n, true
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f), true
	}
	return 0, false
}

func atoiOr(s string, def int) int {
	s = strings.TrimSpace(s)
	if n, err := strconv.Atoi(s); err == nil {
		return n
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return def
}

// ---------- dedup + add ----------

func (s *Store) addMatch(m Match) {
	dateKey := ""
	if !m.Date.IsZero() {
		// Datasets disagree by up to a day on kickoff dates (timezones,
		// matches finishing after midnight), so dedup tolerates +/-1 day.
		for _, delta := range []int{-1, 0, 1} {
			k := m.Date.AddDate(0, 0, delta).Format("2006-01-02") + "|" + m.Home.Base + "|" + m.Away.Base
			if s.dedupDate[k] {
				return
			}
			if delta == 0 {
				dateKey = k
			}
		}
	}
	roundKey := ""
	if m.Round != "" && m.Season != 0 {
		roundKey = fmt.Sprintf("%s|%d|%s|%s|%s", m.Competition, m.Season, m.Round, m.Home.Base, m.Away.Base)
		if s.dedupRound[roundKey] {
			return
		}
	}
	if dateKey != "" {
		s.dedupDate[dateKey] = true
	}
	if roundKey != "" {
		s.dedupRound[roundKey] = true
	}
	s.Matches = append(s.Matches, m)
}

// ---------- loaders ----------

func (s *Store) loadBrasileirao(path string) error {
	t, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, row := range t.rows {
		hg, ok1 := parseGoals(t.get(row, "home_goal"))
		ag, ok2 := parseGoals(t.get(row, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		d, _ := parseDate(t.get(row, "datetime"))
		s.addMatch(Match{
			Date:        d,
			Home:        parseTeam(t.get(row, "home_team"), t.get(row, "home_team_state")),
			Away:        parseTeam(t.get(row, "away_team"), t.get(row, "away_team_state")),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Competition: CompSerieA,
			Season:      atoiOr(t.get(row, "season"), 0),
			Round:       t.get(row, "round"),
			Source:      SrcSerieA,
			HomeShots:   -1, AwayShots: -1, HomeCorners: -1, AwayCorners: -1,
		})
	}
	return nil
}

func (s *Store) loadHistorical(path string) error {
	t, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, row := range t.rows {
		hg, ok1 := parseGoals(t.get(row, "gols_mandante"))
		ag, ok2 := parseGoals(t.get(row, "gols_visitante"))
		if !ok1 || !ok2 {
			continue
		}
		d, _ := parseDate(t.get(row, "data"))
		s.addMatch(Match{
			Date:        d,
			Home:        parseTeam(t.get(row, "equipe_mandante"), t.get(row, "mandante_uf")),
			Away:        parseTeam(t.get(row, "equipe_visitante"), t.get(row, "visitante_uf")),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Competition: CompSerieA,
			Season:      atoiOr(t.get(row, "ano"), 0),
			Round:       t.get(row, "rodada"),
			Arena:       t.get(row, "arena"),
			Source:      SrcSerieAHist,
			HomeShots:   -1, AwayShots: -1, HomeCorners: -1, AwayCorners: -1,
		})
	}
	return nil
}

func (s *Store) loadCup(path string) error {
	t, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, row := range t.rows {
		hg, ok1 := parseGoals(t.get(row, "home_goal"))
		ag, ok2 := parseGoals(t.get(row, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		d, _ := parseDate(t.get(row, "datetime"))
		s.addMatch(Match{
			Date:        d,
			Home:        parseTeam(t.get(row, "home_team"), ""),
			Away:        parseTeam(t.get(row, "away_team"), ""),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Competition: CompCopaDoBrasil,
			Season:      atoiOr(t.get(row, "season"), 0),
			Round:       t.get(row, "round"),
			Source:      SrcCopaDoBrasil,
			HomeShots:   -1, AwayShots: -1, HomeCorners: -1, AwayCorners: -1,
		})
	}
	return nil
}

func (s *Store) loadLibertadores(path string) error {
	t, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, row := range t.rows {
		hg, ok1 := parseGoals(t.get(row, "home_goal"))
		ag, ok2 := parseGoals(t.get(row, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		d, _ := parseDate(t.get(row, "datetime"))
		s.addMatch(Match{
			Date:        d,
			Home:        parseTeam(t.get(row, "home_team"), ""),
			Away:        parseTeam(t.get(row, "away_team"), ""),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Competition: CompLibertadores,
			Season:      atoiOr(t.get(row, "season"), 0),
			Stage:       t.get(row, "stage"),
			Source:      SrcLibertadores,
			HomeShots:   -1, AwayShots: -1, HomeCorners: -1, AwayCorners: -1,
		})
	}
	return nil
}

var extendedCompetitions = map[string]string{
	"serie a":        CompSerieA,
	"serie b":        CompSerieB,
	"serie c":        CompSerieC,
	"copa do brasil": CompCopaDoBrasil,
}

func (s *Store) loadExtended(path string) error {
	t, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, row := range t.rows {
		hg, ok1 := parseGoals(t.get(row, "home_goal"))
		ag, ok2 := parseGoals(t.get(row, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		comp := normalizeText(t.get(row, "tournament"))
		canon, ok := extendedCompetitions[comp]
		if !ok {
			canon = t.get(row, "tournament")
		}
		raw := t.get(row, "date")
		if tm := t.get(row, "time"); tm != "" {
			raw += " " + tm[:min(5, len(tm))]
		}
		d, _ := parseDate(raw)
		season := 0
		if !d.IsZero() {
			season = d.Year()
		}
		s.addMatch(Match{
			Date:        d,
			Home:        parseTeam(t.get(row, "home"), ""),
			Away:        parseTeam(t.get(row, "away"), ""),
			HomeGoals:   hg,
			AwayGoals:   ag,
			Competition: canon,
			Season:      season,
			Source:      SrcExtended,
			HomeShots:   atoiOr(t.get(row, "home_shots"), -1),
			AwayShots:   atoiOr(t.get(row, "away_shots"), -1),
			HomeCorners: atoiOr(t.get(row, "home_corner"), -1),
			AwayCorners: atoiOr(t.get(row, "away_corner"), -1),
		})
	}
	return nil
}

// fifaSkillCols are the attribute columns surfaced in player details.
var fifaSkillCols = []string{
	"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
	"Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
	"Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
	"ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
	"Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
	"Composure", "Marking", "StandingTackle", "SlidingTackle",
	"GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
}

func (s *Store) loadPlayers(path string) error {
	t, err := readCSV(path)
	if err != nil {
		return err
	}
	for _, row := range t.rows {
		name := t.get(row, "name")
		if name == "" {
			continue
		}
		p := Player{
			ID:            t.get(row, "id"),
			Name:          name,
			Age:           atoiOr(t.get(row, "age"), 0),
			Nationality:   t.get(row, "nationality"),
			Overall:       atoiOr(t.get(row, "overall"), 0),
			Potential:     atoiOr(t.get(row, "potential"), 0),
			Club:          t.get(row, "club"),
			Position:      t.get(row, "position"),
			Jersey:        atoiOr(t.get(row, "jersey number"), 0),
			Height:        t.get(row, "height"),
			Weight:        t.get(row, "weight"),
			PreferredFoot: t.get(row, "preferred foot"),
			Value:         t.get(row, "value"),
			Wage:          t.get(row, "wage"),
		}
		for _, col := range fifaSkillCols {
			if v := t.get(row, strings.ToLower(col)); v != "" {
				if n := atoiOr(v, -1); n >= 0 {
					p.Skills = append(p.Skills, Skill{Name: col, Value: n})
				}
			}
		}
		s.Players = append(s.Players, p)
	}
	return nil
}

// LoadStore reads all six datasets from dataDir (e.g. "data/kaggle").
// Load order defines dedup priority: canonical league data first, the
// extended-stats dataset last so its duplicates are dropped.
func LoadStore(dataDir string) (*Store, error) {
	s := &Store{
		dedupRound: map[string]bool{},
		dedupDate:  map[string]bool{},
	}
	steps := []struct {
		file string
		fn   func(string) error
	}{
		{"Brasileirao_Matches.csv", s.loadBrasileirao},
		{"novo_campeonato_brasileiro.csv", s.loadHistorical},
		{"Brazilian_Cup_Matches.csv", s.loadCup},
		{"Libertadores_Matches.csv", s.loadLibertadores},
		{"BR-Football-Dataset.csv", s.loadExtended},
		{"fifa_data.csv", s.loadPlayers},
	}
	for _, st := range steps {
		if err := st.fn(filepath.Join(dataDir, st.file)); err != nil {
			return nil, fmt.Errorf("loading %s: %w", st.file, err)
		}
	}
	sort.SliceStable(s.Matches, func(i, j int) bool {
		return s.Matches[i].Date.Before(s.Matches[j].Date)
	})
	return s, nil
}
