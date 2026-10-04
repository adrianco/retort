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
	"unicode"

	"golang.org/x/text/unicode/norm"
)

// Competition identifiers.
const (
	CompBrasileirao = "Brasileirão"
	CompCopaBrasil  = "Copa do Brasil"
	CompLibertad    = "Libertadores"
	CompSerieB      = "Série B"
	CompSerieC      = "Série C"
)

// Source file identifiers.
const (
	SrcBrasileirao = "Brasileirao_Matches.csv"
	SrcCup         = "Brazilian_Cup_Matches.csv"
	SrcLib         = "Libertadores_Matches.csv"
	SrcBRFootball  = "BR-Football-Dataset.csv"
	SrcHistorical  = "novo_campeonato_brasileiro.csv"
	SrcFIFA        = "fifa_data.csv"
)

// Match is a single game from any match dataset.
type Match struct {
	Date        time.Time
	HomeTeam    string
	AwayTeam    string
	HomeKey     string
	AwayKey     string
	HomeGoals   int
	AwayGoals   int
	Season      int
	Competition string
	Round       string // round number or stage
	Arena       string
	Source      string
	// Extended stats (BR-Football dataset); -1 if unknown
	HomeCorners, AwayCorners, HomeShots, AwayShots int
}

// Player is a FIFA database entry.
type Player struct {
	ID          int
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	ClubKey     string
	Position    string
	Jersey      string
	Height      string
	Weight      string
	Value       string
	Foot        string
}

// DB holds all loaded data.
type DB struct {
	Matches []*Match
	Players []*Player
	// display name per team key
	TeamNames map[string]string
	Counts    map[string]int
	unique    []*Match
	brClubs   map[string]bool
}

var brStates = map[string]bool{}

func init() {
	for _, s := range strings.Fields("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO") {
		brStates[strings.ToLower(s)] = true
	}
}

// StripAccents removes diacritics and lowercases.
func StripAccents(s string) string {
	var b strings.Builder
	for _, r := range norm.NFD.String(s) {
		if unicode.Is(unicode.Mn, r) {
			continue
		}
		b.WriteRune(unicode.ToLower(r))
	}
	return b.String()
}

var teamAliases = map[string]string{
	"vasco da gama":                   "vasco",
	"vasco da gama rj":                "vasco",
	"sport recife":                    "sport",
	"sport club do recife":            "sport",
	"red bull bragantino":             "bragantino",
	"rb bragantino":                   "bragantino",
	"atletico paranaense":             "athletico paranaense",
	"athletico":                       "athletico paranaense",
	"atletico mineiro":                "atletico mineiro",
	"atletico goianiense":             "atletico goianiense",
	"america fc natal":                "america rn",
	"america mineiro":                 "america mg",
	"sport club corinthians paulista": "corinthians",
	"sc corinthians paulista":         "corinthians",
	"portuguesa desportos":            "portuguesa",
	"se palmeiras":                    "palmeiras",
	"sao paulo fc":                    "sao paulo",
	"santos fc":                       "santos",
	"cr flamengo":                     "flamengo",
	"clube de regatas do flamengo":    "flamengo",
	"fluminense fc":                   "fluminense",
	"gremio fbpa":                     "gremio",
	"gremio porto alegrense":          "gremio",
	"sc internacional":                "internacional",
	"cruzeiro ec":                     "cruzeiro",
	"botafogo fr":                     "botafogo",
	"ec bahia":                        "bahia",
	"ec vitoria":                      "vitoria",
	"fortaleza ec":                    "fortaleza",
	"fortaleza esporte clube":         "fortaleza",
	"ceara sc":                        "ceara",
	"ceara sporting club":             "ceara",
	"chapecoense af":                  "chapecoense",
	"goias ec":                        "goias",
	"coritiba fc":                     "coritiba",
	"avai fc":                         "avai",
	"cuiaba ec":                       "cuiaba",
	"juventude rs":                    "juventude",
	"ca paranaense":                   "athletico paranaense",
	"club athletico paranaense":       "athletico paranaense",
	"clube atletico mineiro":          "atletico mineiro",
	"ca mineiro":                      "atletico mineiro",
}

var clubTokens = map[string]bool{"ec": true, "fc": true, "sc": true, "ac": true, "cr": true, "se": true, "ca": true, "af": true, "fbpa": true, "esporte": true, "clube": true, "club": true, "futebol": true}

// Canonical display names for well-known clubs.
var displayNames = map[string]string{
	"sao paulo": "São Paulo", "gremio": "Grêmio", "atletico mineiro": "Atlético Mineiro", "athletico paranaense": "Athletico Paranaense",
	"atletico goianiense": "Atlético Goianiense", "america mg": "América Mineiro", "america rn": "América-RN", "botafogo": "Botafogo",
	"vasco": "Vasco da Gama", "ceara": "Ceará", "goias": "Goiás", "avai": "Avaí", "cuiaba": "Cuiabá", "criciuma": "Criciúma",
	"vitoria": "Vitória", "nautico": "Náutico", "parana": "Paraná", "sport": "Sport Recife", "bragantino": "Red Bull Bragantino",
	"csa": "CSA", "sao caetano": "São Caetano", "santo andre": "Santo André", "ceara sc": "Ceará",
}

// TeamKey normalizes a team name into a canonical key so that
// "Palmeiras-SP", "Palmeiras - SP" and "Palmeiras" all match.
func TeamKey(name string) string {
	s := StripAccents(strings.TrimSpace(name))
	// drop parenthesized parts
	for {
		i := strings.Index(s, "(")
		if i < 0 {
			break
		}
		j := strings.Index(s[i:], ")")
		if j < 0 {
			s = s[:i]
			break
		}
		s = s[:i] + " " + s[i+j+1:]
	}
	s = strings.Map(func(r rune) rune {
		if r == '-' || r == '.' || r == '/' || r == ',' {
			return ' '
		}
		return r
	}, s)
	f := strings.Fields(s)
	if len(f) == 0 {
		return ""
	}
	state := ""
	if len(f) > 1 && brStates[f[len(f)-1]] {
		state = f[len(f)-1]
		f = f[:len(f)-1]
	}
	base := strings.Join(f, " ")
	if a, ok := teamAliases[base]; ok {
		base = a
	} else {
		// drop generic club-type tokens ("EC Juventude", "Fortaleza FC")
		for len(f) > 1 && clubTokens[f[0]] {
			f = f[1:]
		}
		for len(f) > 1 && clubTokens[f[len(f)-1]] {
			f = f[:len(f)-1]
		}
		base = strings.Join(f, " ")
		if a, ok := teamAliases[base]; ok {
			base = a
		}
	}
	switch base {
	case "atletico", "athletico":
		switch state {
		case "mg":
			return "atletico mineiro"
		case "pr":
			return "athletico paranaense"
		case "go":
			return "atletico goianiense"
		case "":
			return "atletico"
		}
		return "atletico " + state
	case "america", "botafogo":
		if base == "botafogo" && (state == "rj" || state == "") {
			return "botafogo"
		}
		if state != "" {
			return base + " " + state
		}
	}
	return base
}

func displayName(name string) string {
	n := strings.TrimSpace(name)
	if i := strings.Index(n, "("); i > 0 {
		n = strings.TrimSpace(n[:i])
	}
	// strip trailing state suffix like "-SP" or " - SP"
	for _, sep := range []string{" - ", "-", " "} {
		if i := strings.LastIndex(n, sep); i > 0 {
			suf := n[i+len(sep):]
			if len(suf) == 2 && brStates[strings.ToLower(suf)] {
				b := StripAccents(n[:i])
				if b == "atletico" || b == "america" || b == "botafogo" {
					return n
				}
				return strings.TrimSpace(n[:i])
			}
		}
	}
	return n
}

// ParseDate handles ISO, ISO with time and Brazilian DD/MM/YYYY formats.
func ParseDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	for _, layout := range []string{"2006-01-02 15:04:05", "2006-01-02", "02/01/2006", "2/1/2006", "02/01/2006 15:04", "2006-01-02T15:04:05"} {
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
	if f, err := strconv.ParseFloat(s, 64); err == nil {
		return int(f)
	}
	return -1
}

func readCSV(path string) ([]map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	header, err := r.Read()
	if err != nil {
		return nil, err
	}
	for i := range header {
		header[i] = strings.TrimSpace(strings.TrimPrefix(header[i], "\ufeff"))
	}
	var rows []map[string]string
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("%s: %w", path, err)
		}
		m := make(map[string]string, len(header))
		for i, h := range header {
			if i < len(rec) {
				m[h] = rec[i]
			}
		}
		rows = append(rows, m)
	}
	return rows, nil
}

// LoadDB loads all six datasets from dir.
func LoadDB(dir string) (*DB, error) {
	db := &DB{TeamNames: map[string]string{}, Counts: map[string]int{}}
	type loader struct {
		file string
		fn   func(map[string]string) *Match
	}
	loaders := []loader{
		{SrcBrasileirao, func(r map[string]string) *Match {
			return &Match{HomeTeam: r["home_team"], AwayTeam: r["away_team"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]),
				Season: atoi(r["season"]), Round: r["round"], Competition: CompBrasileirao, Arena: "", Date: mustDate(r["datetime"])}
		}},
		{SrcCup, func(r map[string]string) *Match {
			return &Match{HomeTeam: r["home_team"], AwayTeam: r["away_team"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]),
				Season: atoi(r["season"]), Round: r["round"], Competition: CompCopaBrasil, Date: mustDate(r["datetime"])}
		}},
		{SrcLib, func(r map[string]string) *Match {
			return &Match{HomeTeam: r["home_team"], AwayTeam: r["away_team"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]),
				Season: atoi(r["season"]), Round: r["stage"], Competition: CompLibertad, Date: mustDate(r["datetime"])}
		}},
		{SrcHistorical, func(r map[string]string) *Match {
			return &Match{HomeTeam: r["Equipe_mandante"], AwayTeam: r["Equipe_visitante"], HomeGoals: atoi(r["Gols_mandante"]), AwayGoals: atoi(r["Gols_visitante"]),
				Season: atoi(r["Ano"]), Round: r["Rodada"], Competition: CompBrasileirao, Arena: r["Arena"], Date: mustDate(r["Data"])}
		}},
		{SrcBRFootball, func(r map[string]string) *Match {
			comp := map[string]string{"Serie A": CompBrasileirao, "Serie B": CompSerieB, "Serie C": CompSerieC, "Copa do Brasil": CompCopaBrasil}[r["tournament"]]
			if comp == "" {
				comp = r["tournament"]
			}
			d := mustDate(r["date"])
			return &Match{HomeTeam: r["home"], AwayTeam: r["away"], HomeGoals: atoi(r["home_goal"]), AwayGoals: atoi(r["away_goal"]),
				Season: d.Year(), Competition: comp, Date: d,
				HomeCorners: atoi(r["home_corner"]), AwayCorners: atoi(r["away_corner"]), HomeShots: atoi(r["home_shots"]), AwayShots: atoi(r["away_shots"])}
		}},
	}
	for _, l := range loaders {
		rows, err := readCSV(filepath.Join(dir, l.file))
		if err != nil {
			return nil, err
		}
		for _, r := range rows {
			m := l.fn(r)
			if m.HomeGoals < 0 || m.AwayGoals < 0 || m.HomeTeam == "" {
				continue
			}
			if l.file != SrcBRFootball {
				m.HomeCorners, m.AwayCorners, m.HomeShots, m.AwayShots = -1, -1, -1, -1
			}
			m.Source = l.file
			m.Round = strings.TrimSpace(m.Round)
			m.HomeKey, m.AwayKey = TeamKey(m.HomeTeam), TeamKey(m.AwayTeam)
			m.HomeTeam, m.AwayTeam = displayName(m.HomeTeam), displayName(m.AwayTeam)
			if d, ok := displayNames[m.HomeKey]; ok {
				m.HomeTeam = d
			}
			if d, ok := displayNames[m.AwayKey]; ok {
				m.AwayTeam = d
			}
			for _, p := range [][2]string{{m.HomeKey, m.HomeTeam}, {m.AwayKey, m.AwayTeam}} {
				// prefer accented display names
				if cur, ok := db.TeamNames[p[0]]; !ok || (cur == StripAccents(cur) && p[1] != StripAccents(p[1])) {
					db.TeamNames[p[0]] = p[1]
				}
			}
			db.Matches = append(db.Matches, m)
			db.Counts[l.file]++
		}
	}
	rows, err := readCSV(filepath.Join(dir, SrcFIFA))
	if err != nil {
		return nil, err
	}
	for _, r := range rows {
		p := &Player{ID: atoi(r["ID"]), Name: r["Name"], Age: atoi(r["Age"]), Nationality: r["Nationality"], Overall: atoi(r["Overall"]),
			Potential: atoi(r["Potential"]), Club: r["Club"], Position: r["Position"], Jersey: r["Jersey Number"], Height: r["Height"],
			Weight: r["Weight"], Value: r["Value"], Foot: r["Preferred Foot"]}
		if p.Club != "" {
			p.ClubKey = TeamKey(p.Club)
		}
		db.Players = append(db.Players, p)
	}
	db.Counts[SrcFIFA] = len(db.Players)
	sort.SliceStable(db.Matches, func(i, j int) bool { return db.Matches[i].Date.Before(db.Matches[j].Date) })
	return db, nil
}

func mustDate(s string) time.Time {
	t, _ := ParseDate(s)
	return t
}
