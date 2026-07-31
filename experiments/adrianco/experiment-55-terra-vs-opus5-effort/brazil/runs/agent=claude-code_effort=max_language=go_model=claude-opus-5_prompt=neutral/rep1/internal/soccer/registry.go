// registry.go turns the many raw spellings of a club into one canonical Team.
//
// Resolution order, both while ingesting CSV rows and when answering a user
// query, is: curated alias -> exact canonical key (base + state/country) ->
// inferred state (a bare "Fluminense" joins "Fluminense-RJ" when RJ is the only
// state ever seen for that base) -> prefix/substring -> fuzzy suggestion.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// TeamRegistry owns the canonical Team set and every mapping into it.
type TeamRegistry struct {
	teams      map[string]*Team // id -> team
	aliasIndex map[string]string
	rawIndex   map[string]*Team // raw spelling -> team (populated by Build)
	observed   map[string]int   // raw spelling -> times seen
	byBase     map[string][]*Team
	built      bool
}

// staticAliasIndex maps every curated spelling (normalised) to a canonical
// team id. It is built once and copied into each registry.
var staticAliasIndex = func() map[string]string {
	idx := map[string]string{}
	for _, ct := range canonicalTeams {
		idx[ct.ID] = ct.ID
		for _, alias := range ct.Aliases {
			n := NormalizeTeamName(alias)
			idx[n.Key()] = ct.ID
			if n.Qualifier == "" && n.Base != "" {
				// A bare alias also claims the unqualified name, which is how
				// "Botafogo" resolves to Botafogo-RJ.
				idx[n.Base] = ct.ID
			}
		}
		n := NormalizeTeamName(ct.Name)
		if _, ok := idx[n.Key()]; !ok {
			idx[n.Key()] = ct.ID
		}
	}
	return idx
}()

// hasCuratedBareName reports whether a name without a state suffix already
// identifies a club on its own ("Vitória" is Vitória-BA, but "América" is not
// enough to tell América-MG from América-RN).
func hasCuratedBareName(name string) bool {
	n := NormalizeTeamName(name)
	if n.Qualifier != "" || n.Base == "" {
		return false
	}
	_, ok := staticAliasIndex[n.Base]
	return ok
}

// NewTeamRegistry creates an empty registry seeded with the curated aliases.
func NewTeamRegistry() *TeamRegistry {
	r := &TeamRegistry{
		teams:      map[string]*Team{},
		aliasIndex: make(map[string]string, len(staticAliasIndex)),
		rawIndex:   map[string]*Team{},
		observed:   map[string]int{},
		byBase:     map[string][]*Team{},
	}
	for k, v := range staticAliasIndex {
		r.aliasIndex[k] = v
	}
	return r
}

// Observe records a raw team spelling seen in a dataset. All spellings must be
// observed before Build is called.
func (r *TeamRegistry) Observe(raw string) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return
	}
	r.observed[raw]++
}

var curatedByID = func() map[string]CanonTeam {
	m := make(map[string]CanonTeam, len(canonicalTeams))
	for _, ct := range canonicalTeams {
		m[ct.ID] = ct
	}
	return m
}()

// Build assigns every observed spelling to a canonical team.
func (r *TeamRegistry) Build() {
	if r.built {
		return
	}
	type entry struct {
		raw  string
		name TeamName
		id   string
	}
	entries := make([]entry, 0, len(r.observed))
	raws := make([]string, 0, len(r.observed))
	for raw := range r.observed {
		raws = append(raws, raw)
	}
	sort.Strings(raws) // deterministic team creation order

	// Pass 1: curated aliases, and collect the state qualifiers seen per base
	// for the inference in pass 2.
	statesByBase := map[string]map[string]bool{}
	for _, raw := range raws {
		n := NormalizeTeamName(raw)
		e := entry{raw: raw, name: n}
		if id, ok := r.aliasIndex[n.Key()]; ok {
			e.id = id
		} else if id, ok := r.aliasIndex[n.Base]; ok && r.qualifierAgrees(id, n) {
			e.id = id
		}
		if e.id == "" && n.Qualifier != "" && n.IsState {
			if statesByBase[n.Base] == nil {
				statesByBase[n.Base] = map[string]bool{}
			}
			statesByBase[n.Base][n.Qualifier] = true
		}
		entries = append(entries, e)
	}

	// Pass 2: canonical key, with single-state inference for bare names.
	for i := range entries {
		e := &entries[i]
		if e.id != "" {
			continue
		}
		n := e.name
		if n.Base == "" {
			continue
		}
		switch {
		case n.Qualifier != "":
			e.id = n.Key()
		default:
			states := statesByBase[n.Base]
			if len(states) == 1 {
				for s := range states {
					e.id = n.Base + "-" + strings.ToLower(s)
				}
				e.id = strings.ReplaceAll(e.id, " ", "-")
			} else {
				e.id = strings.ReplaceAll(n.Base, " ", "-")
			}
		}
	}

	// Materialise teams.
	for _, e := range entries {
		if e.id == "" {
			continue
		}
		t := r.teams[e.id]
		if t == nil {
			t = &Team{ID: e.id}
			if ct, ok := curatedByID[e.id]; ok {
				t.Name, t.State, t.Country, t.Curated = ct.Name, ct.State, ct.Country, true
			} else {
				if e.name.IsState {
					t.State = e.name.Qualifier
					t.Country = "BRA"
				} else if e.name.Qualifier != "" {
					t.Country = e.name.Qualifier
				}
			}
			r.teams[e.id] = t
		}
		t.Aliases = append(t.Aliases, e.raw)
		r.rawIndex[e.raw] = t
	}

	// Pick a display name for the teams that are not curated, recover their
	// state/country from the canonical id, and index everything by base.
	byDisplay := map[string][]*Team{}
	for _, t := range r.teams {
		sort.Strings(t.Aliases)
		if !t.Curated {
			if state, country, ok := qualifierOfID(t.ID); ok {
				t.State, t.Country = state, country
			}
		}
		if t.Name == "" {
			t.Name = stripQualifierSuffix(bestDisplayName(t.Aliases))
		}
		byDisplay[Fold(t.Name)] = append(byDisplay[Fold(t.Name)], t)
	}
	// Two clubs must never share a display name: "Ferroviário" from Ceará and
	// from Paraná keep their state suffix. A curated club keeps its plain name
	// (Flamengo stays Flamengo even though Flamengo-PI plays in the cup).
	for _, sharing := range byDisplay {
		if len(sharing) < 2 {
			continue
		}
		curated := false
		for _, t := range sharing {
			curated = curated || t.Curated
		}
		for _, t := range sharing {
			if curated && t.Curated {
				continue
			}
			switch {
			case t.State != "":
				t.Name += "-" + t.State
			case t.Country != "":
				t.Name += " (" + t.Country + ")"
			}
		}
	}
	for _, t := range r.teams {
		base := NormalizeTeamName(t.Name).Base
		r.byBase[base] = append(r.byBase[base], t)
		if b := NormalizeTeamName(t.ID).Base; b != base {
			r.byBase[b] = append(r.byBase[b], t)
		}
	}
	r.built = true
}

// qualifierAgrees decides whether a name that carries a state or country may
// use the curated club found for its bare base. "Atlético Paranaense - PR" is
// Athletico-PR because the states agree; "Flamengo - PI" is a different club
// from Flamengo (RJ) because they disagree.
func (r *TeamRegistry) qualifierAgrees(id string, n TeamName) bool {
	if n.Qualifier == "" {
		return true
	}
	ct, ok := curatedByID[id]
	if !ok {
		return false
	}
	if n.IsState {
		return strings.EqualFold(ct.State, n.Qualifier)
	}
	return strings.EqualFold(ct.Country, n.Qualifier)
}

// qualifierOfID recovers the state or country that a generated id ends with.
func qualifierOfID(id string) (state, country string, ok bool) {
	i := strings.LastIndex(id, "-")
	if i <= 0 {
		return "", "", false
	}
	suffix := strings.ToUpper(id[i+1:])
	if _, isState := BrazilianStates[suffix]; isState {
		return suffix, "BRA", true
	}
	if _, isCountry := CountryNames[suffix]; isCountry {
		return "", suffix, true
	}
	return "", "", false
}

// stripQualifierSuffix removes a trailing state or country marker from a
// display name, since Team keeps those in their own fields.
func stripQualifierSuffix(name string) string {
	n := NormalizeTeamName(name)
	if n.Qualifier == "" {
		return name
	}
	trimmed := strings.TrimRight(name, " ")
	for _, sep := range []string{" - ", "-", " (", " "} {
		if i := strings.LastIndex(trimmed, sep); i > 0 {
			tail := strings.Trim(trimmed[i+len(sep):], " ()")
			if strings.EqualFold(tail, n.Qualifier) || (len(tail) == 3 && countryCodes[Fold(tail)] == n.Qualifier) {
				return strings.TrimSpace(trimmed[:i])
			}
		}
	}
	return name
}

// bestDisplayName prefers a spelling that keeps its accents and is not padded
// with club-type noise: "Águia Negra-MS" beats "AGUIA NEGRA MS".
func bestDisplayName(aliases []string) string {
	best, bestScore := "", -1<<30
	for _, a := range aliases {
		score := 0
		if a != Fold(a) {
			score += 40 // has accents or capitals
		}
		for _, r := range a {
			if r > 127 {
				score += 10
				break
			}
		}
		score -= len(a)
		if score > bestScore {
			best, bestScore = a, score
		}
	}
	return best
}

// Resolve maps a raw dataset spelling to its canonical team. It only works
// after Build and only for spellings that were observed.
func (r *TeamRegistry) Resolve(raw string) *Team {
	return r.rawIndex[strings.TrimSpace(raw)]
}

// Team returns a team by canonical id.
func (r *TeamRegistry) Team(id string) *Team { return r.teams[id] }

// Teams returns every canonical team, sorted by name.
func (r *TeamRegistry) Teams() []*Team {
	out := make([]*Team, 0, len(r.teams))
	for _, t := range r.teams {
		out = append(out, t)
	}
	sort.Slice(out, func(i, j int) bool { return Fold(out[i].Name) < Fold(out[j].Name) })
	return out
}

// Len reports how many canonical teams exist.
func (r *TeamRegistry) Len() int { return len(r.teams) }

// AmbiguousError is returned when a query matches several clubs and none of
// them is a clear winner.
type AmbiguousError struct {
	Query      string
	Candidates []*Team
}

func (e *AmbiguousError) Error() string {
	names := make([]string, 0, len(e.Candidates))
	for _, c := range e.Candidates {
		names = append(names, fmt.Sprintf("%s (%s)", c.Name, c.ID))
	}
	return fmt.Sprintf("team %q is ambiguous: %s", e.Query, strings.Join(names, ", "))
}

// NotFoundError is returned when nothing matches, carrying suggestions.
type NotFoundError struct {
	Query       string
	Suggestions []string
}

func (e *NotFoundError) Error() string {
	if len(e.Suggestions) == 0 {
		return fmt.Sprintf("no team matches %q", e.Query)
	}
	return fmt.Sprintf("no team matches %q; did you mean: %s", e.Query, strings.Join(e.Suggestions, ", "))
}

// Lookup resolves free text typed by a user (or an LLM) to a team.
//
// Exact identifiers and curated aliases win outright. Otherwise the best
// prefix/substring candidate is returned together with the alternatives, and a
// genuinely ambiguous query (equally strong candidates) yields an
// *AmbiguousError listing them.
func (r *TeamRegistry) Lookup(query string) (*Team, []*Team, error) {
	q := strings.TrimSpace(query)
	if q == "" {
		return nil, nil, &NotFoundError{Query: query}
	}
	if t, ok := r.teams[Fold(q)]; ok {
		return t, nil, nil
	}
	n := NormalizeTeamName(q)
	if id, ok := r.aliasIndex[n.Key()]; ok {
		if t := r.teams[id]; t != nil {
			return t, nil, nil
		}
	}
	if id, ok := r.aliasIndex[n.Base]; ok && r.qualifierAgrees(id, n) {
		if t := r.teams[id]; t != nil {
			return t, nil, nil
		}
	}
	if t, ok := r.teams[n.Key()]; ok {
		return t, nil, nil
	}

	// Base match (ignores the state/country qualifier unless one was given).
	var cands []*Team
	seen := map[string]bool{}
	add := func(t *Team) {
		if t != nil && !seen[t.ID] {
			seen[t.ID] = true
			cands = append(cands, t)
		}
	}
	for _, t := range r.byBase[n.Base] {
		if n.Qualifier != "" && !strings.EqualFold(t.State, n.Qualifier) && !strings.EqualFold(t.Country, n.Qualifier) {
			continue
		}
		add(t)
	}
	if len(cands) == 0 {
		// Prefix, then substring, over canonical names and observed aliases.
		for _, mode := range []string{"prefix", "contains"} {
			for _, t := range r.Teams() {
				hay := append([]string{t.Name, t.ID}, t.Aliases...)
				for _, h := range hay {
					hb := NormalizeTeamName(h).Base
					hit := false
					if mode == "prefix" {
						hit = strings.HasPrefix(hb, n.Base)
					} else {
						hit = strings.Contains(hb, n.Base)
					}
					if hit {
						if n.Qualifier != "" && !strings.EqualFold(t.State, n.Qualifier) && !strings.EqualFold(t.Country, n.Qualifier) {
							continue
						}
						add(t)
						break
					}
				}
			}
			if len(cands) > 0 {
				break
			}
		}
	}

	if len(cands) == 0 {
		return nil, nil, &NotFoundError{Query: query, Suggestions: r.Suggest(query, 5)}
	}

	// With several candidates left, only a club that dwarfs the others in the
	// data is assumed to be the one meant - "Ferroviário" or "América" are
	// reported as ambiguous so the caller can choose, while a stray minor club
	// does not stop a query about a big one.
	sort.SliceStable(cands, func(i, j int) bool {
		if cands[i].Matches != cands[j].Matches {
			return cands[i].Matches > cands[j].Matches
		}
		return Fold(cands[i].Name) < Fold(cands[j].Name)
	})
	if len(cands) > 1 && cands[0].Matches < dominanceFactor*cands[1].Matches {
		return nil, cands, &AmbiguousError{Query: query, Candidates: cands}
	}
	return cands[0], cands[1:], nil
}

// dominanceFactor is how many times more matches the best candidate needs
// before an ambiguous name is resolved silently.
const dominanceFactor = 5

// MustLookup is Lookup without the alternatives, for internal use.
func (r *TeamRegistry) MustLookup(query string) (*Team, error) {
	t, _, err := r.Lookup(query)
	return t, err
}

// Suggest returns the closest team names to a query, for "did you mean".
func (r *TeamRegistry) Suggest(query string, n int) []string {
	q := NormalizeTeamName(query).Base
	if q == "" {
		return nil
	}
	type cand struct {
		name string
		dist int
	}
	var cands []cand
	for _, t := range r.Teams() {
		base := NormalizeTeamName(t.Name).Base
		d := Levenshtein(q, base)
		if strings.Contains(base, q) || strings.Contains(q, base) {
			d = 1
		}
		limit := 3
		if len(q) <= 4 {
			limit = 2
		}
		if d <= limit {
			cands = append(cands, cand{t.Name, d})
		}
	}
	sort.Slice(cands, func(i, j int) bool {
		if cands[i].dist != cands[j].dist {
			return cands[i].dist < cands[j].dist
		}
		return cands[i].name < cands[j].name
	})
	out := make([]string, 0, n)
	for _, c := range cands {
		if len(out) == n {
			break
		}
		out = append(out, c.name)
	}
	return out
}

// LinkClub resolves a fifa_data.csv club name onto an existing team.
//
// It is deliberately stricter than Lookup: a bare name may only join a
// Brazilian (state qualified) club, so "FC Barcelona" never becomes
// Barcelona-EQU while "Atlético Mineiro" still becomes Atlético-MG.
func (r *TeamRegistry) LinkClub(club string) *Team {
	club = strings.TrimSpace(club)
	if club == "" {
		return nil
	}
	n := NormalizeTeamName(club)
	if id, ok := r.aliasIndex[n.Key()]; ok {
		if t := r.teams[id]; t != nil {
			return t
		}
	}
	if id, ok := r.aliasIndex[n.Base]; ok && r.qualifierAgrees(id, n) {
		if t := r.teams[id]; t != nil {
			return t
		}
	}
	if t, ok := r.teams[n.Key()]; ok {
		return t
	}
	if n.Qualifier == "" {
		matches := r.byBase[n.Base]
		if len(matches) == 1 && matches[0].State != "" {
			return matches[0]
		}
	}
	return nil
}
