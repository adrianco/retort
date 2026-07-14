// Context
// -------
// Graph is the in-memory knowledge graph holding all loaded matches and players
// plus the derived indexes that make queries correct and fast.
//
// Two subtleties of the source data are handled here:
//
//  1. Ambiguous club names. Datasets abbreviate clubs to "name + state"
//     ("Atletico-MG", "Atletico-GO", "Atletico-PR"). For such bases the state
//     IS part of the identity, but for unique clubs ("Palmeiras") the state
//     suffix is redundant and is dropped so spellings ("Palmeiras-SP" vs
//     "Palmeiras") unify. A first pass detects which bases occur with more than
//     one state and only those keep the state in their identity key.
//
//  2. Overlapping datasets. Several files cover the same fixtures (e.g.
//     Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv and
//     BR-Football-Dataset.csv all include Brasileirão 2019). g.Matches holds the
//     fixture-deduplicated union (used for raw match listings), while g.primary
//     holds a single authoritative source per (competition, season) so that
//     standings and aggregate statistics are never double counted.
//
// The graph is built once at startup and is read-only thereafter, so it is safe
// for concurrent reads.
package soccer

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
)

// Graph stores the loaded datasets and derived indexes.
type Graph struct {
	Matches []Match // fixture-deduplicated union of all match datasets
	Players []Player

	primary []Match // one authoritative source per (competition, season)

	raw []Match // every loaded match before dedup (input to finalize)

	ambiguous   map[string]bool   // base team key -> appears with >1 state
	teamDisplay map[string]string // team identity key -> preferred display name
}

// NewGraph returns an empty Graph ready to be populated by the loaders.
func NewGraph() *Graph {
	return &Graph{
		ambiguous:   make(map[string]bool),
		teamDisplay: make(map[string]string),
	}
}

func (g *Graph) addMatch(m Match)   { g.raw = append(g.raw, m) }
func (g *Graph) addPlayer(p Player) { g.Players = append(g.Players, p) }

// teamID returns the identity key for a (name, state) pair. Ambiguous bases keep
// their state; unique bases collapse to the bare base so spelling and suffix
// variants unify.
func (g *Graph) teamID(name, state string) string {
	base := TeamKey(name)
	if base == "" {
		return ""
	}
	if g.ambiguous[base] && state != "" {
		return base + "#" + strings.ToLower(state)
	}
	return base
}

// fixtureKey identifies a real-world fixture so overlapping datasets collapse.
func (g *Graph) fixtureKey(m Match) string {
	return strings.Join([]string{
		m.Date.Format("2006-01-02"),
		g.teamID(m.HomeTeam, m.HomeState),
		g.teamID(m.AwayTeam, m.AwayState),
		fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals),
	}, "|")
}

// finalize builds all derived state from g.raw. It runs after every loader.
func (g *Graph) finalize() {
	g.detectAmbiguous()
	g.dedupAndRegister()
	g.buildPrimary()
}

// detectAmbiguous records which base team keys denote more than one real club.
// A base is ambiguous when at least two of its states each account for a
// meaningful share of its matches (>= max(20, 5%)). The threshold filters out
// data noise such as a stray "Flamengo-PI" (2 matches) so the famous club is
// not needlessly suffixed, while still separating Atletico-MG/GO/PR and
// America-MG/RN.
func (g *Graph) detectAmbiguous() {
	counts := map[string]map[string]int{}
	note := func(name, state string) {
		if state == "" {
			return
		}
		base := TeamKey(name)
		if base == "" {
			return
		}
		if counts[base] == nil {
			counts[base] = map[string]int{}
		}
		counts[base][strings.ToLower(state)]++
	}
	for _, m := range g.raw {
		note(m.HomeTeam, m.HomeState)
		note(m.AwayTeam, m.AwayState)
	}
	for base, states := range counts {
		total := 0
		for _, n := range states {
			total += n
		}
		threshold := total / 20 // 5%
		if threshold < 20 {
			threshold = 20
		}
		qualifying := 0
		for _, n := range states {
			if n >= threshold {
				qualifying++
			}
		}
		if qualifying >= 2 {
			g.ambiguous[base] = true
		}
	}
}

// dedupAndRegister builds g.Matches (deduplicated) and the team display registry.
func (g *Graph) dedupAndRegister() {
	seen := make(map[string]int, len(g.raw)) // fixtureKey -> index in g.Matches
	for _, m := range g.raw {
		key := g.fixtureKey(m)
		if idx, dup := seen[key]; dup {
			if m.HasStats && !g.Matches[idx].HasStats {
				mergeStats(&g.Matches[idx], m)
			}
			continue
		}
		seen[key] = len(g.Matches)
		g.Matches = append(g.Matches, m)
		g.registerTeam(m.HomeTeam, m.HomeState)
		g.registerTeam(m.AwayTeam, m.AwayState)
	}
}

func mergeStats(dst *Match, src Match) {
	dst.HasStats = true
	dst.HomeShots, dst.AwayShots = src.HomeShots, src.AwayShots
	dst.HomeCorner, dst.AwayCorner = src.HomeCorner, src.AwayCorner
	dst.HomeAttack, dst.AwayAttack = src.HomeAttack, src.AwayAttack
}

// displayName produces the preferred display form for a team: the normalized
// name, with the state re-appended for ambiguous clubs ("Atletico" -> with
// state "MG" -> "Atletico-MG") so distinct clubs remain visually distinct.
func (g *Graph) displayName(name, state string) string {
	base := NormalizeTeamName(name)
	if g.ambiguous[TeamKey(name)] && state != "" {
		return base + "-" + strings.ToUpper(state)
	}
	return base
}

// registerTeam records a display name for a team identity. When the same team is
// seen spelled multiple ways, an accented spelling ("Grêmio") is preferred over
// a plain-ASCII one ("Gremio").
func (g *Graph) registerTeam(name, state string) {
	id := g.teamID(name, state)
	if id == "" {
		return
	}
	disp := g.displayName(name, state)
	cur, ok := g.teamDisplay[id]
	if !ok {
		g.teamDisplay[id] = disp
		return
	}
	if !hasAccent(cur) && hasAccent(disp) {
		g.teamDisplay[id] = disp
	}
}

// hasAccent reports whether s contains any accented Latin characters.
func hasAccent(s string) bool { return stripDiacritics(s) != s }

// buildPrimary selects one authoritative source per (competition, season).
func (g *Graph) buildPrimary() {
	groups := map[string][]int{}
	for i, m := range g.Matches {
		key := m.Competition + "|" + strconv.Itoa(m.Season)
		groups[key] = append(groups[key], i)
	}
	for _, idxs := range groups {
		best := 1 << 30
		for _, i := range idxs {
			if p := sourcePriority(g.Matches[i].Source, g.Matches[i].Competition); p < best {
				best = p
			}
		}
		for _, i := range idxs {
			if sourcePriority(g.Matches[i].Source, g.Matches[i].Competition) == best {
				g.primary = append(g.primary, g.Matches[i])
			}
		}
	}
}

// sourcePriority ranks datasets for a competition (lower = more authoritative).
// Dedicated competition files win; the broad BR-Football dataset is used only
// when it is the sole source for a competition/season.
func sourcePriority(source, competition string) int {
	switch competition {
	case CompBrasileirao:
		switch source {
		case fileBrasileirao:
			return 0
		case fileNovo:
			return 1
		}
	case CompCopaBrasil:
		if source == fileCup {
			return 0
		}
	case CompLibertadores:
		if source == fileLibertadores {
			return 0
		}
	}
	if source == fileBRFootball {
		return 9
	}
	return 5
}

// ResolveTeam returns the canonical display name for a user-supplied team query,
// or the original query if no team is known. The boolean reports a known team.
func (g *Graph) ResolveTeam(query string) (string, bool) {
	qkey := TeamKey(query)
	if disp, ok := g.teamDisplay[qkey]; ok {
		return disp, true
	}
	// Exact identity hit when the query already carries a disambiguating state.
	if id := g.teamID(query, StateFromName(query)); id != qkey {
		if disp, ok := g.teamDisplay[id]; ok {
			return disp, true
		}
	}
	// Fall back to substring match against known teams (e.g. "Corinthians").
	var best string
	for k, disp := range g.teamDisplay {
		base := strings.SplitN(k, "#", 2)[0]
		if strings.Contains(base, qkey) || strings.Contains(qkey, base) {
			if best == "" || len(disp) < len(best) {
				best = disp
			}
		}
	}
	if best != "" {
		return best, true
	}
	return query, false
}

// displayFor returns the registered display name for a team identity key,
// falling back to the supplied name when unregistered.
func (g *Graph) displayFor(id, fallback string) string {
	if d, ok := g.teamDisplay[id]; ok {
		return d
	}
	return fallback
}

// Teams returns all known team display names, sorted.
func (g *Graph) Teams() []string {
	out := make([]string, 0, len(g.teamDisplay))
	for _, d := range g.teamDisplay {
		out = append(out, d)
	}
	sort.Strings(out)
	return out
}

// Competitions returns all distinct competition names present, sorted.
func (g *Graph) Competitions() []string {
	set := map[string]struct{}{}
	for _, m := range g.Matches {
		set[m.Competition] = struct{}{}
	}
	out := make([]string, 0, len(set))
	for c := range set {
		out = append(out, c)
	}
	sort.Strings(out)
	return out
}

// Seasons returns all distinct seasons present, sorted ascending.
func (g *Graph) Seasons() []int {
	set := map[int]struct{}{}
	for _, m := range g.Matches {
		if m.Season > 0 {
			set[m.Season] = struct{}{}
		}
	}
	out := make([]int, 0, len(set))
	for s := range set {
		out = append(out, s)
	}
	sort.Ints(out)
	return out
}

// Stats summarizes the loaded data, used for diagnostics.
func (g *Graph) Stats() string {
	return fmt.Sprintf("%d matches (%d after source-dedup), %d players, %d teams, %d competitions",
		len(g.Matches), len(g.primary), len(g.Players), len(g.teamDisplay), len(g.Competitions()))
}
