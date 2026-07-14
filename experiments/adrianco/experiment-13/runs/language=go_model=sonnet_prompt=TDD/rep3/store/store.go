package store

import (
	"math"
	"path/filepath"
	"sort"
	"strings"

	"brazilian-soccer-mcp/loader"
)

// MatchSummary is a normalized, competition-agnostic view of a match.
type MatchSummary struct {
	Competition string
	Season      int
	HomeTeam    string
	AwayTeam    string
	HomeGoal    int
	AwayGoal    int
	GoalDiff    int
	Date        string // ISO string
}

// HeadToHeadResult holds head-to-head statistics between two teams.
type HeadToHeadResult struct {
	Team1     string
	Team2     string
	Team1Wins int
	Team2Wins int
	Draws     int
	Total     int
}

// TeamRecord holds a team's season statistics.
type TeamRecord struct {
	Team   string
	Season int
	Played int
	Wins   int
	Draws  int
	Losses int
	GF     int
	GA     int
	Points int
}

// StandingEntry holds one team's position in the league table.
type StandingEntry struct {
	Position int
	Team     string
	Played   int
	Wins     int
	Draws    int
	Losses   int
	GF       int
	GA       int
	GD       int
	Points   int
}

// Store holds all loaded data.
type Store struct {
	Brasileirao  []loader.BrasileiraoMatch
	Cup          []loader.CupMatch
	Libertadores []loader.LibertadoresMatch
	Extended     []loader.ExtendedMatch
	Historical   []loader.HistoricalMatch
	Players      []loader.Player

	// Derived normalized list of all Brasileirao-style matches for fast lookup
	all []MatchSummary
}

// New loads all CSVs from dataDir and returns a populated Store.
func New(dataDir string) (*Store, error) {
	br, err := loader.LoadBrasileiraoMatches(filepath.Join(dataDir, "Brasileirao_Matches.csv"))
	if err != nil {
		return nil, err
	}
	cup, err := loader.LoadCupMatches(filepath.Join(dataDir, "Brazilian_Cup_Matches.csv"))
	if err != nil {
		return nil, err
	}
	lib, err := loader.LoadLibertadoresMatches(filepath.Join(dataDir, "Libertadores_Matches.csv"))
	if err != nil {
		return nil, err
	}
	ext, err := loader.LoadExtendedMatches(filepath.Join(dataDir, "BR-Football-Dataset.csv"))
	if err != nil {
		return nil, err
	}
	hist, err := loader.LoadHistoricalMatches(filepath.Join(dataDir, "novo_campeonato_brasileiro.csv"))
	if err != nil {
		return nil, err
	}
	players, err := loader.LoadPlayers(filepath.Join(dataDir, "fifa_data.csv"))
	if err != nil {
		return nil, err
	}

	s := &Store{
		Brasileirao:  br,
		Cup:          cup,
		Libertadores: lib,
		Extended:     ext,
		Historical:   hist,
		Players:      players,
	}
	s.buildIndex()
	return s, nil
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func (s *Store) buildIndex() {
	for _, m := range s.Brasileirao {
		diff := m.HomeGoal - m.AwayGoal
		s.all = append(s.all, MatchSummary{
			Competition: "Brasileirao Serie A",
			Season:      m.Season,
			HomeTeam:    loader.NormalizeTeamName(m.HomeTeam),
			AwayTeam:    loader.NormalizeTeamName(m.AwayTeam),
			HomeGoal:    m.HomeGoal,
			AwayGoal:    m.AwayGoal,
			GoalDiff:    abs(diff),
			Date:        m.Datetime.Format("2006-01-02"),
		})
	}
	for _, m := range s.Cup {
		diff := m.HomeGoal - m.AwayGoal
		s.all = append(s.all, MatchSummary{
			Competition: "Copa do Brasil",
			Season:      m.Season,
			HomeTeam:    loader.NormalizeTeamName(m.HomeTeam),
			AwayTeam:    loader.NormalizeTeamName(m.AwayTeam),
			HomeGoal:    m.HomeGoal,
			AwayGoal:    m.AwayGoal,
			GoalDiff:    abs(diff),
			Date:        m.Datetime.Format("2006-01-02"),
		})
	}
	for _, m := range s.Libertadores {
		diff := m.HomeGoal - m.AwayGoal
		s.all = append(s.all, MatchSummary{
			Competition: "Copa Libertadores",
			Season:      m.Season,
			HomeTeam:    loader.NormalizeTeamName(m.HomeTeam),
			AwayTeam:    loader.NormalizeTeamName(m.AwayTeam),
			HomeGoal:    m.HomeGoal,
			AwayGoal:    m.AwayGoal,
			GoalDiff:    abs(diff),
			Date:        m.Datetime.Format("2006-01-02"),
		})
	}
	for _, m := range s.Historical {
		diff := m.HomeGoals - m.AwayGoals
		s.all = append(s.all, MatchSummary{
			Competition: "Brasileirao (Historical)",
			Season:      m.Year,
			HomeTeam:    loader.NormalizeTeamName(m.HomeTeam),
			AwayTeam:    loader.NormalizeTeamName(m.AwayTeam),
			HomeGoal:    m.HomeGoals,
			AwayGoal:    m.AwayGoals,
			GoalDiff:    abs(diff),
			Date:        m.Date.Format("2006-01-02"),
		})
	}
}

func normContains(name, query string) bool {
	return strings.Contains(
		strings.ToLower(loader.NormalizeTeamName(name)),
		strings.ToLower(query),
	)
}

// FindMatchesByTeam returns all matches from the unified index where team participates.
func (s *Store) FindMatchesByTeam(team string) []MatchSummary {
	q := strings.ToLower(team)
	var out []MatchSummary
	for _, m := range s.all {
		if strings.Contains(strings.ToLower(m.HomeTeam), q) ||
			strings.Contains(strings.ToLower(m.AwayTeam), q) {
			out = append(out, m)
		}
	}
	return out
}

// FindMatchesBySeason returns all Brasileirão matches in a given season.
func (s *Store) FindMatchesBySeason(season int) []MatchSummary {
	var out []MatchSummary
	for _, m := range s.all {
		if m.Season == season && m.Competition == "Brasileirao Serie A" {
			out = append(out, m)
		}
	}
	return out
}

// HeadToHead returns head-to-head stats between two teams across all competitions.
func (s *Store) HeadToHead(team1, team2 string) HeadToHeadResult {
	q1 := strings.ToLower(team1)
	q2 := strings.ToLower(team2)
	result := HeadToHeadResult{Team1: team1, Team2: team2}
	for _, m := range s.all {
		h := strings.ToLower(m.HomeTeam)
		a := strings.ToLower(m.AwayTeam)
		match1 := (strings.Contains(h, q1) && strings.Contains(a, q2))
		match2 := (strings.Contains(h, q2) && strings.Contains(a, q1))
		if !match1 && !match2 {
			continue
		}
		result.Total++
		if m.HomeGoal > m.AwayGoal {
			if match1 {
				result.Team1Wins++
			} else {
				result.Team2Wins++
			}
		} else if m.AwayGoal > m.HomeGoal {
			if match1 {
				result.Team2Wins++
			} else {
				result.Team1Wins++
			}
		} else {
			result.Draws++
		}
	}
	return result
}

// TeamStats returns win/loss/draw for a team in a given Brasileirão season.
func (s *Store) TeamStats(team string, season int) TeamRecord {
	q := strings.ToLower(team)
	rec := TeamRecord{Team: team, Season: season}
	for _, m := range s.all {
		if m.Season != season {
			continue
		}
		h := strings.ToLower(m.HomeTeam)
		a := strings.ToLower(m.AwayTeam)
		isHome := strings.Contains(h, q)
		isAway := strings.Contains(a, q)
		if !isHome && !isAway {
			continue
		}
		rec.Played++
		if isHome {
			rec.GF += m.HomeGoal
			rec.GA += m.AwayGoal
			if m.HomeGoal > m.AwayGoal {
				rec.Wins++
			} else if m.HomeGoal == m.AwayGoal {
				rec.Draws++
			} else {
				rec.Losses++
			}
		} else {
			rec.GF += m.AwayGoal
			rec.GA += m.HomeGoal
			if m.AwayGoal > m.HomeGoal {
				rec.Wins++
			} else if m.HomeGoal == m.AwayGoal {
				rec.Draws++
			} else {
				rec.Losses++
			}
		}
	}
	rec.Points = rec.Wins*3 + rec.Draws
	return rec
}

// FindPlayersByName returns players whose name contains the query (case-insensitive).
func (s *Store) FindPlayersByName(name string) []loader.Player {
	q := strings.ToLower(name)
	var out []loader.Player
	for _, p := range s.Players {
		if strings.Contains(strings.ToLower(p.Name), q) {
			out = append(out, p)
		}
	}
	return out
}

// FindPlayersByNationality returns players with exact nationality match.
func (s *Store) FindPlayersByNationality(nationality string) []loader.Player {
	var out []loader.Player
	for _, p := range s.Players {
		if strings.EqualFold(p.Nationality, nationality) {
			out = append(out, p)
		}
	}
	return out
}

// FindPlayersByClub returns players whose club name contains the query.
func (s *Store) FindPlayersByClub(club string) []loader.Player {
	q := strings.ToLower(club)
	var out []loader.Player
	for _, p := range s.Players {
		if strings.Contains(strings.ToLower(p.Club), q) {
			out = append(out, p)
		}
	}
	return out
}

// LeagueStandings computes the final standings for a Brasileirão season
// from the Brasileirao dataset (most complete for season standings).
func (s *Store) LeagueStandings(season int) []StandingEntry {
	table := map[string]*StandingEntry{}
	for _, m := range s.Brasileirao {
		if m.Season != season {
			continue
		}
		home := loader.NormalizeTeamName(m.HomeTeam)
		away := loader.NormalizeTeamName(m.AwayTeam)
		if _, ok := table[home]; !ok {
			table[home] = &StandingEntry{Team: home}
		}
		if _, ok := table[away]; !ok {
			table[away] = &StandingEntry{Team: away}
		}
		h := table[home]
		a := table[away]
		h.Played++
		a.Played++
		h.GF += m.HomeGoal
		h.GA += m.AwayGoal
		a.GF += m.AwayGoal
		a.GA += m.HomeGoal
		if m.HomeGoal > m.AwayGoal {
			h.Wins++
			a.Losses++
		} else if m.HomeGoal < m.AwayGoal {
			a.Wins++
			h.Losses++
		} else {
			h.Draws++
			a.Draws++
		}
	}
	standings := make([]StandingEntry, 0, len(table))
	for _, e := range table {
		e.Points = e.Wins*3 + e.Draws
		e.GD = e.GF - e.GA
		standings = append(standings, *e)
	}
	sort.Slice(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].Wins != standings[j].Wins {
			return standings[i].Wins > standings[j].Wins
		}
		return standings[i].GD > standings[j].GD
	})
	for i := range standings {
		standings[i].Position = i + 1
	}
	return standings
}

// BiggestWins returns the top N matches by goal difference across all competitions.
func (s *Store) BiggestWins(n int) []MatchSummary {
	sorted := make([]MatchSummary, len(s.all))
	copy(sorted, s.all)
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].GoalDiff > sorted[j].GoalDiff
	})
	if n > len(sorted) {
		n = len(sorted)
	}
	return sorted[:n]
}

// AverageGoalsPerMatch returns the average total goals per match across all data.
func (s *Store) AverageGoalsPerMatch() float64 {
	if len(s.all) == 0 {
		return 0
	}
	total := 0
	for _, m := range s.all {
		total += m.HomeGoal + m.AwayGoal
	}
	avg := float64(total) / float64(len(s.all))
	return math.Round(avg*100) / 100
}
