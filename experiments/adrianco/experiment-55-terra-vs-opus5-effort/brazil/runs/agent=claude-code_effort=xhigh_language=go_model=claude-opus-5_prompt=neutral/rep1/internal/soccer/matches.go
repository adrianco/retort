// matches.go answers match-shaped questions: "show me all Flamengo vs Fluminense
// matches", "what did Palmeiras play in 2023", "find the Copa do Brasil finals".
//
// Every match query funnels through MatchFilter so that the MCP tools, the
// head-to-head report and the analytics helpers all share one definition of what
// it means to select matches. Filters operate on the de-duplicated view of the
// data by default; IncludeDuplicates exposes the raw per-file rows instead.
package soccer

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// MatchFilter selects matches. The zero value matches everything.
type MatchFilter struct {
	Team              string // club on either side
	Opponent          string // club on the other side (requires Team)
	HomeTeam          string // club that must be at home
	AwayTeam          string // club that must be away
	Competition       Competition
	Season            int
	SeasonFrom        int
	SeasonTo          int
	DateFrom          time.Time
	DateTo            time.Time
	Round             int
	Stage             string
	Venue             string
	MinTotalGoals     int
	MinGoalDifference int
	IncludeDuplicates bool
}

// resolvedFilter is a MatchFilter with clubs already resolved to Team pointers.
type resolvedFilter struct {
	filter                      MatchFilter
	team, opponent, home, away  *Team
	alternatives                []*Team
	teamLabel, opponentLabel    string
	homeLabel, awayLabel, scope string
}

// resolve turns the string fields of a filter into team references, returning a
// descriptive error when a name cannot be matched.
func (g *Graph) resolve(f MatchFilter) (*resolvedFilter, error) {
	rf := &resolvedFilter{filter: f}
	lookup := func(name string, dst **Team, label *string) error {
		if strings.TrimSpace(name) == "" {
			return nil
		}
		t, alts, err := g.ResolveTeam(name)
		if err != nil {
			return err
		}
		*dst = t
		*label = t.Display
		rf.alternatives = append(rf.alternatives, alts...)
		return nil
	}
	if err := lookup(f.Team, &rf.team, &rf.teamLabel); err != nil {
		return nil, err
	}
	if err := lookup(f.Opponent, &rf.opponent, &rf.opponentLabel); err != nil {
		return nil, err
	}
	if err := lookup(f.HomeTeam, &rf.home, &rf.homeLabel); err != nil {
		return nil, err
	}
	if err := lookup(f.AwayTeam, &rf.away, &rf.awayLabel); err != nil {
		return nil, err
	}
	rf.scope = describeScope(f, rf)
	return rf, nil
}

// matches reports whether a single match passes the resolved filter.
func (rf *resolvedFilter) matches(m *Match) bool {
	f := rf.filter
	if !f.IncludeDuplicates && !m.primary {
		return false
	}
	if f.Competition != "" && m.Competition != f.Competition {
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
	if rf.team != nil && !m.Involves(rf.team.ID) {
		return false
	}
	if rf.opponent != nil {
		if rf.team == nil {
			if !m.Involves(rf.opponent.ID) {
				return false
			}
		} else if m.OpponentOf(rf.team.ID) != rf.opponent.ID {
			return false
		}
	}
	if rf.home != nil && m.HomeID != rf.home.ID {
		return false
	}
	if rf.away != nil && m.AwayID != rf.away.ID {
		return false
	}
	if f.Round != 0 && m.Round != f.Round {
		return false
	}
	if f.Stage != "" && !strings.Contains(foldKey(m.StageLabel()), foldKey(f.Stage)) {
		return false
	}
	if f.Venue != "" && !strings.Contains(foldKey(m.Venue), foldKey(f.Venue)) {
		return false
	}
	if f.MinTotalGoals > 0 && m.TotalGoals() < f.MinTotalGoals {
		return false
	}
	if f.MinGoalDifference > 0 && m.GoalDifference() < f.MinGoalDifference {
		return false
	}
	if !f.DateFrom.IsZero() && (!m.HasDate || m.Date.Before(f.DateFrom)) {
		return false
	}
	if !f.DateTo.IsZero() && (!m.HasDate || m.Date.After(f.DateTo)) {
		return false
	}
	return true
}

// candidates narrows the scan to a club's own match list when possible, which
// turns most queries into a walk over a few hundred rows instead of ~24,000.
func (g *Graph) candidates(rf *resolvedFilter) []*Match {
	if rf.filter.IncludeDuplicates {
		return g.matches
	}
	for _, t := range []*Team{rf.team, rf.home, rf.away, rf.opponent} {
		if t != nil {
			return g.teamMatches(t)
		}
	}
	if rf.filter.Competition != "" && rf.filter.Season != 0 {
		return g.SeasonMatches(rf.filter.Competition, rf.filter.Season)
	}
	return g.matches
}

// FindMatches returns every match passing the filter, newest first.
func (g *Graph) FindMatches(f MatchFilter) ([]*Match, *resolvedFilter, error) {
	rf, err := g.resolve(f)
	if err != nil {
		return nil, nil, err
	}
	var out []*Match
	for _, m := range g.candidates(rf) {
		if rf.matches(m) {
			out = append(out, m)
		}
	}
	sortMatchesNewestFirst(out)
	return out, rf, nil
}

func sortMatchesNewestFirst(ms []*Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		a, b := ms[i], ms[j]
		if a.HasDate != b.HasDate {
			return a.HasDate
		}
		if !a.Date.Equal(b.Date) {
			return a.Date.After(b.Date)
		}
		return a.ID < b.ID
	})
}

// describeScope renders the filter as the English phrase used in report titles.
func describeScope(f MatchFilter, rf *resolvedFilter) string {
	var parts []string
	switch {
	case rf.team != nil && rf.opponent != nil:
		parts = append(parts, fmt.Sprintf("%s vs %s", rf.teamLabel, rf.opponentLabel))
	case rf.team != nil:
		parts = append(parts, rf.teamLabel)
	}
	if rf.home != nil {
		parts = append(parts, fmt.Sprintf("%s at home", rf.homeLabel))
	}
	if rf.away != nil {
		parts = append(parts, fmt.Sprintf("%s away", rf.awayLabel))
	}
	if f.Competition != "" {
		parts = append(parts, string(f.Competition))
	}
	switch {
	case f.Season != 0:
		parts = append(parts, fmt.Sprintf("%d season", f.Season))
	case f.SeasonFrom != 0 && f.SeasonTo != 0:
		parts = append(parts, fmt.Sprintf("%d-%d", f.SeasonFrom, f.SeasonTo))
	case f.SeasonFrom != 0:
		parts = append(parts, fmt.Sprintf("from %d", f.SeasonFrom))
	case f.SeasonTo != 0:
		parts = append(parts, fmt.Sprintf("up to %d", f.SeasonTo))
	}
	if f.Stage != "" {
		parts = append(parts, f.Stage)
	}
	if f.Round != 0 {
		parts = append(parts, fmt.Sprintf("round %d", f.Round))
	}
	if f.Venue != "" {
		parts = append(parts, "at "+f.Venue)
	}
	if !f.DateFrom.IsZero() || !f.DateTo.IsZero() {
		from, to := "the start", "the end"
		if !f.DateFrom.IsZero() {
			from = f.DateFrom.Format("2006-01-02")
		}
		if !f.DateTo.IsZero() {
			to = f.DateTo.Format("2006-01-02")
		}
		parts = append(parts, fmt.Sprintf("%s to %s", from, to))
	}
	if len(parts) == 0 {
		return "all competitions, all seasons"
	}
	return strings.Join(parts, ", ")
}

// MatchView is the serialisable form of a match, with team names resolved and a
// ready-to-read one line rendering.
type MatchView struct {
	ID          string      `json:"id"`
	Date        string      `json:"date"`
	Competition string      `json:"competition"`
	Season      int         `json:"season"`
	Stage       string      `json:"stage,omitempty"`
	HomeTeam    string      `json:"home_team"`
	AwayTeam    string      `json:"away_team"`
	HomeTeamID  string      `json:"home_team_id"`
	AwayTeamID  string      `json:"away_team_id"`
	HomeGoals   int         `json:"home_goals"`
	AwayGoals   int         `json:"away_goals"`
	Result      string      `json:"result"`
	Venue       string      `json:"venue,omitempty"`
	Sources     []string    `json:"sources"`
	Stats       *MatchStats `json:"stats,omitempty"`
	Line        string      `json:"line"`
}

// View renders a match for output.
func (g *Graph) View(m *Match) MatchView {
	result := "draw"
	switch m.WinnerID() {
	case m.HomeID:
		result = "home win"
	case m.AwayID:
		result = "away win"
	}
	v := MatchView{
		ID:          m.ID,
		Date:        m.DateString(),
		Competition: string(m.Competition),
		Season:      m.Season,
		Stage:       m.StageLabel(),
		HomeTeam:    m.home.Display,
		AwayTeam:    m.away.Display,
		HomeTeamID:  m.HomeID,
		AwayTeamID:  m.AwayID,
		HomeGoals:   m.HomeGoals,
		AwayGoals:   m.AwayGoals,
		Result:      result,
		Venue:       m.Venue,
		Sources:     m.SourceList(),
		Stats:       m.Stats,
	}
	v.Line = v.String()
	return v
}

// String renders the standard one line match summary used across every report,
// e.g. "2023-09-03: Flamengo 2-1 Fluminense (Série A Round 22)".
func (v MatchView) String() string {
	context := shortCompetition(v.Competition)
	if v.Stage != "" {
		context += " " + v.Stage
	}
	if v.Venue != "" {
		context += ", " + v.Venue
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)", v.Date, v.HomeTeam, v.HomeGoals, v.AwayGoals, v.AwayTeam, context)
}

func shortCompetition(name string) string { return Competition(name).Short() }

// Views converts a slice of matches, applying an optional limit.
func (g *Graph) Views(ms []*Match, limit int) []MatchView {
	if limit > 0 && len(ms) > limit {
		ms = ms[:limit]
	}
	out := make([]MatchView, 0, len(ms))
	for _, m := range ms {
		out = append(out, g.View(m))
	}
	return out
}

// MatchSearchResult is the payload of the search_matches tool.
type MatchSearchResult struct {
	Query        string      `json:"query"`
	TotalMatches int         `json:"total_matches"`
	Returned     int         `json:"returned"`
	Matches      []MatchView `json:"matches"`
	HeadToHead   *H2HSummary `json:"head_to_head,omitempty"`
	Note         string      `json:"note,omitempty"`
}

// SearchMatches runs a filter and packages the result, adding a head-to-head
// summary whenever the query named two clubs.
func (g *Graph) SearchMatches(f MatchFilter, limit int) (*MatchSearchResult, error) {
	ms, rf, err := g.FindMatches(f)
	if err != nil {
		return nil, err
	}
	res := &MatchSearchResult{
		Query:        rf.scope,
		TotalMatches: len(ms),
		Matches:      g.Views(ms, limit),
	}
	res.Returned = len(res.Matches)
	if rf.team != nil && rf.opponent != nil {
		res.HeadToHead = summariseH2H(rf.team, rf.opponent, ms)
	}
	if len(ms) == 0 {
		res.Note = "No matches in the provided datasets match this query. " + g.coverageHint(f)
	} else if res.Returned < res.TotalMatches {
		res.Note = fmt.Sprintf("Showing the %d most recent of %d matches.", res.Returned, res.TotalMatches)
	}
	return res, nil
}

// coverageHint explains what the datasets do contain, so an empty result is
// actionable rather than just empty.
func (g *Graph) coverageHint(f MatchFilter) string {
	if f.Competition != "" {
		seasons := g.Seasons(f.Competition)
		if len(seasons) > 0 {
			return fmt.Sprintf("%s covers seasons %d-%d.", f.Competition, seasons[0], seasons[len(seasons)-1])
		}
	}
	return "Coverage is Série A 2003-2023, Série B/C 2014-2023, Copa do Brasil 2012-2023 and Libertadores 2013-2022."
}

// H2HSummary is the aggregate record between two clubs.
type H2HSummary struct {
	TeamA         string            `json:"team_a"`
	TeamB         string            `json:"team_b"`
	Matches       int               `json:"matches"`
	TeamAWins     int               `json:"team_a_wins"`
	TeamBWins     int               `json:"team_b_wins"`
	Draws         int               `json:"draws"`
	TeamAGoals    int               `json:"team_a_goals"`
	TeamBGoals    int               `json:"team_b_goals"`
	FirstMeeting  string            `json:"first_meeting,omitempty"`
	LastMeeting   string            `json:"last_meeting,omitempty"`
	ByCompetition map[string]string `json:"by_competition,omitempty"`
	Summary       string            `json:"summary"`
}

// summariseH2H tallies a set of matches between two clubs.
func summariseH2H(a, b *Team, ms []*Match) *H2HSummary {
	s := &H2HSummary{TeamA: a.Display, TeamB: b.Display, Matches: len(ms)}
	perComp := map[Competition][3]int{}
	for _, m := range ms {
		ag, bg := m.HomeGoals, m.AwayGoals
		if m.HomeID == b.ID {
			ag, bg = bg, ag
		}
		s.TeamAGoals += ag
		s.TeamBGoals += bg
		rec := perComp[m.Competition]
		switch {
		case ag > bg:
			s.TeamAWins++
			rec[0]++
		case bg > ag:
			s.TeamBWins++
			rec[1]++
		default:
			s.Draws++
			rec[2]++
		}
		perComp[m.Competition] = rec
	}
	if len(ms) > 0 {
		// ms is newest first.
		s.LastMeeting = ms[0].DateString()
		s.FirstMeeting = ms[len(ms)-1].DateString()
	}
	if len(perComp) > 0 {
		s.ByCompetition = map[string]string{}
		for comp, rec := range perComp {
			s.ByCompetition[string(comp)] = fmt.Sprintf("%d matches: %d-%d-%d", rec[0]+rec[1]+rec[2], rec[0], rec[2], rec[1])
		}
	}
	s.Summary = fmt.Sprintf("%s %d wins, %s %d wins, %d draws (goals %d-%d)",
		a.Display, s.TeamAWins, b.Display, s.TeamBWins, s.Draws, s.TeamAGoals, s.TeamBGoals)
	return s
}

// HeadToHeadResult is the payload of the head_to_head tool.
type HeadToHeadResult struct {
	Scope        string      `json:"scope"`
	Summary      H2HSummary  `json:"summary"`
	BiggestWinA  *MatchView  `json:"biggest_win_team_a,omitempty"`
	BiggestWinB  *MatchView  `json:"biggest_win_team_b,omitempty"`
	HomeRecordA  string      `json:"home_record_team_a,omitempty"`
	HomeRecordB  string      `json:"home_record_team_b,omitempty"`
	RecentForm   string      `json:"recent_form,omitempty"`
	Matches      []MatchView `json:"matches"`
	TotalMatches int         `json:"total_matches"`
	Rivalry      string      `json:"rivalry,omitempty"`
	Note         string      `json:"note,omitempty"`
}

// HeadToHead compares two clubs across the whole dataset or a filtered subset.
func (g *Graph) HeadToHead(teamA, teamB string, f MatchFilter, limit int) (*HeadToHeadResult, error) {
	f.Team, f.Opponent = teamA, teamB
	f.HomeTeam, f.AwayTeam = "", ""
	ms, rf, err := g.FindMatches(f)
	if err != nil {
		return nil, err
	}
	res := &HeadToHeadResult{
		Scope:        rf.scope,
		Summary:      *summariseH2H(rf.team, rf.opponent, ms),
		TotalMatches: len(ms),
		Matches:      g.Views(ms, limit),
	}
	if r := rivalryFor(rf.team.ID, rf.opponent.ID); r != nil {
		res.Rivalry = r.Name
	}
	var bestA, bestB *Match
	homeA, homeB := [3]int{}, [3]int{}
	for _, m := range ms {
		ag, bg := m.HomeGoals, m.AwayGoals
		if m.HomeID == rf.opponent.ID {
			ag, bg = bg, ag
		}
		if ag > bg && (bestA == nil || ag-bg > diffFor(bestA, rf.team.ID)) {
			bestA = m
		}
		if bg > ag && (bestB == nil || bg-ag > diffFor(bestB, rf.opponent.ID)) {
			bestB = m
		}
		rec := &homeA
		if m.HomeID == rf.opponent.ID {
			rec = &homeB
		}
		switch {
		case m.HomeGoals > m.AwayGoals:
			rec[0]++
		case m.HomeGoals == m.AwayGoals:
			rec[1]++
		default:
			rec[2]++
		}
	}
	if bestA != nil {
		v := g.View(bestA)
		res.BiggestWinA = &v
	}
	if bestB != nil {
		v := g.View(bestB)
		res.BiggestWinB = &v
	}
	res.HomeRecordA = fmt.Sprintf("%s at home: %dW %dD %dL", rf.team.Display, homeA[0], homeA[1], homeA[2])
	res.HomeRecordB = fmt.Sprintf("%s at home: %dW %dD %dL", rf.opponent.Display, homeB[0], homeB[1], homeB[2])
	res.RecentForm = recentForm(ms, rf.team.ID, 5)
	if len(ms) == 0 {
		res.Note = "These clubs never met in the provided datasets. " + g.coverageHint(f)
	}
	return res, nil
}

// diffFor returns the winning margin of a match from a club's point of view.
func diffFor(m *Match, teamID string) int {
	if m.HomeID == teamID {
		return m.HomeGoals - m.AwayGoals
	}
	return m.AwayGoals - m.HomeGoals
}

// recentForm renders the last n results for a club as "W W D L W".
func recentForm(ms []*Match, teamID string, n int) string {
	var out []string
	for _, m := range ms {
		if len(out) == n {
			break
		}
		switch {
		case m.WinnerID() == "":
			out = append(out, "D")
		case m.WinnerID() == teamID:
			out = append(out, "W")
		default:
			out = append(out, "L")
		}
	}
	return strings.Join(out, " ")
}
