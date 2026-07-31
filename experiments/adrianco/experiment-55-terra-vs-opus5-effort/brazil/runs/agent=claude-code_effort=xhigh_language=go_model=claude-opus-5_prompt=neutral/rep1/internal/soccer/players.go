// players.go answers player-shaped questions: "find all Brazilian players",
// "who are the highest rated players at Fluminense", "show me all forwards from
// Santos", "who is Gabriel Barbosa".
//
// The FIFA export is the only player source, so every answer is scoped to it.
// Where a query cannot be satisfied from that snapshot - most famously the
// unlicensed Brazilian clubs that FIFA 19 omits - the result says so and points
// at the clubs that are covered, instead of returning a bare empty list.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// PlayerFilter selects rows of the FIFA database.
type PlayerFilter struct {
	Name               string
	Nationality        string
	Club               string
	Position           string // exact code (ST) or a group (forward)
	MinOverall         int
	MaxOverall         int
	MinAge             int
	MaxAge             int
	MinPotential       int
	SortBy             string // overall, potential, age, value, name
	BrazilianClubsOnly bool
}

// PlayerView is the serialisable form of a player.
type PlayerView struct {
	ID            int            `json:"id"`
	Name          string         `json:"name"`
	Age           int            `json:"age"`
	Nationality   string         `json:"nationality"`
	Overall       int            `json:"overall"`
	Potential     int            `json:"potential"`
	Club          string         `json:"club,omitempty"`
	ClubTeamID    string         `json:"club_team_id,omitempty"`
	Position      string         `json:"position,omitempty"`
	PositionGroup string         `json:"position_group,omitempty"`
	Jersey        int            `json:"jersey_number,omitempty"`
	Height        string         `json:"height,omitempty"`
	Weight        string         `json:"weight,omitempty"`
	Foot          string         `json:"preferred_foot,omitempty"`
	Value         string         `json:"value,omitempty"`
	Wage          string         `json:"wage,omitempty"`
	Contract      string         `json:"contract_valid_until,omitempty"`
	Skills        map[string]int `json:"skills,omitempty"`
	Line          string         `json:"line"`
}

func view(p *Player, withSkills bool) PlayerView {
	v := PlayerView{
		ID: p.ID, Name: p.Name, Age: p.Age, Nationality: p.Nationality,
		Overall: p.Overall, Potential: p.Potential, Club: p.Club,
		ClubTeamID: p.ClubTeamID, Position: p.Position, PositionGroup: p.PositionGroup(),
		Jersey: p.Jersey, Height: p.Height, Weight: p.Weight, Foot: p.Foot,
		Value: p.Value, Wage: p.Wage, Contract: p.ContractTo,
	}
	if withSkills {
		v.Skills = p.Skills
	}
	club := p.Club
	if club == "" {
		club = "no club"
	}
	v.Line = fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Age: %d, Club: %s, Nationality: %s",
		p.Name, p.Overall, p.Potential, orDash(p.Position), p.Age, club, p.Nationality)
	return v
}

func orDash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}

func playerViews(ps []*Player, limit int) []PlayerView {
	if limit > 0 && len(ps) > limit {
		ps = ps[:limit]
	}
	out := make([]PlayerView, 0, len(ps))
	for _, p := range ps {
		out = append(out, view(p, false))
	}
	return out
}

// ClubBreakdown aggregates the players of one club.
type ClubBreakdown struct {
	Club          string  `json:"club"`
	TeamID        string  `json:"team_id,omitempty"`
	Players       int     `json:"players"`
	AverageRating float64 `json:"average_rating"`
	BestPlayer    string  `json:"best_player,omitempty"`
}

// PlayerSearchResult is the payload of the search_players tool.
type PlayerSearchResult struct {
	Query      string          `json:"query"`
	Total      int             `json:"total_matching"`
	Returned   int             `json:"returned"`
	Players    []PlayerView    `json:"players"`
	ByClub     []ClubBreakdown `json:"by_club,omitempty"`
	Note       string          `json:"note,omitempty"`
	DataSource string          `json:"data_source"`
}

// SearchPlayers filters and ranks the FIFA database.
func (g *Graph) SearchPlayers(f PlayerFilter, limit int, groupByClub bool) (*PlayerSearchResult, error) {
	nameKey := foldKey(f.Name)
	natKey := foldKey(f.Nationality)
	posKey := strings.ToUpper(strings.TrimSpace(f.Position))
	posGroup := positionGroupAliases[foldKey(f.Position)]

	var clubTeam *Team
	if strings.TrimSpace(f.Club) != "" {
		t, _, err := g.ResolveTeam(f.Club)
		if err == nil {
			clubTeam = t
		}
	}
	clubKey := foldKey(f.Club)

	var hits []*Player
	for _, p := range g.players {
		if nameKey != "" && !strings.Contains(p.nameKey, nameKey) {
			continue
		}
		if natKey != "" && foldKey(p.Nationality) != natKey {
			continue
		}
		if clubKey != "" {
			switch {
			case clubTeam != nil && p.ClubTeamID == clubTeam.ID:
			case strings.Contains(foldKey(p.Club), clubKey):
			default:
				continue
			}
		}
		if posGroup != "" {
			if p.PositionGroup() != posGroup {
				continue
			}
		} else if posKey != "" && p.Position != posKey {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxOverall > 0 && p.Overall > f.MaxOverall {
			continue
		}
		if f.MinPotential > 0 && p.Potential < f.MinPotential {
			continue
		}
		if f.MinAge > 0 && p.Age < f.MinAge {
			continue
		}
		if f.MaxAge > 0 && p.Age > f.MaxAge {
			continue
		}
		if f.BrazilianClubsOnly && !g.isBrazilianClub(p.ClubTeamID) {
			continue
		}
		hits = append(hits, p)
	}
	sortPlayers(hits, f.SortBy)

	res := &PlayerSearchResult{
		Query:      describePlayerQuery(f, clubTeam),
		Total:      len(hits),
		Players:    playerViews(hits, limit),
		DataSource: "fifa_data.csv (FIFA 19 export, 18,207 players)",
	}
	res.Returned = len(res.Players)
	if groupByClub {
		res.ByClub = g.groupByClub(hits)
	}
	switch {
	case len(hits) == 0 && clubKey != "":
		res.Note = fmt.Sprintf("No players found for club %q. %s", f.Club, g.clubCoverageNote())
	case len(hits) == 0:
		res.Note = "No players in the FIFA dataset match this query."
	case res.Returned < res.Total:
		res.Note = fmt.Sprintf("Showing the top %d of %d matching players.", res.Returned, res.Total)
	}
	return res, nil
}

// isBrazilianClub reports whether a linked club is a Brazilian one.
func (g *Graph) isBrazilianClub(teamID string) bool {
	if teamID == "" {
		return false
	}
	t, ok := g.Team(teamID)
	return ok && t.IsBrazilian()
}

// clubCoverageNote lists the Brazilian clubs the FIFA export actually contains.
func (g *Graph) clubCoverageNote() string {
	var clubs []string
	for id, ps := range g.playersByClub {
		if t, ok := g.Team(id); ok && t.IsBrazilian() && len(ps) > 0 {
			clubs = append(clubs, t.Display)
		}
	}
	sort.Strings(clubs)
	if len(clubs) == 0 {
		return "The FIFA export contains no Brazilian clubs."
	}
	return "The FIFA 19 export only licenses these Brazilian clubs: " + strings.Join(clubs, ", ") + "."
}

// groupByClub summarises a result set per club, as the specification's example
// output does for Brazilian players.
func (g *Graph) groupByClub(ps []*Player) []ClubBreakdown {
	type acc struct {
		n      int
		sum    int
		teamID string
		best   *Player
	}
	byClub := map[string]*acc{}
	for _, p := range ps {
		club := p.Club
		if club == "" {
			club = "(no club)"
		}
		a := byClub[club]
		if a == nil {
			a = &acc{teamID: p.ClubTeamID}
			byClub[club] = a
		}
		a.n++
		a.sum += p.Overall
		if a.best == nil || p.Overall > a.best.Overall {
			a.best = p
		}
	}
	out := make([]ClubBreakdown, 0, len(byClub))
	for club, a := range byClub {
		cb := ClubBreakdown{Club: club, TeamID: a.teamID, Players: a.n}
		if a.n > 0 {
			cb.AverageRating = round1(float64(a.sum) / float64(a.n))
		}
		if a.best != nil {
			cb.BestPlayer = fmt.Sprintf("%s (%d)", a.best.Name, a.best.Overall)
		}
		out = append(out, cb)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Players != out[j].Players {
			return out[i].Players > out[j].Players
		}
		if out[i].AverageRating != out[j].AverageRating {
			return out[i].AverageRating > out[j].AverageRating
		}
		return out[i].Club < out[j].Club
	})
	return out
}

// sortPlayers orders a result set; the default is by overall rating.
func sortPlayers(ps []*Player, by string) {
	switch foldKey(by) {
	case "age":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Age < ps[j].Age })
	case "potential":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Potential > ps[j].Potential })
	case "value":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].ValueEUR > ps[j].ValueEUR })
	case "wage":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].WageEUR > ps[j].WageEUR })
	case "name":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Name < ps[j].Name })
	default:
		sortPlayersByRating(ps)
	}
}

// describePlayerQuery renders the filter as an English phrase.
func describePlayerQuery(f PlayerFilter, clubTeam *Team) string {
	var parts []string
	if f.Name != "" {
		parts = append(parts, fmt.Sprintf("name contains %q", f.Name))
	}
	if f.Nationality != "" {
		parts = append(parts, f.Nationality+" players")
	}
	if f.Club != "" {
		club := f.Club
		if clubTeam != nil {
			club = clubTeam.Display
		}
		parts = append(parts, "at "+club)
	}
	if f.Position != "" {
		parts = append(parts, "position "+f.Position)
	}
	if f.MinOverall > 0 {
		parts = append(parts, fmt.Sprintf("overall >= %d", f.MinOverall))
	}
	if f.MaxAge > 0 {
		parts = append(parts, fmt.Sprintf("age <= %d", f.MaxAge))
	}
	if f.BrazilianClubsOnly {
		parts = append(parts, "playing for a Brazilian club")
	}
	if len(parts) == 0 {
		return "all players"
	}
	return strings.Join(parts, ", ")
}

// PlayerProfileResult is the payload of the player_profile tool.
type PlayerProfileResult struct {
	Player       PlayerView `json:"player"`
	TopSkills    []string   `json:"top_skills,omitempty"`
	ClubTeam     *TeamRef   `json:"club_in_graph,omitempty"`
	Teammates    []string   `json:"teammates,omitempty"`
	SimilarNames []string   `json:"other_matches,omitempty"`
	Note         string     `json:"note,omitempty"`
}

// PlayerProfile looks a player up by name and returns everything known, linking
// back to the match graph when the club is a Brazilian one.
func (g *Graph) PlayerProfile(name string) (*PlayerProfileResult, error) {
	key := foldKey(name)
	if key == "" {
		return nil, fmt.Errorf("a player name is required")
	}
	var exact, partial []*Player
	for _, p := range g.players {
		switch {
		case p.nameKey == key:
			exact = append(exact, p)
		case strings.Contains(p.nameKey, key):
			partial = append(partial, p)
		}
	}
	hits := exact
	if len(hits) == 0 {
		hits = partial
	}
	if len(hits) == 0 {
		return nil, fmt.Errorf("no player named %q in the FIFA dataset (it holds 18,207 players from the FIFA 19 export)", name)
	}
	sortPlayersByRating(hits)
	p := hits[0]
	res := &PlayerProfileResult{Player: view(p, true), TopSkills: topSkills(p, 8)}
	for i := 1; i < len(hits) && i < 6; i++ {
		res.SimilarNames = append(res.SimilarNames, hits[i].Name+" ("+orDash(hits[i].Club)+")")
	}
	if p.ClubTeamID != "" {
		if t, ok := g.Team(p.ClubTeamID); ok {
			ref := Ref(t)
			res.ClubTeam = &ref
			for _, mate := range g.playersByClub[t.ID] {
				if mate != p && len(res.Teammates) < 5 {
					res.Teammates = append(res.Teammates, fmt.Sprintf("%s (%d)", mate.Name, mate.Overall))
				}
			}
		}
	}
	if len(hits) > 1 {
		res.Note = fmt.Sprintf("%d players matched %q; showing the highest rated.", len(hits), name)
	}
	return res, nil
}

// topSkills lists a player's best rated attributes.
func topSkills(p *Player, n int) []string {
	type kv struct {
		k string
		v int
	}
	var list []kv
	for k, v := range p.Skills {
		list = append(list, kv{k, v})
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].v != list[j].v {
			return list[i].v > list[j].v
		}
		return list[i].k < list[j].k
	})
	var out []string
	for i := 0; i < len(list) && i < n; i++ {
		out = append(out, fmt.Sprintf("%s %d", list[i].k, list[i].v))
	}
	return out
}
