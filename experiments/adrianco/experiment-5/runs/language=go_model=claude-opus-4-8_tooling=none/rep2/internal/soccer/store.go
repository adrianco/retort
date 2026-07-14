// store.go holds the loaded datasets and the cross-cutting helpers (de-dup,
// indexing) used by the query methods in matches.go, players.go, standings.go
// and stats.go.
package soccer

import (
	"sort"
	"strings"
)

// Store is the queryable, in-memory database produced by Load.
type Store struct {
	Matches []Match
	Players []Player

	raw []Match // all parsed matches before source selection
}

// addMatch records a parsed match. De-duplication across the overlapping source
// datasets happens later, in finalize.
func (s *Store) addMatch(m Match) {
	s.raw = append(s.raw, m)
}

// sourcePriority ranks the source datasets. Lower wins. The official,
// single-competition files outrank the broad BR-Football dataset.
func sourcePriority(source string) int {
	switch source {
	case "Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv":
		return 1
	case "novo_campeonato_brasileiro.csv":
		return 2
	default: // BR-Football-Dataset.csv and anything else
		return 3
	}
}

// finalize resolves the overlap between datasets and sorts the result.
//
// The Brasileirão appears in three files that use inconsistent club naming
// ("Athletico-PR" vs "Athletico Paranaense"), so a per-fixture key cannot
// reliably collapse cross-source duplicates. Instead, each (competition,
// season) is served by exactly one source — the highest-priority dataset that
// covers it — which makes double-counting impossible. Within that chosen source
// a fixture-level dedup guards against any in-file repeats.
func (s *Store) finalize() {
	// 1. For each (competition, season), find the best (lowest) source priority.
	type cs struct {
		comp   string
		season int
	}
	best := map[cs]int{}
	for _, m := range s.raw {
		k := cs{m.Competition, m.Season}
		p := sourcePriority(m.Source)
		if cur, ok := best[k]; !ok || p < cur {
			best[k] = p
		}
	}

	// 2. Keep only rows from the winning source for their (competition, season),
	//    de-duplicating fixtures within that source.
	seen := map[string]struct{}{}
	s.Matches = s.Matches[:0]
	for _, m := range s.raw {
		k := cs{m.Competition, m.Season}
		if sourcePriority(m.Source) != best[k] {
			continue
		}
		fk := dedupKey(m)
		if _, dup := seen[fk]; dup {
			continue
		}
		seen[fk] = struct{}{}
		s.Matches = append(s.Matches, m)
	}
	s.raw = nil

	// 3. Sort chronologically.
	sort.SliceStable(s.Matches, func(i, j int) bool {
		a, b := s.Matches[i], s.Matches[j]
		if a.HasDate != b.HasDate {
			return a.HasDate // dated matches first
		}
		if a.HasDate && b.HasDate && !a.Date.Equal(b.Date) {
			return a.Date.Before(b.Date)
		}
		if a.Season != b.Season {
			return a.Season < b.Season
		}
		return a.HomeTeam < b.HomeTeam
	})
}

// dedupKey identifies a fixture by competition, season and the ordered team
// pair, used to drop any repeated rows within a single source dataset. It uses
// fixtureNameKey rather than NormalizeKey so that the state suffix is preserved:
// "Atlético-MG" and "Atlético-GO" are different clubs and must not collapse.
func dedupKey(m Match) string {
	return strings.Join([]string{
		m.Competition,
		itoa(m.Season),
		fixtureNameKey(m.HomeRaw),
		fixtureNameKey(m.AwayRaw),
	}, "|")
}

// fixtureNameKey lowercases and accent-folds a team name but, unlike
// NormalizeKey, keeps any state/country suffix that distinguishes same-named
// clubs. Safe because dedup only compares names from a single source dataset.
func fixtureNameKey(raw string) string {
	s := FoldAccents(strings.TrimSpace(raw))
	s = strings.ToLower(s)
	return multiSpace.ReplaceAllString(s, " ")
}

// Competitions returns the distinct competition names present, sorted.
func (s *Store) Competitions() []string {
	set := map[string]struct{}{}
	for _, m := range s.Matches {
		set[m.Competition] = struct{}{}
	}
	return sortedKeys(set)
}

// Seasons returns the distinct seasons present for an optional competition
// filter (empty competition = all), sorted ascending.
func (s *Store) Seasons(competition string) []int {
	set := map[int]struct{}{}
	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if m.Season != 0 {
			set[m.Season] = struct{}{}
		}
	}
	out := make([]int, 0, len(set))
	for k := range set {
		out = append(out, k)
	}
	sort.Ints(out)
	return out
}

func sortedKeys(set map[string]struct{}) []string {
	out := make([]string, 0, len(set))
	for k := range set {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func itoa(n int) string {
	// small, allocation-free-ish helper avoiding strconv import churn here
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
