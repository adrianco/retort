package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"time"
	"unicode"
)

const (
	serieB           = "Brasileirão Série B"
	serieC           = "Brasileirão Série C"
	serieA           = "Brasileirão Série A"
	cup              = "Copa do Brasil"
	libertadores     = "Copa Libertadores"
	leagueFile       = "Brasileirao_Matches.csv"
	cupFile          = "Brazilian_Cup_Matches.csv"
	libertadoresFile = "Libertadores_Matches.csv"
	extendedFile     = "BR-Football-Dataset.csv"
	historyFile      = "novo_campeonato_brasileiro.csv"
	playerFile       = "fifa_data.csv"
)

type Match struct {
	Date             string            `json:"date"`
	Kickoff          string            `json:"kickoff,omitempty"`
	Home             string            `json:"home"`
	HomeState        string            `json:"home_state,omitempty"`
	AwayState        string            `json:"away_state,omitempty"`
	Away             string            `json:"away"`
	HomeGoals        *int              `json:"home_goals"`
	AwayGoals        *int              `json:"away_goals"`
	Competition      string            `json:"competition"`
	Season           int               `json:"season,omitempty"`
	Round            string            `json:"round,omitempty"`
	Stage            string            `json:"stage,omitempty"`
	HistoricalID     string            `json:"historical_id,omitempty"`
	Stadium          string            `json:"stadium,omitempty"`
	Stats            map[string]string `json:"statistics,omitempty"`
	Sources          []string          `json:"sources"`
	homeKey, awayKey string
}

func (m Match) played() bool { return m.HomeGoals != nil && m.AwayGoals != nil }

type Player struct {
	ID                               int               `json:"id"`
	Name                             string            `json:"name"`
	Age                              int               `json:"age"`
	Nationality                      string            `json:"nationality"`
	Club                             string            `json:"club"`
	Overall                          int               `json:"overall"`
	Potential                        int               `json:"potential"`
	Position                         string            `json:"position,omitempty"`
	Attributes                       map[string]string `json:"attributes,omitempty"`
	nameKey, nationalityKey, clubKey string
}

type Store struct {
	matches  []Match
	bySource map[string][]Match
	players  []Player
}

func words(s string) string {
	var b strings.Builder
	for _, r := range strings.ToLower(s) {
		switch {
		case strings.ContainsRune("áàâãä", r):
			r = 'a'
		case strings.ContainsRune("éèêë", r):
			r = 'e'
		case strings.ContainsRune("íìîï", r):
			r = 'i'
		case strings.ContainsRune("óòôõö", r):
			r = 'o'
		case strings.ContainsRune("úùûü", r):
			r = 'u'
		case r == 'ç':
			r = 'c'
		case unicode.Is(unicode.Mn, r):
			continue
		}
		if unicode.IsLetter(r) || unicode.IsDigit(r) {
			b.WriteRune(r)
		} else {
			b.WriteByte(' ')
		}
	}
	return strings.Join(strings.Fields(b.String()), " ")
}

var clubAliases = map[string]string{
	"america mg": "América-MG", "america rn": "América-RN", "america fc natal": "América-RN", "america fc minas gerais": "América-MG",
	"atletico mg": "Atlético Mineiro", "atletico mineiro": "Atlético Mineiro",
	"atletico go": "Atlético Goianiense", "atletico goianiense": "Atlético Goianiense",
	"atletico pr": "Athletico Paranaense", "athletico pr": "Athletico Paranaense",
	"atletico paranaense": "Athletico Paranaense", "athletico paranaense": "Athletico Paranaense", "athletico": "Athletico Paranaense",
	"botafogo": "Botafogo-RJ", "botafogo rj": "Botafogo-RJ", "botafogo sp": "Botafogo-SP", "botafogo pb": "Botafogo-PB",
	"sport club corinthians paulista": "Corinthians", "sc corinthians paulista": "Corinthians", "corinthians paulista": "Corinthians",
	"clube de regatas do flamengo": "Flamengo", "cr flamengo": "Flamengo",
	"fluminense football club": "Fluminense", "sociedade esportiva palmeiras": "Palmeiras", "se palmeiras": "Palmeiras",
	"sao paulo fc": "São Paulo", "sao paulo futebol clube": "São Paulo", "sao paulo": "São Paulo",
	"vasco": "Vasco da Gama", "vasco da gama": "Vasco da Gama", "cr vasco da gama": "Vasco da Gama",
	"sa cr vasco da gama": "Vasco da Gama", "sport recife": "Sport", "sport club do recife": "Sport",
	"ec bahia": "Bahia", "ec juventude": "Juventude", "fortaleza fc": "Fortaleza", "fortaleza esporte clube": "Fortaleza",
	"santa cruz fc": "Santa Cruz", "ca parana": "Paraná", "bragantino": "Red Bull Bragantino",
	"red bull bragantino": "Red Bull Bragantino", "bragantino pa": "Bragantino-PA",
	"santos fc": "Santos", "sc internacional": "Internacional", "gremio fbpa": "Grêmio",
	"gremio": "Grêmio", "avai": "Avaí", "goias": "Goiás", "ceara": "Ceará", "criciuma": "Criciúma",
	"cuiaba": "Cuiabá", "nautico": "Náutico", "nautico capibaribe": "Náutico", "ceara sporting club": "Ceará", "parana": "Paraná", "vitoria": "Vitória", "csa": "CSA",
}

var stateSuffix = regexp.MustCompile(`(?i)[ -]+(ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to)$`)

func clubName(s string) string {
	s = strings.TrimSpace(s)
	key := words(s)
	if name, ok := clubAliases[key]; ok {
		return name
	}
	if suffix := stateSuffix.FindStringSubmatchIndex(s); suffix != nil {
		base := strings.TrimSpace(s[:suffix[0]])
		baseKey := words(base)
		// These names are shared by clubs in different states.
		if slices.Contains([]string{"america", "atletico", "athletico", "botafogo", "bragantino", "sao jose", "operario", "nacional"}, baseKey) {
			return base + "-" + strings.ToUpper(s[suffix[2]:suffix[3]])
		}
		if name, ok := clubAliases[baseKey]; ok {
			return name
		}
		return base
	}
	return s
}

func competitionName(s string) string {
	switch words(s) {
	case "brasileirao", "serie a", "brasileirao serie a", "brasileirao a", "campeonato brasileiro", "campeonato brasileiro serie a":
		return serieA
	case "serie b", "brasileirao serie b":
		return serieB
	case "serie c", "brasileirao serie c":
		return serieC
	case "copa do brasil", "brazilian cup":
		return cup
	case "copa libertadores", "libertadores":
		return libertadores
	default:
		return strings.TrimSpace(s)
	}
}

func parseDate(s string) (time.Time, error) {
	for _, layout := range []string{time.RFC3339, "2006-01-02 15:04:05", time.DateOnly, "02/01/2006 15:04:05", "02/01/2006"} {
		if t, err := time.Parse(layout, strings.TrimSpace(s)); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("invalid date %q (use YYYY-MM-DD or DD/MM/YYYY)", s)
}

func number(s string) int {
	n, _ := strconv.Atoi(strings.TrimSpace(s))
	return n
}

func goals(s string) (*int, error) {
	if s == "" || s == "NA" || s == "-" {
		return nil, nil
	}
	n, err := strconv.Atoi(strings.TrimSuffix(s, ".0"))
	if err != nil || n < 0 {
		return nil, fmt.Errorf("invalid goal count %q", s)
	}
	return &n, nil
}

func readCSV(dir, file string, consume func(map[string]string) error) error {
	f, err := os.Open(filepath.Join(dir, file))
	if err != nil {
		return err
	}
	defer f.Close()
	r := csv.NewReader(f)
	header, err := r.Read()
	if err != nil {
		return fmt.Errorf("%s header: %w", file, err)
	}
	row := make(map[string]string, len(header))
	for record := 2; ; record++ {
		fields, err := r.Read()
		if err == io.EOF {
			return nil
		}
		if err == nil {
			for i, field := range fields {
				row[strings.TrimPrefix(header[i], "\ufeff")] = strings.TrimSpace(field)
			}
			err = consume(row)
		}
		if err != nil {
			return fmt.Errorf("%s record %d: %w", file, record, err)
		}
	}
}

func loadMatch(file string, row map[string]string) (Match, error) {
	m := Match{Sources: []string{file}}
	date, home, away, hg, ag := row["datetime"], row["home_team"], row["away_team"], row["home_goal"], row["away_goal"]
	m.Season, m.Round, m.Stage = number(row["season"]), row["round"], row["stage"]
	switch file {
	case leagueFile:
		m.Competition = serieA
		m.HomeState, m.AwayState = row["home_team_state"], row["away_team_state"]
	case cupFile:
		m.Competition = cup
	case libertadoresFile:
		m.Competition = libertadores
	case historyFile:
		m.Competition = serieA
		date, home, away, hg, ag = row["Data"], row["Equipe_mandante"], row["Equipe_visitante"], row["Gols_mandante"], row["Gols_visitante"]
		m.Season, m.Round, m.Stadium = number(row["Ano"]), row["Rodada"], row["Arena"]
		m.HomeState, m.AwayState, m.HistoricalID = row["Mandante_UF"], row["Visitante_UF"], row["ID"]
	case extendedFile:
		m.Competition = competitionName(row["tournament"])
		date, home, away = row["date"], row["home"], row["away"]
		m.Kickoff = row["time"]
		m.Stats = make(map[string]string)
		for _, key := range []string{"home_corner", "away_corner", "home_attack", "away_attack", "home_shots", "away_shots", "ht_diff", "at_diff", "ht_result", "at_result", "total_corners"} {
			if row[key] != "" {
				m.Stats[key] = strings.TrimSuffix(row[key], ".0")
			}
		}
	}
	if date != "" && date != "NA" {
		t, err := parseDate(date)
		if err != nil {
			return m, err
		}
		m.Date = t.Format(time.DateOnly)
		if strings.Contains(date, ":") {
			m.Kickoff = t.Format(time.TimeOnly)
		}
		if file == extendedFile {
			m.Season = t.Year()
			// These pandemic-delayed editions finished early in the following calendar year.
			if (m.Competition == serieA && m.Date >= "2021-01-01" && m.Date < "2021-03-01") ||
				((m.Competition == serieB || m.Competition == serieC) && m.Date >= "2021-01-01" && m.Date < "2021-02-01") {
				m.Season = 2020
			}
		}
	}
	if home == "" || away == "" || m.Competition == "" {
		return m, fmt.Errorf("missing team or competition")
	}
	m.Home, m.Away = clubName(home), clubName(away)
	m.homeKey, m.awayKey = words(m.Home), words(m.Away)
	var err error
	m.HomeGoals, err = goals(hg)
	if err != nil {
		return m, err
	}
	m.AwayGoals, err = goals(ag)
	return m, err
}

func loadStore(dir string) (*Store, error) {
	s := &Store{bySource: make(map[string][]Match)}
	for _, file := range []string{leagueFile, historyFile, cupFile, libertadoresFile, extendedFile} {
		err := readCSV(dir, file, func(row map[string]string) error {
			m, err := loadMatch(file, row)
			if err == nil {
				s.bySource[file] = append(s.bySource[file], m)
			}
			return err
		})
		if err != nil {
			return nil, err
		}
	}
	err := readCSV(dir, playerFile, func(row map[string]string) error {
		p := Player{
			ID: number(row["ID"]), Name: row["Name"], Age: number(row["Age"]),
			Nationality: row["Nationality"], Club: row["Club"], Overall: number(row["Overall"]),
			Potential: number(row["Potential"]), Position: row["Position"], Attributes: make(map[string]string),
		}
		if p.ID == 0 || p.Name == "" {
			return fmt.Errorf("missing player ID or name")
		}
		p.nameKey, p.nationalityKey, p.clubKey = words(p.Name), words(p.Nationality), words(clubName(p.Club))
		for key, value := range row {
			switch key {
			case "", "ID", "Name", "Age", "Nationality", "Club", "Overall", "Potential", "Position", "Photo", "Flag", "Club Logo":
			default:
				if value != "" {
					p.Attributes[key] = value
				}
			}
		}
		s.players = append(s.players, p)
		return nil
	})
	if err != nil {
		return nil, err
	}
	s.reconcileMatches()
	return s, nil
}
