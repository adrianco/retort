// store.go: the in-memory knowledge graph. It holds the unified match and
// player records, de-duplicates fixtures that appear in more than one source
// (the two Brasileirão datasets and BR-Football overlap on 2012-2022), resolves
// fuzzy team names to canonical keys, and exposes the low-level query
// primitives (FindMatches, players, etc.) that queries.go builds answers on.
package soccer

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// Store is the queryable knowledge graph.
type Store struct {
	Matches []Match
	Players []Player

	duplicates int

	// ambiguous[base] is true when a base club name appears with more than one
	// state, so the state must be kept in the key (e.g. "atletico").
	ambiguous map[string]bool

	// dominantState[base] is the state a bare ambiguous name resolves to when
	// one club clearly prevails (e.g. "flamengo" -> "RJ").
	dominantState map[string]string

	// displayCount tracks how often each (key -> cleaned display name) variant
	// occurs, so finalize can pick the most common spelling for output.
	displayCount map[string]map[string]int
	canonical    map[string]string // team key -> chosen display name

	// teamKeys is the sorted set of all team keys (for fuzzy resolution).
	teamKeys []string
}

func newStore() *Store {
	return &Store{
		ambiguous:    make(map[string]bool),
		displayCount: make(map[string]map[string]int),
		canonical:    make(map[string]string),
	}
}

// LoadEmptyForTest returns a finalized, empty store. It is exported so tests
// that only exercise the query/tool surface need not depend on the datasets.
func LoadEmptyForTest() *Store {
	s := newStore()
	s.finalize()
	return s
}

// addMatch records the raw team names; key assignment and de-duplication are
// deferred to finalize, which first needs to see every name to decide which
// base names are state-ambiguous.
func (s *Store) addMatch(m *Match, rawHome, rawAway string) {
	m.rawHome = rawHome
	m.rawAway = rawAway
	s.Matches = append(s.Matches, *m)
}

// teamKey resolves a raw team name to its canonical matching key, keeping the
// state suffix only for base names that are shared across multiple states. A
// bare ambiguous name (no state) is mapped to that base's dominant club when
// one clearly prevails — e.g. bare "Flamengo" -> Flamengo-RJ, since Flamengo-PI
// is negligible — but stays ambiguous when several clubs are comparable (the
// three Atléticos), so the caller can prompt for disambiguation.
func (s *Store) teamKey(raw string) string {
	rawBase, state := splitBaseState(raw)
	if state == "" {
		if d, ok := s.dominantState[canonBase(rawBase)]; ok {
			state = d
		}
	}
	return baseToKey(rawBase, state, s.ambiguous)
}

func (s *Store) countDisplay(key, display string) {
	if display == "" {
		return
	}
	if s.displayCount[key] == nil {
		s.displayCount[key] = make(map[string]int)
	}
	s.displayCount[key][display]++
}

// dominantStateThresholdPct is how dominant (in % of stated occurrences) a
// single state must be for a bare ambiguous name to resolve to it.
const dominantStateThresholdPct = 85

// finalize assigns canonical team keys, removes exact duplicate rows, chooses a
// display name per team and sorts by date. Cross-source duplicates are NOT
// merged here — keeping every source intact lets CleanBySource later pick the
// most complete source per season (some sources are mid-season snapshots).
func (s *Store) finalize() {
	// Pass 1: tally states per canonical base name to decide (a) which bases
	// are state-ambiguous and (b) whether one state clearly dominates.
	stateCount := map[string]map[string]int{}
	count := func(raw string) {
		rawBase, state := splitBaseState(raw)
		if rawBase == "" {
			return
		}
		base := canonBase(rawBase)
		if stateCount[base] == nil {
			stateCount[base] = map[string]int{}
		}
		stateCount[base][state]++
	}
	for i := range s.Matches {
		count(s.Matches[i].rawHome)
		count(s.Matches[i].rawAway)
	}
	s.dominantState = make(map[string]string)
	for base, sc := range stateCount {
		distinct, total, topN, topState := 0, 0, 0, ""
		for st, n := range sc {
			if st == "" {
				continue
			}
			distinct++
			total += n
			if n > topN {
				topN, topState = n, st
			}
		}
		if distinct > 1 {
			s.ambiguous[base] = true
		}
		if topState != "" && topN*100 >= dominantStateThresholdPct*total {
			s.dominantState[base] = topState
		}
	}

	// Pass 2: assign keys + display names, dropping only exact duplicate rows
	// (same source, day, teams and score).
	seen := map[string]bool{}
	kept := s.Matches[:0]
	for i := range s.Matches {
		m := s.Matches[i]
		m.HomeKey = s.teamKey(m.rawHome)
		m.AwayKey = s.teamKey(m.rawAway)
		if m.HomeKey == "" || m.AwayKey == "" {
			continue
		}
		m.HomeTeam = DisplayTeam(m.rawHome)
		m.AwayTeam = DisplayTeam(m.rawAway)

		sig := fmt.Sprintf("%s|%s|%s|%s|%s|%d-%d",
			m.Source, m.Competition, m.Date.Format("2006-01-02"), m.HomeKey, m.AwayKey, m.HomeGoals, m.AwayGoals)
		if seen[sig] {
			s.duplicates++
			continue
		}
		seen[sig] = true

		s.countDisplay(m.HomeKey, m.HomeTeam)
		s.countDisplay(m.AwayKey, m.AwayTeam)
		kept = append(kept, m)
	}
	s.Matches = kept

	// Resolve each player's club to a canonical team key now that ambiguity is
	// known (clubs were loaded before the ambiguity map existed).
	for i := range s.Players {
		s.Players[i].ClubKey = s.teamKey(s.Players[i].Club)
	}

	for key, variants := range s.displayCount {
		best, bestScore := "", [4]int{-1, -1, -1, -1}
		for disp, n := range variants {
			// Rank candidate display spellings by, in order: no trailing state
			// code (cleaner, e.g. "Flamengo" over "Flamengo-RJ"), then
			// frequency, then accents retained, then length. For genuinely
			// ambiguous clubs every spelling carries the state, so the suffix
			// is preserved naturally.
			sc := [4]int{boolToInt(!endsWithStateCode(disp)), n, nonASCII(disp), len(disp)}
			if betterScore(sc, bestScore) {
				best, bestScore = disp, sc
			}
		}
		s.canonical[key] = best
		s.teamKeys = append(s.teamKeys, key)
	}
	sort.Strings(s.teamKeys)

	for i := range s.Matches {
		if c, ok := s.canonical[s.Matches[i].HomeKey]; ok {
			s.Matches[i].HomeTeam = c
		}
		if c, ok := s.canonical[s.Matches[i].AwayKey]; ok {
			s.Matches[i].AwayTeam = c
		}
	}

	sort.SliceStable(s.Matches, func(i, j int) bool {
		return s.Matches[i].Date.Before(s.Matches[j].Date)
	})
}

// betterScore reports whether candidate score a beats b (lexicographic).
func betterScore(a, b [4]int) bool {
	for i := range a {
		if a[i] != b[i] {
			return a[i] > b[i]
		}
	}
	return false
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

// endsWithStateCode reports whether a display name ends in a "-XX"/" XX" state
// or country code.
func endsWithStateCode(disp string) bool {
	disp = strings.TrimSpace(disp)
	for _, sep := range []string{" - ", "-", " "} {
		if i := strings.LastIndex(disp, sep); i > 0 && isStateCode(disp[i+len(sep):]) {
			return true
		}
	}
	return false
}

func nonASCII(s string) int {
	n := 0
	for _, r := range s {
		if r > 127 {
			n++
		}
	}
	return n
}

// Display returns the canonical display name for a team key (or the key itself).
func (s *Store) Display(key string) string {
	if d, ok := s.canonical[key]; ok {
		return d
	}
	return key
}

// ResolveTeam maps a user-supplied team name to a canonical key. It tries, in
// order: exact key match, then a unique substring match. It returns the key,
// its display name, and whether a confident single match was found. When the
// query is ambiguous (matches several teams), ok is false and the candidate
// display names are returned for disambiguation.
func (s *Store) ResolveTeam(query string) (key, display string, candidates []string, ok bool) {
	// Exact identity first (keeps the state for ambiguous names like Atlético-MG).
	if ek := s.teamKey(query); ek != "" {
		if _, exists := s.canonical[ek]; exists {
			return ek, s.canonical[ek], nil, true
		}
	}
	q := NormalizeTeam(query)
	if q == "" {
		return "", "", nil, false
	}
	if _, exists := s.canonical[q]; exists {
		return q, s.canonical[q], nil, true
	}
	var matches []string
	for _, k := range s.teamKeys {
		if k == q || strings.Contains(k, q) || strings.Contains(q, k) {
			matches = append(matches, k)
		}
	}
	switch len(matches) {
	case 0:
		return "", "", nil, false
	case 1:
		return matches[0], s.canonical[matches[0]], nil, true
	default:
		// If exactly one candidate equals the query as a whole word, take it.
		for _, k := range matches {
			if k == q {
				return k, s.canonical[k], nil, true
			}
		}
		cands := make([]string, 0, len(matches))
		for _, k := range matches {
			cands = append(cands, s.canonical[k])
		}
		sort.Strings(cands)
		return "", "", cands, false
	}
}

// MatchFilter selects matches for FindMatches. Zero-valued fields are ignored.
type MatchFilter struct {
	TeamKey     string // matches either home or away
	HomeKey     string // matches home only
	AwayKey     string // matches away only
	OpponentKey string // combined with TeamKey: the other side
	Competition string // canonical competition name
	Season      int
	SeasonMin   int
	SeasonMax   int
	DateFrom    time.Time
	DateTo      time.Time
}

// FindMatches returns matches satisfying the filter, ordered by date ascending.
func (s *Store) FindMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range s.Matches {
		if f.Competition != "" && m.Competition != f.Competition {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.SeasonMin != 0 && m.Season < f.SeasonMin {
			continue
		}
		if f.SeasonMax != 0 && m.Season > f.SeasonMax {
			continue
		}
		if !f.DateFrom.IsZero() && m.Date.Before(f.DateFrom) {
			continue
		}
		if !f.DateTo.IsZero() && m.Date.After(f.DateTo) {
			continue
		}
		if f.HomeKey != "" && m.HomeKey != f.HomeKey {
			continue
		}
		if f.AwayKey != "" && m.AwayKey != f.AwayKey {
			continue
		}
		if f.TeamKey != "" {
			if m.HomeKey != f.TeamKey && m.AwayKey != f.TeamKey {
				continue
			}
			if f.OpponentKey != "" {
				other := m.AwayKey
				if m.HomeKey != f.TeamKey {
					other = m.HomeKey
				}
				if other != f.OpponentKey {
					continue
				}
			}
		}
		out = append(out, m)
	}
	return out
}

// CleanBySource removes cross-source double-counting for aggregate queries.
// The same fixture often appears in several datasets with slightly different
// kickoff dates (a late kickoff crosses midnight), so day-level de-duplication
// can't catch it. For standings and per-season statistics we instead keep, for
// each (competition, season), only the matches from the single source that
// contributed the most rows — i.e. the most complete record of that season.
func CleanBySource(matches []Match) []Match {
	type ck struct {
		comp   string
		season int
	}
	// Group by (competition, season) -> source -> matches.
	groups := map[ck]map[string][]Match{}
	order := []ck{}
	for _, m := range matches {
		k := ck{m.Competition, m.Season}
		if groups[k] == nil {
			groups[k] = map[string][]Match{}
			order = append(order, k)
		}
		groups[k][m.Source] = append(groups[k][m.Source], m)
	}
	var out []Match
	for _, k := range order {
		var best []Match
		bestSrc := ""
		for src, ms := range groups[k] {
			// Prefer the source with the most rows (the most complete record of
			// that season); break ties toward the curated, lower-rank source.
			switch {
			case best == nil, len(ms) > len(best),
				len(ms) == len(best) && sourceRank(src) < sourceRank(bestSrc):
				best, bestSrc = ms, src
			}
		}
		out = append(out, best...)
	}
	return out
}

// sourceRank orders datasets for tie-breaking in CleanBySource. The curated
// single-competition Kaggle sets are preferred over the broad multi-competition
// BR-Football dataset (which uses looser naming and ±1-day kickoff dates).
func sourceRank(src string) int {
	switch src {
	case "Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv":
		return 0
	case "novo_campeonato_brasileiro.csv":
		return 1
	case "BR-Football-Dataset.csv":
		return 3
	default:
		return 2
	}
}

// FindMatchesClean is FindMatches followed by CleanBySource; use it for
// season-level aggregates (standings, per-season stats and rankings).
func (s *Store) FindMatchesClean(f MatchFilter) []Match {
	return CleanBySource(s.FindMatches(f))
}

// Competitions returns the set of competition names present, sorted.
func (s *Store) Competitions() []string {
	set := map[string]bool{}
	for _, m := range s.Matches {
		set[m.Competition] = true
	}
	out := make([]string, 0, len(set))
	for c := range set {
		out = append(out, c)
	}
	sort.Strings(out)
	return out
}

// SeasonRange returns the min and max season for a competition (0,0 if none).
func (s *Store) SeasonRange(comp string) (min, max int) {
	for _, m := range s.Matches {
		if comp != "" && m.Competition != comp {
			continue
		}
		if m.Season == 0 {
			continue
		}
		if min == 0 || m.Season < min {
			min = m.Season
		}
		if m.Season > max {
			max = m.Season
		}
	}
	return
}

// --- player primitives ------------------------------------------------------

// PlayerFilter selects players. Zero-valued fields are ignored.
type PlayerFilter struct {
	NameKey      string // substring match on normalized name
	NationKey    string // exact match on normalized nationality
	ClubKey      string // exact match on normalized club key (resolved club)
	ClubContains string // substring match on normalized club key (fuzzy club)
	Position     string // exact (case-insensitive) match
	MinOverall   int
}

// FindPlayers returns players satisfying the filter, sorted by Overall desc.
func (s *Store) FindPlayers(f PlayerFilter) []Player {
	pos := strings.ToUpper(strings.TrimSpace(f.Position))
	var out []Player
	for _, p := range s.Players {
		if f.NameKey != "" && !strings.Contains(p.NameKey, f.NameKey) {
			continue
		}
		if f.NationKey != "" && p.NationKey != f.NationKey {
			continue
		}
		if f.ClubKey != "" && p.ClubKey != f.ClubKey {
			continue
		}
		if f.ClubContains != "" && !strings.Contains(p.ClubKey, f.ClubContains) {
			continue
		}
		if pos != "" && strings.ToUpper(p.Position) != pos {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Name < out[j].Name
	})
	return out
}
