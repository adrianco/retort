package soccer

import (
	"fmt"
	"math"
	"sort"
	"strings"
)

// PlayerView is a player as presented to the user.
type PlayerView struct {
	ID            int     `json:"id"`
	Name          string  `json:"name"`
	Age           int     `json:"age"`
	Nationality   string  `json:"nationality"`
	Overall       int     `json:"overall"`
	Potential     int     `json:"potential"`
	Club          string  `json:"club"`
	Position      string  `json:"position"`
	JerseyNumber  int     `json:"jersey_number,omitempty"`
	Height        string  `json:"height,omitempty"`
	Weight        string  `json:"weight,omitempty"`
	Value         string  `json:"value,omitempty"`
	Wage          string  `json:"wage,omitempty"`
	PreferredFoot string  `json:"preferred_foot,omitempty"`
	Joined        string  `json:"joined,omitempty"`
	ContractUntil string  `json:"contract_valid_until,omitempty"`
	Skills        []Skill `json:"skills,omitempty"`
}

func viewPlayer(p *Player, withSkills bool) PlayerView {
	v := PlayerView{ID: p.ID, Name: p.Name, Age: p.Age, Nationality: p.Nationality, Overall: p.Overall,
		Potential: p.Potential, Club: p.Club, Position: p.Position, JerseyNumber: p.Jersey, Height: p.Height,
		Weight: p.Weight, Value: p.Value, Wage: p.Wage, PreferredFoot: p.PreferredFoot, Joined: p.Joined,
		ContractUntil: p.ContractUntil}
	if withSkills {
		v.Skills = p.Skills
	}
	return v
}

// playerBefore orders players best first.
func playerBefore(a, b *Player) bool {
	if a.Overall != b.Overall {
		return a.Overall > b.Overall
	}
	if a.Potential != b.Potential {
		return a.Potential > b.Potential
	}
	return a.Name < b.Name
}

var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"},
	"midfielder": {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
	"defender":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
}

var positionWords = map[string]string{
	"forward": "forward", "forwards": "forward", "attacker": "forward", "attackers": "forward", "fw": "forward",
	"striker": "forward", "strikers": "forward", "winger": "forward", "wingers": "forward",
	"midfielder": "midfielder", "midfielders": "midfielder", "midfield": "midfielder", "mf": "midfielder",
	"defender": "defender", "defenders": "defender", "defence": "defender", "defense": "defender", "df": "defender",
	"goalkeeper": "goalkeeper", "goalkeepers": "goalkeeper", "keeper": "goalkeeper", "keepers": "goalkeeper",
}

// positionsFor turns "forward", "ST" or "ST,CF" into the positions meant.
func positionsFor(position string) map[string]bool {
	out := map[string]bool{}
	for _, part := range strings.Split(position, ",") {
		p := Fold(part)
		if p == "" {
			continue
		}
		if group, ok := positionWords[p]; ok {
			for _, code := range positionGroups[group] {
				out[code] = true
			}
			continue
		}
		out[strings.ToUpper(p)] = true
	}
	return out
}

var demonyms = map[string]string{
	"brazilian": "brazil", "brasil": "brazil", "brasileiro": "brazil", "argentine": "argentina", "argentinian": "argentina",
	"uruguayan": "uruguay", "colombian": "colombia", "chilean": "chile", "paraguayan": "paraguay", "peruvian": "peru",
	"ecuadorian": "ecuador", "venezuelan": "venezuela", "bolivian": "bolivia", "portuguese": "portugal",
	"spanish": "spain", "french": "france", "german": "germany", "english": "england", "italian": "italy",
	"dutch": "netherlands", "belgian": "belgium", "mexican": "mexico",
}

func nationalityKey(n string) string {
	f := Fold(n)
	if c, ok := demonyms[f]; ok {
		return c
	}
	return f
}

// PlayerQuery selects players. Zero values mean "any".
type PlayerQuery struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	MaxAge      int
}

// nameMatches reports whether every word asked for is in the player's name.
func nameMatches(name, query string) bool {
	n := Fold(name)
	for _, w := range strings.Fields(Fold(query)) {
		if !strings.Contains(n, w) {
			return false
		}
	}
	return true
}

// playersAt finds a club's players by its key, or failing that by name.
func (s *Store) playersAt(key, name string) []*Player {
	var out []*Player
	for _, p := range s.Players {
		if p.ClubKey == key {
			out = append(out, p)
		}
	}
	if len(out) == 0 && strings.TrimSpace(name) != "" {
		q := Fold(name)
		for _, p := range s.Players {
			if p.Club != "" && strings.Contains(Fold(p.Club), q) {
				out = append(out, p)
			}
		}
	}
	return out
}

// FindPlayers returns the players meeting the query, best first.
func (s *Store) FindPlayers(q PlayerQuery) []*Player {
	candidates := s.Players
	if q.Club != "" {
		candidates = s.playersAt(NormalizeTeam(q.Club).Key, q.Club)
	}
	positions := positionsFor(q.Position)
	nationality := nationalityKey(q.Nationality)
	var out []*Player
	for _, p := range candidates {
		if q.Name != "" && !nameMatches(p.Name, q.Name) {
			continue
		}
		if nationality != "" && Fold(p.Nationality) != nationality {
			continue
		}
		if len(positions) > 0 && !positions[p.Position] {
			continue
		}
		if q.MinOverall > 0 && p.Overall < q.MinOverall {
			continue
		}
		if q.MaxAge > 0 && p.Age > q.MaxAge {
			continue
		}
		out = append(out, p)
	}
	return out
}

// PlayerList is a list of players found.
type PlayerList struct {
	Description string       `json:"description"`
	Total       int          `json:"total"`
	Returned    int          `json:"returned"`
	Players     []PlayerView `json:"players"`
}

// SearchPlayers lists players, best rated first.
func (s *Store) SearchPlayers(q PlayerQuery, limit int) PlayerList {
	found := s.FindPlayers(q)
	if limit <= 0 {
		limit = 20
	}
	list := PlayerList{Description: describePlayers(q), Total: len(found)}
	for i, p := range found {
		if i == limit {
			break
		}
		list.Players = append(list.Players, viewPlayer(p, false))
	}
	list.Returned = len(list.Players)
	return list
}

func describePlayers(q PlayerQuery) string {
	d := "Players"
	if q.Position != "" {
		d = titleCase(Fold(q.Position)) + " players"
	}
	if q.Nationality != "" {
		d += " from " + titleCase(nationalityKey(q.Nationality))
	}
	if q.Club != "" {
		d += " at " + q.Club
	}
	if q.Name != "" {
		d += fmt.Sprintf(" named %q", q.Name)
	}
	if q.MinOverall > 0 {
		d += fmt.Sprintf(" rated %d+", q.MinOverall)
	}
	return d + " (FIFA player data, highest rated first)"
}

func (l PlayerList) Text() string {
	var b strings.Builder
	if l.Total == 0 {
		fmt.Fprintf(&b, "%s: no players found.\n", l.Description)
		return b.String()
	}
	fmt.Fprintf(&b, "%s — %d found:\n", l.Description, l.Total)
	for i, p := range l.Players {
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Position: %s, Club: %s, Nationality: %s, Age: %d\n",
			i+1, p.Name, p.Overall, p.Position, orNone(p.Club), p.Nationality, p.Age)
	}
	if l.Total > l.Returned {
		fmt.Fprintf(&b, "... (%d more)\n", l.Total-l.Returned)
	}
	return b.String()
}

func orNone(s string) string {
	if s == "" {
		return "no club"
	}
	return s
}

// PlayerProfile describes one player, with other players of similar name.
type PlayerProfile struct {
	Player     *PlayerView  `json:"player"`
	OtherMatch []PlayerView `json:"other_matches,omitempty"`
}

// PlayerProfile finds the player a name refers to: an exact name first,
// otherwise the highest rated player whose name contains every word.
func (s *Store) PlayerProfile(name string) (PlayerProfile, error) {
	found := s.FindPlayers(PlayerQuery{Name: name})
	if len(found) == 0 {
		return PlayerProfile{}, &NotFoundError{Kind: "player", Name: name}
	}
	best := found[0]
	for _, p := range found {
		if Fold(p.Name) == Fold(name) {
			best = p
			break
		}
	}
	v := viewPlayer(best, true)
	profile := PlayerProfile{Player: &v}
	for _, p := range found {
		if p != best && len(profile.OtherMatch) < 10 {
			profile.OtherMatch = append(profile.OtherMatch, viewPlayer(p, false))
		}
	}
	return profile, nil
}

func (p PlayerProfile) Text() string {
	var b strings.Builder
	v := p.Player
	fmt.Fprintf(&b, "%s (FIFA player data)\n", v.Name)
	fmt.Fprintf(&b, "- Club: %s\n- Nationality: %s\n- Position: %s", orNone(v.Club), v.Nationality, v.Position)
	if v.JerseyNumber > 0 {
		fmt.Fprintf(&b, " (#%d)", v.JerseyNumber)
	}
	fmt.Fprintf(&b, "\n- Overall: %d, Potential: %d\n- Age: %d", v.Overall, v.Potential, v.Age)
	if v.Height != "" || v.Weight != "" {
		fmt.Fprintf(&b, ", Height: %s, Weight: %s", v.Height, v.Weight)
	}
	b.WriteString("\n")
	if v.PreferredFoot != "" {
		fmt.Fprintf(&b, "- Preferred foot: %s\n", v.PreferredFoot)
	}
	if v.Value != "" {
		fmt.Fprintf(&b, "- Value: %s, Wage: %s\n", v.Value, v.Wage)
	}
	if len(v.Skills) > 0 {
		top := append([]Skill(nil), v.Skills...)
		sort.SliceStable(top, func(i, j int) bool { return top[i].Rating > top[j].Rating })
		var parts []string
		for _, s := range top[:min(6, len(top))] {
			parts = append(parts, fmt.Sprintf("%s %d", s.Name, s.Rating))
		}
		fmt.Fprintf(&b, "- Best attributes: %s\n", strings.Join(parts, ", "))
	}
	if len(p.OtherMatch) > 0 {
		b.WriteString("Other players with a similar name:\n")
		for _, o := range p.OtherMatch {
			fmt.Fprintf(&b, "- %s - Overall: %d, Club: %s\n", o.Name, o.Overall, orNone(o.Club))
		}
	}
	return b.String()
}

// ClubCount is how many players of a nationality a club has.
type ClubCount struct {
	Club           string  `json:"club"`
	Players        int     `json:"players"`
	AverageOverall float64 `json:"average_overall"`
	BestPlayer     string  `json:"best_player"`
}

// NationalityByClub is how a nationality's players spread over clubs.
type NationalityByClub struct {
	Nationality string      `json:"nationality"`
	Clubs       []ClubCount `json:"clubs"`
}

// isBrazilianSquad decides whether a club in the player data is a
// Brazilian club. Its name must match a club in the Brazilian domestic
// match data, and since clubs abroad can share a name with a smaller
// Brazilian club ("Boavista"), it must also be one of the major clubs, or
// have a mostly Brazilian squad.
func (s *Store) isBrazilianSquad(clubKey string) bool {
	if clubKey == "" || !s.IsBrazilianClub(clubKey) {
		return false
	}
	if t := s.Teams[clubKey]; t != nil && t.Known {
		return true
	}
	squad, brazilians := 0, 0
	for _, p := range s.Players {
		if p.ClubKey == clubKey {
			squad++
			if nationalityKey(p.Nationality) == "brazil" {
				brazilians++
			}
		}
	}
	return brazilians*2 > squad
}

// PlayersAtBrazilianClubs counts a nationality's players at each club that
// plays in Brazilian domestic competitions, combining the player data with
// the match data.
func (s *Store) PlayersAtBrazilianClubs(nationality string) NationalityByClub {
	if nationality == "" {
		nationality = "Brazil"
	}
	result := NationalityByClub{Nationality: titleCase(nationalityKey(nationality))}
	byClub := map[string]*ClubCount{}
	totals := map[string]int{}
	brazilian := map[string]bool{}
	var order []string
	for _, p := range s.FindPlayers(PlayerQuery{Nationality: nationality}) {
		isBrazilian, seen := brazilian[p.ClubKey]
		if !seen {
			isBrazilian = s.isBrazilianSquad(p.ClubKey)
			brazilian[p.ClubKey] = isBrazilian
		}
		if !isBrazilian {
			continue
		}
		c, ok := byClub[p.ClubKey]
		if !ok {
			c = &ClubCount{Club: p.Club, BestPlayer: p.Name}
			byClub[p.ClubKey] = c
			order = append(order, p.ClubKey)
		}
		c.Players++
		totals[p.ClubKey] += p.Overall
	}
	for _, key := range order {
		c := byClub[key]
		c.AverageOverall = math.Round(float64(totals[key])*10/float64(c.Players)) / 10
		result.Clubs = append(result.Clubs, *c)
	}
	sort.SliceStable(result.Clubs, func(i, j int) bool {
		if result.Clubs[i].Players != result.Clubs[j].Players {
			return result.Clubs[i].Players > result.Clubs[j].Players
		}
		return result.Clubs[i].AverageOverall > result.Clubs[j].AverageOverall
	})
	return result
}

func (n NationalityByClub) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s players at Brazilian clubs (FIFA player data, clubs found in the Brazilian match data):\n", n.Nationality)
	if len(n.Clubs) == 0 {
		b.WriteString("- None found.\n")
	}
	for _, c := range n.Clubs {
		fmt.Fprintf(&b, "- %s: %d %s (avg rating: %.1f, best: %s)\n", c.Club, c.Players, plural(c.Players, "player", "players"), c.AverageOverall, c.BestPlayer)
	}
	return b.String()
}
