package soccer

import (
	"fmt"
	"sort"
)

// Store is the in-memory database of matches and players. It is read-only after
// loading, so its query methods are safe for concurrent use.
type Store struct {
	Matches  []Match
	Players  []Player
	Warnings []string

	// displayName maps a matching key to a canonical display name (the most
	// common cleaned spelling seen for that key).
	displayName map[string]string
}

// NewStore returns an empty Store ready to be populated.
func NewStore() *Store {
	return &Store{displayName: map[string]string{}}
}

// AddMatches appends matches to the store.
func (s *Store) AddMatches(m []Match) { s.Matches = append(s.Matches, m...) }

// AddPlayers appends players to the store.
func (s *Store) AddPlayers(p []Player) { s.Players = append(s.Players, p...) }

// Index deduplicates overlapping fixtures and builds derived lookups. Call
// once after all data has been added.
func (s *Store) Index() {
	s.dedupeMatches()

	// Choose, for each team key, the most frequent cleaned spelling as the
	// canonical display name.
	counts := map[string]map[string]int{}
	tally := func(key, name string) {
		if key == "" {
			return
		}
		if counts[key] == nil {
			counts[key] = map[string]int{}
		}
		counts[key][name]++
	}
	for _, m := range s.Matches {
		tally(m.HomeKey, m.HomeTeam)
		tally(m.AwayKey, m.AwayTeam)
	}
	s.displayName = make(map[string]string, len(counts))
	for key, names := range counts {
		best, bestN := "", -1
		for name, n := range names {
			// Prefer higher count, then the longer (more descriptive) name for
			// deterministic ties.
			if n > bestN || (n == bestN && len(name) > len(best)) {
				best, bestN = name, n
			}
		}
		s.displayName[key] = best
	}
}

// dedupeMatches collapses the same fixture appearing across multiple source
// files. Several datasets overlap (e.g. the 2019 Brasileirão appears in three
// files), which would otherwise multiply every team's games and points. Two
// rows are considered the same fixture when they share the same match day and
// the same two teams; the surviving copy is enriched with any extended
// statistics found on a duplicate. Rows without a usable date are never merged,
// since the date is what makes the key safe.
func (s *Store) dedupeMatches() {
	seen := make(map[string]int, len(s.Matches)) // fixture key -> index in out
	out := s.Matches[:0]
	dropped := 0
	fixtureKey := func(day, home, away string) string {
		return day + "|" + home + "|" + away
	}
	for _, m := range s.Matches {
		if m.Date.IsZero() {
			out = append(out, m)
			continue
		}
		// Different sources record the same fixture up to a day apart (kick-off
		// vs UTC date), so probe the previous, same and next day.
		var hit = -1
		for _, off := range []int{-1, 0, 1} {
			day := m.Date.AddDate(0, 0, off).Format("2006-01-02")
			if idx, ok := seen[fixtureKey(day, m.HomeKey, m.AwayKey)]; ok {
				hit = idx
				break
			}
		}
		if hit >= 0 {
			mergeStats(&out[hit], m)
			dropped++
			continue
		}
		seen[fixtureKey(m.Date.Format("2006-01-02"), m.HomeKey, m.AwayKey)] = len(out)
		out = append(out, m)
	}
	s.Matches = out
	if dropped > 0 {
		s.Warnings = append(s.Warnings,
			fmt.Sprintf("deduplicated %d overlapping fixtures across datasets", dropped))
	}
}

// mergeStats copies extended statistics and round/stage metadata from src into
// dst when dst is missing them, so the kept copy is as complete as possible.
func mergeStats(dst *Match, src Match) {
	if dst.HomeShots < 0 && src.HomeShots >= 0 {
		dst.HomeShots, dst.AwayShots = src.HomeShots, src.AwayShots
	}
	if dst.HomeCorners < 0 && src.HomeCorners >= 0 {
		dst.HomeCorners, dst.AwayCorners = src.HomeCorners, src.AwayCorners
	}
	if dst.Round == "" && src.Round != "" {
		dst.Round = src.Round
	}
	if dst.Stage == "" && src.Stage != "" {
		dst.Stage = src.Stage
	}
}

// DisplayName returns the canonical display name for a team key. A curated name
// wins (for clubs whose raw spellings are ambiguous), then the most common
// cleaned spelling seen in the data, then the key itself.
func (s *Store) DisplayName(key string) string {
	if name, ok := canonicalDisplayName(key); ok {
		return name
	}
	if name, ok := s.displayName[key]; ok {
		return name
	}
	return key
}

// Teams returns the sorted list of distinct team keys known to the store.
func (s *Store) Teams() []string {
	keys := make([]string, 0, len(s.displayName))
	for k := range s.displayName {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// Seasons returns the sorted distinct seasons present in match data.
func (s *Store) Seasons() []int {
	set := map[int]struct{}{}
	for _, m := range s.Matches {
		if m.Season > 0 {
			set[m.Season] = struct{}{}
		}
	}
	out := make([]int, 0, len(set))
	for y := range set {
		out = append(out, y)
	}
	sort.Ints(out)
	return out
}

// Competitions returns the sorted distinct competition names.
func (s *Store) Competitions() []string {
	set := map[string]struct{}{}
	for _, m := range s.Matches {
		set[m.Competition] = struct{}{}
	}
	out := make([]string, 0, len(set))
	for c := range set {
		out = append(out, c)
	}
	sort.Strings(out)
	return out
}
