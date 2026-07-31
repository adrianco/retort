// store.go holds the loaded datasets plus the indexes that keep lookups fast:
// matches by team, by competition and by competition+season, players by club,
// nationality, id and name token.
package soccer

import (
	"sort"
	"strings"
	"time"
)

// Store is the queryable, read-only view of every dataset.
type Store struct {
	DataDir      string
	Teams        *TeamRegistry
	Matches      []*Match
	Players      []*Player
	Graph        *Graph
	Datasets     []DatasetInfo
	Anomalies    []string // rows the loader refused to trust, reported by dataset_info
	LoadedAt     time.Time
	LoadDuration time.Duration

	matchByID     map[string]*Match
	byTeam        map[string][]*Match
	byComp        map[string][]*Match
	byCompSeason  map[compSeason][]*Match
	seasonsByComp map[string][]int

	playerByID    map[int]*Player
	playersByTeam map[string][]*Player
	playersByNat  map[string][]*Player
	playerTokens  map[string][]*Player

	standingsCacheFields
}

type compSeason struct {
	comp   string
	season int
}

func (s *Store) index() {
	s.matchByID = make(map[string]*Match, len(s.Matches))
	s.byTeam = make(map[string][]*Match, s.Teams.Len())
	s.byComp = map[string][]*Match{}
	s.byCompSeason = map[compSeason][]*Match{}
	s.seasonsByComp = map[string][]int{}

	teamSeasons := map[string]map[int]bool{}
	teamComps := map[string]map[string]bool{}
	seasonSeen := map[compSeason]bool{}

	for _, m := range s.Matches {
		s.matchByID[m.ID] = m
		s.byTeam[m.HomeTeamID] = append(s.byTeam[m.HomeTeamID], m)
		s.byTeam[m.AwayTeamID] = append(s.byTeam[m.AwayTeamID], m)
		s.byComp[m.CompetitionID] = append(s.byComp[m.CompetitionID], m)
		cs := compSeason{m.CompetitionID, m.Season}
		s.byCompSeason[cs] = append(s.byCompSeason[cs], m)
		if !seasonSeen[cs] {
			seasonSeen[cs] = true
			s.seasonsByComp[m.CompetitionID] = append(s.seasonsByComp[m.CompetitionID], m.Season)
		}
		for _, id := range []string{m.HomeTeamID, m.AwayTeamID} {
			if teamSeasons[id] == nil {
				teamSeasons[id] = map[int]bool{}
				teamComps[id] = map[string]bool{}
			}
			teamSeasons[id][m.Season] = true
			teamComps[id][m.CompetitionID] = true
		}
	}
	for comp := range s.seasonsByComp {
		sort.Ints(s.seasonsByComp[comp])
	}
	for _, t := range s.Teams.Teams() {
		t.Matches = len(s.byTeam[t.ID])
		for season := range teamSeasons[t.ID] {
			t.Seasons = append(t.Seasons, season)
		}
		sort.Ints(t.Seasons)
		for comp := range teamComps[t.ID] {
			t.CompIDs = append(t.CompIDs, comp)
		}
		sort.Strings(t.CompIDs)
	}

	s.playerByID = make(map[int]*Player, len(s.Players))
	s.playersByTeam = map[string][]*Player{}
	s.playersByNat = map[string][]*Player{}
	s.playerTokens = map[string][]*Player{}
	for _, p := range s.Players {
		s.playerByID[p.ID] = p
		if p.TeamID != "" {
			s.playersByTeam[p.TeamID] = append(s.playersByTeam[p.TeamID], p)
		}
		if p.Nationality != "" {
			s.playersByNat[Fold(p.Nationality)] = append(s.playersByNat[Fold(p.Nationality)], p)
		}
		for _, tok := range strings.Fields(nonAlnum.ReplaceAllString(Fold(p.Name), " ")) {
			s.playerTokens[tok] = append(s.playerTokens[tok], p)
		}
	}
	for _, t := range s.Teams.Teams() {
		t.Squad = len(s.playersByTeam[t.ID])
	}
}

// The accessors below hand out the store's own slices. The store is read-only
// once loaded and shared by concurrent tool calls, so callers must copy before
// sorting or otherwise modifying what they get back.

// Match returns a match by id.
func (s *Store) Match(id string) *Match { return s.matchByID[id] }

// CompetitionMatches returns every match of a competition.
func (s *Store) CompetitionMatches(comp string) []*Match { return s.byComp[comp] }

// SeasonMatches returns every match of one competition season.
func (s *Store) SeasonMatches(comp string, season int) []*Match {
	return s.byCompSeason[compSeason{comp, season}]
}

// Seasons lists the seasons available for a competition.
func (s *Store) Seasons(comp string) []int { return s.seasonsByComp[comp] }

// CompetitionsWithData returns the competitions that actually have matches.
func (s *Store) CompetitionsWithData() []Competition {
	var out []Competition
	for _, c := range Competitions() {
		if len(s.byComp[c.ID]) > 0 {
			out = append(out, c)
		}
	}
	return out
}

// Player returns a player by FIFA id.
func (s *Store) Player(id int) *Player { return s.playerByID[id] }

// PlayersForTeam returns the FIFA squad linked to a canonical team.
func (s *Store) PlayersForTeam(teamID string) []*Player { return s.playersByTeam[teamID] }

// PlayersByNationality returns every player of a nationality.
func (s *Store) PlayersByNationality(nat string) []*Player { return s.playersByNat[Fold(nat)] }

// Stats summarises what was loaded.
type Stats struct {
	Teams        int            `json:"teams"`
	Matches      int            `json:"matches"`
	Players      int            `json:"players"`
	Competitions int            `json:"competitions"`
	GraphNodes   int            `json:"graph_nodes"`
	GraphEdges   int            `json:"graph_edges"`
	LoadMillis   int64          `json:"load_ms"`
	PerComp      map[string]int `json:"matches_per_competition"`
}

// Summary reports load statistics.
func (s *Store) Summary() Stats {
	perComp := map[string]int{}
	for comp, ms := range s.byComp {
		perComp[comp] = len(ms)
	}
	st := Stats{
		Teams: s.Teams.Len(), Matches: len(s.Matches), Players: len(s.Players),
		Competitions: len(s.CompetitionsWithData()), PerComp: perComp,
		LoadMillis: s.LoadDuration.Milliseconds(),
	}
	if s.Graph != nil {
		st.GraphNodes, st.GraphEdges = s.Graph.Size()
	}
	return st
}

// DateRange returns the first and last match dates in the store.
func (s *Store) DateRange() (time.Time, time.Time) {
	if len(s.Matches) == 0 {
		return time.Time{}, time.Time{}
	}
	return s.Matches[0].Date, s.Matches[len(s.Matches)-1].Date
}

// sortSlice is a tiny generic helper used across the package.
func sortSlice[T any](s []T, less func(a, b T) bool) {
	sort.SliceStable(s, func(i, j int) bool { return less(s[i], s[j]) })
}
