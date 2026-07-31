// graph.go holds the assembled knowledge graph and the entity-resolution logic
// that turns a user's free-text club name into a canonical Team node.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// Graph is the in-memory knowledge graph: Team, Match, Competition and Player
// nodes plus the adjacency indexes used to answer queries quickly.
type Graph struct {
	Teams   map[string]*Team
	Matches []*Match
	Players []*Player
	Stats   LoadStats

	teamOrder   []*Team
	byTeam      map[string][]*Match
	byComp      map[string][]*Match
	byPair      map[string][]*Match
	clubPlayers map[string][]*Player
	playersByID map[int]*Player
	aliasIndex  map[string][]*Team // slug of a raw spelling -> teams
	baseIndex   map[string][]*Team // canonical base -> teams
	seasons     map[string]map[int]int
}

func newGraph() *Graph {
	return &Graph{
		Teams:       map[string]*Team{},
		byTeam:      map[string][]*Match{},
		byComp:      map[string][]*Match{},
		byPair:      map[string][]*Match{},
		clubPlayers: map[string][]*Player{},
		playersByID: map[int]*Player{},
		aliasIndex:  map[string][]*Team{},
		baseIndex:   map[string][]*Team{},
		seasons:     map[string]map[int]int{},
	}
}

// ---------------------------------------------------------------------------
// Entity resolution during load
// ---------------------------------------------------------------------------

// teamResolver learns, over a first pass across every raw team name, which club
// bases appear with which regions. A stateless spelling of a base seen with
// exactly one region can then be attributed to that region with confidence.
type teamResolver struct {
	regionsByBase map[string]map[string]int
}

func newTeamResolver() *teamResolver {
	return &teamResolver{regionsByBase: map[string]map[string]int{}}
}

func (r *teamResolver) observe(raw, hint string) {
	p := ParseTeamName(raw)
	region := p.Region
	if region == "" {
		region = normalizeHint(hint)
	}
	if region == "" {
		return
	}
	if r.regionsByBase[p.Base] == nil {
		r.regionsByBase[p.Base] = map[string]int{}
	}
	r.regionsByBase[p.Base][region]++
}

// resolve produces the canonical (id, parsed name, region) for a raw spelling.
//
// Precedence is: a region spelled out in the name, then the curated default for
// the club, then the dataset's state column, then a region that is the only one
// ever observed for this base. The curated default deliberately outranks the
// state column because novo_campeonato_brasileiro.csv mislabels Vitória (a
// Bahia club) as "ES" in 179 rows; trusting the column would split the club in
// two and corrupt every table it appears in.
func (r *teamResolver) resolve(raw, hint string) (string, ParsedName, string) {
	p := ParseTeamName(raw)
	region := p.Region
	if region == "" {
		region = p.DefaultRegion
	}
	if region == "" {
		region = normalizeHint(hint)
	}
	if region == "" {
		if seen := r.regionsByBase[p.Base]; len(seen) == 1 {
			for k := range seen {
				region = k
			}
		}
	}
	return TeamID(p.Base, region), p, region
}

func normalizeHint(hint string) string {
	hint = strings.ToUpper(strings.TrimSpace(hint))
	if isRegionCode(hint) {
		return hint
	}
	return ""
}

// ensureTeam resolves raw to a team ID, creating the Team node on first sight.
func (g *Graph) ensureTeam(r *teamResolver, raw, hint string) string {
	id, p, region := r.resolve(raw, hint)
	if id == "" {
		return ""
	}
	t, ok := g.Teams[id]
	if !ok {
		t = &Team{ID: id, Base: p.Base, Region: region}
		if IsBrazilianRegion(region) {
			t.State = RegionName(region)
			t.Country = "Brazil"
		} else if region != "" {
			t.Country = RegionName(region)
		}
		g.Teams[id] = t
		g.teamOrder = append(g.teamOrder, t)
	}
	t.Aliases = addAlias(t.Aliases, strings.TrimSpace(raw))
	if p.Clean != "" {
		t.Aliases = addAlias(t.Aliases, p.Clean)
	}
	return id
}

// linkClub attaches a FIFA club name to a Team node when one can be identified.
// FIFA 19 only licenses a handful of Brazilian clubs, so an unmatched club is
// the normal case.
//
// Name matching alone is not enough: FIFA also contains Boavista FC and CD
// Nacional of Portugal and Club América of Mexico, whose names collide with
// Boavista-RJ, Nacional-AM and América-MG. The squad's nationality mix is used
// as a second signal — a genuinely Brazilian club in this dataset fields an
// overwhelmingly Brazilian squad.
func (g *Graph) linkClub(r *teamResolver, club string, brazilianShare float64) string {
	if strings.TrimSpace(club) == "" {
		return ""
	}
	if brazilianShare < 0.6 {
		return ""
	}
	id, _, _ := r.resolve(club, "")
	if t, ok := g.Teams[id]; ok && t.Country == "Brazil" {
		return id
	}
	// Fall back to a base-only match against a Brazilian club.
	p := ParseTeamName(club)
	for _, t := range g.teamOrder {
		if t.Base == p.Base && t.Country == "Brazil" {
			return t.ID
		}
	}
	return ""
}

// ---------------------------------------------------------------------------
// Finalisation: display names and indexes
// ---------------------------------------------------------------------------

func (g *Graph) finalize() {
	for _, t := range g.Teams {
		t.Name = displayNameFor(t)
	}

	sort.SliceStable(g.Matches, func(i, j int) bool {
		if !g.Matches[i].Date.Equal(g.Matches[j].Date) {
			return g.Matches[i].Date.Before(g.Matches[j].Date)
		}
		return g.Matches[i].ID < g.Matches[j].ID
	})

	for _, m := range g.Matches {
		g.byTeam[m.HomeTeamID] = append(g.byTeam[m.HomeTeamID], m)
		g.byTeam[m.AwayTeamID] = append(g.byTeam[m.AwayTeamID], m)
		g.byComp[m.Competition] = append(g.byComp[m.Competition], m)
		g.byPair[pairKey(m.HomeTeamID, m.AwayTeamID)] = append(g.byPair[pairKey(m.HomeTeamID, m.AwayTeamID)], m)
		if g.seasons[m.Competition] == nil {
			g.seasons[m.Competition] = map[int]int{}
		}
		g.seasons[m.Competition][m.Season]++
		g.Teams[m.HomeTeamID].matchCount++
		g.Teams[m.AwayTeamID].matchCount++
	}

	for _, t := range g.Teams {
		sort.Strings(t.Aliases)
		g.baseIndex[t.Base] = append(g.baseIndex[t.Base], t)
		for _, a := range t.Aliases {
			s := Slug(a)
			g.aliasIndex[s] = appendUniqueTeam(g.aliasIndex[s], t)
		}
		g.aliasIndex[Slug(t.Name)] = appendUniqueTeam(g.aliasIndex[Slug(t.Name)], t)
		g.aliasIndex[t.ID] = appendUniqueTeam(g.aliasIndex[t.ID], t)
	}

	for _, p := range g.Players {
		g.playersByID[p.ID] = p
		if p.ClubTeamID != "" {
			g.clubPlayers[p.ClubTeamID] = append(g.clubPlayers[p.ClubTeamID], p)
		}
	}
	for id := range g.clubPlayers {
		sort.SliceStable(g.clubPlayers[id], func(i, j int) bool {
			return g.clubPlayers[id][i].Overall > g.clubPlayers[id][j].Overall
		})
	}

	sort.SliceStable(g.teamOrder, func(i, j int) bool {
		if g.teamOrder[i].matchCount != g.teamOrder[j].matchCount {
			return g.teamOrder[i].matchCount > g.teamOrder[j].matchCount
		}
		return g.teamOrder[i].Name < g.teamOrder[j].Name
	})
}

func appendUniqueTeam(list []*Team, t *Team) []*Team {
	for _, v := range list {
		if v == t {
			return list
		}
	}
	return append(list, t)
}

// displayNameFor prefers a curated name, then the most informative spelling
// actually observed (accented and reasonably long, but not a full legal name).
func displayNameFor(t *Team) string {
	if n, ok := canonicalDisplay[t.ID]; ok {
		return n
	}
	best := ""
	bestScore := -1 << 30
	for _, a := range t.Aliases {
		clean := ParseTeamName(a).Clean
		if clean == "" {
			continue
		}
		score := 0
		if clean != FoldASCII(clean) {
			score += 50 // keeps the accented spelling
		}
		score -= len(strings.Fields(clean)) * 3 // prefer short forms over legal names
		score -= abs(len(clean) - 12)
		if score > bestScore {
			bestScore, best = score, clean
		}
	}
	if best == "" {
		best = t.Base
	}
	if t.Region != "" && !IsBrazilianRegion(t.Region) {
		return fmt.Sprintf("%s (%s)", best, t.Region)
	}
	return best
}

func abs(v int) int {
	if v < 0 {
		return -v
	}
	return v
}

// ---------------------------------------------------------------------------
// Lookup API
// ---------------------------------------------------------------------------

// TeamMatch is a scored candidate produced by team resolution.
type TeamMatch struct {
	Team  *Team
	Score int
	How   string
}

// SearchTeams ranks clubs against a free-text query. Matching is diacritic- and
// case-insensitive and understands state suffixes ("Atletico-MG", "Atletico MG",
// "Atletico Mineiro" all reach the same club).
func (g *Graph) SearchTeams(query string, limit int) []TeamMatch {
	q := strings.TrimSpace(query)
	if q == "" {
		return nil
	}
	p := ParseTeamName(q)
	qSlug := Slug(q)

	seen := map[*Team]TeamMatch{}
	consider := func(t *Team, score int, how string) {
		if cur, ok := seen[t]; !ok || score > cur.Score {
			seen[t] = TeamMatch{Team: t, Score: score, How: how}
		}
	}

	// Exact canonical ID.
	if t, ok := g.Teams[qSlug]; ok {
		consider(t, 1000, "id")
	}
	// Exact ID built from the parsed name (handles "Atletico MG").
	region := p.Region
	if region == "" {
		region = p.DefaultRegion
	}
	if t, ok := g.Teams[TeamID(p.Base, region)]; ok {
		consider(t, 990, "canonical name")
	}
	if p.Region != "" {
		if t, ok := g.Teams[TeamID(p.Base, p.Region)]; ok {
			consider(t, 995, "name+state")
		}
	}
	// Exact raw spelling.
	for _, t := range g.aliasIndex[qSlug] {
		consider(t, 900, "alias")
	}
	// Exact base, possibly several clubs across states.
	for _, t := range g.baseIndex[p.Base] {
		consider(t, 800, "base name")
	}
	// Prefix / substring over every known spelling.
	if len(qSlug) >= 3 {
		for _, t := range g.teamOrder {
			for _, cand := range append([]string{t.Name, t.Base}, t.Aliases...) {
				cs := Slug(cand)
				switch {
				case cs == qSlug:
					consider(t, 850, "alias")
				case strings.HasPrefix(cs, qSlug):
					consider(t, 600, "prefix")
				case strings.Contains(cs, qSlug):
					consider(t, 400, "substring")
				}
			}
		}
	}

	out := make([]TeamMatch, 0, len(seen))
	for _, v := range seen {
		out = append(out, v)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Score != out[j].Score {
			return out[i].Score > out[j].Score
		}
		if out[i].Team.matchCount != out[j].Team.matchCount {
			return out[i].Team.matchCount > out[j].Team.matchCount
		}
		return out[i].Team.Name < out[j].Team.Name
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// AmbiguousTeamError reports that a query matched several clubs equally well.
type AmbiguousTeamError struct {
	Query      string
	Candidates []*Team
}

func (e *AmbiguousTeamError) Error() string {
	names := make([]string, 0, len(e.Candidates))
	for _, t := range e.Candidates {
		names = append(names, fmt.Sprintf("%s (%s)", t.Name, teamRegionLabel(t)))
	}
	return fmt.Sprintf("%q matches several clubs: %s — please be more specific",
		e.Query, strings.Join(names, ", "))
}

// UnknownTeamError reports that no club matched at all.
type UnknownTeamError struct {
	Query       string
	Suggestions []string
}

func (e *UnknownTeamError) Error() string {
	if len(e.Suggestions) == 0 {
		return fmt.Sprintf("no club matching %q is present in the datasets", e.Query)
	}
	return fmt.Sprintf("no club matching %q; did you mean %s?", e.Query, strings.Join(e.Suggestions, ", "))
}

// ResolveTeam maps a free-text club name onto exactly one Team node.
// It returns an *AmbiguousTeamError when the query is genuinely ambiguous
// (for example "Atletico", which exists in seven Brazilian states).
func (g *Graph) ResolveTeam(query string) (*Team, error) {
	cands := g.SearchTeams(query, 12)
	if len(cands) == 0 {
		return nil, &UnknownTeamError{Query: query}
	}
	best := cands[0]
	if len(cands) > 1 && cands[1].Score == best.Score {
		// A tie on score is only ambiguous if the runner-up is comparably
		// well represented in the data; otherwise the popular club wins.
		if cands[1].Team.matchCount*3 > best.Team.matchCount {
			tied := []*Team{}
			for _, c := range cands {
				if c.Score == best.Score {
					tied = append(tied, c.Team)
				}
			}
			return nil, &AmbiguousTeamError{Query: query, Candidates: tied}
		}
	}
	return best.Team, nil
}

func teamRegionLabel(t *Team) string {
	if t.Region == "" {
		return "unknown region"
	}
	return RegionName(t.Region)
}

// Team returns a club by canonical ID.
func (g *Graph) Team(id string) *Team { return g.Teams[id] }

// TeamMatches returns every match a club played, in chronological order.
func (g *Graph) TeamMatches(id string) []*Match { return g.byTeam[id] }

// PairMatches returns every meeting between two clubs.
func (g *Graph) PairMatches(a, b string) []*Match { return g.byPair[pairKey(a, b)] }

// CompetitionMatches returns every match of a competition.
func (g *Graph) CompetitionMatches(id string) []*Match { return g.byComp[id] }

// AllTeams returns clubs ordered by how often they appear in the match data.
func (g *Graph) AllTeams() []*Team { return g.teamOrder }

// Competitions returns the competition catalog with per-season coverage.
type CompetitionCoverage struct {
	Competition
	Seasons     []int `json:"seasons"`
	FirstSeason int   `json:"first_season"`
	LastSeason  int   `json:"last_season"`
	MatchCount  int   `json:"match_count"`
	TeamCount   int   `json:"team_count"`
}

// CompetitionCoverage describes every competition present in the graph.
func (g *Graph) CompetitionCoverage() []CompetitionCoverage {
	var out []CompetitionCoverage
	for _, id := range []string{CompSerieA, CompSerieB, CompSerieC, CompCopaDoBrasil, CompLibertadores} {
		ms := g.byComp[id]
		if len(ms) == 0 {
			continue
		}
		seasons := make([]int, 0, len(g.seasons[id]))
		for s := range g.seasons[id] {
			seasons = append(seasons, s)
		}
		sort.Ints(seasons)
		teams := map[string]bool{}
		for _, m := range ms {
			teams[m.HomeTeamID] = true
			teams[m.AwayTeamID] = true
		}
		cov := CompetitionCoverage{
			Competition: competitionCatalog[id],
			Seasons:     seasons,
			MatchCount:  len(ms),
			TeamCount:   len(teams),
		}
		if len(seasons) > 0 {
			cov.FirstSeason, cov.LastSeason = seasons[0], seasons[len(seasons)-1]
		}
		out = append(out, cov)
	}
	return out
}

// CompetitionName renders a competition ID for display.
func CompetitionName(id string) string {
	if c, ok := competitionCatalog[id]; ok {
		return c.Name
	}
	return id
}

// ResolveCompetition maps free text ("Brasileirão", "serie a", "libertadores")
// onto a competition ID.
func ResolveCompetition(q string) (string, error) {
	s := Slug(q)
	if s == "" {
		return "", nil
	}
	switch s {
	case "seriea", "a", "brasileirao", "brasileiraoseriea", "campeonatobrasileiro",
		"campeonatobrasileiroseriea", "brasileiraoa", "brasileirodeseriea", "brazilianseriea":
		return CompSerieA, nil
	case "serieb", "b", "brasileiraoserieb", "brasileiraob", "brazilianserieb":
		return CompSerieB, nil
	case "seriec", "c", "brasileiraoseriec", "brasileiraoc", "brazilianseriec":
		return CompSerieC, nil
	case "copadobrasil", "cup", "braziliancup", "copabrasil", "copadobrazil":
		return CompCopaDoBrasil, nil
	case "libertadores", "copalibertadores", "conmebollibertadores":
		return CompLibertadores, nil
	}
	for id, c := range competitionCatalog {
		if strings.Contains(Slug(c.Name), s) || strings.Contains(Slug(id), s) {
			return id, nil
		}
	}
	return "", fmt.Errorf("unknown competition %q (known: serie-a, serie-b, serie-c, copa-do-brasil, libertadores)", q)
}

// ToView converts a Team node to its wire form.
func (t *Team) ToView() TeamView {
	return TeamView{
		ID: t.ID, Name: t.Name, State: t.State, Country: t.Country,
		MatchCount: t.matchCount, Aliases: t.Aliases,
	}
}

// ToView converts a Match node to its wire form, resolving team names.
func (g *Graph) ToView(m *Match) MatchView {
	home := g.teamName(m.HomeTeamID)
	away := g.teamName(m.AwayTeamID)
	v := MatchView{
		Date:        FormatDate(m.Date),
		KickOff:     m.KickOff,
		Competition: CompetitionName(m.Competition),
		Season:      m.Season,
		Round:       m.Round,
		Stage:       m.Stage,
		HomeTeam:    home,
		AwayTeam:    away,
		HomeGoals:   m.HomeGoals,
		AwayGoals:   m.AwayGoals,
		Score:       fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals),
		Venue:       m.Venue,
		Stats:       m.Stats,
		Sources:     m.Sources,
	}
	switch {
	case m.HomeGoals > m.AwayGoals:
		v.Result = "home_win"
	case m.AwayGoals > m.HomeGoals:
		v.Result = "away_win"
	default:
		v.Result = "draw"
	}
	v.Summary = matchSummary(v)
	return v
}

func matchSummary(v MatchView) string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s: %s %d-%d %s (%s", v.Date, v.HomeTeam, v.HomeGoals, v.AwayGoals, v.AwayTeam, v.Competition)
	if v.Season > 0 {
		fmt.Fprintf(&b, " %d", v.Season)
	}
	if v.Stage != "" {
		fmt.Fprintf(&b, " %s", v.Stage)
	} else if v.Round > 0 {
		fmt.Fprintf(&b, " Round %d", v.Round)
	}
	b.WriteString(")")
	return b.String()
}

func (g *Graph) teamName(id string) string {
	if t, ok := g.Teams[id]; ok {
		return t.Name
	}
	return id
}

// ToViews converts a slice of matches.
func (g *Graph) ToViews(ms []*Match) []MatchView {
	out := make([]MatchView, 0, len(ms))
	for _, m := range ms {
		out = append(out, g.ToView(m))
	}
	return out
}
