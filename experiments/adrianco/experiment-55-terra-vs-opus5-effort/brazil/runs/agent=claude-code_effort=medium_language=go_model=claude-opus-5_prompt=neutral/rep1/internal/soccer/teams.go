package soccer

import (
	"sort"
	"strconv"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/normalize"
)

// Record is a win/draw/loss and goal tally.
type Record struct {
	Matches       int     `json:"matches"`
	Wins          int     `json:"wins"`
	Draws         int     `json:"draws"`
	Losses        int     `json:"losses"`
	GoalsFor      int     `json:"goals_for"`
	GoalsAgainst  int     `json:"goals_against"`
	GoalDiff      int     `json:"goal_difference"`
	Points        int     `json:"points"`
	WinRate       float64 `json:"win_rate_pct"`
	PointsPerGame float64 `json:"points_per_game"`
}

func (r *Record) add(gf, ga int) {
	r.Matches++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
		r.Points += 3
	case gf == ga:
		r.Draws++
		r.Points++
	default:
		r.Losses++
	}
}

func (r *Record) finish() {
	r.GoalDiff = r.GoalsFor - r.GoalsAgainst
	if r.Matches > 0 {
		r.WinRate = round2(100 * float64(r.Wins) / float64(r.Matches))
		r.PointsPerGame = round2(float64(r.Points) / float64(r.Matches))
	}
}

// TeamStats is the full profile of a club, optionally scoped to a season or
// competition.
type TeamStats struct {
	Team          string            `json:"team"`
	TeamID        string            `json:"team_id"`
	State         string            `json:"state,omitempty"`
	Scope         string            `json:"scope"`
	Overall       Record            `json:"overall"`
	Home          Record            `json:"home"`
	Away          Record            `json:"away"`
	ByCompetition map[string]Record `json:"by_competition,omitempty"`
	BySeason      map[string]Record `json:"by_season,omitempty"`
	BiggestWin    string            `json:"biggest_win,omitempty"`
	BiggestLoss   string            `json:"biggest_loss,omitempty"`
	FirstMatch    string            `json:"first_match,omitempty"`
	LastMatch     string            `json:"last_match,omitempty"`
	Summary       string            `json:"summary"`
}

// TeamStatsFilter scopes a team query.
type TeamStatsFilter struct {
	Team        string
	Season      int
	Competition string
	Venue       string // "home", "away" or ""
}

// TeamStatistics computes a club's record over the selected matches.
func (g *Graph) TeamStatistics(f TeamStatsFilter) (*TeamStats, error) {
	t, err := g.ResolveTeam(f.Team)
	if err != nil {
		return nil, err
	}
	comp := normalize.Deaccent(f.Competition)

	st := &TeamStats{
		Team: t.Name, TeamID: t.ID, State: t.State,
		ByCompetition: map[string]Record{},
		BySeason:      map[string]Record{},
	}
	byComp := map[string]*Record{}
	bySeason := map[string]*Record{}
	bestWin, worstLoss := -1, -1

	for _, i := range t.matchIdx {
		m := &g.Matches[i]
		if comp != "" && !strings.Contains(normalize.Deaccent(m.Competition), comp) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		home := m.Home.ID == t.ID
		if f.Venue == "home" && !home {
			continue
		}
		if f.Venue == "away" && home {
			continue
		}
		gf, ga := m.HomeGoals, m.AwayGoals
		if !home {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		st.Overall.add(gf, ga)
		if home {
			st.Home.add(gf, ga)
		} else {
			st.Away.add(gf, ga)
		}
		rc := byComp[m.Competition]
		if rc == nil {
			rc = &Record{}
			byComp[m.Competition] = rc
		}
		rc.add(gf, ga)
		key := strconv.Itoa(m.Season)
		rs := bySeason[key]
		if rs == nil {
			rs = &Record{}
			bySeason[key] = rs
		}
		rs.add(gf, ga)

		if gf-ga > bestWin {
			bestWin = gf - ga
			st.BiggestWin = describeMatch(*m)
		}
		if ga-gf > worstLoss {
			worstLoss = ga - gf
			st.BiggestLoss = describeMatch(*m)
		}
		date := m.Date.Format("2006-01-02")
		if st.FirstMatch == "" || date < st.FirstMatch {
			st.FirstMatch = date
		}
		if date > st.LastMatch {
			st.LastMatch = date
		}
	}
	if st.Overall.Matches == 0 {
		return nil, &ErrNoData{What: "matches for " + t.Name + " " + scopeLabel(f)}
	}
	if bestWin <= 0 {
		st.BiggestWin = ""
	}
	if worstLoss <= 0 {
		st.BiggestLoss = ""
	}
	st.Overall.finish()
	st.Home.finish()
	st.Away.finish()
	for k, v := range byComp {
		v.finish()
		st.ByCompetition[k] = *v
	}
	for k, v := range bySeason {
		v.finish()
		st.BySeason[k] = *v
	}
	st.Scope = strings.TrimSpace(scopeLabel(f))
	st.Summary = teamSummary(st)
	return st, nil
}

func scopeLabel(f TeamStatsFilter) string {
	var parts []string
	if f.Season != 0 {
		parts = append(parts, strconv.Itoa(f.Season))
	}
	if f.Competition != "" {
		parts = append(parts, f.Competition)
	}
	switch f.Venue {
	case "home":
		parts = append(parts, "home only")
	case "away":
		parts = append(parts, "away only")
	}
	if len(parts) == 0 {
		return "all competitions and seasons"
	}
	return strings.Join(parts, ", ")
}

func teamSummary(st *TeamStats) string {
	r := st.Overall
	return st.Team + " (" + st.Scope + "): " + itoa(r.Matches) + " matches, " +
		itoa(r.Wins) + "W " + itoa(r.Draws) + "D " + itoa(r.Losses) + "L, " +
		"GF " + itoa(r.GoalsFor) + " GA " + itoa(r.GoalsAgainst) +
		", win rate " + ftoa(r.WinRate) + "%"
}

// ErrNoData signals an empty but well-formed query.
type ErrNoData struct{ What string }

func (e *ErrNoData) Error() string { return "no data found for " + e.What }

// TeamSearchResult describes a club plus how much data backs it.
type TeamSearchResult struct {
	Team
	Sample []string `json:"sample_aliases,omitempty"`
}

// SearchTeams finds clubs by fuzzy name, or lists them all when query is empty.
func (g *Graph) SearchTeams(query string, state string, limit int) []*Team {
	if limit <= 0 {
		limit = 25
	}
	needle := normalize.Deaccent(strings.TrimSpace(query))
	var out []*Team
	for _, id := range g.teamOrder {
		t := g.teams[id]
		if state != "" && !strings.EqualFold(t.State, state) {
			continue
		}
		if needle != "" {
			if !strings.Contains(normalize.Deaccent(t.Name), needle) &&
				!strings.Contains(id, strings.ReplaceAll(needle, " ", "-")) &&
				!g.aliasContains(t, needle) {
				continue
			}
		}
		out = append(out, t)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].MatchCount > out[j].MatchCount })
	if len(out) > limit {
		out = out[:limit]
	}
	return out
}

// CompareTeams puts two clubs side by side with their head-to-head record.
type TeamComparison struct {
	A          *TeamStats `json:"team_a"`
	B          *TeamStats `json:"team_b"`
	HeadToHead *H2H       `json:"head_to_head"`
	Summary    string     `json:"summary"`
}

// Compare builds a two-club comparison scoped by season/competition.
func (g *Graph) Compare(a, b string, season int, competition string) (*TeamComparison, error) {
	sa, err := g.TeamStatistics(TeamStatsFilter{Team: a, Season: season, Competition: competition})
	if err != nil {
		return nil, err
	}
	sb, err := g.TeamStatistics(TeamStatsFilter{Team: b, Season: season, Competition: competition})
	if err != nil {
		return nil, err
	}
	h, err := g.HeadToHead(a, b, competition, season)
	if err != nil {
		return nil, err
	}
	return &TeamComparison{
		A: sa, B: sb, HeadToHead: h,
		Summary: sa.Summary + " | " + sb.Summary + " | " + h.Summary,
	}, nil
}
