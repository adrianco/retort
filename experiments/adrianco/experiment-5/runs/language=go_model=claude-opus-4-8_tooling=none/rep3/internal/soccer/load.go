// Context: CSV loaders. Each of the six datasets has a different schema; the
// functions here translate every row into the shared Match/Player model and tag
// it with a canonical Competition and the originating Source file name. All
// reading is UTF-8 and tolerant of missing/garbage fields (bad rows are skipped
// rather than failing the whole load).
package soccer

import (
	"encoding/csv"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// Source file names (also used as Match.Source tags).
const (
	fileBrasileirao  = "Brasileirao_Matches.csv"
	fileCopaBrasil   = "Brazilian_Cup_Matches.csv"
	fileLibertadores = "Libertadores_Matches.csv"
	fileBRFootball   = "BR-Football-Dataset.csv"
	fileNovo         = "novo_campeonato_brasileiro.csv"
	filePlayers      = "fifa_data.csv"
)

// LoadStore reads every dataset under dir and returns a populated Store.
// Missing optional files are tolerated; a Store is always returned.
func LoadStore(dir string) (*Store, error) {
	s := &Store{}

	type loader struct {
		file string
		fn   func(string) ([]Match, error)
	}
	loaders := []loader{
		{fileBrasileirao, loadBrasileirao},
		{fileCopaBrasil, loadCopaBrasil},
		{fileLibertadores, loadLibertadores},
		{fileBRFootball, loadBRFootball},
		{fileNovo, loadNovo},
	}
	for _, l := range loaders {
		path := filepath.Join(dir, l.file)
		if _, err := os.Stat(path); err != nil {
			continue // optional file absent
		}
		ms, err := l.fn(path)
		if err != nil {
			return s, err
		}
		s.Matches = append(s.Matches, ms...)
	}

	playerPath := filepath.Join(dir, filePlayers)
	if _, err := os.Stat(playerPath); err == nil {
		ps, err := loadPlayers(playerPath)
		if err != nil {
			return s, err
		}
		s.Players = ps
	}

	s.index()
	return s, nil
}

// openCSV returns a csv.Reader configured to tolerate ragged rows and strips a
// leading UTF-8 BOM if present.
func openCSV(path string) (*csv.Reader, *os.File, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, nil, err
	}
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1 // allow ragged rows
	r.LazyQuotes = true
	r.ReuseRecord = true
	return r, f, nil
}

// header maps a CSV header row to column indexes by (BOM-trimmed) name.
func header(rec []string) map[string]int {
	h := make(map[string]int, len(rec))
	for i, name := range rec {
		name = strings.TrimPrefix(name, "\ufeff")
		h[strings.TrimSpace(name)] = i
	}
	return h
}

func get(rec []string, idx int) string {
	if idx < 0 || idx >= len(rec) {
		return ""
	}
	return strings.TrimSpace(rec[idx])
}

// atoi parses an int, tolerating floats like "2.0" and empty strings.
func atoi(s string) (int, bool) {
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

// dateLayouts covers the formats seen across the datasets.
var dateLayouts = []string{
	"2006-01-02 15:04:05",
	"2006-01-02",
	"02/01/2006",
	"2006-01-02T15:04:05",
}

// parseDate tries each known layout and returns the time plus a YYYY-MM-DD
// display string. ok is false if nothing parsed.
func parseDate(s string) (t time.Time, display string, ok bool) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, "", false
	}
	for _, layout := range dateLayouts {
		if t, err := time.Parse(layout, s); err == nil {
			return t, t.Format("2006-01-02"), true
		}
	}
	// Last resort: keep the raw string, no parsed time.
	return time.Time{}, s, false
}

// finalizeTeams fills the normalized keys and cleaned display names on a Match.
func finalizeTeams(m *Match, rawHome, rawAway string) {
	hd, hs := cleanTeamName(rawHome)
	ad, as := cleanTeamName(rawAway)
	m.HomeTeam, m.AwayTeam = hd, ad
	if m.HomeState == "" {
		m.HomeState = hs
	}
	if m.AwayState == "" {
		m.AwayState = as
	}
	m.HomeKey = normKey(rawHome)
	m.AwayKey = normKey(rawAway)
}

// --- individual dataset loaders -------------------------------------------

func loadBrasileirao(path string) ([]Match, error) {
	return loadMatchRows(path, func(h map[string]int, rec []string) (Match, bool) {
		m := Match{Competition: CompBrasileirao, Source: fileBrasileirao}
		m.HomeState = get(rec, h["home_team_state"])
		m.AwayState = get(rec, h["away_team_state"])
		finalizeTeams(&m, get(rec, h["home_team"]), get(rec, h["away_team"]))
		applyScore(&m, get(rec, h["home_goal"]), get(rec, h["away_goal"]))
		m.Season, _ = atoi(get(rec, h["season"]))
		m.Round = get(rec, h["round"])
		m.Date, m.DateStr, _ = parseDate(get(rec, h["datetime"]))
		if m.Season == 0 && !m.Date.IsZero() {
			m.Season = m.Date.Year()
		}
		return m, m.HomeKey != "" && m.AwayKey != ""
	})
}

func loadCopaBrasil(path string) ([]Match, error) {
	return loadMatchRows(path, func(h map[string]int, rec []string) (Match, bool) {
		m := Match{Competition: CompCopaBrasil, Source: fileCopaBrasil}
		finalizeTeams(&m, get(rec, h["home_team"]), get(rec, h["away_team"]))
		applyScore(&m, get(rec, h["home_goal"]), get(rec, h["away_goal"]))
		m.Season, _ = atoi(get(rec, h["season"]))
		m.Round = get(rec, h["round"])
		m.Stage = get(rec, h["round"])
		m.Date, m.DateStr, _ = parseDate(get(rec, h["datetime"]))
		if m.Season == 0 && !m.Date.IsZero() {
			m.Season = m.Date.Year()
		}
		return m, m.HomeKey != "" && m.AwayKey != ""
	})
}

func loadLibertadores(path string) ([]Match, error) {
	return loadMatchRows(path, func(h map[string]int, rec []string) (Match, bool) {
		m := Match{Competition: CompLibertadores, Source: fileLibertadores}
		finalizeTeams(&m, get(rec, h["home_team"]), get(rec, h["away_team"]))
		applyScore(&m, get(rec, h["home_goal"]), get(rec, h["away_goal"]))
		m.Season, _ = atoi(get(rec, h["season"]))
		m.Stage = get(rec, h["stage"])
		m.Date, m.DateStr, _ = parseDate(get(rec, h["datetime"]))
		if m.Season == 0 && !m.Date.IsZero() {
			m.Season = m.Date.Year()
		}
		return m, m.HomeKey != "" && m.AwayKey != ""
	})
}

// brFootballComp maps the tournament column to a canonical competition name.
func brFootballComp(t string) string {
	switch strings.ToLower(strings.TrimSpace(t)) {
	case "serie a":
		return CompBrasileirao
	case "serie b":
		return CompSerieB
	case "serie c":
		return CompSerieC
	case "copa do brasil":
		return CompCopaBrasil
	default:
		return strings.TrimSpace(t)
	}
}

func loadBRFootball(path string) ([]Match, error) {
	return loadMatchRows(path, func(h map[string]int, rec []string) (Match, bool) {
		m := Match{Source: fileBRFootball}
		m.Competition = brFootballComp(get(rec, h["tournament"]))
		finalizeTeams(&m, get(rec, h["home"]), get(rec, h["away"]))
		applyScore(&m, get(rec, h["home_goal"]), get(rec, h["away_goal"]))
		m.Date, m.DateStr, _ = parseDate(get(rec, h["date"]))
		if !m.Date.IsZero() {
			m.Season = m.Date.Year()
		}
		return m, m.HomeKey != "" && m.AwayKey != ""
	})
}

func loadNovo(path string) ([]Match, error) {
	return loadMatchRows(path, func(h map[string]int, rec []string) (Match, bool) {
		m := Match{Competition: CompBrasileirao, Source: fileNovo}
		m.HomeState = get(rec, h["Mandante_UF"])
		m.AwayState = get(rec, h["Visitante_UF"])
		finalizeTeams(&m, get(rec, h["Equipe_mandante"]), get(rec, h["Equipe_visitante"]))
		applyScore(&m, get(rec, h["Gols_mandante"]), get(rec, h["Gols_visitante"]))
		m.Season, _ = atoi(get(rec, h["Ano"]))
		m.Round = get(rec, h["Rodada"])
		m.Arena = get(rec, h["Arena"])
		m.Date, m.DateStr, _ = parseDate(get(rec, h["Data"]))
		if m.Season == 0 && !m.Date.IsZero() {
			m.Season = m.Date.Year()
		}
		return m, m.HomeKey != "" && m.AwayKey != ""
	})
}

func applyScore(m *Match, hg, ag string) {
	h, okH := atoi(hg)
	a, okA := atoi(ag)
	m.HomeGoal, m.AwayGoal = h, a
	m.HasScore = okH && okA
}

// loadMatchRows is the shared CSV-driving loop: it reads the header, then calls
// build for each data row, appending Matches for which build returns ok.
func loadMatchRows(path string, build func(h map[string]int, rec []string) (Match, bool)) ([]Match, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var h map[string]int
	var out []Match
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue // skip malformed line
		}
		if h == nil {
			h = header(rec)
			continue
		}
		if m, ok := build(h, rec); ok {
			out = append(out, m)
		}
	}
	return out, nil
}

func loadPlayers(path string) ([]Player, error) {
	r, f, err := openCSV(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var h map[string]int
	var out []Player
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		if h == nil {
			h = header(rec)
			continue
		}
		name := get(rec, h["Name"])
		if name == "" {
			continue
		}
		p := Player{Name: name}
		p.ID, _ = atoi(get(rec, h["ID"]))
		p.Age, _ = atoi(get(rec, h["Age"]))
		p.Nationality = get(rec, h["Nationality"])
		p.Overall, _ = atoi(get(rec, h["Overall"]))
		p.Potential, _ = atoi(get(rec, h["Potential"]))
		p.Club = get(rec, h["Club"])
		p.ClubKey = normKey(p.Club)
		p.Position = get(rec, h["Position"])
		p.Jersey = get(rec, h["Jersey Number"])
		p.Height = get(rec, h["Height"])
		p.Weight = get(rec, h["Weight"])
		p.Value = get(rec, h["Value"])
		p.Wage = get(rec, h["Wage"])
		p.PreferredFt = get(rec, h["Preferred Foot"])
		out = append(out, p)
	}
	return out, nil
}
