// query_match.go implements match search and head-to-head analysis: the
// "Match Queries" and head-to-head parts of the specification.
package soccer

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// MatchFilter describes a match search. Every field is optional; an empty
// filter matches the whole corpus.
type MatchFilter struct {
	Team        string // club that played, home or away
	Opponent    string // restricts Team's matches to meetings with this club
	HomeTeam    string // club that played at home
	AwayTeam    string // club that played away
	Competition string
	Season      int
	SeasonFrom  int
	SeasonTo    int
	DateFrom    string
	DateTo      string
	Round       int
	Stage       string
	Venue       string // "home", "away" or "" — interpreted relative to Team
	MinGoalDiff int
	MinGoals    int
	DerbiesOnly bool
	Sort        string // date_desc (default), date_asc, goal_diff, total_goals
	Limit       int
}

// MatchSearchResult is the result of a match search.
type MatchSearchResult struct {
	Description string      `json:"description"`
	Total       int         `json:"total_matches"`
	Returned    int         `json:"returned"`
	Matches     []MatchView `json:"matches"`
	Record      *Record     `json:"record,omitempty"` // from Team's point of view
	HeadToHead  *H2HSummary `json:"head_to_head,omitempty"`
	Rivalry     string      `json:"rivalry,omitempty"`
	Note        string      `json:"note,omitempty"`
}

// SearchMatches applies a filter over the match corpus.
func (g *Graph) SearchMatches(f MatchFilter) (*MatchSearchResult, error) {
	var teamID, oppID, homeID, awayID string
	var err error
	resolve := func(q string) (string, error) {
		if strings.TrimSpace(q) == "" {
			return "", nil
		}
		t, err := g.ResolveTeam(q)
		if err != nil {
			return "", err
		}
		return t.ID, nil
	}
	if teamID, err = resolve(f.Team); err != nil {
		return nil, err
	}
	if oppID, err = resolve(f.Opponent); err != nil {
		return nil, err
	}
	if homeID, err = resolve(f.HomeTeam); err != nil {
		return nil, err
	}
	if awayID, err = resolve(f.AwayTeam); err != nil {
		return nil, err
	}

	compID := ""
	if strings.TrimSpace(f.Competition) != "" {
		if compID, err = ResolveCompetition(f.Competition); err != nil {
			return nil, err
		}
	}

	var from, to time.Time
	if f.DateFrom != "" {
		if from, err = ParseDateOnly(f.DateFrom); err != nil {
			return nil, fmt.Errorf("date_from: %w", err)
		}
	}
	if f.DateTo != "" {
		if to, err = ParseDateOnly(f.DateTo); err != nil {
			return nil, fmt.Errorf("date_to: %w", err)
		}
		to = to.Add(24*time.Hour - time.Second)
	}

	// Pick the narrowest index available.
	var pool []*Match
	switch {
	case teamID != "" && oppID != "":
		pool = g.PairMatches(teamID, oppID)
	case teamID != "":
		pool = g.byTeam[teamID]
	case homeID != "" && awayID != "":
		pool = g.PairMatches(homeID, awayID)
	case homeID != "":
		pool = g.byTeam[homeID]
	case awayID != "":
		pool = g.byTeam[awayID]
	case compID != "":
		pool = g.byComp[compID]
	default:
		pool = g.Matches
	}

	stage, stageExact := normalizeStage(f.Stage)
	out := make([]*Match, 0, 64)
	for _, m := range pool {
		if compID != "" && m.Competition != compID {
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
		if !from.IsZero() && m.Date.Before(from) {
			continue
		}
		if !to.IsZero() && m.Date.After(to) {
			continue
		}
		if f.Round != 0 && m.Round != f.Round {
			continue
		}
		if stage != "" {
			ms, _ := normalizeStage(m.Stage)
			if stageExact && ms != stage {
				continue
			}
			if !stageExact && !strings.Contains(ms, stage) {
				continue
			}
		}
		if homeID != "" && m.HomeTeamID != homeID {
			continue
		}
		if awayID != "" && m.AwayTeamID != awayID {
			continue
		}
		if teamID != "" {
			switch strings.ToLower(f.Venue) {
			case "home":
				if m.HomeTeamID != teamID {
					continue
				}
			case "away":
				if m.AwayTeamID != teamID {
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
		if f.MinGoalDiff > 0 && abs(m.GoalDiff()) < f.MinGoalDiff {
			continue
		}
		if f.MinGoals > 0 && m.TotalGoals() < f.MinGoals {
			continue
		}
		if f.DerbiesOnly {
			if _, ok := RivalryFor(m.HomeTeamID, m.AwayTeamID); !ok {
				continue
			}
		}
		out = append(out, m)
	}

	sortMatches(out, f.Sort)

	res := &MatchSearchResult{
		Description: describeFilter(g, f, teamID, oppID, homeID, awayID, compID),
		Total:       len(out),
	}
	limit := f.Limit
	if limit <= 0 {
		limit = 25
	}
	shown := out
	if len(shown) > limit {
		shown = shown[:limit]
		res.Note = fmt.Sprintf("showing the first %d of %d matches; raise \"limit\" to see more", limit, len(out))
	}
	res.Matches = g.ToViews(shown)
	res.Returned = len(res.Matches)

	if teamID != "" {
		rec := recordFor(out, teamID)
		res.Record = &rec
	}
	if teamID != "" && oppID != "" {
		s := h2hSummary(g, out, teamID, oppID)
		res.HeadToHead = &s
		if r, ok := RivalryFor(teamID, oppID); ok {
			res.Rivalry = r.Name
		}
	}
	return res, nil
}

// normalizeStage canonicalises a knockout stage name. The second return value
// reports whether the input named a known stage, in which case matching must be
// exact — otherwise a search for "final" would also return every
// "Quarterfinals" and "Semifinals" tie, since those contain the word.
func normalizeStage(s string) (string, bool) {
	switch Slug(s) {
	case "":
		return "", false
	case "final", "finals", "thefinal", "grandfinal":
		return "final", true
	case "semi", "semis", "semifinal", "semifinals", "semifinale":
		return "semifinals", true
	case "quarter", "quarters", "quarterfinal", "quarterfinals":
		return "quarterfinals", true
	case "r16", "last16", "roundof16", "16thround", "octavos":
		return "roundof16", true
	case "group", "groups", "groupstage", "groupphase":
		return "groupstage", true
	}
	return Slug(s), false
}

func sortMatches(ms []*Match, mode string) {
	switch strings.ToLower(mode) {
	case "date_asc", "oldest":
		sort.SliceStable(ms, func(i, j int) bool { return ms[i].Date.Before(ms[j].Date) })
	case "goal_diff", "biggest_win", "margin":
		sort.SliceStable(ms, func(i, j int) bool {
			a, b := abs(ms[i].GoalDiff()), abs(ms[j].GoalDiff())
			if a != b {
				return a > b
			}
			return ms[i].TotalGoals() > ms[j].TotalGoals()
		})
	case "total_goals", "highest_scoring":
		sort.SliceStable(ms, func(i, j int) bool { return ms[i].TotalGoals() > ms[j].TotalGoals() })
	default: // date_desc
		sort.SliceStable(ms, func(i, j int) bool { return ms[i].Date.After(ms[j].Date) })
	}
}

func describeFilter(g *Graph, f MatchFilter, teamID, oppID, homeID, awayID, compID string) string {
	var parts []string
	switch {
	case teamID != "" && oppID != "":
		parts = append(parts, fmt.Sprintf("%s vs %s", g.teamName(teamID), g.teamName(oppID)))
	case teamID != "":
		label := g.teamName(teamID)
		switch strings.ToLower(f.Venue) {
		case "home":
			label += " (home matches)"
		case "away":
			label += " (away matches)"
		}
		parts = append(parts, label)
	}
	if homeID != "" {
		parts = append(parts, g.teamName(homeID)+" at home")
	}
	if awayID != "" {
		parts = append(parts, g.teamName(awayID)+" away")
	}
	if compID != "" {
		parts = append(parts, CompetitionName(compID))
	}
	switch {
	case f.Season != 0:
		parts = append(parts, fmt.Sprintf("season %d", f.Season))
	case f.SeasonFrom != 0 || f.SeasonTo != 0:
		parts = append(parts, fmt.Sprintf("seasons %d-%d", f.SeasonFrom, f.SeasonTo))
	}
	if f.Stage != "" {
		parts = append(parts, f.Stage)
	}
	if f.Round != 0 {
		parts = append(parts, fmt.Sprintf("round %d", f.Round))
	}
	if f.DerbiesOnly {
		parts = append(parts, "derbies only")
	}
	if len(parts) == 0 {
		return "all matches"
	}
	return strings.Join(parts, ", ")
}

func recordFor(ms []*Match, teamID string) Record {
	var r Record
	for _, m := range ms {
		if m.HomeTeamID == teamID {
			r.add(m.HomeGoals, m.AwayGoals)
		} else if m.AwayTeamID == teamID {
			r.add(m.AwayGoals, m.HomeGoals)
		}
	}
	r.finalize()
	return r
}

// ---------------------------------------------------------------------------
// Head to head
// ---------------------------------------------------------------------------

// H2HSummary is the aggregate record between two clubs.
type H2HSummary struct {
	TeamA      string `json:"team_a"`
	TeamB      string `json:"team_b"`
	Played     int    `json:"played"`
	TeamAWins  int    `json:"team_a_wins"`
	TeamBWins  int    `json:"team_b_wins"`
	Draws      int    `json:"draws"`
	TeamAGoals int    `json:"team_a_goals"`
	TeamBGoals int    `json:"team_b_goals"`
	Line       string `json:"line"`
}

func h2hSummary(g *Graph, ms []*Match, aID, bID string) H2HSummary {
	s := H2HSummary{TeamA: g.teamName(aID), TeamB: g.teamName(bID)}
	for _, m := range ms {
		if !m.Involves(aID) || !m.Involves(bID) {
			continue
		}
		s.Played++
		ag, bg := m.HomeGoals, m.AwayGoals
		if m.AwayTeamID == aID {
			ag, bg = m.AwayGoals, m.HomeGoals
		}
		s.TeamAGoals += ag
		s.TeamBGoals += bg
		switch {
		case ag > bg:
			s.TeamAWins++
		case bg > ag:
			s.TeamBWins++
		default:
			s.Draws++
		}
	}
	s.Line = fmt.Sprintf("%s %d wins, %s %d wins, %d draws (goals %d-%d)",
		s.TeamA, s.TeamAWins, s.TeamB, s.TeamBWins, s.Draws, s.TeamAGoals, s.TeamBGoals)
	return s
}

// H2HCompetitionSplit breaks a head-to-head down by competition.
type H2HCompetitionSplit struct {
	Competition string `json:"competition"`
	Played      int    `json:"played"`
	TeamAWins   int    `json:"team_a_wins"`
	TeamBWins   int    `json:"team_b_wins"`
	Draws       int    `json:"draws"`
}

// HeadToHeadResult is the full head-to-head report between two clubs.
type HeadToHeadResult struct {
	Summary         H2HSummary            `json:"summary"`
	Rivalry         string                `json:"rivalry,omitempty"`
	ByCompetition   []H2HCompetitionSplit `json:"by_competition"`
	FirstMeeting    *MatchView            `json:"first_meeting,omitempty"`
	LastMeeting     *MatchView            `json:"last_meeting,omitempty"`
	BiggestTeamAWin *MatchView            `json:"biggest_team_a_win,omitempty"`
	BiggestTeamBWin *MatchView            `json:"biggest_team_b_win,omitempty"`
	Matches         []MatchView           `json:"matches"`
	Note            string                `json:"note,omitempty"`
}

// HeadToHead compares two clubs across the whole corpus, optionally narrowed to
// a competition and/or a season range.
func (g *Graph) HeadToHead(teamA, teamB, competition string, seasonFrom, seasonTo, limit int) (*HeadToHeadResult, error) {
	a, err := g.ResolveTeam(teamA)
	if err != nil {
		return nil, err
	}
	b, err := g.ResolveTeam(teamB)
	if err != nil {
		return nil, err
	}
	if a.ID == b.ID {
		return nil, fmt.Errorf("%q and %q resolve to the same club (%s)", teamA, teamB, a.Name)
	}
	compID := ""
	if strings.TrimSpace(competition) != "" {
		if compID, err = ResolveCompetition(competition); err != nil {
			return nil, err
		}
	}

	var ms []*Match
	for _, m := range g.PairMatches(a.ID, b.ID) {
		if compID != "" && m.Competition != compID {
			continue
		}
		if seasonFrom != 0 && m.Season < seasonFrom {
			continue
		}
		if seasonTo != 0 && m.Season > seasonTo {
			continue
		}
		ms = append(ms, m)
	}
	sort.SliceStable(ms, func(i, j int) bool { return ms[i].Date.Before(ms[j].Date) })

	res := &HeadToHeadResult{Summary: h2hSummary(g, ms, a.ID, b.ID)}
	if r, ok := RivalryFor(a.ID, b.ID); ok {
		res.Rivalry = r.Name
	}
	if len(ms) == 0 {
		res.Note = fmt.Sprintf("no meetings between %s and %s in the loaded datasets", a.Name, b.Name)
		res.ByCompetition = []H2HCompetitionSplit{}
		res.Matches = []MatchView{}
		return res, nil
	}

	splits := map[string]*H2HCompetitionSplit{}
	var bestA, bestB *Match
	for _, m := range ms {
		s, ok := splits[m.Competition]
		if !ok {
			s = &H2HCompetitionSplit{Competition: CompetitionName(m.Competition)}
			splits[m.Competition] = s
		}
		s.Played++
		w := m.WinnerID()
		switch w {
		case a.ID:
			s.TeamAWins++
			if bestA == nil || abs(m.GoalDiff()) > abs(bestA.GoalDiff()) {
				bestA = m
			}
		case b.ID:
			s.TeamBWins++
			if bestB == nil || abs(m.GoalDiff()) > abs(bestB.GoalDiff()) {
				bestB = m
			}
		default:
			s.Draws++
		}
	}
	for _, id := range sortedKeys(splits) {
		res.ByCompetition = append(res.ByCompetition, *splits[id])
	}

	first := g.ToView(ms[0])
	last := g.ToView(ms[len(ms)-1])
	res.FirstMeeting, res.LastMeeting = &first, &last
	if bestA != nil {
		v := g.ToView(bestA)
		res.BiggestTeamAWin = &v
	}
	if bestB != nil {
		v := g.ToView(bestB)
		res.BiggestTeamBWin = &v
	}

	if limit <= 0 {
		limit = 20
	}
	// Most recent meetings first for the listing.
	rev := make([]*Match, len(ms))
	for i, m := range ms {
		rev[len(ms)-1-i] = m
	}
	if len(rev) > limit {
		res.Note = fmt.Sprintf("showing the %d most recent of %d meetings", limit, len(rev))
		rev = rev[:limit]
	}
	res.Matches = g.ToViews(rev)
	return res, nil
}

// DerbyReport lists derby fixtures matching a season/competition window.
type DerbyReport struct {
	Description string      `json:"description"`
	Total       int         `json:"total_matches"`
	Derbies     []DerbyLine `json:"derbies"`
	Matches     []MatchView `json:"matches"`
}

// DerbyLine aggregates one rivalry inside a DerbyReport.
type DerbyLine struct {
	Rivalry string `json:"rivalry"`
	TeamA   string `json:"team_a"`
	TeamB   string `json:"team_b"`
	Played  int    `json:"played"`
}

// Derbies finds every meeting between traditional rivals in a window.
func (g *Graph) Derbies(competition string, season, seasonFrom, seasonTo, limit int) (*DerbyReport, error) {
	f := MatchFilter{
		Competition: competition,
		Season:      season,
		SeasonFrom:  seasonFrom,
		SeasonTo:    seasonTo,
		DerbiesOnly: true,
		Sort:        "date_desc",
		Limit:       limit,
	}
	res, err := g.SearchMatches(f)
	if err != nil {
		return nil, err
	}
	counts := map[string]*DerbyLine{}
	for _, m := range g.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if seasonFrom != 0 && m.Season < seasonFrom {
			continue
		}
		if seasonTo != 0 && m.Season > seasonTo {
			continue
		}
		if competition != "" {
			compID, err := ResolveCompetition(competition)
			if err != nil {
				return nil, err
			}
			if m.Competition != compID {
				continue
			}
		}
		r, ok := RivalryFor(m.HomeTeamID, m.AwayTeamID)
		if !ok {
			continue
		}
		line, ok := counts[r.Name]
		if !ok {
			line = &DerbyLine{Rivalry: r.Name, TeamA: g.teamName(r.TeamAID), TeamB: g.teamName(r.TeamBID)}
			counts[r.Name] = line
		}
		line.Played++
	}
	rep := &DerbyReport{Description: res.Description, Total: res.Total, Matches: res.Matches}
	for _, k := range sortedKeys(counts) {
		rep.Derbies = append(rep.Derbies, *counts[k])
	}
	sort.SliceStable(rep.Derbies, func(i, j int) bool { return rep.Derbies[i].Played > rep.Derbies[j].Played })
	if rep.Derbies == nil {
		rep.Derbies = []DerbyLine{}
	}
	return rep, nil
}
