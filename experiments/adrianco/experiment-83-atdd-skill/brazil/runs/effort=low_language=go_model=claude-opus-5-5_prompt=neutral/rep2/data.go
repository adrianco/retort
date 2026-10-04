package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode"

	"golang.org/x/text/runes"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

// Competition names used throughout.
const (
	CompSerieA       = "Brasileirão Serie A"
	CompSerieB       = "Brasileirão Serie B"
	CompSerieC       = "Brasileirão Serie C"
	CompCopaDoBrasil = "Copa do Brasil"
	CompLibertadores = "Copa Libertadores"
)

// Match is a single match from any of the match datasets.
type Match struct {
	Date        time.Time
	HomeTeam    string // raw name from source
	AwayTeam    string
	HomeGoals   int
	AwayGoals   int
	Season      int
	Competition string
	Round       string // round number or stage
	Arena       string
	Source      string // source file
	homeKey     string
	awayKey     string
	// Extended stats (BR-Football-Dataset only); -1 when unknown.
	HomeCorners, AwayCorners int
	HomeShots, AwayShots     int
	HomeAttacks, AwayAttacks int
}

// Player is a row from the FIFA dataset.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string
	Jersey      string
	Height      string
	Weight      string
	Value       string
	Foot        string
	Skills      map[string]int
	clubKey     string
	nameKey     string
}

// DB holds all loaded data.
type DB struct {
	Matches []*Match
	Players []*Player
	Sources map[string]int // file -> rows loaded

	finalOnce   sync.Once
	finalRounds map[int]string
}

var skillCols = []string{"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Dribbling",
	"BallControl", "Acceleration", "SprintSpeed", "Stamina", "Strength", "ShotPower", "LongShots",
	"Vision", "Penalties", "StandingTackle", "GKReflexes"}

// ---------- normalization ----------

var accentStripper = transform.Chain(norm.NFD, runes.Remove(runes.In(unicode.Mn)), norm.NFC)

// Fold lowercases and strips accents.
func Fold(s string) string {
	out, _, err := transform.String(accentStripper, s)
	if err != nil {
		out = s
	}
	return strings.ToLower(out)
}

var fillerTokens = map[string]bool{"fc": true, "ec": true, "clube": true, "club": true,
	"futebol": true, "de": true, "da": true, "do": true, "red": true, "bull": true, "esporte": true,
	"cr": true}

var tokenAlias = map[string]string{
	"athletico": "atletico", "mineiro": "mg", "paranaense": "pr", "goianiense": "go",
	"gremio": "gremio", "vasco": "vasco", "cearense": "ce", "baiano": "ba",
	"uru": "uruguay", "arg": "argentina", "equ": "ecuador", "bol": "bolivia",
	"par": "paraguay", "chi": "chile", "col": "colombia", "per": "peru", "ven": "venezuela",
}

// whole-name aliases applied after folding
var nameAlias = map[string]string{
	"sport club corinthians paulista":  "corinthians",
	"sociedade esportiva palmeiras":    "palmeiras",
	"clube de regatas do flamengo":     "flamengo",
	"fluminense football club":         "fluminense",
	"sao paulo futebol clube":          "sao paulo",
	"sao paulo fc":                     "sao paulo",
	"santos futebol clube":             "santos",
	"gremio foot ball porto alegrense": "gremio",
	"sport club internacional":         "internacional",
	"club athletico paranaense":        "atletico pr",
	"clube atletico mineiro":           "atletico mg",
	"cruzeiro esporte clube":           "cruzeiro",
	"club de regatas vasco da gama":    "vasco",
	"botafogo de futebol e regatas":    "botafogo rj",
	"sport club do recife":             "sport",
	"sport recife":                     "sport",
	"esporte clube bahia":              "bahia",
	"fortaleza esporte clube":          "fortaleza",
	"ceara sporting club":              "ceara",
	"fla":                              "flamengo",
	"flu":                              "fluminense",
	"timao":                            "corinthians",
	"verdao":                           "palmeiras",
	"spfc":                             "sao paulo",
	"inter":                            "internacional",
	"galo":                             "atletico mg",
	"furacao":                          "atletico pr",
}

// TeamTokens returns the normalized token list for a team name.
func TeamTokens(name string) []string {
	s := Fold(name)
	if a, ok := nameAlias[strings.TrimSpace(s)]; ok {
		s = a
	}
	s = strings.Map(func(r rune) rune {
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			return r
		}
		return ' '
	}, s)
	if a, ok := nameAlias[strings.Join(strings.Fields(s), " ")]; ok {
		s = a
	}
	var toks []string
	for _, t := range strings.Fields(s) {
		if a, ok := tokenAlias[t]; ok {
			t = a
		}
		if fillerTokens[t] {
			continue
		}
		toks = append(toks, t)
	}
	return toks
}

// TeamKey is a canonical string for a team name.
func TeamKey(name string) string { return strings.Join(TeamTokens(name), " ") }

// TeamMatches reports whether team name (or key) matches the query: all query
// tokens must be present in the team tokens.
func teamKeyMatches(key string, query []string) bool {
	if len(query) == 0 {
		return false
	}
	have := strings.Fields(key)
	for _, q := range query {
		found := false
		for _, h := range have {
			if h == q {
				found = true
				break
			}
		}
		if !found {
			return false
		}
	}
	return true
}

// TeamMatches reports whether the raw team name matches a free-text query.
func TeamMatches(name, query string) bool {
	return teamKeyMatches(TeamKey(name), TeamTokens(query))
}

var brStates = map[string]bool{"ac": true, "al": true, "ap": true, "am": true, "ba": true, "ce": true,
	"df": true, "es": true, "go": true, "ma": true, "mt": true, "ms": true, "mg": true, "pa": true,
	"pb": true, "pr": true, "pe": true, "pi": true, "rj": true, "rn": true, "rs": true, "ro": true,
	"rr": true, "sc": true, "sp": true, "se": true, "to": true}

// DisplayName strips state suffixes like "-SP" or " - MG" for presentation,
// except where the state disambiguates (e.g. Atlético-MG vs Atlético-PR).
func DisplayName(name string) string {
	n := strings.TrimSpace(name)
	for _, sep := range []string{" - ", "-"} {
		if i := strings.LastIndex(n, sep); i > 0 {
			suf := strings.TrimSpace(n[i+len(sep):])
			if len(suf) == 2 && brStates[strings.ToLower(suf)] {
				base := strings.TrimSpace(n[:i])
				fb := Fold(base)
				if fb == "atletico" || fb == "athletico" || fb == "america" || fb == "botafogo" {
					return base + "-" + strings.ToUpper(suf)
				}
				return base
			}
		}
	}
	return n
}

// NormalizeCompetition maps a free-text competition name to a canonical one.
// Returns "" if empty or unknown.
func NormalizeCompetition(s string) string {
	f := Fold(strings.TrimSpace(s))
	switch {
	case f == "":
		return ""
	case strings.Contains(f, "liberta"):
		return CompLibertadores
	case strings.Contains(f, "copa do brasil") || strings.Contains(f, "brazilian cup") || f == "cup" || strings.Contains(f, "copa brasil"):
		return CompCopaDoBrasil
	case strings.Contains(f, "serie b"):
		return CompSerieB
	case strings.Contains(f, "serie c"):
		return CompSerieC
	case strings.Contains(f, "serie a") || strings.Contains(f, "brasileir") || strings.Contains(f, "league"):
		return CompSerieA
	}
	return s
}

// ParseDate handles ISO, ISO with time and Brazilian DD/MM/YYYY formats.
func ParseDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02T15:04:05", "2006-01-02", "02/01/2006", "2/1/2006", "02/01/2006 15:04"} {
		if t, err := time.Parse(layout, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("unrecognized date %q", s)
}

func atoi(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return -1
	}
	if n, err := strconv.Atoi(s); err == nil {
		return n
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return -1
}

// ---------- loading ----------

type csvRows struct {
	idx  map[string]int
	rows [][]string
}

func (c *csvRows) get(row []string, col string) string {
	i, ok := c.idx[col]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func readCSV(path string) (*csvRows, error) {
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
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	c := &csvRows{idx: map[string]int{}}
	for i, h := range header {
		h = strings.TrimPrefix(h, "\ufeff")
		c.idx[strings.TrimSpace(h)] = i
	}
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		c.rows = append(c.rows, row)
	}
	return c, nil
}

// LoadDB loads all six datasets from dir.
func LoadDB(dir string) (*DB, error) {
	db := &DB{Sources: map[string]int{}}
	loaders := []struct {
		file string
		fn   func(*csvRows) int
	}{
		{"Brasileirao_Matches.csv", db.loadBrasileirao},
		{"Brazilian_Cup_Matches.csv", db.loadCup},
		{"Libertadores_Matches.csv", db.loadLibertadores},
		{"BR-Football-Dataset.csv", db.loadBRFootball},
		{"novo_campeonato_brasileiro.csv", db.loadNovo},
		{"fifa_data.csv", db.loadFIFA},
	}
	for _, l := range loaders {
		c, err := readCSV(filepath.Join(dir, l.file))
		if err != nil {
			return nil, err
		}
		db.Sources[l.file] = l.fn(c)
	}
	return db, nil
}

func (db *DB) add(m *Match) bool {
	if m.HomeTeam == "" || m.AwayTeam == "" || m.HomeGoals < 0 || m.AwayGoals < 0 {
		return false
	}
	if m.Season == 0 && !m.Date.IsZero() {
		m.Season = m.Date.Year()
	}
	if m.HomeCorners == 0 && m.AwayCorners == 0 && m.Source != "BR-Football-Dataset.csv" {
		m.HomeCorners, m.AwayCorners, m.HomeShots, m.AwayShots, m.HomeAttacks, m.AwayAttacks = -1, -1, -1, -1, -1, -1
	}
	m.homeKey, m.awayKey = TeamKey(m.HomeTeam), TeamKey(m.AwayTeam)
	db.Matches = append(db.Matches, m)
	return true
}

func (db *DB) loadBrasileirao(c *csvRows) int {
	n := 0
	for _, r := range c.rows {
		d, _ := ParseDate(c.get(r, "datetime"))
		if db.add(&Match{Date: d, HomeTeam: c.get(r, "home_team"), AwayTeam: c.get(r, "away_team"),
			HomeGoals: atoi(c.get(r, "home_goal")), AwayGoals: atoi(c.get(r, "away_goal")),
			Season: atoi(c.get(r, "season")), Round: c.get(r, "round"), Competition: CompSerieA,
			Source: "Brasileirao_Matches.csv"}) {
			n++
		}
	}
	return n
}

func (db *DB) loadCup(c *csvRows) int {
	n := 0
	for _, r := range c.rows {
		d, _ := ParseDate(c.get(r, "datetime"))
		if db.add(&Match{Date: d, HomeTeam: c.get(r, "home_team"), AwayTeam: c.get(r, "away_team"),
			HomeGoals: atoi(c.get(r, "home_goal")), AwayGoals: atoi(c.get(r, "away_goal")),
			Season: atoi(c.get(r, "season")), Round: c.get(r, "round"), Competition: CompCopaDoBrasil,
			Source: "Brazilian_Cup_Matches.csv"}) {
			n++
		}
	}
	return n
}

func (db *DB) loadLibertadores(c *csvRows) int {
	n := 0
	for _, r := range c.rows {
		d, _ := ParseDate(c.get(r, "datetime"))
		if db.add(&Match{Date: d, HomeTeam: c.get(r, "home_team"), AwayTeam: c.get(r, "away_team"),
			HomeGoals: atoi(c.get(r, "home_goal")), AwayGoals: atoi(c.get(r, "away_goal")),
			Season: atoi(c.get(r, "season")), Round: c.get(r, "stage"), Competition: CompLibertadores,
			Source: "Libertadores_Matches.csv"}) {
			n++
		}
	}
	return n
}

func (db *DB) loadBRFootball(c *csvRows) int {
	n := 0
	for _, r := range c.rows {
		d, _ := ParseDate(c.get(r, "date"))
		comp := NormalizeCompetition(c.get(r, "tournament"))
		if db.add(&Match{Date: d, HomeTeam: c.get(r, "home"), AwayTeam: c.get(r, "away"),
			HomeGoals: atoi(c.get(r, "home_goal")), AwayGoals: atoi(c.get(r, "away_goal")),
			Competition: comp, Source: "BR-Football-Dataset.csv",
			HomeCorners: atoi(c.get(r, "home_corner")), AwayCorners: atoi(c.get(r, "away_corner")),
			HomeShots: atoi(c.get(r, "home_shots")), AwayShots: atoi(c.get(r, "away_shots")),
			HomeAttacks: atoi(c.get(r, "home_attack")), AwayAttacks: atoi(c.get(r, "away_attack"))}) {
			n++
		}
	}
	return n
}

func (db *DB) loadNovo(c *csvRows) int {
	n := 0
	for _, r := range c.rows {
		d, _ := ParseDate(c.get(r, "Data"))
		if db.add(&Match{Date: d, HomeTeam: c.get(r, "Equipe_mandante"), AwayTeam: c.get(r, "Equipe_visitante"),
			HomeGoals: atoi(c.get(r, "Gols_mandante")), AwayGoals: atoi(c.get(r, "Gols_visitante")),
			Season: atoi(c.get(r, "Ano")), Round: c.get(r, "Rodada"), Arena: c.get(r, "Arena"),
			Competition: CompSerieA, Source: "novo_campeonato_brasileiro.csv"}) {
			n++
		}
	}
	return n
}

func (db *DB) loadFIFA(c *csvRows) int {
	n := 0
	for _, r := range c.rows {
		p := &Player{ID: atoi(c.get(r, "ID")), Name: c.get(r, "Name"), Age: atoi(c.get(r, "Age")),
			Nationality: c.get(r, "Nationality"), Overall: atoi(c.get(r, "Overall")),
			Potential: atoi(c.get(r, "Potential")), Club: c.get(r, "Club"), Position: c.get(r, "Position"),
			Jersey: c.get(r, "Jersey Number"), Height: c.get(r, "Height"), Weight: c.get(r, "Weight"),
			Value: c.get(r, "Value"), Foot: c.get(r, "Preferred Foot"), Skills: map[string]int{}}
		if p.Name == "" {
			continue
		}
		for _, s := range skillCols {
			if v := atoi(c.get(r, s)); v >= 0 {
				p.Skills[s] = v
			}
		}
		p.clubKey = TeamKey(p.Club)
		p.nameKey = Fold(p.Name)
		db.Players = append(db.Players, p)
		n++
	}
	return n
}
