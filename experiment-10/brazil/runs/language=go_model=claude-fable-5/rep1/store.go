// store.go loads the six Kaggle CSV datasets into an in-memory store and
// provides team-name normalization so the same club is recognized across
// files that spell it differently ("Palmeiras-SP", "Palmeiras", "Sao Paulo",
// "São Paulo", "Athletico Paranaense" vs "Atletico-PR", ...).
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

// Competition display names.
const (
	CompSerieA       = "Brasileirão Série A"
	CompSerieB       = "Brasileirão Série B"
	CompSerieC       = "Brasileirão Série C"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Match is one match from any of the five match datasets, deduplicated.
type Match struct {
	Date        time.Time
	Competition string
	Season      int
	Round       string // "Round 22", "Final", "group stage", ... ("" if unknown)
	HomeTeam    string // display name as it appears in the source file
	AwayTeam    string
	HomeKey     string // normalized team key (see teamKey)
	AwayKey     string
	HomeGoals   int
	AwayGoals   int
	Stadium     string
	Source      string

	// Extended stats from BR-Football-Dataset.csv (-1 when unavailable).
	HomeShots, AwayShots     int
	HomeCorners, AwayCorners int
	HomeAttacks, AwayAttacks int
}

// HasStats reports whether extended match statistics are available.
func (m *Match) HasStats() bool { return m.HomeShots >= 0 || m.HomeCorners >= 0 }

// Player is one row from the FIFA player dataset.
type Player struct {
	ID            int
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	Position      string
	JerseyNumber  string
	Height        string
	Weight        string
	Value         string
	Wage          string
	PreferredFoot string
	NameKey       string
	ClubKey       string
}

// Store holds all loaded data.
type Store struct {
	Matches []*Match
	Players []*Player
}

// ---------------------------------------------------------------------------
// Team name normalization
// ---------------------------------------------------------------------------

var accentReplacer = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ç", "c", "ñ", "n",
	"Á", "a", "À", "a", "Â", "a", "Ã", "a", "Ä", "a",
	"É", "e", "È", "e", "Ê", "e", "Ë", "e",
	"Í", "i", "Ì", "i", "Î", "i", "Ï", "i",
	"Ó", "o", "Ò", "o", "Ô", "o", "Õ", "o", "Ö", "o",
	"Ú", "u", "Ù", "u", "Û", "u", "Ü", "u",
	"Ç", "c", "Ñ", "n",
)

var brazilStates = map[string]bool{
	"ac": true, "al": true, "ap": true, "am": true, "ba": true, "ce": true,
	"df": true, "es": true, "go": true, "ma": true, "mt": true, "ms": true,
	"mg": true, "pa": true, "pb": true, "pr": true, "pe": true, "pi": true,
	"rj": true, "rn": true, "rs": true, "ro": true, "rr": true, "sc": true,
	"sp": true, "se": true, "to": true,
}

// Clubs whose base name alone is ambiguous: the state suffix must be kept
// (e.g. Atlético-MG vs Atlético-GO vs Atlético-PR are different clubs).
var ambiguousBases = map[string]bool{
	"atletico":   true,
	"america":    true,
	"botafogo":   true,
	"boavista":   true,
	"bragantino": true,
	"nacional":   true,
	"audax":      true,
	"barcelona":  true,
	"guarani":    true,
}

// teamAliases maps alternate normalized spellings to a canonical key.
var teamAliases = map[string]string{
	"athletico paranaense": "athletico pr",
	"atletico paranaense":  "athletico pr",
	"atletico pr":          "athletico pr",
	"athletico":            "athletico pr",
	"atletico mineiro":     "atletico mg",
	"atletico goianiense":  "atletico go",
	"america mineiro":      "america mg",
	"america de natal":     "america rn",
	"america fc natal":     "america rn",
	"vasco da gama":        "vasco",
	"red bull bragantino":  "bragantino",
	"rb bragantino":        "bragantino",
	"bragantino":           "bragantino",
	"bragantino sp":        "bragantino",
	"sport recife":         "sport",
	"sport club do recife": "sport",
	"sao paulo fc":         "sao paulo",
	"gremio fbpa":          "gremio",
	"botafogo":             "botafogo rj", // plain "Botafogo" means the Rio club
	"ceara sporting club":  "ceara",
	"america fc":           "america mg", // FIFA's "América FC (Minas Gerais)"
	"ec bahia":             "bahia",
	"fortaleza fc":         "fortaleza",
	"fortaleza ec":         "fortaleza",
	"ec vitoria":           "vitoria",
	"csa al":               "csa",
	"cs alagoano":          "csa",
	"crb al":               "crb",
}

// normalizeText lowercases, removes accents and punctuation, collapses spaces.
func normalizeText(s string) string {
	// Drop parenthetical annotations: "Boavista (antigo EC Barreira) - RJ".
	for {
		open := strings.Index(s, "(")
		if open < 0 {
			break
		}
		close := strings.Index(s[open:], ")")
		if close < 0 {
			s = s[:open]
			break
		}
		s = s[:open] + " " + s[open+close+1:]
	}
	s = accentReplacer.Replace(strings.ToLower(s))
	var b strings.Builder
	for _, r := range s {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') {
			b.WriteRune(r)
		} else {
			b.WriteRune(' ')
		}
	}
	return strings.Join(strings.Fields(b.String()), " ")
}

// teamKey returns the canonical key for a team name.
func teamKey(name string) string {
	k := normalizeText(name)
	if k == "" {
		return ""
	}
	if alias, ok := teamAliases[k]; ok {
		return alias
	}
	// Strip a trailing Brazilian state abbreviation ("palmeiras sp" ->
	// "palmeiras") unless the base name is ambiguous without it.
	toks := strings.Fields(k)
	if len(toks) > 1 && brazilStates[toks[len(toks)-1]] {
		base := strings.Join(toks[:len(toks)-1], " ")
		if !ambiguousBases[base] {
			if alias, ok := teamAliases[base]; ok {
				return alias
			}
			return base
		}
	}
	return k
}

// keyContains reports whether key contains query as a whole-word phrase.
func keyContains(key, query string) bool {
	if key == query {
		return true
	}
	return strings.Contains(" "+key+" ", " "+query+" ")
}

// teamMatcher matches team keys against a user query. If any team in the
// dataset matches the query key exactly, only exact matches are accepted;
// otherwise whole-word containment is used (so "flamengo" finds
// "Flamengo-RJ" but "gremio" does not drag in "Grêmio Prudente" when plain
// Grêmio exists).
type teamMatcher struct {
	query string
	exact bool
}

func (s *Store) newTeamMatcher(query string) *teamMatcher {
	q := teamKey(query)
	m := &teamMatcher{query: q}
	for _, mt := range s.Matches {
		if mt.HomeKey == q || mt.AwayKey == q {
			m.exact = true
			return m
		}
	}
	for _, p := range s.Players {
		if p.ClubKey == q {
			m.exact = true
			return m
		}
	}
	return m
}

func (m *teamMatcher) matches(key string) bool {
	if m.query == "" {
		return false
	}
	if m.exact {
		return key == m.query
	}
	return keyContains(key, m.query)
}

// ---------------------------------------------------------------------------
// Competition name handling
// ---------------------------------------------------------------------------

// canonicalCompetition maps a user-supplied competition name to the display
// name used internally, or "" if unrecognized.
func canonicalCompetition(s string) string {
	n := normalizeText(s)
	switch {
	case n == "":
		return ""
	case strings.Contains(n, "libertadores"):
		return CompLibertadores
	case strings.Contains(n, "copa do brasil"), strings.Contains(n, "brazilian cup"),
		strings.Contains(n, "cup"):
		return CompCopaDoBrasil
	case strings.Contains(n, "serie b"):
		return CompSerieB
	case strings.Contains(n, "serie c"):
		return CompSerieC
	case strings.Contains(n, "serie a"), strings.Contains(n, "brasileir"),
		strings.Contains(n, "campeonato"):
		return CompSerieA
	}
	return ""
}

// ---------------------------------------------------------------------------
// CSV loading
// ---------------------------------------------------------------------------

func newMatch() *Match {
	return &Match{
		HomeShots: -1, AwayShots: -1,
		HomeCorners: -1, AwayCorners: -1,
		HomeAttacks: -1, AwayAttacks: -1,
	}
}

var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
}

func parseDate(s string) (time.Time, bool) {
	s = strings.TrimSpace(s)
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, true
		}
	}
	return time.Time{}, false
}

// readCSV reads a whole CSV file (UTF-8, optional BOM) and returns the header
// and data rows. Rows are allowed to have varying field counts.
func readCSV(path string) ([]string, [][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	header, err := r.Read()
	if err != nil {
		return nil, nil, fmt.Errorf("%s: %w", path, err)
	}
	header[0] = strings.TrimPrefix(header[0], "\uFEFF")
	var rows [][]string
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, nil, fmt.Errorf("%s: %w", path, err)
		}
		rows = append(rows, rec)
	}
	return header, rows, nil
}

// columnIndex builds a header-name -> column-index map.
func columnIndex(header []string) map[string]int {
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(h)] = i
	}
	return idx
}

func field(row []string, idx map[string]int, name string) string {
	i, ok := idx[name]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func parseIntField(s string) (int, bool) {
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

// LoadStore loads all six CSV files from dir, deduplicating matches that
// appear in more than one dataset.
func LoadStore(dir string) (*Store, error) {
	s := &Store{}
	// Dedup index. League and Copa do Brasil matches (a pairing occurs at a
	// given venue at most once per season: double round-robin / knockout
	// legs) are keyed by competition|season|home|away so the same match is
	// recognized even when sources disagree slightly on the date.
	// Libertadores comes from a single file and is keyed by date.
	seen := map[string]*Match{}
	// Teams seen per competition-season in the primary (per-competition)
	// files. The secondary BR-Football dataset has noisier team names and
	// the occasional mislabeled row, so in seasons substantially covered by
	// a primary file its rows are kept only when both teams are already
	// known there (this admits genuine fixtures missing from a partial
	// primary season while rejecting mislabeled rows); for uncovered
	// seasons (Série A 2020+, Série B/C) it is the source of record.
	teamsInSeason := map[string]map[string]bool{}
	covered := map[string]int{}
	const secondarySource = "BR-Football-Dataset.csv"
	add := func(m *Match) {
		var key string
		switch m.Competition {
		case CompLibertadores:
			key = fmt.Sprintf("%s|%s|%s|%s", m.Competition, m.Date.Format("2006-01-02"), m.HomeKey, m.AwayKey)
		default:
			key = fmt.Sprintf("%s|%d|%s|%s", m.Competition, m.Season, m.HomeKey, m.AwayKey)
		}
		seasonKey := fmt.Sprintf("%s|%d", m.Competition, m.Season)
		if m.Source != secondarySource {
			covered[seasonKey]++
			if teamsInSeason[seasonKey] == nil {
				teamsInSeason[seasonKey] = map[string]bool{}
			}
			teamsInSeason[seasonKey][m.HomeKey] = true
			teamsInSeason[seasonKey][m.AwayKey] = true
		} else if covered[seasonKey] >= 50 && seen[key] == nil {
			teams := teamsInSeason[seasonKey]
			if !teams[m.HomeKey] || !teams[m.AwayKey] {
				return
			}
		}
		if prev, ok := seen[key]; ok {
			// Keep the first-loaded copy but merge extended stats/stadium.
			if !prev.HasStats() && m.HasStats() {
				prev.HomeShots, prev.AwayShots = m.HomeShots, m.AwayShots
				prev.HomeCorners, prev.AwayCorners = m.HomeCorners, m.AwayCorners
				prev.HomeAttacks, prev.AwayAttacks = m.HomeAttacks, m.AwayAttacks
			}
			if prev.Stadium == "" {
				prev.Stadium = m.Stadium
			}
			if prev.Round == "" {
				prev.Round = m.Round
			}
			return
		}
		seen[key] = m
		s.Matches = append(s.Matches, m)
	}

	if err := loadBrasileirao(filepath.Join(dir, "Brasileirao_Matches.csv"), add); err != nil {
		return nil, err
	}
	if err := loadNovo(filepath.Join(dir, "novo_campeonato_brasileiro.csv"), add); err != nil {
		return nil, err
	}
	if err := loadCup(filepath.Join(dir, "Brazilian_Cup_Matches.csv"), add); err != nil {
		return nil, err
	}
	if err := loadLibertadores(filepath.Join(dir, "Libertadores_Matches.csv"), add); err != nil {
		return nil, err
	}
	if err := loadBRFootball(filepath.Join(dir, "BR-Football-Dataset.csv"), add); err != nil {
		return nil, err
	}
	if err := loadPlayers(filepath.Join(dir, "fifa_data.csv"), s); err != nil {
		return nil, err
	}

	sort.Slice(s.Matches, func(i, j int) bool { return s.Matches[i].Date.After(s.Matches[j].Date) })
	return s, nil
}

func loadBrasileirao(path string, add func(*Match)) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := columnIndex(header)
	for _, row := range rows {
		date, ok := parseDate(field(row, idx, "datetime"))
		if !ok {
			continue
		}
		hg, ok1 := parseIntField(field(row, idx, "home_goal"))
		ag, ok2 := parseIntField(field(row, idx, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		m := newMatch()
		m.Date = date
		m.Competition = CompSerieA
		m.Season, _ = parseIntField(field(row, idx, "season"))
		if r := field(row, idx, "round"); r != "" {
			m.Round = "Round " + r
		}
		m.HomeTeam = field(row, idx, "home_team")
		m.AwayTeam = field(row, idx, "away_team")
		m.HomeKey = teamKey(m.HomeTeam)
		m.AwayKey = teamKey(m.AwayTeam)
		m.HomeGoals, m.AwayGoals = hg, ag
		m.Source = "Brasileirao_Matches.csv"
		add(m)
	}
	return nil
}

func loadNovo(path string, add func(*Match)) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := columnIndex(header)
	for _, row := range rows {
		date, ok := parseDate(field(row, idx, "Data"))
		if !ok {
			continue
		}
		hg, ok1 := parseIntField(field(row, idx, "Gols_mandante"))
		ag, ok2 := parseIntField(field(row, idx, "Gols_visitante"))
		if !ok1 || !ok2 {
			continue
		}
		m := newMatch()
		m.Date = date
		m.Competition = CompSerieA
		m.Season, _ = parseIntField(field(row, idx, "Ano"))
		if r := field(row, idx, "Rodada"); r != "" {
			m.Round = "Round " + r
		}
		m.HomeTeam = field(row, idx, "Equipe_mandante")
		m.AwayTeam = field(row, idx, "Equipe_visitante")
		m.HomeKey = teamKey(m.HomeTeam)
		m.AwayKey = teamKey(m.AwayTeam)
		m.HomeGoals, m.AwayGoals = hg, ag
		m.Stadium = field(row, idx, "Arena")
		m.Source = "novo_campeonato_brasileiro.csv"
		add(m)
	}
	return nil
}

func loadCup(path string, add func(*Match)) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := columnIndex(header)
	var matches []*Match
	maxRound := map[int]int{} // season -> highest round number (the final)
	rounds := map[*Match]int{}
	for _, row := range rows {
		date, ok := parseDate(field(row, idx, "datetime"))
		if !ok {
			continue
		}
		hg, ok1 := parseIntField(field(row, idx, "home_goal"))
		ag, ok2 := parseIntField(field(row, idx, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		m := newMatch()
		m.Date = date
		m.Competition = CompCopaDoBrasil
		m.Season, _ = parseIntField(field(row, idx, "season"))
		m.HomeTeam = field(row, idx, "home_team")
		m.AwayTeam = field(row, idx, "away_team")
		m.HomeKey = teamKey(m.HomeTeam)
		m.AwayKey = teamKey(m.AwayTeam)
		m.HomeGoals, m.AwayGoals = hg, ag
		m.Source = "Brazilian_Cup_Matches.csv"
		if r, ok := parseIntField(field(row, idx, "round")); ok {
			rounds[m] = r
			if r > maxRound[m.Season] {
				maxRound[m.Season] = r
			}
		}
		matches = append(matches, m)
	}
	// The cup dataset numbers rounds 1..N per season; the highest round of a
	// season is the final.
	for _, m := range matches {
		if r, ok := rounds[m]; ok {
			if r == maxRound[m.Season] {
				m.Round = "Final"
			} else {
				m.Round = fmt.Sprintf("Round %d", r)
			}
		}
		add(m)
	}
	return nil
}

func loadLibertadores(path string, add func(*Match)) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := columnIndex(header)
	for _, row := range rows {
		date, ok := parseDate(field(row, idx, "datetime"))
		if !ok {
			continue
		}
		hg, ok1 := parseIntField(field(row, idx, "home_goal"))
		ag, ok2 := parseIntField(field(row, idx, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		m := newMatch()
		m.Date = date
		m.Competition = CompLibertadores
		m.Season, _ = parseIntField(field(row, idx, "season"))
		m.Round = field(row, idx, "stage")
		m.HomeTeam = field(row, idx, "home_team")
		m.AwayTeam = field(row, idx, "away_team")
		m.HomeKey = teamKey(m.HomeTeam)
		m.AwayKey = teamKey(m.AwayTeam)
		m.HomeGoals, m.AwayGoals = hg, ag
		m.Source = "Libertadores_Matches.csv"
		add(m)
	}
	return nil
}

func loadBRFootball(path string, add func(*Match)) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := columnIndex(header)
	for _, row := range rows {
		date, ok := parseDate(field(row, idx, "date"))
		if !ok {
			continue
		}
		hg, ok1 := parseIntField(field(row, idx, "home_goal"))
		ag, ok2 := parseIntField(field(row, idx, "away_goal"))
		if !ok1 || !ok2 {
			continue
		}
		var comp string
		switch field(row, idx, "tournament") {
		case "Serie A":
			comp = CompSerieA
		case "Serie B":
			comp = CompSerieB
		case "Serie C":
			comp = CompSerieC
		case "Copa do Brasil":
			comp = CompCopaDoBrasil
		default:
			continue
		}
		m := newMatch()
		m.Date = date
		m.Competition = comp
		m.Season = date.Year() // Brazilian seasons follow the calendar year
		m.HomeTeam = field(row, idx, "home")
		m.AwayTeam = field(row, idx, "away")
		m.HomeKey = teamKey(m.HomeTeam)
		m.AwayKey = teamKey(m.AwayTeam)
		m.HomeGoals, m.AwayGoals = hg, ag
		if n, ok := parseIntField(field(row, idx, "home_shots")); ok {
			m.HomeShots = n
		}
		if n, ok := parseIntField(field(row, idx, "away_shots")); ok {
			m.AwayShots = n
		}
		if n, ok := parseIntField(field(row, idx, "home_corner")); ok {
			m.HomeCorners = n
		}
		if n, ok := parseIntField(field(row, idx, "away_corner")); ok {
			m.AwayCorners = n
		}
		if n, ok := parseIntField(field(row, idx, "home_attack")); ok {
			m.HomeAttacks = n
		}
		if n, ok := parseIntField(field(row, idx, "away_attack")); ok {
			m.AwayAttacks = n
		}
		m.Source = "BR-Football-Dataset.csv"
		add(m)
	}
	return nil
}

func loadPlayers(path string, s *Store) error {
	header, rows, err := readCSV(path)
	if err != nil {
		return err
	}
	idx := columnIndex(header)
	for _, row := range rows {
		name := field(row, idx, "Name")
		if name == "" {
			continue
		}
		p := &Player{Name: name}
		p.ID, _ = parseIntField(field(row, idx, "ID"))
		p.Age, _ = parseIntField(field(row, idx, "Age"))
		p.Nationality = field(row, idx, "Nationality")
		p.Overall, _ = parseIntField(field(row, idx, "Overall"))
		p.Potential, _ = parseIntField(field(row, idx, "Potential"))
		p.Club = field(row, idx, "Club")
		p.Position = field(row, idx, "Position")
		p.JerseyNumber = field(row, idx, "Jersey Number")
		p.Height = field(row, idx, "Height")
		p.Weight = field(row, idx, "Weight")
		p.Value = field(row, idx, "Value")
		p.Wage = field(row, idx, "Wage")
		p.PreferredFoot = field(row, idx, "Preferred Foot")
		p.NameKey = normalizeText(name)
		p.ClubKey = teamKey(p.Club)
		s.Players = append(s.Players, p)
	}
	return nil
}
