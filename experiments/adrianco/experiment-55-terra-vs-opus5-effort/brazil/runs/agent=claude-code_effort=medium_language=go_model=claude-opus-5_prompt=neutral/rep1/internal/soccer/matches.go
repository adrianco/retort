package soccer

import (
	"sort"
	"strings"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/normalize"
)

// MatchFilter describes a match search. Every field is optional; the zero
// filter selects everything.
type MatchFilter struct {
	Team        string // any club, home or away
	Venue       string // "home", "away" or "" (any) — applies to Team
	Opponent    string // restricts to fixtures against this club
	Competition string // substring match on the competition name
	Season      int
	SeasonFrom  int
	SeasonTo    int
	From        time.Time
	To          time.Time
	Round       string // substring match on round/stage, e.g. "final"
	MinGoals    int
	Limit       int
	Ascending   bool // default is most recent first
}

// MatchQueryResult is the answer to a match search.
type MatchQueryResult struct {
	Query      MatchFilter `json:"-"`
	Total      int         `json:"total_matches"`
	Returned   int         `json:"returned"`
	Matches    []Match     `json:"matches"`
	HeadToHead *H2H        `json:"head_to_head,omitempty"`
	Summary    string      `json:"summary"`
}

// FindMatches applies a filter over the whole graph.
func (g *Graph) FindMatches(f MatchFilter) (*MatchQueryResult, error) {
	var teamID, oppID string
	var teamName, oppName string

	candidates := allIndexes(len(g.Matches))
	if f.Team != "" {
		t, err := g.ResolveTeam(f.Team)
		if err != nil {
			return nil, err
		}
		teamID, teamName = t.ID, t.Name
		candidates = t.matchIdx
	}
	if f.Opponent != "" {
		o, err := g.ResolveTeam(f.Opponent)
		if err != nil {
			return nil, err
		}
		oppID, oppName = o.ID, o.Name
		if teamID == "" {
			candidates = o.matchIdx
		}
	}

	comp := normalize.Deaccent(f.Competition)
	round := normalize.Deaccent(f.Round)

	var hits []int
	for _, i := range candidates {
		m := &g.Matches[i]
		if teamID != "" {
			switch f.Venue {
			case "home":
				if m.Home.ID != teamID {
					continue
				}
			case "away":
				if m.Away.ID != teamID {
					continue
				}
			default:
				if !m.Involves(teamID) {
					continue
				}
			}
		}
		if oppID != "" && !m.Involves(oppID) {
			continue
		}
		if comp != "" && !strings.Contains(normalize.Deaccent(m.Competition), comp) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.SeasonFrom != 0 && m.Season < f.SeasonFrom {
			continue
		}
		if f.SeasonTo != 0 && m.Season > f.SeasonTo {
			continue
		}
		if !f.From.IsZero() && m.Date.Before(f.From) {
			continue
		}
		if !f.To.IsZero() && m.Date.After(f.To) {
			continue
		}
		if round != "" {
			hay := normalize.Deaccent(m.Round + " " + m.Stage)
			if !strings.Contains(hay, round) {
				continue
			}
		}
		if f.MinGoals > 0 && m.TotalGoals() < f.MinGoals {
			continue
		}
		hits = append(hits, i)
	}

	sort.SliceStable(hits, func(a, b int) bool {
		da, db := g.Matches[hits[a]].Date, g.Matches[hits[b]].Date
		if f.Ascending {
			return da.Before(db)
		}
		return da.After(db)
	})

	limit := f.Limit
	if limit <= 0 {
		limit = 25
	}
	res := &MatchQueryResult{Query: f, Total: len(hits)}
	for _, i := range hits {
		if len(res.Matches) >= limit {
			break
		}
		res.Matches = append(res.Matches, g.Matches[i])
	}
	res.Returned = len(res.Matches)

	if teamID != "" && oppID != "" {
		res.HeadToHead = g.headToHeadOver(teamID, teamName, oppID, oppName, hits)
	}
	res.Summary = matchSummary(res, teamName, oppName)
	return res, nil
}

func matchSummary(res *MatchQueryResult, team, opp string) string {
	var b strings.Builder
	switch {
	case team != "" && opp != "":
		b.WriteString(team + " vs " + opp + ": ")
	case team != "":
		b.WriteString(team + ": ")
	}
	b.WriteString(plural(res.Total, "match", "matches") + " found")
	if res.Returned < res.Total {
		b.WriteString(", showing " + itoa(res.Returned))
	}
	if res.HeadToHead != nil {
		h := res.HeadToHead
		b.WriteString(". Head-to-head: " + h.TeamA + " " + itoa(h.WinsA) + " wins, " +
			h.TeamB + " " + itoa(h.WinsB) + " wins, " + itoa(h.Draws) + " draws")
	}
	return b.String()
}

// H2H is a head-to-head record between two clubs.
type H2H struct {
	TeamA      string         `json:"team_a"`
	TeamB      string         `json:"team_b"`
	Matches    int            `json:"matches"`
	WinsA      int            `json:"wins_a"`
	WinsB      int            `json:"wins_b"`
	Draws      int            `json:"draws"`
	GoalsA     int            `json:"goals_a"`
	GoalsB     int            `json:"goals_b"`
	FirstMeet  string         `json:"first_meeting,omitempty"`
	LastMeet   string         `json:"last_meeting,omitempty"`
	AvgGoals   float64        `json:"avg_goals_per_match"`
	ByComp     map[string]int `json:"matches_by_competition,omitempty"`
	BiggestWin string         `json:"biggest_win,omitempty"`
	Summary    string         `json:"summary"`
}

func (g *Graph) headToHeadOver(idA, nameA, idB, nameB string, idxs []int) *H2H {
	h := &H2H{TeamA: nameA, TeamB: nameB, ByComp: map[string]int{}}
	var first, last time.Time
	bestMargin := -1
	var totalGoals int
	for _, i := range idxs {
		m := &g.Matches[i]
		if !m.Involves(idA) || !m.Involves(idB) {
			continue
		}
		h.Matches++
		h.ByComp[m.Competition]++
		totalGoals += m.TotalGoals()
		ga, gb := m.HomeGoals, m.AwayGoals
		if m.Away.ID == idA {
			ga, gb = m.AwayGoals, m.HomeGoals
		}
		h.GoalsA += ga
		h.GoalsB += gb
		switch {
		case ga > gb:
			h.WinsA++
		case gb > ga:
			h.WinsB++
		default:
			h.Draws++
		}
		if first.IsZero() || m.Date.Before(first) {
			first = m.Date
		}
		if m.Date.After(last) {
			last = m.Date
		}
		if margin := abs(ga - gb); margin > bestMargin {
			bestMargin = margin
			h.BiggestWin = describeMatch(*m)
		}
	}
	if h.Matches > 0 {
		h.AvgGoals = round2(float64(totalGoals) / float64(h.Matches))
		h.FirstMeet = first.Format("2006-01-02")
		h.LastMeet = last.Format("2006-01-02")
	}
	h.Summary = nameA + " " + itoa(h.WinsA) + " wins, " + nameB + " " + itoa(h.WinsB) +
		" wins, " + itoa(h.Draws) + " draws over " + plural(h.Matches, "meeting", "meetings")
	return h
}

// HeadToHead computes the full record between two clubs.
func (g *Graph) HeadToHead(a, b string, competition string, season int) (*H2H, error) {
	ta, err := g.ResolveTeam(a)
	if err != nil {
		return nil, err
	}
	tb, err := g.ResolveTeam(b)
	if err != nil {
		return nil, err
	}
	comp := normalize.Deaccent(competition)
	var idxs []int
	for _, i := range ta.matchIdx {
		m := &g.Matches[i]
		if !m.Involves(tb.ID) {
			continue
		}
		if comp != "" && !strings.Contains(normalize.Deaccent(m.Competition), comp) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		idxs = append(idxs, i)
	}
	return g.headToHeadOver(ta.ID, ta.Name, tb.ID, tb.Name, idxs), nil
}

// describeMatch renders a fixture as one human-readable line.
func describeMatch(m Match) string {
	var b strings.Builder
	b.WriteString(m.Date.Format("2006-01-02"))
	b.WriteString(": ")
	b.WriteString(m.Home.Name)
	b.WriteString(" ")
	b.WriteString(itoa(m.HomeGoals))
	b.WriteString("-")
	b.WriteString(itoa(m.AwayGoals))
	b.WriteString(" ")
	b.WriteString(m.Away.Name)
	b.WriteString(" (")
	b.WriteString(m.Competition)
	if m.Stage != "" {
		b.WriteString(" " + m.Stage)
	} else if m.Round != "" {
		b.WriteString(" Round " + m.Round)
	}
	b.WriteString(")")
	return b.String()
}

func allIndexes(n int) []int {
	out := make([]int, n)
	for i := range out {
		out[i] = i
	}
	return out
}
