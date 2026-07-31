package soccer

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/normalize"
)

// Graph is the read-only knowledge graph: canonical clubs, deduplicated
// matches, FIFA players, and the indexes that make lookups O(1).
//
// It is built once at start-up and never mutated afterwards, so all query
// methods are safe for concurrent use.
type Graph struct {
	Matches []Match
	Players []Player

	teams     map[string]*Team
	teamOrder []string

	playersByClub map[string][]int
	playersByNat  map[string][]int
	playersByName map[string][]int

	competitions map[string]map[int]bool // competition -> seasons present
	stats        LoadStats
}

// LoadStats records what the loader found, for the server_info tool.
type LoadStats struct {
	DataDir  string         `json:"data_dir"`
	FileRows map[string]int `json:"rows_per_file"`
	// SkippedRows counts rows dropped for having no usable score ("NA") or an
	// unparseable date, per file.
	SkippedRows  map[string]int `json:"skipped_rows,omitempty"`
	RawMatches   int            `json:"raw_match_rows"`
	Matches      int            `json:"unique_matches"`
	Duplicates   int            `json:"merged_duplicates"`
	Teams        int            `json:"teams"`
	Players      int            `json:"players"`
	Competitions []string       `json:"competitions"`
	LoadDuration string         `json:"load_duration"`
}

// Load reads every CSV in dir and builds the graph.
func Load(dir string) (*Graph, error) {
	start := time.Now()
	g := &Graph{
		teams:         map[string]*Team{},
		playersByClub: map[string][]int{},
		playersByNat:  map[string][]int{},
		playersByName: map[string][]int{},
		competitions:  map[string]map[int]bool{},
		stats: LoadStats{DataDir: dir,
			FileRows: map[string]int{}, SkippedRows: map[string]int{}},
	}

	type fileResult struct {
		file    string
		matches []Match
		skipped int
		err     error
	}
	results := make([]fileResult, len(MatchFiles))
	var wg sync.WaitGroup
	for i, file := range MatchFiles {
		wg.Add(1)
		go func(i int, file string) {
			defer wg.Done()
			ms, skipped, err := loadMatchFile(dir, file)
			results[i] = fileResult{file: file, matches: ms, skipped: skipped, err: err}
		}(i, file)
	}
	var players []Player
	var playerErr error
	wg.Add(1)
	go func() {
		defer wg.Done()
		players, playerErr = loadPlayers(dir)
	}()
	wg.Wait()

	if playerErr != nil {
		return nil, playerErr
	}
	batches := make([][]Match, 0, len(results))
	for _, res := range results {
		if res.err != nil {
			return nil, res.err
		}
		g.stats.FileRows[res.file] = len(res.matches)
		g.stats.RawMatches += len(res.matches)
		if res.skipped > 0 {
			g.stats.SkippedRows[res.file] = res.skipped
		}
		batches = append(batches, res.matches)
	}

	g.mergeMatches(batches)
	g.Players = players
	g.index()
	g.stats.LoadDuration = time.Since(start).String()
	return g, nil
}

// dedupKey identifies the same fixture across datasets.
//
// League fixtures use competition+season+home+away: a double round robin plays
// each ordered pair exactly once per season, so this is exact even when two
// files disagree about the calendar date (they do, by a day, around midnight
// kick-offs). Knockout competitions can replay a pairing, so those also key on
// the date.
func dedupKey(m Match) string {
	switch m.Competition {
	case SerieA, SerieB, SerieC:
		return fmt.Sprintf("%s|%d|%s|%s", m.Competition, m.Season, m.Home.ID, m.Away.ID)
	default:
		return fmt.Sprintf("%s|%d|%s|%s|%s", m.Competition, m.Season, m.Home.ID, m.Away.ID,
			m.Date.Format("2006-01"))
	}
}

// mergeMatches folds every file's fixtures into g.Matches, merging duplicates
// so that round numbers, venues and shot statistics from different sources end
// up on one record.
func (g *Graph) mergeMatches(batches [][]Match) {
	seen := make(map[string]int, 20000)
	for _, batch := range batches {
		for _, m := range batch {
			key := dedupKey(m)
			if pos, ok := seen[key]; ok {
				g.stats.Duplicates++
				mergeInto(&g.Matches[pos], m)
				continue
			}
			seen[key] = len(g.Matches)
			g.Matches = append(g.Matches, m)
		}
	}
	sort.SliceStable(g.Matches, func(i, j int) bool {
		if !g.Matches[i].Date.Equal(g.Matches[j].Date) {
			return g.Matches[i].Date.Before(g.Matches[j].Date)
		}
		return g.Matches[i].Home.Name < g.Matches[j].Home.Name
	})
	g.stats.Matches = len(g.Matches)
}

// mergeInto fills gaps in dst from src without overwriting existing values.
func mergeInto(dst *Match, src Match) {
	if dst.Round == "" {
		dst.Round = src.Round
	}
	if dst.Stage == "" {
		dst.Stage = src.Stage
	}
	if dst.Venue == "" {
		dst.Venue = src.Venue
	}
	if dst.KickOff == "" {
		dst.KickOff = src.KickOff
	}
	if dst.Stats == nil {
		dst.Stats = src.Stats
	}
	if dst.Home.State == "" {
		dst.Home.State = src.Home.State
	}
	if dst.Away.State == "" {
		dst.Away.State = src.Away.State
	}
	for _, s := range src.Sources {
		if !contains(dst.Sources, s) {
			dst.Sources = append(dst.Sources, s)
		}
	}
}

func contains(xs []string, s string) bool {
	for _, x := range xs {
		if x == s {
			return true
		}
	}
	return false
}

// index builds every lookup table over the merged matches and players.
func (g *Graph) index() {
	for i := range g.Matches {
		m := &g.Matches[i]
		for _, ref := range []TeamRef{m.Home, m.Away} {
			t := g.ensureTeam(ref)
			t.matchIdx = append(t.matchIdx, i)
		}
		if g.competitions[m.Competition] == nil {
			g.competitions[m.Competition] = map[int]bool{}
		}
		g.competitions[m.Competition][m.Season] = true
	}

	for _, t := range g.teams {
		t.MatchCount = len(t.matchIdx)
		t.StateName = normalize.StateName(t.State)
		comps := map[string]bool{}
		seasons := map[int]bool{}
		for _, mi := range t.matchIdx {
			comps[g.Matches[mi].Competition] = true
			seasons[g.Matches[mi].Season] = true
		}
		t.Competitions = sortedKeys(comps)
		t.Seasons = sortedInts(seasons)
		t.Aliases = sortedKeys(t.aliasSet)
	}
	g.teamOrder = make([]string, 0, len(g.teams))
	for id := range g.teams {
		g.teamOrder = append(g.teamOrder, id)
	}
	sort.Strings(g.teamOrder)

	for i, p := range g.Players {
		if p.ClubID != "" {
			g.playersByClub[p.ClubID] = append(g.playersByClub[p.ClubID], i)
		}
		if p.Nationality != "" {
			g.playersByNat[normalize.Deaccent(p.Nationality)] = append(
				g.playersByNat[normalize.Deaccent(p.Nationality)], i)
		}
		for _, tok := range strings.Fields(normalize.Deaccent(p.Name)) {
			tok = strings.Trim(tok, ".")
			if tok != "" {
				g.playersByName[tok] = append(g.playersByName[tok], i)
			}
		}
	}

	g.stats.Teams = len(g.teams)
	g.stats.Players = len(g.Players)
	g.stats.FileRows[FilePlayers] = len(g.Players)
	g.stats.Competitions = sortedKeys(setOfKeys(g.competitions))
}

func setOfKeys[V any](m map[string]V) map[string]bool {
	out := make(map[string]bool, len(m))
	for k := range m {
		out[k] = true
	}
	return out
}

func (g *Graph) ensureTeam(ref TeamRef) *Team {
	t, ok := g.teams[ref.ID]
	if !ok {
		t = &Team{ID: ref.ID, Name: ref.Name, State: ref.State, aliasSet: map[string]bool{}}
		g.teams[ref.ID] = t
	}
	if t.State == "" && ref.State != "" {
		t.State = ref.State
	}
	if ref.Raw != "" && ref.Raw != t.Name {
		t.aliasSet[ref.Raw] = true
	}
	return t
}

func sortedKeys(m map[string]bool) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

func sortedInts(m map[int]bool) []int {
	out := make([]int, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Ints(out)
	return out
}

// Stats returns the load summary.
func (g *Graph) Stats() LoadStats { return g.stats }

// Teams returns every club, ordered by canonical ID.
func (g *Graph) Teams() []*Team {
	out := make([]*Team, 0, len(g.teamOrder))
	for _, id := range g.teamOrder {
		out = append(out, g.teams[id])
	}
	return out
}

// TeamByID returns the club with the given canonical ID.
func (g *Graph) TeamByID(id string) (*Team, bool) {
	t, ok := g.teams[id]
	return t, ok
}

// Competitions lists the tournaments present, with their seasons.
func (g *Graph) Competitions() map[string][]int {
	out := make(map[string][]int, len(g.competitions))
	for comp, seasons := range g.competitions {
		out[comp] = sortedInts(seasons)
	}
	return out
}

// ErrTeamNotFound is returned when a name cannot be resolved to a club.
type ErrTeamNotFound struct {
	Query       string
	Suggestions []string
}

func (e *ErrTeamNotFound) Error() string {
	if len(e.Suggestions) > 0 {
		return fmt.Sprintf("no team matching %q; did you mean: %s", e.Query, strings.Join(e.Suggestions, ", "))
	}
	return fmt.Sprintf("no team matching %q", e.Query)
}

// ResolveTeam maps a free-text club name onto a graph node. It tries, in
// order: canonical ID from the normaliser, exact folded display name, then a
// substring search over names and recorded aliases.
func (g *Graph) ResolveTeam(query string) (*Team, error) {
	q := strings.TrimSpace(query)
	if q == "" {
		return nil, &ErrTeamNotFound{Query: query}
	}
	if t, ok := g.teams[normalize.Resolve(q).ID]; ok {
		return t, nil
	}
	if t, ok := g.teams[strings.ToLower(q)]; ok {
		return t, nil
	}

	needle := normalize.Deaccent(q)
	var exact, prefix, sub []*Team
	for _, id := range g.teamOrder {
		t := g.teams[id]
		name := normalize.Deaccent(t.Name)
		switch {
		case name == needle:
			exact = append(exact, t)
		case strings.HasPrefix(name, needle):
			prefix = append(prefix, t)
		case strings.Contains(name, needle) || g.aliasContains(t, needle):
			sub = append(sub, t)
		}
	}
	for _, group := range [][]*Team{exact, prefix, sub} {
		if len(group) > 0 {
			// Prefer the club with the most matches: "Santos" should be the
			// Serie A side, not Santos-AP.
			sort.SliceStable(group, func(i, j int) bool { return group[i].MatchCount > group[j].MatchCount })
			return group[0], nil
		}
	}
	return nil, &ErrTeamNotFound{Query: query, Suggestions: g.suggest(needle)}
}

func (g *Graph) aliasContains(t *Team, needle string) bool {
	for _, a := range t.Aliases {
		if strings.Contains(normalize.Deaccent(a), needle) {
			return true
		}
	}
	return false
}

// suggest offers the closest names by shared prefix, for error messages.
func (g *Graph) suggest(needle string) []string {
	if len(needle) < 3 {
		return nil
	}
	var out []string
	head := needle[:3]
	for _, id := range g.teamOrder {
		if strings.HasPrefix(normalize.Deaccent(g.teams[id].Name), head) {
			out = append(out, g.teams[id].Name)
			if len(out) == 5 {
				break
			}
		}
	}
	return out
}

// TeamMatches returns the indexes of every match a club played, in date order.
func (g *Graph) TeamMatches(id string) []int {
	if t, ok := g.teams[id]; ok {
		return t.matchIdx
	}
	return nil
}
