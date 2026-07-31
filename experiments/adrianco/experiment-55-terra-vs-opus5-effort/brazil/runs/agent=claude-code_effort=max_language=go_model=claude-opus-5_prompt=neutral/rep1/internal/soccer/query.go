// query.go implements the match and player searches that sit behind the MCP
// tools: filtering by team, opponent, venue, competition, season, date range,
// round/stage and result, plus free text resolution of the arguments.
package soccer

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// Venue restricts a team filter to home or away fixtures.
type Venue string

// Venue values.
const (
	VenueAny  Venue = "any"
	VenueHome Venue = "home"
	VenueAway Venue = "away"
)

// ParseVenue reads a venue from free text.
func ParseVenue(s string) (Venue, error) {
	switch Fold(strings.TrimSpace(s)) {
	case "", "any", "all", "both", "either":
		return VenueAny, nil
	case "home":
		return VenueHome, nil
	case "away":
		return VenueAway, nil
	}
	return VenueAny, fmt.Errorf("unknown venue %q (use home, away or any)", s)
}

// MatchFilter selects matches. The zero value matches everything.
type MatchFilter struct {
	TeamID        string
	OpponentID    string
	Venue         Venue
	CompetitionID string
	Season        int
	SeasonFrom    int
	SeasonTo      int
	From          time.Time
	To            time.Time
	Round         int
	Stage         string // substring match, case/accent insensitive
	Result        string // win | loss | draw, relative to TeamID
	MinTotalGoals int
	MinMargin     int
	Sort          string // date_desc (default) | date_asc | goals_desc | margin_desc
	Limit         int
	Offset        int
}

func (f MatchFilter) matches(m *Match) bool {
	if f.CompetitionID != "" && m.CompetitionID != f.CompetitionID {
		return false
	}
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if f.SeasonFrom != 0 && m.Season < f.SeasonFrom {
		return false
	}
	if f.SeasonTo != 0 && m.Season > f.SeasonTo {
		return false
	}
	if !f.From.IsZero() && m.Date.Before(f.From) {
		return false
	}
	if !f.To.IsZero() && m.Date.After(f.To) {
		return false
	}
	if f.Round != 0 && m.Round != f.Round {
		return false
	}
	if f.Stage != "" && !StageMatches(m.Stage, f.Stage) {
		return false
	}
	if f.MinTotalGoals > 0 && m.TotalGoals() < f.MinTotalGoals {
		return false
	}
	if f.MinMargin > 0 && m.GoalMargin() < f.MinMargin {
		return false
	}
	if f.TeamID != "" {
		switch f.Venue {
		case VenueHome:
			if m.HomeTeamID != f.TeamID {
				return false
			}
		case VenueAway:
			if m.AwayTeamID != f.TeamID {
				return false
			}
		default:
			if !m.Involves(f.TeamID) {
				return false
			}
		}
		if f.OpponentID != "" && m.Opponent(f.TeamID) != f.OpponentID {
			return false
		}
		if f.Result != "" {
			want, ok := parseResult(f.Result)
			if !ok || m.ResultFor(f.TeamID) != want {
				return false
			}
		}
	} else if f.OpponentID != "" && !m.Involves(f.OpponentID) {
		return false
	}
	return true
}

// parseResult reads "win", "draw" or "loss" (and their obvious variants) as
// the single letter Match.ResultFor returns.
func parseResult(s string) (string, bool) {
	switch Fold(strings.TrimSpace(s)) {
	case "w", "win", "wins", "won", "victory", "v":
		return "W", true
	case "d", "draw", "draws", "drew", "tie", "tied":
		return "D", true
	case "l", "loss", "losses", "lose", "lost", "defeat":
		return "L", true
	}
	return "", false
}

// StageMatches compares a match stage with a filter, on whole words: asking
// for "final" must not return every quarterfinal, but "semi" should still find
// the semifinals and "final" must find "final (inferred)".
func StageMatches(stage, want string) bool {
	s, w := Fold(strings.TrimSpace(stage)), Fold(strings.TrimSpace(want))
	if w == "" {
		return true
	}
	if s == w || strings.HasPrefix(s, w+" ") {
		return true
	}
	for _, word := range strings.Fields(nonAlnum.ReplaceAllString(s, " ")) {
		if strings.HasPrefix(word, w) {
			return true
		}
	}
	return false
}

// MatchPage is a page of match results plus the unpaged total.
type MatchPage struct {
	Matches []*Match
	Total   int
}

// FindMatches applies a filter, choosing the cheapest index available.
func (s *Store) FindMatches(f MatchFilter) MatchPage {
	var candidates []*Match
	switch {
	case f.TeamID != "":
		candidates = s.byTeam[f.TeamID]
	case f.CompetitionID != "" && f.Season != 0:
		candidates = s.byCompSeason[compSeason{f.CompetitionID, f.Season}]
	case f.CompetitionID != "":
		candidates = s.byComp[f.CompetitionID]
	default:
		candidates = s.Matches
	}
	out := make([]*Match, 0, 64)
	for _, m := range candidates {
		if f.matches(m) {
			out = append(out, m)
		}
	}
	total := len(out)
	sortMatches(out, f.Sort)
	if f.Offset > 0 {
		if f.Offset >= len(out) {
			out = nil
		} else {
			out = out[f.Offset:]
		}
	}
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return MatchPage{Matches: out, Total: total}
}

func sortMatches(ms []*Match, mode string) {
	switch mode {
	case "date_asc":
		sortSlice(ms, func(a, b *Match) bool { return a.Date.Before(b.Date) })
	case "goals_desc":
		sortSlice(ms, func(a, b *Match) bool {
			if a.TotalGoals() != b.TotalGoals() {
				return a.TotalGoals() > b.TotalGoals()
			}
			return a.Date.After(b.Date)
		})
	case "margin_desc":
		sortSlice(ms, func(a, b *Match) bool {
			if a.GoalMargin() != b.GoalMargin() {
				return a.GoalMargin() > b.GoalMargin()
			}
			if a.TotalGoals() != b.TotalGoals() {
				return a.TotalGoals() > b.TotalGoals()
			}
			return a.Date.After(b.Date)
		})
	default: // date_desc
		sortSlice(ms, func(a, b *Match) bool { return a.Date.After(b.Date) })
	}
}

// ---------------------------------------------------------------------------
// Player queries
// ---------------------------------------------------------------------------

// PlayerFilter selects players from fifa_data.csv.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string // raw club text
	TeamID      string // canonical club
	Position    string // exact code (ST) or group (forward)
	MinOverall  int
	MaxOverall  int
	MinAge      int
	MaxAge      int
	Sort        string // overall_desc (default) | potential_desc | age_asc | name
	Limit       int
	Offset      int
}

// PlayerPage is a page of players plus the unpaged total.
type PlayerPage struct {
	Players []*Player
	Total   int
}

func (f PlayerFilter) matches(p *Player) bool {
	if f.Nationality != "" && Fold(p.Nationality) != Fold(f.Nationality) {
		return false
	}
	if f.TeamID != "" && p.TeamID != f.TeamID {
		return false
	}
	if f.Club != "" && !strings.Contains(Fold(p.Club), Fold(f.Club)) {
		return false
	}
	if f.Position != "" {
		want := Fold(f.Position)
		if !strings.EqualFold(p.Position, f.Position) && p.PositionGroup() != want {
			return false
		}
	}
	if f.MinOverall > 0 && p.Overall < f.MinOverall {
		return false
	}
	if f.MaxOverall > 0 && p.Overall > f.MaxOverall {
		return false
	}
	if f.MinAge > 0 && p.Age < f.MinAge {
		return false
	}
	if f.MaxAge > 0 && p.Age > f.MaxAge {
		return false
	}
	if f.Name != "" && !matchesName(p.Name, f.Name) {
		return false
	}
	return true
}

// matchesName is a forgiving name comparison: substring on the whole name, or
// every query token appearing as a prefix of some name token ("gab bar" finds
// "Gabriel Barbosa").
func matchesName(name, query string) bool {
	fn, fq := Fold(name), Fold(query)
	if strings.Contains(fn, fq) {
		return true
	}
	nameTokens := strings.Fields(nonAlnum.ReplaceAllString(fn, " "))
	for _, qt := range strings.Fields(nonAlnum.ReplaceAllString(fq, " ")) {
		hit := false
		for _, nt := range nameTokens {
			if strings.HasPrefix(nt, qt) {
				hit = true
				break
			}
		}
		if !hit {
			return false
		}
	}
	return true
}

// FindPlayers applies a player filter.
func (s *Store) FindPlayers(f PlayerFilter) PlayerPage {
	var candidates []*Player
	switch {
	case f.TeamID != "":
		candidates = s.playersByTeam[f.TeamID]
	case f.Nationality != "":
		candidates = s.playersByNat[Fold(f.Nationality)]
	default:
		candidates = s.Players
	}
	out := make([]*Player, 0, 32)
	for _, p := range candidates {
		if f.matches(p) {
			out = append(out, p)
		}
	}
	total := len(out)
	switch f.Sort {
	case "potential_desc":
		sortSlice(out, func(a, b *Player) bool { return a.Potential > b.Potential })
	case "age_asc":
		sortSlice(out, func(a, b *Player) bool { return a.Age < b.Age })
	case "age_desc":
		sortSlice(out, func(a, b *Player) bool { return a.Age > b.Age })
	case "name":
		sortSlice(out, func(a, b *Player) bool { return Fold(a.Name) < Fold(b.Name) })
	default:
		sortSlice(out, func(a, b *Player) bool {
			if a.Overall != b.Overall {
				return a.Overall > b.Overall
			}
			return Fold(a.Name) < Fold(b.Name)
		})
	}
	if f.Offset > 0 {
		if f.Offset >= len(out) {
			out = nil
		} else {
			out = out[f.Offset:]
		}
	}
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return PlayerPage{Players: out, Total: total}
}

// SuggestPlayers returns the closest player names to a query, used when a
// lookup finds nothing.
func (s *Store) SuggestPlayers(query string, n int) []string {
	q := Fold(strings.TrimSpace(query))
	if q == "" {
		return nil
	}
	type cand struct {
		name string
		dist int
	}
	seen := map[string]bool{}
	var cands []cand
	for _, tok := range strings.Fields(nonAlnum.ReplaceAllString(q, " ")) {
		for name, players := range s.playerTokens {
			d := Levenshtein(tok, name)
			if d > 2 {
				continue
			}
			for _, p := range players {
				if seen[p.Name] {
					continue
				}
				seen[p.Name] = true
				cands = append(cands, cand{p.Name, d})
			}
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

// ClubSummary aggregates the FIFA squad of one club.
type ClubSummary struct {
	Club       string  `json:"club"`
	TeamID     string  `json:"team_id,omitempty"`
	Country    string  `json:"country,omitempty"`
	Players    int     `json:"players"`
	AvgOverall float64 `json:"avg_overall"`
	MaxOverall int     `json:"max_overall"`
	TopPlayer  string  `json:"top_player"`
	Brazilians int     `json:"brazilian_players"`
}

// ClubFilter selects which FIFA clubs ClubSummaries reports on.
type ClubFilter struct {
	LinkedOnly bool   // only clubs that also appear in the match data
	Country    string // country of the linked club, e.g. "BRA"
	MinPlayers int
}

// ClubSummaries aggregates the FIFA squads by club.
func (s *Store) ClubSummaries(f ClubFilter) []ClubSummary {
	type acc struct {
		sum, max, n, br int
		top             string
		teamID          string
		country         string
	}
	byClub := map[string]*acc{}
	for _, p := range s.Players {
		if p.Club == "" {
			continue
		}
		if (f.LinkedOnly || f.Country != "") && p.TeamID == "" {
			continue
		}
		if f.Country != "" {
			team := s.Teams.Team(p.TeamID)
			if team == nil || !strings.EqualFold(team.Country, f.Country) {
				continue
			}
		}
		a := byClub[p.Club]
		if a == nil {
			a = &acc{teamID: p.TeamID}
			if team := s.Teams.Team(p.TeamID); team != nil {
				a.country = team.Country
			}
			byClub[p.Club] = a
		}
		a.n++
		a.sum += p.Overall
		if p.Overall > a.max {
			a.max, a.top = p.Overall, p.Name
		}
		if Fold(p.Nationality) == "brazil" {
			a.br++
		}
	}
	out := make([]ClubSummary, 0, len(byClub))
	for club, a := range byClub {
		if a.n < f.MinPlayers {
			continue
		}
		out = append(out, ClubSummary{
			Club: club, TeamID: a.teamID, Country: a.country, Players: a.n,
			AvgOverall: round1(float64(a.sum) / float64(a.n)),
			MaxOverall: a.max, TopPlayer: a.top, Brazilians: a.br,
		})
	}
	sortSlice(out, func(a, b ClubSummary) bool {
		if a.AvgOverall != b.AvgOverall {
			return a.AvgOverall > b.AvgOverall
		}
		return a.Club < b.Club
	})
	return out
}

func round1(f float64) float64 { return float64(int(f*10+0.5)) / 10 }

// ---------------------------------------------------------------------------
// Argument resolution helpers shared by the tools
// ---------------------------------------------------------------------------

// ResolveTeam maps user text to a canonical team, returning the alternatives
// considered so that callers can explain themselves.
func (s *Store) ResolveTeam(q string) (*Team, []*Team, error) { return s.Teams.Lookup(q) }

// ResolveSeason parses a season, accepting "2019" or 2019.
func ResolveSeason(v any) (int, error) {
	switch t := v.(type) {
	case nil:
		return 0, nil
	case int:
		return t, nil
	case float64:
		return int(t), nil
	case string:
		if strings.TrimSpace(t) == "" {
			return 0, nil
		}
		var year int
		if _, err := fmt.Sscanf(strings.TrimSpace(t), "%d", &year); err != nil {
			return 0, fmt.Errorf("invalid season %q", t)
		}
		return year, nil
	}
	return 0, fmt.Errorf("invalid season %v", v)
}

// TeamProfile is everything known about one club.
type TeamProfile struct {
	Team          *Team             `json:"team"`
	Record        Record            `json:"record"`
	Home          Record            `json:"home_record"`
	Away          Record            `json:"away_record"`
	ByCompetition []CompRecord      `json:"by_competition"`
	FirstMatch    *Match            `json:"first_match,omitempty"`
	LastMatch     *Match            `json:"last_match,omitempty"`
	BiggestWin    *Match            `json:"biggest_win,omitempty"`
	HeaviestLoss  *Match            `json:"heaviest_defeat,omitempty"`
	Stadiums      []NameCount       `json:"stadiums,omitempty"`
	Squad         []*Player         `json:"squad,omitempty"`
	Rivals        []Rivalry         `json:"rivalries,omitempty"`
	RivalNames    map[string]string `json:"rival_names,omitempty"` // club id -> display name
	Titles        []SeasonTitle     `json:"league_titles,omitempty"`
}

// NameCount is a generic labelled counter.
type NameCount struct {
	Name  string `json:"name"`
	Count int    `json:"count"`
}

// SeasonTitle records a league season won by a club (computed from results).
type SeasonTitle struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Points      int    `json:"points"`
}

// CompRecord is a club's record within one competition.
type CompRecord struct {
	CompetitionID string `json:"competition"`
	Record        Record `json:"record"`
}

// Profile assembles a full club profile.
func (s *Store) Profile(teamID string) *TeamProfile {
	t := s.Teams.Team(teamID)
	if t == nil {
		return nil
	}
	p := &TeamProfile{Team: t}
	byComp := map[string]*Record{}
	stadiums := map[string]int{}
	ms := s.byTeam[teamID]
	for _, m := range ms {
		p.Record.Add(m, teamID)
		if m.HomeTeamID == teamID {
			p.Home.Add(m, teamID)
		} else {
			p.Away.Add(m, teamID)
		}
		r := byComp[m.CompetitionID]
		if r == nil {
			r = &Record{}
			byComp[m.CompetitionID] = r
		}
		r.Add(m, teamID)
		if m.Venue != "" && m.HomeTeamID == teamID {
			stadiums[m.Venue]++
		}
		if p.FirstMatch == nil || m.Date.Before(p.FirstMatch.Date) {
			p.FirstMatch = m
		}
		if p.LastMatch == nil || m.Date.After(p.LastMatch.Date) {
			p.LastMatch = m
		}
		margin := m.GoalsFor(teamID) - m.GoalsAgainst(teamID)
		if margin > 0 && (p.BiggestWin == nil || margin > p.BiggestWin.GoalsFor(teamID)-p.BiggestWin.GoalsAgainst(teamID)) {
			p.BiggestWin = m
		}
		if margin < 0 && (p.HeaviestLoss == nil || margin < p.HeaviestLoss.GoalsFor(teamID)-p.HeaviestLoss.GoalsAgainst(teamID)) {
			p.HeaviestLoss = m
		}
	}
	p.Record.TeamID, p.Record.TeamName = t.ID, t.Name
	for comp, r := range byComp {
		r.TeamID, r.TeamName = t.ID, t.Name
		p.ByCompetition = append(p.ByCompetition, CompRecord{CompetitionID: comp, Record: *r})
	}
	sortSlice(p.ByCompetition, func(a, b CompRecord) bool {
		if a.Record.Matches != b.Record.Matches {
			return a.Record.Matches > b.Record.Matches
		}
		return a.CompetitionID < b.CompetitionID // ties must not depend on map order
	})
	for name, n := range stadiums {
		p.Stadiums = append(p.Stadiums, NameCount{name, n})
	}
	sortSlice(p.Stadiums, func(a, b NameCount) bool {
		if a.Count != b.Count {
			return a.Count > b.Count
		}
		return a.Name < b.Name
	})
	if len(p.Stadiums) > 5 {
		p.Stadiums = p.Stadiums[:5]
	}
	// The squad is copied before sorting: the store's slices are shared by
	// every caller and must stay untouched.
	p.Squad = append([]*Player(nil), s.playersByTeam[teamID]...)
	sortSlice(p.Squad, func(a, b *Player) bool {
		if a.Overall != b.Overall {
			return a.Overall > b.Overall
		}
		return a.ID < b.ID
	})
	for _, r := range Rivalries() {
		if r.TeamA != teamID && r.TeamB != teamID {
			continue
		}
		p.Rivals = append(p.Rivals, r)
		other := r.TeamA
		if other == teamID {
			other = r.TeamB
		}
		if rival := s.Teams.Team(other); rival != nil {
			if p.RivalNames == nil {
				p.RivalNames = map[string]string{}
			}
			p.RivalNames[other] = rival.Name
		}
	}
	for _, c := range s.CompetitionsWithData() {
		if c.Kind != "league" {
			continue
		}
		for _, season := range s.Seasons(c.ID) {
			table := s.Standings(c.ID, season, StandingsOptions{})
			if len(table.Rows) > 0 && table.Rows[0].TeamID == teamID && table.Complete {
				p.Titles = append(p.Titles, SeasonTitle{Competition: c.ID, Season: season, Points: table.Rows[0].Points})
			}
		}
	}
	return p
}
