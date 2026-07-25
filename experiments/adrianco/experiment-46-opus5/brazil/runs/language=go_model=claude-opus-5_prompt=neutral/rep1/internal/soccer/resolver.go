// resolver.go - raw team spelling -> canonical club node.
//
// Context
//
//	Club identity is resolved in two passes because it depends on statistics of
//	the corpus as a whole:
//
//	  Pass 1 (observe)  every raw team spelling in every match row is fed to the
//	                    resolver. Spellings covered by the curated table in
//	                    clubs.go are recognised immediately; the rest are
//	                    tallied as (base name, region) pairs.
//
//	  Pass 2 (finalize) each un-curated base name becomes one club per region
//	                    it was seen with. Bases seen with several regions are
//	                    genuinely several clubs ("Flamengo - PI" is not
//	                    Flamengo), so region-less rows are attached to the most
//	                    frequent one. Display names are then chosen from the
//	                    observed spellings, preferring the accented form
//	                    ("São Bento" over "Sao Bento").
//
//	Only after finalize can resolve() be called to turn a spelling into a club
//	ID. Query-time lookups (a user typing "flamengo") go through Resolve, which
//	falls back to fuzzy name search when the exact machinery finds nothing.
package soccer

import (
	"sort"
	"strings"
)

type resolver struct {
	clubs   map[string]*Club // club ID -> club
	byKey   map[string]*Club // "base|REGION" -> curated club
	byBase  map[string]*Club // "base"        -> curated club
	curated map[string]bool  // club IDs that came from the curated table

	counts   map[string]map[string]int // base -> region -> occurrences
	rawCount map[string]int            // raw spelling -> occurrences

	baseRegion map[string]map[string]string // base -> region -> club ID ("" key = default)
	cache      map[string]string            // raw spelling -> club ID
}

func newResolver() *resolver {
	r := &resolver{
		clubs:      make(map[string]*Club),
		byKey:      make(map[string]*Club),
		byBase:     make(map[string]*Club),
		curated:    make(map[string]bool),
		counts:     make(map[string]map[string]int),
		rawCount:   make(map[string]int),
		baseRegion: make(map[string]map[string]string),
		cache:      make(map[string]string),
	}
	for _, kc := range knownClubs {
		c := &Club{ID: kc.ID, Name: kc.Name, State: kc.State, Country: kc.Country}
		r.clubs[c.ID] = c
		r.curated[c.ID] = true
		for _, alias := range kc.Aliases {
			p := ParseTeamName(alias)
			if p.Region != "" {
				if _, dup := r.byKey[p.Key()]; !dup {
					r.byKey[p.Key()] = c
				}
			}
			if _, dup := r.byBase[p.Base]; !dup {
				r.byBase[p.Base] = c
			}
		}
	}
	return r
}

// lookupCurated implements the two-step curated lookup: exact base|region
// first, then region-agnostic base but only when the regions agree.
func (r *resolver) lookupCurated(p NameParts) *Club {
	if c, ok := r.byKey[p.Key()]; ok {
		return c
	}
	if c, ok := r.byBase[p.Base]; ok {
		if p.Region == "" || p.Region == c.State {
			return c
		}
	}
	return nil
}

// observe records one occurrence of a raw team spelling. Must be called for
// every team cell of every match row before finalize.
func (r *resolver) observe(raw string) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return
	}
	r.rawCount[raw]++
	p := ParseTeamName(raw)
	if r.lookupCurated(p) != nil {
		return
	}
	if r.counts[p.Base] == nil {
		r.counts[p.Base] = make(map[string]int)
	}
	r.counts[p.Base][p.Region]++
}

// finalize turns the observations into club nodes.
func (r *resolver) finalize() {
	for base, regions := range r.counts {
		known := make([]string, 0, len(regions))
		for reg := range regions {
			if reg != "" {
				known = append(known, reg)
			}
		}
		// Most frequent region first; alphabetical tie-break keeps the build
		// deterministic.
		sort.Slice(known, func(i, j int) bool {
			if regions[known[i]] != regions[known[j]] {
				return regions[known[i]] > regions[known[j]]
			}
			return known[i] < known[j]
		})

		mapping := make(map[string]string, len(known)+1)
		switch len(known) {
		case 0:
			mapping[""] = slugify(base)
		default:
			for _, reg := range known {
				mapping[reg] = slugify(base) + "-" + strings.ToLower(reg)
			}
			mapping[""] = mapping[known[0]]
		}
		r.baseRegion[base] = mapping

		for reg, id := range mapping {
			if reg == "" {
				continue
			}
			if _, ok := r.clubs[id]; !ok {
				r.clubs[id] = &Club{ID: id, State: reg, Country: regionCountry(reg)}
			}
		}
		if len(known) == 0 {
			id := mapping[""]
			if _, ok := r.clubs[id]; !ok {
				r.clubs[id] = &Club{ID: id}
			}
		}
	}

	// Choose display names and collect aliases from the observed spellings.
	type candidate struct {
		display string
		score   int
	}
	best := make(map[string]candidate)
	aliases := make(map[string]map[string]bool)
	for raw, count := range r.rawCount {
		id := r.resolve(raw)
		if id == "" {
			continue
		}
		if aliases[id] == nil {
			aliases[id] = make(map[string]bool)
		}
		aliases[id][raw] = true
		if r.curated[id] {
			continue // curated clubs keep their hand-written display name
		}
		display := stripRegionSuffix(raw)
		score := count
		if hasAccent(display) {
			score += 1_000_000 // prefer "São Bento" over "Sao Bento"
		}
		if cur, ok := best[id]; !ok || score > cur.score ||
			(score == cur.score && display < cur.display) {
			best[id] = candidate{display: display, score: score}
		}
	}
	for id, c := range best {
		if club, ok := r.clubs[id]; ok {
			club.Name = c.display
		}
	}
	for id, set := range aliases {
		club, ok := r.clubs[id]
		if !ok {
			continue
		}
		list := make([]string, 0, len(set))
		for a := range set {
			list = append(list, a)
		}
		sort.Strings(list)
		club.Aliases = list
	}
	for _, club := range r.clubs {
		if club.Name == "" {
			club.Name = strings.ReplaceAll(club.ID, "-", " ")
		}
		club.sortName = normalizeText(club.Name)
		club.aliasNames = make([]string, 0, len(club.Aliases))
		club.aliasBases = make([]string, 0, len(club.Aliases))
		for _, a := range club.Aliases {
			club.aliasNames = append(club.aliasNames, normalizeText(a))
			club.aliasBases = append(club.aliasBases, ParseTeamName(a).Base)
		}
	}
}

// resolve maps a raw spelling to a club ID, returning "" if it is unknown.
func (r *resolver) resolve(raw string) string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return ""
	}
	if id, ok := r.cache[raw]; ok {
		return id
	}
	id := r.resolveUncached(raw)
	r.cache[raw] = id
	return id
}

func (r *resolver) resolveUncached(raw string) string {
	p := ParseTeamName(raw)
	if c := r.lookupCurated(p); c != nil {
		return c.ID
	}
	if mapping, ok := r.baseRegion[p.Base]; ok {
		if id, ok := mapping[p.Region]; ok {
			return id
		}
		if id, ok := mapping[""]; ok {
			return id
		}
	}
	return ""
}

// regionCountry names the country a region code belongs to.
func regionCountry(code string) string {
	if IsBrazilianState(code) {
		return "Brazil"
	}
	if name, ok := foreignRegions[code]; ok {
		return name
	}
	return ""
}

// slugify turns a normalized base name into a URL-ish identifier.
func slugify(base string) string {
	return strings.ReplaceAll(strings.TrimSpace(base), " ", "-")
}
