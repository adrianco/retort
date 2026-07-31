package soccer

import (
	"sort"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/normalize"
)

// PlayerFilter scopes a FIFA player search.
type PlayerFilter struct {
	Name               string
	Nationality        string
	Club               string
	Position           string
	MinOverall         int
	MaxOverall         int
	MinAge             int
	MaxAge             int
	BrazilianClubsOnly bool
	SortBy             string // "overall" (default), "potential", "age", "name"
	Limit              int
}

// PlayerQueryResult is the answer to a player search.
type PlayerQueryResult struct {
	Total    int      `json:"total_matching"`
	Returned int      `json:"returned"`
	Players  []Player `json:"players"`
	Summary  string   `json:"summary"`
}

// FindPlayers searches the FIFA dataset.
func (g *Graph) FindPlayers(f PlayerFilter) *PlayerQueryResult {
	name := normalize.Deaccent(strings.TrimSpace(f.Name))
	nat := normalize.Deaccent(strings.TrimSpace(f.Nationality))
	pos := strings.ToUpper(strings.TrimSpace(f.Position))

	// Club can be a canonical club or free text. Prefer the canonical route so
	// that "Sport Club do Recife" finds players listed under "Sport Recife" —
	// and, just as importantly, so that "Santos" does not also drag in Santos
	// Laguna. Only when the canonical ID matches nobody do we fall back to a
	// substring search over the raw club strings.
	clubID, clubText := "", ""
	if f.Club != "" {
		clubID = normalize.Resolve(f.Club).ID
		if len(g.playersByClub[clubID]) == 0 {
			clubID = ""
			clubText = normalize.Deaccent(strings.TrimSpace(f.Club))
		}
	}

	candidates := allIndexes(len(g.Players))
	if clubID != "" {
		if idxs, ok := g.playersByClub[clubID]; ok {
			candidates = idxs
		}
	} else if nat != "" {
		if idxs, ok := g.playersByNat[nat]; ok {
			candidates = idxs
		}
	}

	var hits []int
	for _, i := range candidates {
		p := &g.Players[i]
		if name != "" && !strings.Contains(normalize.Deaccent(p.Name), name) {
			continue
		}
		if nat != "" && normalize.Deaccent(p.Nationality) != nat {
			continue
		}
		if clubID != "" && p.ClubID != clubID {
			continue
		}
		if clubText != "" && !strings.Contains(normalize.Deaccent(p.Club), clubText) {
			continue
		}
		if pos != "" && !strings.EqualFold(p.Position, pos) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxOverall > 0 && p.Overall > f.MaxOverall {
			continue
		}
		if f.MinAge > 0 && p.Age < f.MinAge {
			continue
		}
		if f.MaxAge > 0 && p.Age > f.MaxAge {
			continue
		}
		if f.BrazilianClubsOnly {
			if _, ok := g.teams[p.ClubID]; !ok {
				continue
			}
		}
		hits = append(hits, i)
	}

	less := func(a, b int) bool { return g.Players[a].Overall > g.Players[b].Overall }
	switch strings.ToLower(f.SortBy) {
	case "potential":
		less = func(a, b int) bool { return g.Players[a].Potential > g.Players[b].Potential }
	case "age":
		less = func(a, b int) bool { return g.Players[a].Age < g.Players[b].Age }
	case "name":
		less = func(a, b int) bool { return g.Players[a].Name < g.Players[b].Name }
	}
	sort.SliceStable(hits, less)

	limit := f.Limit
	if limit <= 0 {
		limit = 20
	}
	res := &PlayerQueryResult{Total: len(hits)}
	for _, i := range hits {
		if len(res.Players) >= limit {
			break
		}
		res.Players = append(res.Players, g.Players[i])
	}
	res.Returned = len(res.Players)
	res.Summary = plural(res.Total, "player", "players") + " matched"
	if res.Returned < res.Total {
		res.Summary += ", showing top " + itoa(res.Returned)
	}
	if res.Returned > 0 {
		p := res.Players[0]
		res.Summary += ". Top result: " + p.Name + " (overall " + itoa(p.Overall) +
			", " + p.Position + ", " + p.Club + ")"
	}
	return res
}

// ClubSquad summarises the FIFA players registered at one club.
type ClubSquad struct {
	Club          string         `json:"club"`
	ClubID        string         `json:"club_id,omitempty"`
	Players       int            `json:"player_count"`
	AvgOverall    float64        `json:"avg_overall"`
	AvgAge        float64        `json:"avg_age"`
	TopPlayer     string         `json:"top_player,omitempty"`
	Nationalities map[string]int `json:"nationalities,omitempty"`
	Squad         []Player       `json:"squad,omitempty"`
	Summary       string         `json:"summary"`
}

// Squad returns the FIFA roster for a club, cross-referenced with the match
// graph so we can report whether the club also appears in the fixture data.
func (g *Graph) Squad(club string, includePlayers bool) (*ClubSquad, error) {
	res := g.FindPlayers(PlayerFilter{Club: club, Limit: 1 << 30, SortBy: "overall"})
	if res.Total == 0 {
		return nil, &ErrNoData{What: "players at club " + club}
	}
	sq := &ClubSquad{Club: res.Players[0].Club, ClubID: res.Players[0].ClubID,
		Players: res.Total, Nationalities: map[string]int{}}
	var sumOverall, sumAge, ageCount int
	for _, p := range res.Players {
		sumOverall += p.Overall
		if p.Age > 0 {
			sumAge += p.Age
			ageCount++
		}
		if p.Nationality != "" {
			sq.Nationalities[p.Nationality]++
		}
	}
	sq.AvgOverall = round2(float64(sumOverall) / float64(res.Total))
	if ageCount > 0 {
		sq.AvgAge = round2(float64(sumAge) / float64(ageCount))
	}
	sq.TopPlayer = res.Players[0].Name
	if includePlayers {
		sq.Squad = res.Players
	}
	sq.Summary = sq.Club + ": " + plural(sq.Players, "player", "players") +
		", average rating " + ftoa(sq.AvgOverall) + ", top rated " + sq.TopPlayer
	if t, ok := g.teams[sq.ClubID]; ok {
		sq.Summary += ". " + t.Name + " appears in " + plural(t.MatchCount, "match", "matches") +
			" of the fixture data."
	}
	return sq, nil
}

// ClubRating pairs a Brazilian club with its FIFA squad rating.
type ClubRating struct {
	Club       string  `json:"club"`
	ClubID     string  `json:"club_id"`
	Players    int     `json:"players"`
	AvgOverall float64 `json:"avg_overall"`
	TopPlayer  string  `json:"top_player"`
	TopOverall int     `json:"top_overall"`
	MatchCount int     `json:"fixture_matches"`
}

// BrazilianClubRatings cross-references the FIFA player file with the match
// graph: only clubs that appear in both are reported. This is the canonical
// "player + match data" join.
//
// minPlayers filters out clubs represented by one or two players. Without it
// the ranking is topped by foreign Libertadores opponents that happen to have a
// single well-rated Brazilian on the books, which is not what "Brazilian
// players at Brazilian clubs" is asking.
func (g *Graph) BrazilianClubRatings(nationality string, minPlayers, limit int) []ClubRating {
	if minPlayers <= 0 {
		minPlayers = 3
	}
	nat := normalize.Deaccent(strings.TrimSpace(nationality))
	type acc struct {
		club       string
		n, sum     int
		topName    string
		topOverall int
	}
	byClub := map[string]*acc{}
	for i := range g.Players {
		p := &g.Players[i]
		if p.ClubID == "" {
			continue
		}
		if _, inGraph := g.teams[p.ClubID]; !inGraph {
			continue
		}
		if nat != "" && normalize.Deaccent(p.Nationality) != nat {
			continue
		}
		a := byClub[p.ClubID]
		if a == nil {
			a = &acc{club: p.Club}
			byClub[p.ClubID] = a
		}
		a.n++
		a.sum += p.Overall
		if p.Overall > a.topOverall {
			a.topOverall, a.topName = p.Overall, p.Name
		}
	}
	out := make([]ClubRating, 0, len(byClub))
	for id, a := range byClub {
		if a.n < minPlayers {
			continue
		}
		cr := ClubRating{Club: a.club, ClubID: id, Players: a.n,
			AvgOverall: round2(float64(a.sum) / float64(a.n)),
			TopPlayer:  a.topName, TopOverall: a.topOverall}
		if t, ok := g.teams[id]; ok {
			cr.MatchCount = t.MatchCount
		}
		out = append(out, cr)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].AvgOverall != out[j].AvgOverall {
			return out[i].AvgOverall > out[j].AvgOverall
		}
		return out[i].Club < out[j].Club
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}
