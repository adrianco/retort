package loader

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"strconv"
	"strings"
	"time"

	"brazilian-soccer-mcp/pkg/data"
	"brazilian-soccer-mcp/pkg/datautil"
)

// Manager holds all loaded datasets and provides access to them.
type Manager struct {
	BrasileiraoMatches     []data.Match
	BrazilianCupMatches    []data.Match
	LibertadoresMatches    []data.Match
	BRFootballMatches      []data.Match
	NovoCampeonatoMatches  []data.Match
	Players                []data.Player
}

// NewManager creates an empty Manager.
func NewManager() *Manager {
	return &Manager{}
}

// LoadBrasileirao loads Brasileirao_Matches.csv
func (m *Manager) LoadBrasileirao(path string) error {
	recs, err := parseCSV(path)
	if err != nil {
		return err
	}
	matches := make([]data.Match, 0, len(recs))
	for i, r := range recs {
		m := parseBrasileiraoRow(r, i)
		matches = append(matches, m)
	}
	m.BrasileiraoMatches = matches
	return nil
}

// LoadBrazilianCup loads Brazilian_Cup_Matches.csv
func (m *Manager) LoadBrazilianCup(path string) error {
	recs, err := parseCSV(path)
	if err != nil {
		return err
	}
	matches := make([]data.Match, 0, len(recs))
	for i, r := range recs {
		m := parseBrazilianCupRow(r, i)
		matches = append(matches, m)
	}
	m.BrazilianCupMatches = matches
	return nil
}

// LoadLibertadores loads Libertadores_Matches.csv
func (m *Manager) LoadLibertadores(path string) error {
	recs, err := parseCSV(path)
	if err != nil {
		return err
	}
	matches := make([]data.Match, 0, len(recs))
	for i, r := range recs {
		m := parseLibertadoresRow(r, i)
		matches = append(matches, m)
	}
	m.LibertadoresMatches = matches
	return nil
}

// LoadBRFootball loads BR-Football-Dataset.csv
func (m *Manager) LoadBRFootball(path string) error {
	recs, err := parseCSV(path)
	if err != nil {
		return err
	}
	matches := make([]data.Match, 0, len(recs))
	for i, r := range recs {
		m := parseBRFootballRow(r, i)
		matches = append(matches, m)
	}
	m.BRFootballMatches = matches
	return nil
}

// LoadNovoCampeonato loads novo_campeonato_brasileiro.csv
func (m *Manager) LoadNovoCampeonato(path string) error {
	recs, err := parseCSV(path)
	if err != nil {
		return err
	}
	matches := make([]data.Match, 0, len(recs))
	for i, r := range recs {
		m := parseNovoCampeonatoRow(r, i)
		matches = append(matches, m)
	}
	m.NovoCampeonatoMatches = matches
	return nil
}

// LoadPlayers loads fifa_data.csv
func (m *Manager) LoadPlayers(path string) error {
	recs, err := parseFIFACSV(path)
	if err != nil {
		return err
	}
	players := make([]data.Player, 0, len(recs))
	for i, r := range recs {
		p := parsePlayerRow(r, i)
		players = append(players, p)
	}
	m.Players = players
	return nil
}

// AllMatches returns every match from all datasets, deduplicated by a composite key.
func (m *Manager) AllMatches() []data.Match {
	seen := make(map[string]bool)
	all := make([]data.Match, 0)
	for _, sm := range []struct{ src []data.Match; name string }{
		{m.BrasileiraoMatches, "brasileirao"},
		{m.BrazilianCupMatches, "brazilian_cup"},
		{m.LibertadoresMatches, "libertadores"},
		{m.BRFootballMatches, "br_football"},
		{m.NovoCampeonatoMatches, "novo_campeonato"},
	} {
		for _, match := range sm.src {
			key := matchKey(match)
			if !seen[key] {
				seen[key] = true
				match.Source = sm.name
				all = append(all, match)
			}
		}
	}
	return all
}

// AllMatchesBySource returns matches grouped by source dataset.
func (m *Manager) AllMatchesBySource() map[string][]data.Match {
	result := map[string][]data.Match{}
	for _, match := range m.BrasileiraoMatches {
		result["brasileirao"] = append(result["brasileirao"], match)
	}
	for _, match := range m.BrazilianCupMatches {
		result["brazilian_cup"] = append(result["brazilian_cup"], match)
	}
	for _, match := range m.LibertadoresMatches {
		result["libertadores"] = append(result["libertadores"], match)
	}
	for _, match := range m.BRFootballMatches {
		result["br_football"] = append(result["br_football"], match)
	}
	for _, match := range m.NovoCampeonatoMatches {
		result["novo_campeonato"] = append(result["novo_campeonato"], match)
	}
	return result
}

// TotalMatchCount returns the total number of loaded matches.
func (m *Manager) TotalMatchCount() int {
	return len(m.BrasileiraoMatches) + len(m.BrazilianCupMatches) +
		len(m.LibertadoresMatches) + len(m.BRFootballMatches) +
		len(m.NovoCampeonatoMatches)
}

// TotalPlayerCount returns the number of loaded players.
func (m *Manager) TotalPlayerCount() int {
	return len(m.Players)
}

// DataSourceInfo returns information about each dataset.
func (m *Manager) DataSourceInfo() map[string]int {
	return map[string]int{
		"brasileirao_matches":     len(m.BrasileiraoMatches),
		"brazilian_cup_matches":   len(m.BrazilianCupMatches),
		"libertadores_matches":    len(m.LibertadoresMatches),
		"br_football_matches":     len(m.BRFootballMatches),
		"novo_campeonato_matches": len(m.NovoCampeonatoMatches),
		"fifa_players":            len(m.Players),
	}
}

func matchKey(m data.Match) string {
	ht := datautil.NormalizeTeam(m.HomeTeam)
	at := datautil.NormalizeTeam(m.AwayTeam)
	return fmt.Sprintf("%s_%s_%d_%d_%s", ht, at, m.Season, m.Round, m.Date)
}

// parseCSV is a generic CSV reader.
func parseCSV(path string) ([][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()
	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	reader.TrimLeadingSpace = true
	reader.FieldsPerRecord = -1 // allow variable fields

	var records [][]string
	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			// skip bad rows
			continue
		}
		records = append(records, row)
	}
	return records, nil
}

// parseFIFACSV reads the FIFA player CSV which has a BOM and complex headers.
func parseFIFACSV(path string) ([][]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", path, err)
	}
	defer f.Close()

	// Create a custom reader to strip BOM
	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	reader.TrimLeadingSpace = true
	reader.FieldsPerRecord = -1

	// Read header to check for BOM
	header, err := reader.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}
	// If first field has BOM, strip it
	if len(header) > 0 && len(header[0]) > 0 && header[0][0] == 0xEF && len(header[0]) >= 3 && header[0][1] == 0xBB && header[0][2] == 0xBF {
		header[0] = header[0][3:]
	}

	var records [][]string
	records = append(records, header)

	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}
		records = append(records, row)
	}
	return records, nil
}

func parseBrasileiraoRow(r []string, idx int) data.Match {
	m := data.Match{Source: "Brasileirao_Matches.csv", ID: fmt.Sprintf("b%d", idx)}
	if len(r) < 8 {
		return m
	}
	// datetime,"home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
	if dt, err := parseDateTime(r[0]); err == nil {
		m.DateTime = dt
		m.Date = dt.Format("2006-01-02")
		m.Time = dt.Format("15:04:05")
	}
	m.HomeTeam = unquote(r[1])
	m.HomeTeamState = unquote(r[2])
	m.AwayTeam = unquote(r[3])
	m.AwayTeamState = unquote(r[4])
	m.HomeGoals = parseInt(r[5])
	m.AwayGoals = parseInt(r[6])
	m.Season = parseInt(r[7])
	if len(r) > 8 {
		m.Round = parseInt(r[8])
	}
	return m
}

func parseBrazilianCupRow(r []string, idx int) data.Match {
	m := data.Match{Source: "Brazilian_Cup_Matches.csv", ID: fmt.Sprintf("bc%d", idx)}
	if len(r) < 7 {
		return m
	}
	// round,datetime,"home_team","away_team","home_goal","away_goal","season"
	if len(r) > 0 {
		m.Round = parseInt(r[0])
	}
	if dt, err := parseDateTime(r[1]); err == nil {
		m.DateTime = dt
		m.Date = dt.Format("2006-01-02")
		m.Time = dt.Format("15:04:05")
	}
	m.HomeTeam = unquote(r[2])
	m.AwayTeam = unquote(r[3])
	m.HomeGoals = parseInt(r[4])
	m.AwayGoals = parseInt(r[5])
	m.Season = parseInt(r[6])
	return m
}

func parseLibertadoresRow(r []string, idx int) data.Match {
	m := data.Match{Source: "Libertadores_Matches.csv", ID: fmt.Sprintf("l%d", idx)}
	if len(r) < 7 {
		return m
	}
	// datetime,"home_team","away_team","home_goal","away_goal","season","stage"
	if dt, err := parseDateTime(r[0]); err == nil {
		m.DateTime = dt
		m.Date = dt.Format("2006-01-02")
		m.Time = dt.Format("15:04:05")
	}
	m.HomeTeam = unquote(r[1])
	m.AwayTeam = unquote(r[2])
	m.HomeGoals = parseInt(r[3])
	m.AwayGoals = parseInt(r[4])
	m.Season = parseInt(r[5])
	m.Stage = unquote(r[6])
	return m
}

func parseBRFootballRow(r []string, idx int) data.Match {
	m := data.Match{Source: "BR-Football-Dataset.csv", ID: fmt.Sprintf("bf%d", idx)}
	if len(r) < 17 {
		return m
	}
	// tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
	m.Tournament = unquote(r[0])
	m.HomeTeam = unquote(r[1])
	m.HomeGoals = int(parseFloat(r[2]))
	m.AwayGoals = int(parseFloat(r[3]))
	m.AwayTeam = unquote(r[4])
	m.HomeCorners = parseFloat(r[5])
	m.AwayCorners = parseFloat(r[6])
	m.HomeAttacks = parseFloat(r[7])
	m.AwayAttacks = parseFloat(r[8])
	m.HomeShots = parseFloat(r[9])
	m.AwayShots = parseFloat(r[10])
	m.Time = unquote(r[11])
	m.Date = unquote(r[12])
	m.HTResult = unquote(r[15])
	m.ATResult = unquote(r[16])
	m.TotalCorners = parseFloat(r[17])
	// Try to parse date as ISO
	if dt, err := time.Parse("2006-01-02", m.Date); err == nil {
		m.DateTime = dt
	}
	return m
}

func parseNovoCampeonatoRow(r []string, idx int) data.Match {
	m := data.Match{Source: "novo_campeonato_brasileiro.csv", ID: unquote(r[0])}
	if len(r) < 13 {
		return m
	}
	// ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
	// Data format: 29/03/2003
	if dt, err := parseBrazilianDate(unquote(r[1])); err == nil {
		m.DateTime = dt
		m.Date = dt.Format("2006-01-02")
	}
	m.Season = parseInt(r[2])
	m.Round = parseInt(r[3])
	m.HomeTeam = unquote(r[4])
	m.AwayTeam = unquote(r[5])
	m.HomeGoals = parseInt(r[6])
	m.AwayGoals = parseInt(r[7])
	m.HomeTeamState = unquote(r[8])
	m.AwayTeamState = unquote(r[9])
	m.Winner = unquote(r[10])
	m.Stadium = unquote(r[11])
	return m
}

func parsePlayerRow(r []string, idx int) data.Player {
	p := data.Player{ID: idx}
	if len(r) < 40 {
		return p
	}
	// First column might have BOM - the actual header row is:
	// empty,ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight,LS,ST,RS,LW,LF,CF,RF,RW,LAM,CAM,RAM,LM,LCM,CM,RCM,RM,LWB,LDM,CDM,RDM,RWB,LB,LCB,CB,RCB,RB,Crossing,Finishing,HeadingAccuracy,ShortPassing,Volleys,Dribbling,Curve,FKAccuracy,LongPassing,BallControl,Acceleration,SprintSpeed,Agility,Reactions,Balance,ShotPower,Jumping,Stamina,Strength,LongShots,Aggression,Interceptions,Positioning,Vision,Penalties,Composure,Marking,StandingTackle,SlidingTackle,GKDiving,GKHandling,GKKicking,GKPositioning,GKReflexes,Release Clause

	p.ID = parseInt(r[1])
	p.Name = unquote(r[2])
	p.Age = parseInt(r[3])
	p.Nationality = unquote(r[5])
	p.Overall = parseInt(r[7])
	p.Potential = parseInt(r[8])
	p.Club = unquote(r[9])
	p.Position = unquote(r[20])
	if len(r) > 22 {
		p.JerseyNumber = unquote(r[22])
	}
	if len(r) > 25 {
		p.Height = unquote(r[26])
	}
	if len(r) > 27 {
		p.Weight = unquote(r[27])
	}
	if len(r) > 19 {
		p.SkillMoves = unquote(r[18])
	}
	if len(r) > 14 {
		p.PreferredFoot = unquote(r[14])
	}
	if len(r) > 18 {
		p.WorkRate = unquote(r[18])
	}
	p.Special = parseInt(r[13])
	p.InternationalReputation = parseInt(r[15])
	p.WeakFoot = parseInt(r[16])
	return p
}

func unquote(s string) string {
	if len(s) >= 2 && s[0] == '"' && s[len(s)-1] == '"' {
		return s[1 : len(s)-1]
	}
	return s
}

func parseInt(s string) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	v, err := strconv.Atoi(s)
	if err != nil {
		return 0
	}
	return v
}

func parseFloat(s string) float64 {
	s = strings.TrimSpace(s)
	if s == "" {
		return 0
	}
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0
	}
	return math.Round(v*100) / 100
}

func parseDateTime(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	formats := []string{
		"2006-01-02 15:04:05",
		"2006-01-02T15:04:05",
		"2006-01-02",
		"02/01/2006 15:04:05",
		"02/01/2006",
	}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("cannot parse datetime: %s", s)
}

func parseBrazilianDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	if t, err := time.Parse("02/01/2006", s); err == nil {
		return t, nil
	}
	return time.Time{}, fmt.Errorf("cannot parse brazilian date: %s", s)
}
