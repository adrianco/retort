// Context: the in-memory Store and the query-parameter / result types used by
// the query engine (query.go) and the MCP tools (mcp.go). Lookups are linear
// scans over the loaded slices, which is well within the performance budget
// (~25k matches, ~18k players) stated in TASK.md.
package soccer

import (
	"sort"
	"strings"
	"time"
)

// Store holds every loaded Match and Player.
type Store struct {
	Matches []Match
	Players []Player

	teamNames map[string]string // normalized key -> a representative display name
}

// sourcePriority lists, per canonical competition, the preferred source files in
// order. The same real fixture appears in several datasets (e.g. BR-Football's
// "Serie A" duplicates the Brasileirão files), which would triple-count goals,
// matches and points. canonicalize keeps, for each (competition, season), only
// the matches from the single highest-priority source that actually covers that
// season — so each fixture is counted exactly once while no season is dropped.
var sourcePriority = map[string][]string{
	CompBrasileirao:  {fileNovo, fileBrasileirao, fileBRFootball},
	CompCopaBrasil:   {fileCopaBrasil, fileBRFootball},
	CompLibertadores: {fileLibertadores},
	CompSerieB:       {fileBRFootball},
	CompSerieC:       {fileBRFootball},
}

// canonicalize replaces s.Matches with the de-duplicated canonical set.
func (s *Store) canonicalize() {
	// sourcesFor[comp][season] = set of source files present.
	present := map[string]map[int]map[string]bool{}
	for _, m := range s.Matches {
		bySeason := present[m.Competition]
		if bySeason == nil {
			bySeason = map[int]map[string]bool{}
			present[m.Competition] = bySeason
		}
		set := bySeason[m.Season]
		if set == nil {
			set = map[string]bool{}
			bySeason[m.Season] = set
		}
		set[m.Source] = true
	}

	// chosen[comp][season] = the single source to keep.
	chosen := map[string]map[int]string{}
	for comp, bySeason := range present {
		chosen[comp] = map[int]string{}
		prio := sourcePriority[comp]
		for season, set := range bySeason {
			pick := ""
			for _, src := range prio {
				if set[src] {
					pick = src
					break
				}
			}
			if pick == "" {
				// Unknown competition: keep whichever source has the most rows by
				// picking deterministically (first seen alphabetical-ish is fine).
				for src := range set {
					if pick == "" || src < pick {
						pick = src
					}
				}
			}
			chosen[comp][season] = pick
		}
	}

	kept := s.Matches[:0]
	for _, m := range s.Matches {
		if chosen[m.Competition][m.Season] == m.Source {
			kept = append(kept, m)
		}
	}
	s.Matches = kept
}

// index builds auxiliary lookup structures after loading.
func (s *Store) index() {
	s.canonicalize()
	s.teamNames = make(map[string]string)
	for _, m := range s.Matches {
		if _, ok := s.teamNames[m.HomeKey]; !ok && m.HomeTeam != "" {
			s.teamNames[m.HomeKey] = m.HomeTeam
		}
		if _, ok := s.teamNames[m.AwayKey]; !ok && m.AwayTeam != "" {
			s.teamNames[m.AwayKey] = m.AwayTeam
		}
	}
}

// DisplayName returns a representative display name for a normalized key, or the
// key itself if unknown.
func (s *Store) DisplayName(key string) string {
	if n, ok := s.teamNames[key]; ok {
		return n
	}
	return key
}

// MatchFilter parameterizes SearchMatches and the statistics helpers.
type MatchFilter struct {
	Team        string    // matches either side unless Venue narrows it
	Opponent    string    // the other side
	Competition string    // free-text; canonicalized for comparison
	Season      int       // exact season; 0 = any
	SeasonTo    int       // inclusive upper bound for a season range; 0 = ignore
	DateFrom    time.Time // inclusive; zero = ignore
	DateTo      time.Time // inclusive; zero = ignore
	Venue       string    // "home" | "away" | "" — applies to Team
	Source      string    // restrict to a single source CSV
	ScoredOnly  bool      // drop fixtures without goal data
	Limit       int       // 0 = no limit
}

// canonComp folds a competition string for loose comparison.
func canonComp(s string) string {
	return strings.ToLower(foldAccents(strings.TrimSpace(s)))
}

// compMatches reports whether a match's competition satisfies a free-text query.
// It understands a few common aliases for the Brazilian competitions.
func compMatches(matchComp, query string) bool {
	if query == "" {
		return true
	}
	mc := canonComp(matchComp)
	q := canonComp(query)
	switch q {
	case "brasileirao", "brasileirao serie a", "serie a", "campeonato brasileiro", "brazilian league":
		return mc == canonComp(CompBrasileirao)
	case "copa do brasil", "brazilian cup", "cup":
		return mc == canonComp(CompCopaBrasil)
	case "libertadores", "copa libertadores":
		return mc == canonComp(CompLibertadores)
	case "serie b", "brasileirao serie b":
		return mc == canonComp(CompSerieB)
	case "serie c", "brasileirao serie c":
		return mc == canonComp(CompSerieC)
	}
	return strings.Contains(mc, q)
}

// keep reports whether m passes every active criterion in f (ignoring Team /
// Opponent / Venue, which the callers handle so they can track perspective).
func (f MatchFilter) keepBase(m Match) bool {
	if f.ScoredOnly && !m.HasScore {
		return false
	}
	if f.Competition != "" && !compMatches(m.Competition, f.Competition) {
		return false
	}
	if f.Season != 0 {
		if f.SeasonTo != 0 {
			if m.Season < f.Season || m.Season > f.SeasonTo {
				return false
			}
		} else if m.Season != f.Season {
			return false
		}
	}
	if !f.DateFrom.IsZero() && (m.Date.IsZero() || m.Date.Before(f.DateFrom)) {
		return false
	}
	if !f.DateTo.IsZero() && (m.Date.IsZero() || m.Date.After(f.DateTo)) {
		return false
	}
	if f.Source != "" && m.Source != f.Source {
		return false
	}
	return true
}

// PlayerFilter parameterizes SearchPlayers.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// TeamRecord is an aggregated win/draw/loss summary from one team's viewpoint.
type TeamRecord struct {
	Team        string
	Season      int
	Competition string
	Venue       string
	Matches     int
	Wins        int
	Draws       int
	Losses      int
	GoalsFor    int
	GoalsAgst   int
}

// Points uses the standard 3-1-0 scheme.
func (r TeamRecord) Points() int { return r.Wins*3 + r.Draws }

// GoalDiff is goals for minus goals against.
func (r TeamRecord) GoalDiff() int { return r.GoalsFor - r.GoalsAgst }

// WinRate is wins / matches as a percentage (0 when no matches).
func (r TeamRecord) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return 100 * float64(r.Wins) / float64(r.Matches)
}

// HeadToHead summarizes the matchup between two teams.
type HeadToHead struct {
	TeamA, TeamB string
	AWins        int
	BWins        int
	Draws        int
	AGoals       int
	BGoals       int
	Matches      []Match
}

// CompetitionSummary holds aggregate statistical-analysis numbers.
type CompetitionSummary struct {
	Competition string
	Season      int
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
}

// AvgGoals returns mean goals per match.
func (c CompetitionSummary) AvgGoals() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.TotalGoals) / float64(c.Matches)
}

// HomeWinRate returns home wins as a percentage of matches.
func (c CompetitionSummary) HomeWinRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return 100 * float64(c.HomeWins) / float64(c.Matches)
}

// AwayWinRate returns away wins as a percentage of matches.
func (c CompetitionSummary) AwayWinRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return 100 * float64(c.AwayWins) / float64(c.Matches)
}

// DrawRate returns draws as a percentage of matches.
func (c CompetitionSummary) DrawRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return 100 * float64(c.Draws) / float64(c.Matches)
}

// sortMatchesByDateDesc orders matches most-recent first; undated rows sink to
// the bottom but keep a stable relative order.
func sortMatchesByDateDesc(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		return ms[i].Date.After(ms[j].Date)
	})
}
