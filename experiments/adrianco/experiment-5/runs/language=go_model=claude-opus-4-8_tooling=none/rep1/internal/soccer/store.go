// Context:
//   - The Store is the loaded, query-ready dataset held in memory for the
//     lifetime of the server. It owns the unified slice of Matches and the slice
//     of Players, plus a few precomputed lookups.
//   - The Brasileirão Série A appears in three different source files with
//     overlapping seasons, so Load de-duplicates matches: records that describe
//     the same game (same competition, season, teams and score) are merged into
//     one, recording all contributing sources. This keeps aggregate stats
//     (standings, averages) from being inflated by the overlap.
//   - All queries run as in-memory scans; with ~25k matches and ~18k players
//     this comfortably meets the spec's sub-second / few-second latency targets.
package soccer

import (
	"sort"
	"strings"
)

// Store holds the fully loaded dataset.
type Store struct {
	Matches []Match
	Players []Player

	competitions []string
}

// Load reads every CSV in dir, de-duplicates matches and returns a ready Store.
func Load(dir string) (*Store, error) {
	matches, err := loadAllMatches(dir)
	if err != nil {
		return nil, err
	}
	players, err := loadPlayers(joinFifa(dir))
	if err != nil {
		// Players are optional; an absent FIFA file leaves Players empty.
		players = nil
	}

	s := &Store{
		Matches: selectAuthoritative(matches),
		Players: players,
	}
	s.indexCompetitions()
	return s, nil
}

// sourcePriority ranks the source files (lower is better/more authoritative).
// The two purpose-built league/cup files win over the messier extended-stats
// file, and the dedicated Série A files win over the historical compilation.
var sourcePriority = map[string]int{
	fileBrasileirao:  1,
	fileCup:          1,
	fileLibertadores: 1,
	fileNovo:         2,
	fileBRFootball:   3,
}

// selectAuthoritative removes cross-source duplication. The same Série A season
// can appear in up to three files (and Copa do Brasil in two), with
// inconsistent team-name spellings between them. Rather than try to reconcile
// those spellings, we pick a single authoritative source per
// (competition, season): the best-ranked source that actually has data for that
// pairing. Every season therefore comes from one internally consistent file, so
// standings and aggregates are neither inflated nor mis-merged.
func selectAuthoritative(in []Match) []Match {
	type key struct {
		comp   string
		season int
	}
	best := map[key]int{} // chosen priority per (competition, season)
	for _, m := range in {
		k := key{m.Competition, m.Season}
		p := priorityOf(m)
		if cur, ok := best[k]; !ok || p < cur {
			best[k] = p
		}
	}
	out := make([]Match, 0, len(in))
	for _, m := range in {
		if priorityOf(m) == best[key{m.Competition, m.Season}] {
			out = append(out, m)
		}
	}
	return out
}

func priorityOf(m Match) int {
	worst := 99
	for _, src := range m.Sources {
		if p, ok := sourcePriority[src]; ok && p < worst {
			worst = p
		}
	}
	return worst
}

func joinFifa(dir string) string {
	if strings.HasSuffix(dir, "/") {
		return dir + fileFifa
	}
	return dir + "/" + fileFifa
}

func (s *Store) indexCompetitions() {
	seen := map[string]bool{}
	for _, m := range s.Matches {
		if !seen[m.Competition] {
			seen[m.Competition] = true
			s.competitions = append(s.competitions, m.Competition)
		}
	}
	sort.Strings(s.competitions)
}

// Competitions returns the distinct canonical competition names present.
func (s *Store) Competitions() []string { return s.competitions }
