// graph.go assembles the knowledge graph.
//
// Building happens in five passes:
//
//  1. every CSV is read (loader.go) into raw records;
//  2. every team spelling seen anywhere is grouped by canonical base, which is
//     what lets "Palmeiras-SP", "Palmeiras" and "Palmeiras - SP" become one node
//     while keeping "Atlético-MG" and "Atlético-PR" apart;
//  3. raw matches are turned into Match nodes with resolved team edges;
//  4. overlapping datasets are de-duplicated: each real fixture elects one
//     primary row, and the losing rows donate their extra columns (stadium from
//     the historic file, shots/corners from BR-Football) to the winner;
//  5. lookup indexes are built - by team, by competition/season, by player club
//     and nationality, plus the fuzzy name index used to resolve user input.
package soccer

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// Graph is the in-memory knowledge graph. It is read-only once built, so it is
// safe for concurrent use by the MCP server.
type Graph struct {
	matches  []*Match
	teams    map[string]*Team
	teamList []*Team
	players  []*Player

	byName        map[string][]*Team // fuzzy lookup key -> teams
	byBase        map[string][]*Team // canonical base -> clubs sharing it
	bySeason      map[string][]*Match
	playersByClub map[string][]*Player
	playersByNat  map[string][]*Player

	champions  []ChampionEntry
	titles     map[string][]Title
	sources    []SourceInfo
	unresolved []string
	dataDir    string
	loadedAt   time.Time
	loadTime   time.Duration
}

// Unresolved lists rows that could not be attached to two distinct clubs. It is
// exposed so tests and the dataset_info tool can assert the graph is complete.
func (g *Graph) Unresolved() []string { return g.unresolved }

// Load reads every dataset in dir and returns the assembled graph. dir may be
// the data/kaggle directory itself or any parent of it.
func Load(dir string) (*Graph, error) {
	start := time.Now()
	dataDir, err := FindDataDir(dir)
	if err != nil {
		return nil, err
	}

	var raws []*rawMatch
	var players []*Player
	g := &Graph{
		teams:         map[string]*Team{},
		byName:        map[string][]*Team{},
		byBase:        map[string][]*Team{},
		bySeason:      map[string][]*Match{},
		playersByClub: map[string][]*Player{},
		playersByNat:  map[string][]*Player{},
		dataDir:       dataDir,
	}
	for _, ds := range Datasets {
		res, err := loadFile(dataDir, ds)
		if err != nil {
			return nil, fmt.Errorf("loading %s: %w", ds.File, err)
		}
		raws = append(raws, res.matches...)
		players = append(players, res.players...)
		g.sources = append(g.sources, res.info)
	}

	g.buildTeams(raws)
	g.buildMatches(raws)
	g.labelCupStages()
	g.deduplicate()
	g.indexMatches()
	g.finalizeDisplayNames()
	g.attachPlayers(players)
	g.buildNameIndex()
	g.buildChampions()

	g.loadedAt = time.Now()
	g.loadTime = time.Since(start)
	return g, nil
}

// baseGroup collects every spelling that shares a canonical base.
type baseGroup struct {
	base    string
	byKey   map[string]*variantGroup // state/country key -> variants
	bareRaw map[string]int
	bare    int
}

// variantGroup is one club: a base plus a specific state or country.
type variantGroup struct {
	state   string
	country string
	count   int
	raws    map[string]int
	pretty  map[string]int
}

// buildTeams performs pass 2: group all spellings and mint one Team per club.
func (g *Graph) buildTeams(raws []*rawMatch) {
	groups := map[string]*baseGroup{}
	observe := func(p nameParts, raw string) {
		if p.empty() {
			return
		}
		bg := groups[p.Base]
		if bg == nil {
			bg = &baseGroup{base: p.Base, byKey: map[string]*variantGroup{}, bareRaw: map[string]int{}}
			groups[p.Base] = bg
		}
		if p.State == "" && p.Country == "" {
			bg.bare++
			bg.bareRaw[raw]++
			return
		}
		key := p.State + "/" + p.Country
		vg := bg.byKey[key]
		if vg == nil {
			vg = &variantGroup{state: p.State, country: p.Country, raws: map[string]int{}, pretty: map[string]int{}}
			bg.byKey[key] = vg
		}
		vg.count++
		vg.raws[raw]++
		vg.pretty[p.Pretty]++
	}
	for _, m := range raws {
		observe(m.homeParts, m.homeRaw)
		observe(m.awayParts, m.awayRaw)
	}

	for _, bg := range groups {
		switch len(bg.byKey) {
		case 0:
			// Nothing but bare spellings: one stateless club.
			vg := &variantGroup{raws: map[string]int{}, pretty: map[string]int{}}
			for raw, n := range bg.bareRaw {
				vg.raws[raw] += n
				vg.pretty[parseTeamName(raw).Pretty] += n
				vg.count += n
			}
			g.addTeam(bg.base, vg, false)
		case 1:
			// One state seen: bare spellings belong to it.
			for _, vg := range bg.byKey {
				for raw, n := range bg.bareRaw {
					vg.raws[raw] += n
					vg.pretty[parseTeamName(raw).Pretty] += n
					vg.count += n
				}
				g.addTeam(bg.base, vg, false)
			}
		default:
			// Several clubs share this base: keep them apart and qualify their
			// display names with the state.
			keys := make([]string, 0, len(bg.byKey))
			for k := range bg.byKey {
				keys = append(keys, k)
			}
			sort.Strings(keys)
			for _, k := range keys {
				g.addTeam(bg.base, bg.byKey[k], true)
			}
		}
	}

	g.teamList = make([]*Team, 0, len(g.teams))
	for _, t := range g.teams {
		g.teamList = append(g.teamList, t)
	}
	sort.Slice(g.teamList, func(i, j int) bool { return g.teamList[i].ID < g.teamList[j].ID })
	for _, t := range g.teamList {
		g.byBase[t.base] = append(g.byBase[t.base], t)
	}
}

// addTeam mints a Team node from a variant group. qualify forces the state to be
// part of the display name because a rival club shares the base name.
func (g *Graph) addTeam(base string, vg *variantGroup, qualify bool) {
	id := teamID(base, vg.state, vg.country)
	name := bestSpelling(vg.pretty, base)
	if name == "" {
		name = titleCase(base)
	}
	display := name
	if qualify {
		switch {
		case vg.country != "":
			display = fmt.Sprintf("%s (%s)", name, vg.country)
		case vg.state != "":
			display = fmt.Sprintf("%s-%s", name, vg.state)
		}
	} else if vg.country != "" {
		display = fmt.Sprintf("%s (%s)", name, vg.country)
	}
	aliases := make([]string, 0, len(vg.raws))
	for raw := range vg.raws {
		aliases = append(aliases, raw)
	}
	sort.Strings(aliases)
	if override, ok := displayOverrides[id]; ok {
		name = override
		if qualify && vg.state != "" {
			display = fmt.Sprintf("%s-%s", name, vg.state)
		} else {
			display = name
		}
	}
	g.teams[id] = &Team{
		ID: id, Name: name, Display: display,
		State: vg.state, Country: vg.country, Aliases: aliases,
		base: base,
	}
}

// displayOverrides pins the preferred modern spelling for clubs whose datasets
// disagree. Athletico Paranaense is spelled "Atlético" in rows from before its
// 2018 rebrand, which would otherwise win the accent tie-break.
var displayOverrides = map[string]string{
	"atletico-pr": "Athletico",
}

// finalizeDisplayNames drops the state suffix from the dominant club of a shared
// base once match counts are known, so the graph says "Flamengo" rather than
// "Flamengo-RJ" while still distinguishing "Atlético-MG" from "Athletico-PR".
func (g *Graph) finalizeDisplayNames() {
	for _, group := range g.byBase {
		if len(group) < 2 {
			continue
		}
		ranked := make([]*Team, len(group))
		copy(ranked, group)
		sort.SliceStable(ranked, func(i, j int) bool { return len(ranked[i].matchIdx) > len(ranked[j].matchIdx) })
		top, next := ranked[0], ranked[1]
		if len(top.matchIdx) >= 50 && len(top.matchIdx) >= 10*(len(next.matchIdx)+1) {
			top.Display = top.Name
		}
	}
}

// bestSpelling picks the nicest display spelling among the observed variants:
// prefer a spelling that matches the canonical base (so "Vasco da Gama" beats
// the abbreviated "Vasco"), then accented forms, then the most frequent, then
// the shortest.
func bestSpelling(counts map[string]int, base string) string {
	type cand struct {
		text    string
		count   int
		accent  int
		exact   bool
		badCaps int
	}
	var cands []cand
	for text, n := range counts {
		text = strings.TrimSpace(text)
		if text == "" {
			continue
		}
		cands = append(cands, cand{text, n, accentScore(text), foldKey(text) == base, miscapitalisedConnectives(text)})
	}
	if len(cands) == 0 {
		return ""
	}
	sort.Slice(cands, func(i, j int) bool {
		a, b := cands[i], cands[j]
		if a.exact != b.exact {
			return a.exact
		}
		if a.badCaps != b.badCaps {
			return a.badCaps < b.badCaps
		}
		if a.accent != b.accent {
			return a.accent > b.accent
		}
		if a.count != b.count {
			return a.count > b.count
		}
		if len(a.text) != len(b.text) {
			return len(a.text) < len(b.text)
		}
		return a.text < b.text
	})
	return cands[0].text
}

// portugueseConnectives are the small words that stay lower case in a properly
// written club name ("Vasco da Gama", not "Vasco Da Gama").
var portugueseConnectives = map[string]bool{
	"da": true, "de": true, "do": true, "das": true, "dos": true, "e": true, "y": true,
}

// miscapitalisedConnectives counts connectives written with a capital letter,
// used to prefer "Vasco da Gama" over the BR-Football spelling "Vasco Da Gama".
func miscapitalisedConnectives(s string) int {
	n := 0
	for i, w := range strings.Fields(s) {
		if i == 0 {
			continue
		}
		if portugueseConnectives[strings.ToLower(w)] && w != strings.ToLower(w) {
			n++
		}
	}
	return n
}

// resolveParts maps parsed name parts onto a club. An exact base+state hit wins;
// otherwise the clubs sharing the base are considered, preferring the curated
// default state and finally the club with the most matches. byBase is ordered by
// team ID, so the fallback is deterministic.
func (g *Graph) resolveParts(p nameParts) (*Team, bool) {
	if p.empty() {
		return nil, false
	}
	if t, ok := g.teams[teamID(p.Base, p.State, p.Country)]; ok {
		return t, true
	}
	group := g.byBase[p.Base]
	switch len(group) {
	case 0:
		return nil, false
	case 1:
		return group[0], true
	}
	if p.Country != "" {
		for _, t := range group {
			if strings.EqualFold(t.Country, p.Country) {
				return t, true
			}
		}
	}
	if p.State != "" {
		for _, t := range group {
			if strings.EqualFold(t.State, p.State) {
				return t, true
			}
		}
	}
	if def := defaultStates[p.Base]; def != "" {
		for _, t := range group {
			if strings.EqualFold(t.State, def) {
				return t, true
			}
		}
	}
	best := group[0]
	for _, t := range group[1:] {
		if len(t.matchIdx) > len(best.matchIdx) {
			best = t
		}
	}
	return best, true
}

// buildMatches performs pass 3: raw rows become Match nodes with team edges.
func (g *Graph) buildMatches(raws []*rawMatch) {
	g.matches = make([]*Match, 0, len(raws))
	for i, r := range raws {
		home, okH := g.resolveParts(r.homeParts)
		away, okA := g.resolveParts(r.awayParts)
		if !okH || !okA || home == away {
			// Either a spelling no other row shares, or two spellings that
			// collapsed onto the same club: neither can be scored reliably.
			g.unresolved = append(g.unresolved, fmt.Sprintf("%s: %s vs %s", r.source, r.homeRaw, r.awayRaw))
			continue
		}
		m := &Match{
			ID:          fmt.Sprintf("%s-%06d", r.source, i),
			Source:      r.source,
			Competition: r.competition,
			Season:      r.season,
			Round:       r.round,
			Stage:       r.stage,
			Date:        r.date,
			HasDate:     r.hasDate,
			HomeID:      home.ID,
			AwayID:      away.ID,
			HomeRaw:     r.homeRaw,
			AwayRaw:     r.awayRaw,
			HomeGoals:   r.homeGoals,
			AwayGoals:   r.awayGoals,
			Venue:       r.venue,
			Stats:       r.stats,
			home:        home,
			away:        away,
		}
		g.matches = append(g.matches, m)
	}
	sort.SliceStable(g.matches, func(i, j int) bool {
		a, b := g.matches[i], g.matches[j]
		if a.HasDate != b.HasDate {
			return a.HasDate
		}
		if !a.Date.Equal(b.Date) {
			return a.Date.Before(b.Date)
		}
		return a.ID < b.ID
	})
}

// cupStageNames labels Copa do Brasil rounds counting back from the final. The
// file only numbers rounds 1..8 and the number of the final varies by season.
var cupStageNames = []string{"final", "semifinals", "quarterfinals", "round of 16", "round of 32", "round of 64", "round of 128"}

// labelCupStages turns Copa do Brasil round numbers into stage names by working
// backwards from the last round played in each season.
func (g *Graph) labelCupStages() {
	maxRound := map[int]int{}
	for _, m := range g.matches {
		if m.Competition != CopaDoBrasil || m.Source != "copa_do_brasil" {
			continue
		}
		if m.Round > maxRound[m.Season] {
			maxRound[m.Season] = m.Round
		}
	}
	// A season whose data stops early (2021 in the provided file) must not have
	// its last recorded round labelled "final".
	complete := map[int]bool{}
	for season, r := range maxRound {
		count := 0
		for _, m := range g.matches {
			if m.Competition == CopaDoBrasil && m.Source == "copa_do_brasil" && m.Season == season && m.Round == r {
				count++
			}
		}
		complete[season] = count <= 2
	}
	for _, m := range g.matches {
		if m.Competition != CopaDoBrasil || m.Source != "copa_do_brasil" || m.Round == 0 {
			continue
		}
		last := maxRound[m.Season]
		if !complete[m.Season] {
			continue
		}
		back := last - m.Round
		if back >= 0 && back < len(cupStageNames) {
			m.Stage = cupStageNames[back]
		}
	}
}

// sourceRank gives the preferred dataset for a competition; lower wins. The
// dedicated per-competition files carry explicit seasons and rounds, so they
// beat the wide BR-Football export, which in turn beats nothing else.
func sourceRank(comp Competition, source string) int {
	switch comp {
	case SerieA:
		switch source {
		case "brasileirao":
			return 0
		case "historic_brasileirao":
			return 1
		case "br_football":
			return 2
		}
	case CopaDoBrasil:
		switch source {
		case "copa_do_brasil":
			return 0
		case "br_football":
			return 1
		}
	}
	return 0
}

// fixtureKey identifies a real-world fixture independently of which file it came
// from: the same competition, season and home/away pair.
func fixtureKey(m *Match) string {
	return fmt.Sprintf("%s|%d|%s|%s", m.Competition, m.Season, m.HomeID, m.AwayID)
}

// deduplicate performs pass 4. Serie A 2014-2019 appears in three files; without
// this every aggregate would triple count. The winning row also absorbs columns
// that only the losing files provide.
func (g *Graph) deduplicate() {
	groups := map[string][]*Match{}
	for _, m := range g.matches {
		k := fixtureKey(m)
		groups[k] = append(groups[k], m)
	}
	for _, group := range groups {
		if len(group) == 1 {
			group[0].primary = true
			continue
		}
		best := sourceRank(group[0].Competition, group[0].Source)
		for _, m := range group[1:] {
			if r := sourceRank(m.Competition, m.Source); r < best {
				best = r
			}
		}
		var primaries, others []*Match
		for _, m := range group {
			if sourceRank(m.Competition, m.Source) == best {
				m.primary = true
				primaries = append(primaries, m)
			} else {
				others = append(others, m)
			}
		}
		for _, dup := range others {
			target := nearestMatch(primaries, dup)
			if target == nil {
				continue
			}
			target.dupes = append(target.dupes, dup.Source)
			enrich(target, dup)
		}
	}
}

// nearestMatch picks the primary row closest in time to a duplicate row, which
// matters for the rare fixture that a season plays twice at the same venue.
func nearestMatch(primaries []*Match, dup *Match) *Match {
	var best *Match
	var bestDelta time.Duration
	for _, p := range primaries {
		if !p.HasDate || !dup.HasDate {
			if best == nil {
				best = p
			}
			continue
		}
		d := p.Date.Sub(dup.Date)
		if d < 0 {
			d = -d
		}
		if best == nil || d < bestDelta {
			best, bestDelta = p, d
		}
	}
	return best
}

// enrich copies information a duplicate row has and the primary row lacks.
func enrich(primary, dup *Match) {
	if primary.Stats == nil && dup.Stats != nil {
		primary.Stats = dup.Stats
	}
	if primary.Venue == "" && dup.Venue != "" {
		primary.Venue = dup.Venue
	}
	if primary.Round == 0 && dup.Round != 0 {
		primary.Round = dup.Round
	}
	if primary.Stage == "" && dup.Stage != "" {
		primary.Stage = dup.Stage
	}
	if !primary.HasDate && dup.HasDate {
		primary.Date, primary.HasDate = dup.Date, true
	}
}

// seasonKey indexes matches by competition and season.
func seasonKey(comp Competition, season int) string { return fmt.Sprintf("%s|%d", comp, season) }

// indexMatches performs pass 5 for matches: per team and per competition/season.
func (g *Graph) indexMatches() {
	for i, m := range g.matches {
		if !m.primary {
			continue
		}
		m.home.matchIdx = append(m.home.matchIdx, i)
		m.away.matchIdx = append(m.away.matchIdx, i)
		k := seasonKey(m.Competition, m.Season)
		g.bySeason[k] = append(g.bySeason[k], m)
	}
}

// attachPlayers links FIFA rows to clubs in the graph and indexes them.
func (g *Graph) attachPlayers(players []*Player) {
	g.players = players
	g.linkClubs(players)
	for _, p := range players {
		nat := foldKey(p.Nationality)
		g.playersByNat[nat] = append(g.playersByNat[nat], p)
	}
	for _, list := range g.playersByClub {
		sortPlayersByRating(list)
	}
	for _, list := range g.playersByNat {
		sortPlayersByRating(list)
	}
}

func sortPlayersByRating(list []*Player) {
	sort.SliceStable(list, func(i, j int) bool {
		if list[i].Overall != list[j].Overall {
			return list[i].Overall > list[j].Overall
		}
		return list[i].Name < list[j].Name
	})
}

// linkClubs joins the FIFA player rows to clubs in the match graph.
//
// Name matching alone is not enough: "FC Barcelona" shares a base with the
// Ecuadorian Barcelona that plays in the Libertadores file. A club therefore
// only links when the evidence agrees with the name - a Brazilian club must have
// a squad that is mostly Brazilian, and a foreign club must match by full name
// rather than by base alone.
func (g *Graph) linkClubs(players []*Player) {
	byClub := map[string][]*Player{}
	var order []string
	for _, p := range players {
		if p.Club == "" {
			continue
		}
		if _, seen := byClub[p.Club]; !seen {
			order = append(order, p.Club)
		}
		byClub[p.Club] = append(byClub[p.Club], p)
	}
	sort.Strings(order)
	for _, club := range order {
		squad := byClub[club]
		t, ok := g.resolveParts(parseTeamName(club))
		if !ok {
			continue
		}
		if t.State != "" {
			// A club with a Brazilian state suffix: require a Brazilian squad.
			if majorityNationality(squad) != "brazil" {
				continue
			}
		} else if foldKey(club) != foldKey(t.Name) && foldKey(club) != foldKey(t.Display) {
			// A foreign or state-less club: require the whole name to match.
			continue
		}
		for _, p := range squad {
			p.ClubTeamID = t.ID
			g.playersByClub[t.ID] = append(g.playersByClub[t.ID], p)
		}
	}
}

// majorityNationality returns the folded nationality shared by more than half of
// a squad, or "" when no nationality has a majority.
func majorityNationality(squad []*Player) string {
	counts := map[string]int{}
	for _, p := range squad {
		counts[foldKey(p.Nationality)]++
	}
	for nat, n := range counts {
		if n*2 > len(squad) {
			return nat
		}
	}
	return ""
}

// buildNameIndex registers every way a user might name a team.
func (g *Graph) buildNameIndex() {
	add := func(key string, t *Team) {
		key = foldKey(key)
		if key == "" {
			return
		}
		for _, existing := range g.byName[key] {
			if existing == t {
				return
			}
		}
		g.byName[key] = append(g.byName[key], t)
	}
	for _, t := range g.teamList {
		add(t.ID, t)
		add(t.Name, t)
		add(t.Display, t)
		if t.State != "" {
			add(t.Name+" "+t.State, t)
		}
		for _, a := range t.Aliases {
			add(a, t)
			if p := parseTeamName(a); !p.empty() {
				add(p.Base, t)
				add(p.Pretty, t)
			}
		}
	}
	for _, entry := range nicknameTable {
		t, _, err := g.ResolveTeam(entry.Club)
		if err != nil || t == nil {
			continue
		}
		t.Nicknames = append(t.Nicknames, entry.Names...)
		for _, n := range entry.Names {
			add(n, t)
		}
	}
	// Sort each bucket so the club with the most matches answers first.
	for _, list := range g.byName {
		sort.SliceStable(list, func(i, j int) bool { return len(list[i].matchIdx) > len(list[j].matchIdx) })
	}
}

// ErrUnknownTeam is returned when no club can be matched to the user's input.
type ErrUnknownTeam struct {
	Query       string
	Suggestions []string
}

func (e *ErrUnknownTeam) Error() string {
	if len(e.Suggestions) > 0 {
		return fmt.Sprintf("unknown team %q; did you mean %s?", e.Query, strings.Join(e.Suggestions, ", "))
	}
	return fmt.Sprintf("unknown team %q", e.Query)
}

// ResolveTeam maps free-form user input to a club. It returns the best match
// plus any other plausible candidates, so callers can tell the user when their
// query was ambiguous ("Atlético" matches four different clubs).
func (g *Graph) ResolveTeam(query string) (*Team, []*Team, error) {
	q := foldKey(query)
	if q == "" {
		return nil, nil, &ErrUnknownTeam{Query: query}
	}
	if hits := g.byName[q]; len(hits) > 0 {
		return hits[0], hits[1:], nil
	}
	p := parseTeamName(query)
	if !p.empty() {
		if t, ok := g.teams[teamID(p.Base, p.State, p.Country)]; ok {
			return t, nil, nil
		}
		if hits := g.byName[foldKey(p.Base)]; len(hits) > 0 {
			return hits[0], hits[1:], nil
		}
		if t, ok := g.resolveParts(p); ok {
			return t, nil, nil
		}
	}
	// Fall back to prefix then substring matching over every known key.
	var prefix, contains []*Team
	seen := map[*Team]bool{}
	for key, list := range g.byName {
		var bucket *[]*Team
		switch {
		case strings.HasPrefix(key, q):
			bucket = &prefix
		case strings.Contains(key, q):
			bucket = &contains
		default:
			continue
		}
		for _, t := range list {
			if seen[t] {
				continue
			}
			seen[t] = true
			*bucket = append(*bucket, t)
		}
	}
	cands := append(prefix, contains...)
	if len(cands) == 0 {
		return nil, nil, &ErrUnknownTeam{Query: query, Suggestions: g.suggestTeams(q, 5)}
	}
	sort.SliceStable(cands, func(i, j int) bool { return len(cands[i].matchIdx) > len(cands[j].matchIdx) })
	return cands[0], cands[1:], nil
}

// suggestTeams offers the closest known names for an unmatched query.
func (g *Graph) suggestTeams(q string, n int) []string {
	type scored struct {
		name  string
		score int
	}
	var out []scored
	for _, t := range g.teamList {
		s := similarity(q, foldKey(t.Name))
		if s > 0 {
			out = append(out, scored{t.Display, s})
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].score != out[j].score {
			return out[i].score > out[j].score
		}
		return out[i].name < out[j].name
	})
	var names []string
	for i := 0; i < len(out) && i < n; i++ {
		names = append(names, out[i].name)
	}
	return names
}

// similarity counts shared leading characters plus shared trigrams; good enough
// to catch typos without pulling in a Levenshtein implementation.
func similarity(a, b string) int {
	score := 0
	for i := 0; i < len(a) && i < len(b) && a[i] == b[i]; i++ {
		score += 2
	}
	if len(a) >= 3 && len(b) >= 3 {
		set := map[string]bool{}
		for i := 0; i+3 <= len(a); i++ {
			set[a[i:i+3]] = true
		}
		for i := 0; i+3 <= len(b); i++ {
			if set[b[i:i+3]] {
				score++
			}
		}
	}
	return score
}

// Team returns a club by canonical ID.
func (g *Graph) Team(id string) (*Team, bool) {
	t, ok := g.teams[id]
	return t, ok
}

// Teams returns every club, ordered by ID.
func (g *Graph) Teams() []*Team { return g.teamList }

// Matches returns the de-duplicated match list (one row per real fixture).
func (g *Graph) Matches() []*Match {
	out := make([]*Match, 0, len(g.matches))
	for _, m := range g.matches {
		if m.primary {
			out = append(out, m)
		}
	}
	return out
}

// Players returns every FIFA player row.
func (g *Graph) Players() []*Player { return g.players }

// Sources describes what each file contributed.
func (g *Graph) Sources() []SourceInfo { return g.sources }

// DataDir is the directory the CSV files were read from.
func (g *Graph) DataDir() string { return g.dataDir }

// LoadDuration reports how long building the graph took.
func (g *Graph) LoadDuration() time.Duration { return g.loadTime }

// teamMatches returns the primary matches a club played, oldest first.
func (g *Graph) teamMatches(t *Team) []*Match {
	out := make([]*Match, 0, len(t.matchIdx))
	for _, i := range t.matchIdx {
		out = append(out, g.matches[i])
	}
	return out
}

// SeasonMatches returns the primary matches of one competition season.
func (g *Graph) SeasonMatches(comp Competition, season int) []*Match {
	return g.bySeason[seasonKey(comp, season)]
}

// Seasons lists the seasons available for a competition, ascending.
func (g *Graph) Seasons(comp Competition) []int {
	seen := map[int]bool{}
	for _, m := range g.matches {
		if m.primary && m.Competition == comp {
			seen[m.Season] = true
		}
	}
	out := make([]int, 0, len(seen))
	for s := range seen {
		out = append(out, s)
	}
	sort.Ints(out)
	return out
}

// Stats summarises the graph, used by the dataset_info tool and the tests.
type Stats struct {
	Teams            int            `json:"teams"`
	Matches          int            `json:"matches"`
	MatchRows        int            `json:"match_rows_including_duplicates"`
	Players          int            `json:"players"`
	Competitions     map[string]int `json:"matches_by_competition"`
	SeasonRange      string         `json:"season_range"`
	BrazilianPlayers int            `json:"brazilian_players"`
	LinkedClubs      int            `json:"clubs_with_squad_data"`
	LoadMillis       int64          `json:"load_millis"`
}

// Stats computes the summary counters for the whole graph.
func (g *Graph) Stats() Stats {
	s := Stats{
		Teams:        len(g.teamList),
		MatchRows:    len(g.matches),
		Players:      len(g.players),
		Competitions: map[string]int{},
		LoadMillis:   g.loadTime.Milliseconds(),
	}
	minSeason, maxSeason := 0, 0
	for _, m := range g.matches {
		if !m.primary {
			continue
		}
		s.Matches++
		s.Competitions[string(m.Competition)]++
		if minSeason == 0 || m.Season < minSeason {
			minSeason = m.Season
		}
		if m.Season > maxSeason {
			maxSeason = m.Season
		}
	}
	s.SeasonRange = fmt.Sprintf("%d-%d", minSeason, maxSeason)
	s.BrazilianPlayers = len(g.playersByNat[foldKey("Brazil")])
	s.LinkedClubs = len(g.playersByClub)
	return s
}
