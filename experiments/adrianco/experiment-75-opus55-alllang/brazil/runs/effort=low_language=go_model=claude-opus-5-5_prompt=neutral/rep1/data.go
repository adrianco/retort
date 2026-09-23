package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// Competition names used across the dataset.
const (
	CompBrasileirao = "Brasileirão"
	CompCopaBrasil  = "Copa do Brasil"
	CompLibertad    = "Libertadores"
	CompSerieB      = "Série B"
	CompSerieC      = "Série C"
)

// Match is a single normalized match record from any source file.
type Match struct {
	Date        time.Time
	HasTime     bool
	Home, Away  string // display names as in source
	HomeKey     string // normalized team keys
	AwayKey     string
	HomeGoals   int
	AwayGoals   int
	Competition string
	Season      int
	Round       string // round number or stage
	Arena       string
	Source      string
	// Extended stats (BR-Football-Dataset); -1 when unknown.
	HomeCorners, AwayCorners, HomeShots, AwayShots, HomeAttacks, AwayAttacks int
}

// Player is a FIFA player record.
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
}

// DB holds all loaded data.
type DB struct {
	Matches []*Match
	Players []*Player
	// display name per team key (most common/nicest form seen)
	TeamNames map[string]string
	Files     map[string]int // rows loaded per file
}

var (
	suffixRe = regexp.MustCompile(`\s*(?:-|–)\s*([A-Za-z]{2})$`)
	parenRe  = regexp.MustCompile(`\s*\([^)]*\)`)
	spaceRe  = regexp.MustCompile(`\s+`)
	// generic club-type affixes such as "EC Bahia" or "Fortaleza FC"
	clubAffixRe = regexp.MustCompile(`^(ec|sc|cr|se|fc|ca|ac) | (fc|ec|sc|fbpa|ac)$`)
	stateRe     = regexp.MustCompile(` (AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO)$`)
)

// stripAccents removes diacritics: "São Paulo" -> "Sao Paulo".
var accentReplacer = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i", "ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u", "ç", "c", "ñ", "n",
	"Á", "A", "À", "A", "Â", "A", "Ã", "A", "Ä", "A", "É", "E", "È", "E", "Ê", "E", "Ë", "E",
	"Í", "I", "Ì", "I", "Î", "I", "Ï", "I", "Ó", "O", "Ò", "O", "Ô", "O", "Õ", "O", "Ö", "O",
	"Ú", "U", "Ù", "U", "Û", "U", "Ü", "U", "Ç", "C", "Ñ", "N")

func stripAccents(s string) string { return accentReplacer.Replace(s) }

// aliases map a normalized base name to a canonical key.
var aliases = map[string]string{
	"vasco da gama":                   "vasco",
	"cr vasco da gama":                "vasco",
	"red bull bragantino":             "bragantino",
	"rb bragantino":                   "bragantino",
	"athletico":                       "athletico paranaense",
	"atletico paranaense":             "athletico paranaense",
	"athletico-pr":                    "athletico paranaense",
	"atletico mineiro":                "atletico mineiro",
	"atletico goianiense":             "atletico goianiense",
	"sport recife":                    "sport",
	"sport club do recife":            "sport",
	"sport club corinthians paulista": "corinthians",
	"sc corinthians paulista":         "corinthians",
	"se palmeiras":                    "palmeiras",
	"sociedade esportiva palmeiras":   "palmeiras",
	"cr flamengo":                     "flamengo",
	"clube de regatas do flamengo":    "flamengo",
	"fluminense fc":                   "fluminense",
	"sao paulo fc":                    "sao paulo",
	"santos fc":                       "santos",
	"gremio fbpa":                     "gremio",
	"sc internacional":                "internacional",
	"cruzeiro ec":                     "cruzeiro",
	"botafogo fr":                     "botafogo",
	"america mineiro":                 "america mg",
	"america fc natal":                "america rn",
	"clube do remo":                   "remo",
	"ec vitoria":                      "vitoria",
	"ec bahia":                        "bahia",
	"ceara sc":                        "ceara",
	"fortaleza ec":                    "fortaleza",
	"coritiba fc":                     "coritiba",
	"goias ec":                        "goias",
}

// ambiguous bases need the state to disambiguate.
var ambiguous = map[string]map[string]string{
	"atletico": {"MG": "atletico mineiro", "PR": "athletico paranaense", "GO": "atletico goianiense", "": "atletico mineiro"},
	"america":  {"MG": "america mg", "RN": "america rn", "": "america mg"},
	"botafogo": {"RJ": "botafogo", "SP": "botafogo sp", "PB": "botafogo pb", "": "botafogo"},
	"flamengo": {"PI": "flamengo pi", "RJ": "flamengo", "": "flamengo"},
}

// NormalizeTeam converts any team name variant to a canonical key.
func NormalizeTeam(name string) string {
	s := strings.TrimSpace(stripAccents(name))
	s = parenRe.ReplaceAllString(s, "")
	s = strings.TrimSpace(s)
	state := ""
	if m := suffixRe.FindStringSubmatch(s); m != nil {
		state = strings.ToUpper(m[1])
		s = s[:len(s)-len(m[0])]
	} else if m := stateRe.FindStringSubmatch(s); m != nil {
		state = m[1]
		s = s[:len(s)-len(m[0])]
	}
	s = strings.ToLower(spaceRe.ReplaceAllString(strings.TrimSpace(s), " "))
	if a, ok := aliases[s]; ok {
		return a
	}
	s = clubAffixRe.ReplaceAllString(s, "")
	if st, ok := ambiguous[s]; ok {
		if k, ok := st[state]; ok {
			return k
		}
		return s + " " + strings.ToLower(state)
	}
	if a, ok := aliases[s]; ok {
		return a
	}
	return s
}

// ParseDate handles ISO, ISO with time and Brazilian DD/MM/YYYY formats.
func ParseDate(s string) (time.Time, bool, error) {
	s = strings.TrimSpace(s)
	for _, f := range []string{"2006-01-02 15:04:05", "2006-01-02T15:04:05", "2006-01-02 15:04"} {
		if t, err := time.Parse(f, s); err == nil {
			return t, true, nil
		}
	}
	for _, f := range []string{"2006-01-02", "02/01/2006", "2/1/2006"} {
		if t, err := time.Parse(f, s); err == nil {
			return t, false, nil
		}
	}
	return time.Time{}, false, fmt.Errorf("unrecognized date %q", s)
}

func atoi(s string) int {
	s = strings.TrimSpace(s)
	if i, err := strconv.Atoi(s); err == nil {
		return i
	}
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return -1
}

func readCSV(path string, fn func(rec map[string]string)) (int, error) {
	f, err := os.Open(path)
	if err != nil {
		return 0, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	hdr, err := r.Read()
	if err != nil {
		return 0, err
	}
	for i := range hdr {
		hdr[i] = strings.TrimSpace(strings.TrimPrefix(hdr[i], "\ufeff"))
	}
	n := 0
	for {
		row, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return n, fmt.Errorf("%s: %w", path, err)
		}
		rec := make(map[string]string, len(hdr))
		for i, h := range hdr {
			if i < len(row) {
				rec[h] = row[i]
			}
		}
		fn(rec)
		n++
	}
	return n, nil
}

// LoadDB loads all six CSV files from dir.
func LoadDB(dir string) (*DB, error) {
	db := &DB{TeamNames: map[string]string{}, Files: map[string]int{}}
	add := func(m *Match) {
		if m.HomeGoals < 0 || m.AwayGoals < 0 {
			return
		}
		m.HomeKey, m.AwayKey = NormalizeTeam(m.Home), NormalizeTeam(m.Away)
		db.noteName(m.HomeKey, m.Home)
		db.noteName(m.AwayKey, m.Away)
		db.Matches = append(db.Matches, m)
	}
	noStats := func(m *Match) *Match {
		m.HomeCorners, m.AwayCorners, m.HomeShots, m.AwayShots, m.HomeAttacks, m.AwayAttacks = -1, -1, -1, -1, -1, -1
		return m
	}
	type loader struct {
		file string
		fn   func(map[string]string)
	}
	loaders := []loader{
		{"Brasileirao_Matches.csv", func(r map[string]string) {
			d, ht, _ := ParseDate(r["datetime"])
			add(noStats(&Match{Date: d, HasTime: ht, Home: r["home_team"], Away: r["away_team"],
				HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]), Competition: CompBrasileirao,
				Season: atoi(r["season"]), Round: r["round"], Source: "Brasileirao_Matches.csv"}))
		}},
		{"Brazilian_Cup_Matches.csv", func(r map[string]string) {
			d, ht, _ := ParseDate(r["datetime"])
			add(noStats(&Match{Date: d, HasTime: ht, Home: r["home_team"], Away: r["away_team"],
				HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]), Competition: CompCopaBrasil,
				Season: atoi(r["season"]), Round: r["round"], Source: "Brazilian_Cup_Matches.csv"}))
		}},
		{"Libertadores_Matches.csv", func(r map[string]string) {
			d, ht, _ := ParseDate(r["datetime"])
			add(noStats(&Match{Date: d, HasTime: ht, Home: r["home_team"], Away: r["away_team"],
				HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]), Competition: CompLibertad,
				Season: atoi(r["season"]), Round: r["stage"], Source: "Libertadores_Matches.csv"}))
		}},
		{"BR-Football-Dataset.csv", func(r map[string]string) {
			d, _, _ := ParseDate(r["date"])
			comp := r["tournament"]
			switch comp {
			case "Serie A":
				comp = CompBrasileirao
			case "Serie B":
				comp = CompSerieB
			case "Serie C":
				comp = CompSerieC
			}
			add(&Match{Date: d, Home: r["home"], Away: r["away"],
				HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]), Competition: comp,
				Season: d.Year(), Source: "BR-Football-Dataset.csv",
				HomeCorners: atoi(r["home_corner"]), AwayCorners: atoi(r["away_corner"]),
				HomeShots: atoi(r["home_shots"]), AwayShots: atoi(r["away_shots"]),
				HomeAttacks: atoi(r["home_attack"]), AwayAttacks: atoi(r["away_attack"])})
		}},
		{"novo_campeonato_brasileiro.csv", func(r map[string]string) {
			d, _, _ := ParseDate(r["Data"])
			add(noStats(&Match{Date: d, Home: r["Equipe_mandante"], Away: r["Equipe_visitante"],
				HomeGoals: atoi(r["Gols_mandante"]), AwayGoals: atoi(r["Gols_visitante"]), Competition: CompBrasileirao,
				Season: atoi(r["Ano"]), Round: r["Rodada"], Arena: r["Arena"], Source: "novo_campeonato_brasileiro.csv"}))
		}},
		{"fifa_data.csv", func(r map[string]string) {
			p := &Player{ID: atoi(r["ID"]), Name: r["Name"], Age: atoi(r["Age"]), Nationality: r["Nationality"],
				Overall: atoi(r["Overall"]), Potential: atoi(r["Potential"]), Club: r["Club"], Position: r["Position"],
				Jersey: r["Jersey Number"], Height: r["Height"], Weight: r["Weight"], Value: r["Value"],
				Foot: r["Preferred Foot"], Skills: map[string]int{}}
			for _, k := range skillCols {
				if v := atoi(r[k]); v >= 0 {
					p.Skills[k] = v
				}
			}
			db.Players = append(db.Players, p)
		}},
	}
	for _, l := range loaders {
		n, err := readCSV(filepath.Join(dir, l.file), l.fn)
		if err != nil {
			return nil, err
		}
		db.Files[l.file] = n
	}
	return db, nil
}

var skillCols = []string{"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
	"Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions",
	"Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions",
	"Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle",
	"GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"}

// noteName records a display name for a key, preferring accented, suffix-free forms.
func (db *DB) noteName(key, raw string) {
	clean := strings.TrimSpace(parenRe.ReplaceAllString(raw, ""))
	if m := suffixRe.FindStringSubmatch(clean); m != nil && !ambiguousBase(clean[:len(clean)-len(m[0])]) {
		clean = strings.TrimSpace(clean[:len(clean)-len(m[0])])
	}
	cur, ok := db.TeamNames[key]
	if !ok || score(clean) > score(cur) {
		db.TeamNames[key] = clean
	}
}

func ambiguousBase(s string) bool {
	_, ok := ambiguous[strings.ToLower(stripAccents(strings.TrimSpace(s)))]
	return ok
}

func score(s string) int {
	n := 0
	if stripAccents(s) != s {
		n += 2
	}
	if len(s) < 25 {
		n++
	}
	return n
}

// displayNames gives canonical display names for common clubs.
var displayNames = map[string]string{
	"flamengo": "Flamengo", "fluminense": "Fluminense", "botafogo": "Botafogo", "vasco": "Vasco da Gama",
	"atletico mineiro": "Atlético Mineiro", "athletico paranaense": "Athletico Paranaense",
	"atletico goianiense": "Atlético Goianiense", "america mg": "América Mineiro", "america rn": "América-RN",
	"sao paulo": "São Paulo", "gremio": "Grêmio", "bragantino": "Red Bull Bragantino", "csa": "CSA",
	"sport": "Sport Recife", "botafogo sp": "Botafogo-SP", "botafogo pb": "Botafogo-PB", "flamengo pi": "Flamengo-PI",
}

// Name returns the display name for a team key.
func (db *DB) Name(key string) string {
	if n, ok := displayNames[key]; ok {
		return n
	}
	if n, ok := db.TeamNames[key]; ok {
		return n
	}
	return key
}
