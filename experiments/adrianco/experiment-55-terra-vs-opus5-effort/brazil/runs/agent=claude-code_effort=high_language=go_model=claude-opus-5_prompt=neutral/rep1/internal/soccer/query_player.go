// query_player.go implements the "Player Queries" section over the FIFA 19
// player database, including the cross-file link from a FIFA club to the club
// that appears in the match datasets.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// positionGroups maps a coarse role onto the FIFA position codes.
var positionGroups = map[string][]string{
	"goalkeeper": {"GK"},
	"defender":   {"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"},
	"midfielder": {"CM", "LCM", "RCM", "CDM", "LDM", "RDM", "CAM", "LAM", "RAM", "LM", "RM"},
	"forward":    {"ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"},
}

var positionGroupAliases = map[string]string{
	"gk": "goalkeeper", "goalkeepers": "goalkeeper", "keeper": "goalkeeper",
	"defenders": "defender", "defence": "defender", "defense": "defender", "def": "defender",
	"midfielders": "midfielder", "midfield": "midfielder", "mid": "midfielder",
	"forwards": "forward", "attackers": "forward", "attacker": "forward",
	"strikers": "forward", "striker": "forward", "att": "forward",
}

// PlayerView is the wire representation of a player.
type PlayerView struct {
	ID           int    `json:"id"`
	Name         string `json:"name"`
	Age          int    `json:"age"`
	Nationality  string `json:"nationality"`
	Overall      int    `json:"overall"`
	Potential    int    `json:"potential"`
	Club         string `json:"club"`
	Position     string `json:"position"`
	JerseyNumber int    `json:"jersey_number,omitempty"`
	Value        string `json:"value,omitempty"`
	Wage         string `json:"wage,omitempty"`
	Summary      string `json:"summary"`
}

// PlayerProfileView adds the full attribute set to a PlayerView.
type PlayerProfileView struct {
	PlayerView
	Height            string         `json:"height,omitempty"`
	Weight            string         `json:"weight,omitempty"`
	PreferredFoot     string         `json:"preferred_foot,omitempty"`
	WorkRate          string         `json:"work_rate,omitempty"`
	BodyType          string         `json:"body_type,omitempty"`
	Joined            string         `json:"joined,omitempty"`
	ContractUntil     string         `json:"contract_valid_until,omitempty"`
	ReleaseClause     string         `json:"release_clause,omitempty"`
	IntlReputation    int            `json:"international_reputation,omitempty"`
	WeakFoot          int            `json:"weak_foot,omitempty"`
	SkillMoves        int            `json:"skill_moves,omitempty"`
	Skills            map[string]int `json:"skills,omitempty"`
	TopSkills         []SkillValue   `json:"top_skills,omitempty"`
	LinkedClubTeamID  string         `json:"linked_club_team_id,omitempty"`
	LinkedClubMatches int            `json:"linked_club_match_count,omitempty"`
}

// SkillValue is one named FIFA attribute.
type SkillValue struct {
	Skill string `json:"skill"`
	Value int    `json:"value"`
}

func (p *Player) toView() PlayerView {
	v := PlayerView{
		ID: p.ID, Name: p.Name, Age: p.Age, Nationality: p.Nationality,
		Overall: p.Overall, Potential: p.Potential, Club: p.Club,
		Position: p.Position, JerseyNumber: p.JerseyNumber,
		Value: p.Value, Wage: p.Wage,
	}
	club := p.Club
	if club == "" {
		club = "no club"
	}
	pos := p.Position
	if pos == "" {
		pos = "n/a"
	}
	v.Summary = fmt.Sprintf("%s — Overall: %d, Potential: %d, Position: %s, Club: %s, Age: %d, Nationality: %s",
		p.Name, p.Overall, p.Potential, pos, club, p.Age, p.Nationality)
	return v
}

// PlayerFilter describes a player search.
type PlayerFilter struct {
	Name               string
	Nationality        string
	Club               string
	Position           string // exact code ("LW") or a group ("forward")
	MinOverall         int
	MaxOverall         int
	MinPotential       int
	MinAge             int
	MaxAge             int
	BrazilianClubsOnly bool
	SortBy             string // overall (default), potential, age, value, name
	GroupBy            string // club, nationality, position
	Limit              int
}

// GroupCount is an aggregate bucket produced by GroupBy.
type GroupCount struct {
	Key        string  `json:"key"`
	Players    int     `json:"players"`
	AvgOverall float64 `json:"avg_overall"`
	TopPlayer  string  `json:"top_player,omitempty"`
	TopOverall int     `json:"top_overall,omitempty"`
}

// PlayerSearchResult is the result of a player search.
type PlayerSearchResult struct {
	Description string       `json:"description"`
	Total       int          `json:"total_players"`
	Returned    int          `json:"returned"`
	Players     []PlayerView `json:"players"`
	Groups      []GroupCount `json:"groups,omitempty"`
	AvgOverall  float64      `json:"avg_overall,omitempty"`
	Note        string       `json:"note,omitempty"`
}

// SearchPlayers filters and ranks the FIFA player database.
func (g *Graph) SearchPlayers(f PlayerFilter) (*PlayerSearchResult, error) {
	nameQ := Slug(f.Name)
	natQ := Slug(f.Nationality)
	clubQ := Slug(f.Club)

	// A club query is also matched against the canonical club graph so that
	// "Atletico-MG" or "Galo" style spellings still reach "Atlético Mineiro".
	clubTeamID := ""
	if clubQ != "" {
		if t, err := g.ResolveTeam(f.Club); err == nil {
			clubTeamID = t.ID
		}
	}

	var wantPositions map[string]bool
	posLabel := ""
	if p := strings.TrimSpace(f.Position); p != "" {
		key := strings.ToLower(p)
		if alias, ok := positionGroupAliases[key]; ok {
			key = alias
		}
		if codes, ok := positionGroups[key]; ok {
			wantPositions = map[string]bool{}
			for _, c := range codes {
				wantPositions[c] = true
			}
			posLabel = key + "s"
		} else {
			wantPositions = map[string]bool{strings.ToUpper(p): true}
			posLabel = strings.ToUpper(p)
		}
	}

	var hits []*Player
	for _, p := range g.Players {
		if nameQ != "" && !strings.Contains(Slug(p.Name), nameQ) {
			continue
		}
		if natQ != "" && !strings.Contains(Slug(p.Nationality), natQ) {
			continue
		}
		if clubQ != "" {
			if !strings.Contains(Slug(p.Club), clubQ) && (clubTeamID == "" || p.ClubTeamID != clubTeamID) {
				continue
			}
		}
		if f.BrazilianClubsOnly && !g.isBrazilianClub(p) {
			continue
		}
		if wantPositions != nil && !wantPositions[strings.ToUpper(p.Position)] {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxOverall != 0 && p.Overall > f.MaxOverall {
			continue
		}
		if f.MinPotential != 0 && p.Potential < f.MinPotential {
			continue
		}
		if f.MinAge != 0 && p.Age < f.MinAge {
			continue
		}
		if f.MaxAge != 0 && p.Age > f.MaxAge {
			continue
		}
		hits = append(hits, p)
	}

	sortPlayers(hits, f.SortBy)

	res := &PlayerSearchResult{
		Description: describePlayerFilter(f, posLabel),
		Total:       len(hits),
	}
	if len(hits) == 0 {
		res.Players = []PlayerView{}
		res.Note = g.emptyPlayerNote(f)
		return res, nil
	}

	sum := 0
	for _, p := range hits {
		sum += p.Overall
	}
	res.AvgOverall = round1(float64(sum) / float64(len(hits)))

	if f.GroupBy != "" {
		res.Groups = groupPlayers(hits, f.GroupBy)
	}

	limit := f.Limit
	if limit <= 0 {
		limit = 20
	}
	shown := hits
	if len(shown) > limit {
		shown = shown[:limit]
		res.Note = fmt.Sprintf("showing the top %d of %d players; raise \"limit\" to see more", limit, len(hits))
	}
	res.Players = make([]PlayerView, 0, len(shown))
	for _, p := range shown {
		res.Players = append(res.Players, p.toView())
	}
	res.Returned = len(res.Players)
	return res, nil
}

func (g *Graph) isBrazilianClub(p *Player) bool {
	if p.ClubTeamID == "" {
		return false
	}
	t, ok := g.Teams[p.ClubTeamID]
	return ok && t.Country == "Brazil"
}

func sortPlayers(ps []*Player, mode string) {
	switch strings.ToLower(mode) {
	case "potential":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Potential > ps[j].Potential })
	case "age", "youngest":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Age < ps[j].Age })
	case "oldest":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Age > ps[j].Age })
	case "value":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].ValueEUR > ps[j].ValueEUR })
	case "wage":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].WageEUR > ps[j].WageEUR })
	case "name":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Name < ps[j].Name })
	default: // overall
		sort.SliceStable(ps, func(i, j int) bool {
			if ps[i].Overall != ps[j].Overall {
				return ps[i].Overall > ps[j].Overall
			}
			return ps[i].Potential > ps[j].Potential
		})
	}
}

func groupPlayers(ps []*Player, by string) []GroupCount {
	key := func(p *Player) string {
		switch strings.ToLower(by) {
		case "nationality":
			return p.Nationality
		case "position":
			return p.Position
		default:
			return p.Club
		}
	}
	type acc struct {
		n, sum, top int
		topName     string
	}
	m := map[string]*acc{}
	for _, p := range ps {
		k := key(p)
		if k == "" {
			k = "(none)"
		}
		a, ok := m[k]
		if !ok {
			a = &acc{}
			m[k] = a
		}
		a.n++
		a.sum += p.Overall
		if p.Overall > a.top {
			a.top, a.topName = p.Overall, p.Name
		}
	}
	out := make([]GroupCount, 0, len(m))
	for _, k := range sortedKeys(m) {
		a := m[k]
		out = append(out, GroupCount{
			Key: k, Players: a.n,
			AvgOverall: round1(float64(a.sum) / float64(a.n)),
			TopPlayer:  a.topName, TopOverall: a.top,
		})
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Players != out[j].Players {
			return out[i].Players > out[j].Players
		}
		return out[i].AvgOverall > out[j].AvgOverall
	})
	return out
}

func describePlayerFilter(f PlayerFilter, posLabel string) string {
	var parts []string
	if f.Name != "" {
		parts = append(parts, fmt.Sprintf("name contains %q", f.Name))
	}
	if posLabel != "" {
		parts = append(parts, posLabel)
	}
	if f.Nationality != "" {
		parts = append(parts, f.Nationality+" players")
	}
	if f.Club != "" {
		parts = append(parts, "at "+f.Club)
	}
	if f.BrazilianClubsOnly {
		parts = append(parts, "at Brazilian clubs")
	}
	if f.MinOverall != 0 {
		parts = append(parts, fmt.Sprintf("overall >= %d", f.MinOverall))
	}
	if f.MaxAge != 0 {
		parts = append(parts, fmt.Sprintf("age <= %d", f.MaxAge))
	}
	if len(parts) == 0 {
		return "all players"
	}
	return strings.Join(parts, ", ")
}

// emptyPlayerNote explains an empty result, which for club queries is usually
// because FIFA 19 only licensed a subset of Brazilian clubs.
func (g *Graph) emptyPlayerNote(f PlayerFilter) string {
	if f.Club == "" {
		return "no players match these criteria"
	}
	clubs := g.BrazilianFIFAClubs()
	if len(clubs) == 0 {
		return fmt.Sprintf("no players found for club %q", f.Club)
	}
	return fmt.Sprintf("no players found for club %q. The FIFA 19 dataset only licenses %d Brazilian clubs: %s",
		f.Club, len(clubs), strings.Join(clubs, ", "))
}

// BrazilianFIFAClubs lists the FIFA club names that link to a Brazilian club in
// the match datasets.
func (g *Graph) BrazilianFIFAClubs() []string {
	seen := map[string]bool{}
	for _, p := range g.Players {
		if g.isBrazilianClub(p) && p.Club != "" {
			seen[p.Club] = true
		}
	}
	out := make([]string, 0, len(seen))
	for k := range seen {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

// PlayerProfile returns the full attribute set for one player, looked up by
// name (fuzzy) or by FIFA ID.
func (g *Graph) PlayerProfile(query string, id int) (*PlayerProfileView, error) {
	var p *Player
	if id != 0 {
		p = g.playersByID[id]
		if p == nil {
			return nil, fmt.Errorf("no player with FIFA ID %d", id)
		}
	} else {
		q := Slug(query)
		if q == "" {
			return nil, fmt.Errorf("a player name or id is required")
		}
		var candidates []*Player
		for _, cand := range g.Players {
			s := Slug(cand.Name)
			if s == q {
				candidates = []*Player{cand}
				break
			}
			if strings.Contains(s, q) {
				candidates = append(candidates, cand)
			}
		}
		if len(candidates) == 0 {
			if near := g.similarPlayerNames(query, 5); len(near) > 0 {
				return nil, fmt.Errorf("no player named %q in the FIFA 19 dataset; the closest names are: %s",
					query, strings.Join(near, ", "))
			}
			return nil, fmt.Errorf("no player matching %q in the FIFA dataset", query)
		}
		sortPlayers(candidates, "overall")
		p = candidates[0]
	}

	v := &PlayerProfileView{
		PlayerView:       p.toView(),
		Height:           p.Height,
		Weight:           p.Weight,
		PreferredFoot:    p.PreferredFoot,
		WorkRate:         p.WorkRate,
		BodyType:         p.BodyType,
		Joined:           p.Joined,
		ContractUntil:    p.ContractUntil,
		ReleaseClause:    p.ReleaseClause,
		IntlReputation:   p.IntlReputation,
		WeakFoot:         p.WeakFoot,
		SkillMoves:       p.SkillMoves,
		Skills:           p.Skills,
		LinkedClubTeamID: p.ClubTeamID,
	}
	if t, ok := g.Teams[p.ClubTeamID]; ok {
		v.LinkedClubMatches = t.matchCount
	}
	for k, val := range p.Skills {
		v.TopSkills = append(v.TopSkills, SkillValue{Skill: k, Value: val})
	}
	sort.SliceStable(v.TopSkills, func(i, j int) bool {
		if v.TopSkills[i].Value != v.TopSkills[j].Value {
			return v.TopSkills[i].Value > v.TopSkills[j].Value
		}
		return v.TopSkills[i].Skill < v.TopSkills[j].Skill
	})
	if len(v.TopSkills) > 8 {
		v.TopSkills = v.TopSkills[:8]
	}
	return v, nil
}

// similarPlayerNames finds players sharing a name token with the query, so that
// a miss can suggest alternatives instead of simply failing.
func (g *Graph) similarPlayerNames(query string, limit int) []string {
	tokens := tokenize(query)
	if len(tokens) == 0 {
		return nil
	}
	var hits []*Player
	for _, p := range g.Players {
		nameTokens := tokenize(p.Name)
		for _, qt := range tokens {
			if len(qt) < 3 {
				continue
			}
			for _, nt := range nameTokens {
				if nt == qt {
					hits = append(hits, p)
					goto next
				}
			}
		}
	next:
	}
	sortPlayers(hits, "overall")
	out := make([]string, 0, limit)
	for _, p := range hits {
		if len(out) == limit {
			break
		}
		out = append(out, fmt.Sprintf("%s (%s, overall %d)", p.Name, p.Club, p.Overall))
	}
	return out
}

// ClubSquadResult is a club's squad in the FIFA dataset.
type ClubSquadResult struct {
	Query         string       `json:"query"`
	FIFAClub      string       `json:"fifa_club,omitempty"`
	LinkedTeam    *TeamView    `json:"linked_team,omitempty"`
	Squad         []PlayerView `json:"squad"`
	SquadSize     int          `json:"squad_size"`
	AvgOverall    float64      `json:"avg_overall,omitempty"`
	AvgAge        float64      `json:"avg_age,omitempty"`
	ByNationality []GroupCount `json:"by_nationality,omitempty"`
	ByPosition    []GroupCount `json:"by_position,omitempty"`
	Note          string       `json:"note,omitempty"`
}

// ClubSquad returns the FIFA squad for a club, resolving the club name through
// the match-data team graph when possible. This is the cross-file join between
// the player dataset and the match datasets.
func (g *Graph) ClubSquad(club string, limit int) (*ClubSquadResult, error) {
	if strings.TrimSpace(club) == "" {
		return nil, fmt.Errorf("a club name is required")
	}
	res := &ClubSquadResult{Query: club}
	var teamID string
	if t, err := g.ResolveTeam(club); err == nil {
		teamID = t.ID
		tv := t.ToView()
		res.LinkedTeam = &tv
	}

	q := Slug(club)
	var squad []*Player
	for _, p := range g.Players {
		if (teamID != "" && p.ClubTeamID == teamID) || (q != "" && strings.Contains(Slug(p.Club), q)) {
			squad = append(squad, p)
		}
	}
	if len(squad) == 0 {
		res.Squad = []PlayerView{}
		res.Note = g.emptyPlayerNote(PlayerFilter{Club: club})
		return res, nil
	}
	sortPlayers(squad, "overall")
	res.FIFAClub = squad[0].Club
	res.SquadSize = len(squad)

	sumO, sumA := 0, 0
	for _, p := range squad {
		sumO += p.Overall
		sumA += p.Age
	}
	res.AvgOverall = round1(float64(sumO) / float64(len(squad)))
	res.AvgAge = round1(float64(sumA) / float64(len(squad)))
	res.ByNationality = groupPlayers(squad, "nationality")
	res.ByPosition = groupPlayers(squad, "position")

	if limit <= 0 {
		limit = 30
	}
	shown := squad
	if len(shown) > limit {
		shown = shown[:limit]
		res.Note = fmt.Sprintf("showing the top %d of %d squad members", limit, len(squad))
	}
	for _, p := range shown {
		res.Squad = append(res.Squad, p.toView())
	}
	return res, nil
}
