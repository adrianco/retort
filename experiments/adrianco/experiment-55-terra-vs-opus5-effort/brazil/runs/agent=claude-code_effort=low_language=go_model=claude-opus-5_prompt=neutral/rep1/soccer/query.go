// query.go implements the query layer over the loaded Store: match search,
// head-to-head records, team and competition statistics, league tables computed
// from results, and player search. Everything runs against in-memory slices so
// even full-dataset aggregations complete in milliseconds.
package soccer

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// MatchFilter selects matches. Zero valued fields are ignored.
type MatchFilter struct {
	Team        string // matches home or away
	Opponent    string // together with Team, restricts to head-to-head
	HomeTeam    string
	AwayTeam    string
	Competition string
	Season      int
	From        string // inclusive ISO date
	To          string // inclusive ISO date
	Stage       string
	Round       string
	Venue       string // home / away / any, relative to Team
	Limit       int
}

// ResolveTeam finds the canonical key that best answers a user's team name.
// It prefers the team with the most matches among the candidates so that
// "Atletico" resolves to the club that actually appears most in the data.
func (s *Store) ResolveTeam(query string) (string, bool) {
	if strings.TrimSpace(query) == "" {
		return "", false
	}
	exact := CanonicalTeam(query)
	if _, ok := s.matchesByTeam[exact]; ok {
		return exact, true
	}
	best, bestN := "", -1
	keys := make([]string, 0, len(s.matchesByTeam))
	for k := range s.matchesByTeam {
		keys = append(keys, k)
	}
	sort.Strings(keys) // deterministic tie-breaking
	for _, k := range keys {
		if !TeamMatches(query, k) {
			continue
		}
		if n := len(s.matchesByTeam[k]); n > bestN {
			best, bestN = k, n
		}
	}
	return best, best != ""
}

// candidateMatches narrows the search space using the team index when possible.
func (s *Store) candidateMatches(f MatchFilter) []*Match {
	for _, name := range []string{f.Team, f.HomeTeam, f.AwayTeam} {
		if name == "" {
			continue
		}
		if key, ok := s.ResolveTeam(name); ok {
			return s.matchesByTeam[key]
		}
		return nil // named team is unknown: no results
	}
	return s.Matches
}

// SearchMatches returns matches satisfying the filter, most recent first.
func (s *Store) SearchMatches(f MatchFilter) []*Match {
	var from, to time.Time
	if f.From != "" {
		from, _, _ = ParseDate(f.From)
	}
	if f.To != "" {
		to, _, _ = ParseDate(f.To)
	}
	comp := ""
	if f.Competition != "" {
		if comp = ResolveCompetition(f.Competition); comp == "" {
			comp = f.Competition
		}
	}
	teamKey := ""
	if f.Team != "" {
		if k, ok := s.ResolveTeam(f.Team); ok {
			teamKey = k
		} else {
			return nil
		}
	}

	var out []*Match
	for _, m := range s.candidateMatches(f) {
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if comp != "" && !strings.EqualFold(m.Competition, comp) {
			continue
		}
		if !from.IsZero() && m.Date.Before(from) {
			continue
		}
		if !to.IsZero() && m.Date.After(to.Add(24*time.Hour-time.Second)) {
			continue
		}
		if f.Stage != "" && !NameMatches(f.Stage, m.Stage) {
			continue
		}
		if f.Round != "" && !strings.EqualFold(strings.TrimSpace(f.Round), m.Round) {
			continue
		}
		if f.HomeTeam != "" && !TeamMatches(f.HomeTeam, m.HomeKey) {
			continue
		}
		if f.AwayTeam != "" && !TeamMatches(f.AwayTeam, m.AwayKey) {
			continue
		}
		if teamKey != "" {
			if !m.Involves(teamKey) {
				continue
			}
			switch strings.ToLower(f.Venue) {
			case "home":
				if m.HomeKey != teamKey {
					continue
				}
			case "away":
				if m.AwayKey != teamKey {
					continue
				}
			}
		}
		if f.Opponent != "" && !(TeamMatches(f.Opponent, m.HomeKey) || TeamMatches(f.Opponent, m.AwayKey)) {
			continue
		}
		if f.Opponent != "" && teamKey != "" && (TeamMatches(f.Opponent, teamKey)) {
			continue // team and opponent resolved to the same club
		}
		out = append(out, m)
	}

	sort.SliceStable(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// Record is a win/draw/loss and goals summary.
type Record struct {
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	Points       int     `json:"points"`
	WinRate      float64 `json:"win_rate_pct"`
}

// add folds one result into the record from the perspective of a team.
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
	r.WinRate = round1(100 * float64(r.Wins) / float64(r.Matches))
}

// GoalDifference is goals for minus goals against.
func (r Record) GoalDifference() int { return r.GoalsFor - r.GoalsAgainst }

func round1(f float64) float64 {
	return float64(int(f*10+0.5)) / 10
}

// TeamReport is the full statistical picture of one club under a filter.
type TeamReport struct {
	Team          string            `json:"team"`
	Filter        string            `json:"filter"`
	Overall       Record            `json:"overall"`
	Home          Record            `json:"home"`
	Away          Record            `json:"away"`
	ByCompetition map[string]Record `json:"by_competition"`
	BySeason      map[int]Record    `json:"by_season"`
	BiggestWin    *Match            `json:"biggest_win,omitempty"`
	BiggestLoss   *Match            `json:"biggest_loss,omitempty"`
}

// TeamStats aggregates a team's results under the supplied filter.
func (s *Store) TeamStats(f MatchFilter) (*TeamReport, error) {
	key, ok := s.ResolveTeam(f.Team)
	if !ok {
		return nil, fmt.Errorf("unknown team %q", f.Team)
	}
	venue := f.Venue
	f.Venue = "" // apply venue split ourselves so home/away are both reported
	matches := s.SearchMatches(f)

	rep := &TeamReport{
		Team:          s.DisplayName(key),
		Filter:        describeFilter(f),
		ByCompetition: map[string]Record{},
		BySeason:      map[int]Record{},
	}
	bestWin, bestLoss := 0, 0
	for _, m := range matches {
		home := m.HomeKey == key
		if (strings.EqualFold(venue, "home") && !home) || (strings.EqualFold(venue, "away") && home) {
			continue
		}
		gf, ga := m.HomeGoals, m.AwayGoals
		if !home {
			gf, ga = ga, gf
		}
		rep.Overall.add(gf, ga)
		if home {
			rep.Home.add(gf, ga)
		} else {
			rep.Away.add(gf, ga)
		}
		c := rep.ByCompetition[m.Competition]
		c.add(gf, ga)
		rep.ByCompetition[m.Competition] = c
		sr := rep.BySeason[m.Season]
		sr.add(gf, ga)
		rep.BySeason[m.Season] = sr

		if d := gf - ga; d > bestWin {
			bestWin, rep.BiggestWin = d, m
		} else if -d > bestLoss {
			bestLoss, rep.BiggestLoss = -d, m
		}
	}
	if rep.Overall.Matches == 0 {
		return nil, fmt.Errorf("no matches found for %s%s", rep.Team, suffixFilter(rep.Filter))
	}
	return rep, nil
}

// H2H is a head-to-head summary between two clubs.
type H2H struct {
	TeamA        string   `json:"team_a"`
	TeamB        string   `json:"team_b"`
	Filter       string   `json:"filter"`
	Matches      int      `json:"matches"`
	WinsA        int      `json:"wins_a"`
	WinsB        int      `json:"wins_b"`
	Draws        int      `json:"draws"`
	GoalsA       int      `json:"goals_a"`
	GoalsB       int      `json:"goals_b"`
	Results      []*Match `json:"results"`
	FirstMeeting string   `json:"first_meeting,omitempty"`
	LastMeeting  string   `json:"last_meeting,omitempty"`
}

// HeadToHead compares two clubs across every competition in the data.
func (s *Store) HeadToHead(a, b string, f MatchFilter) (*H2H, error) {
	ka, ok := s.ResolveTeam(a)
	if !ok {
		return nil, fmt.Errorf("unknown team %q", a)
	}
	kb, ok := s.ResolveTeam(b)
	if !ok {
		return nil, fmt.Errorf("unknown team %q", b)
	}
	if ka == kb {
		return nil, fmt.Errorf("%q and %q are the same club", a, b)
	}
	limit := f.Limit
	f.Team, f.Opponent, f.Venue, f.Limit = a, "", "", 0
	all := s.SearchMatches(f)

	h := &H2H{TeamA: s.DisplayName(ka), TeamB: s.DisplayName(kb), Filter: describeFilter(f)}
	for _, m := range all {
		if !(m.Involves(ka) && m.Involves(kb)) {
			continue
		}
		h.Matches++
		ga, gb := m.HomeGoals, m.AwayGoals
		if m.HomeKey != ka {
			ga, gb = gb, ga
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
		h.Results = append(h.Results, m)
	}
	if h.Matches == 0 {
		return nil, fmt.Errorf("no matches between %s and %s in the dataset", h.TeamA, h.TeamB)
	}
	h.LastMeeting = h.Results[0].DateString
	h.FirstMeeting = h.Results[len(h.Results)-1].DateString
	if limit > 0 && len(h.Results) > limit {
		h.Results = h.Results[:limit]
	}
	return h, nil
}

// StandingRow is one line of a computed league table.
type StandingRow struct {
	Position int    `json:"position"`
	Team     string `json:"team"`
	Record
	GoalDiff int `json:"goal_difference"`
}

// Standings computes a league table for a competition and season directly from
// match results, using the standard 3-1-0 scoring and goal difference then
// goals scored as tie breakers.
func (s *Store) Standings(competition string, season int) ([]StandingRow, error) {
	comp := ResolveCompetition(competition)
	if comp == "" {
		comp = competition
	}
	if comp == "" {
		comp = CompSerieA
	}
	recs := map[string]*Record{}
	n := 0
	for _, m := range s.Matches {
		if m.Season != season || !strings.EqualFold(m.Competition, comp) {
			continue
		}
		n++
		for _, side := range []struct {
			key    string
			gf, ga int
		}{{m.HomeKey, m.HomeGoals, m.AwayGoals}, {m.AwayKey, m.AwayGoals, m.HomeGoals}} {
			r, ok := recs[side.key]
			if !ok {
				r = &Record{}
				recs[side.key] = r
			}
			r.add(side.gf, side.ga)
		}
	}
	if n == 0 {
		return nil, fmt.Errorf("no %s matches found for season %d", comp, season)
	}
	rows := make([]StandingRow, 0, len(recs))
	for k, r := range recs {
		rows = append(rows, StandingRow{Team: s.DisplayName(k), Record: *r, GoalDiff: r.GoalDifference()})
	}
	sort.Slice(rows, func(i, j int) bool {
		a, b := rows[i], rows[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDiff != b.GoalDiff {
			return a.GoalDiff > b.GoalDiff
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	for i := range rows {
		rows[i].Position = i + 1
	}
	return rows, nil
}

// CompetitionStats is an aggregate summary over a set of matches.
type CompetitionStats struct {
	Scope          string  `json:"scope"`
	Matches        int     `json:"matches"`
	TotalGoals     int     `json:"total_goals"`
	GoalsPerMatch  float64 `json:"goals_per_match"`
	HomeWins       int     `json:"home_wins"`
	AwayWins       int     `json:"away_wins"`
	Draws          int     `json:"draws"`
	HomeWinRate    float64 `json:"home_win_rate_pct"`
	AwayWinRate    float64 `json:"away_win_rate_pct"`
	DrawRate       float64 `json:"draw_rate_pct"`
	HomeGoals      int     `json:"home_goals"`
	AwayGoals      int     `json:"away_goals"`
	CleanSheets    int     `json:"clean_sheets"`
	Seasons        []int   `json:"seasons,omitempty"`
	Teams          int     `json:"teams"`
	BiggestMargin  int     `json:"biggest_margin"`
	HighestScoring *Match  `json:"highest_scoring_match,omitempty"`
}

// Stats computes aggregate statistics over the matches selected by a filter.
func (s *Store) Stats(f MatchFilter) (*CompetitionStats, error) {
	f.Limit = 0
	matches := s.SearchMatches(f)
	if len(matches) == 0 {
		return nil, fmt.Errorf("no matches found%s", suffixFilter(describeFilter(f)))
	}
	st := &CompetitionStats{Scope: describeFilter(f), Matches: len(matches)}
	if st.Scope == "" {
		st.Scope = "all competitions, all seasons"
	}
	seasons := map[int]bool{}
	teams := map[string]bool{}
	mostGoals := -1
	for _, m := range matches {
		st.HomeGoals += m.HomeGoals
		st.AwayGoals += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			st.HomeWins++
		case m.AwayGoals > m.HomeGoals:
			st.AwayWins++
		default:
			st.Draws++
		}
		if m.HomeGoals == 0 || m.AwayGoals == 0 {
			st.CleanSheets++
		}
		if d := m.GoalDiff(); d > st.BiggestMargin {
			st.BiggestMargin = d
		}
		if g := m.HomeGoals + m.AwayGoals; g > mostGoals {
			mostGoals, st.HighestScoring = g, m
		}
		seasons[m.Season] = true
		teams[m.HomeKey] = true
		teams[m.AwayKey] = true
	}
	st.TotalGoals = st.HomeGoals + st.AwayGoals
	n := float64(st.Matches)
	st.GoalsPerMatch = round2(float64(st.TotalGoals) / n)
	st.HomeWinRate = round1(100 * float64(st.HomeWins) / n)
	st.AwayWinRate = round1(100 * float64(st.AwayWins) / n)
	st.DrawRate = round1(100 * float64(st.Draws) / n)
	st.Teams = len(teams)
	for y := range seasons {
		if y != 0 {
			st.Seasons = append(st.Seasons, y)
		}
	}
	sort.Ints(st.Seasons)
	return st, nil
}

func round2(f float64) float64 { return float64(int(f*100+0.5)) / 100 }

// BiggestWins returns the matches with the largest goal margins.
func (s *Store) BiggestWins(f MatchFilter) []*Match {
	limit := f.Limit
	if limit <= 0 {
		limit = 10
	}
	f.Limit = 0
	matches := s.SearchMatches(f)
	sort.SliceStable(matches, func(i, j int) bool {
		if matches[i].GoalDiff() != matches[j].GoalDiff() {
			return matches[i].GoalDiff() > matches[j].GoalDiff()
		}
		return matches[i].HomeGoals+matches[i].AwayGoals > matches[j].HomeGoals+matches[j].AwayGoals
	})
	if len(matches) > limit {
		matches = matches[:limit]
	}
	return matches
}

// TeamRanking is one team's aggregate record used for league-wide rankings.
type TeamRanking struct {
	Team string `json:"team"`
	Record
	GoalDiff int `json:"goal_difference"`
}

// RankTeams ranks every team appearing in the filtered matches by a metric:
// "points", "wins", "win_rate", "goals_for", "goals_against" or "goal_diff",
// optionally restricted to home or away matches via the filter's Venue field.
// Teams with fewer than minMatches appearances are excluded.
func (s *Store) RankTeams(f MatchFilter, metric string, minMatches int) ([]TeamRanking, error) {
	venue := strings.ToLower(f.Venue)
	f.Venue, f.Limit = "", 0
	matches := s.SearchMatches(f)
	if len(matches) == 0 {
		return nil, fmt.Errorf("no matches found%s", suffixFilter(describeFilter(f)))
	}
	recs := map[string]*Record{}
	touch := func(k string) *Record {
		r, ok := recs[k]
		if !ok {
			r = &Record{}
			recs[k] = r
		}
		return r
	}
	for _, m := range matches {
		if venue != "away" {
			touch(m.HomeKey).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			touch(m.AwayKey).add(m.AwayGoals, m.HomeGoals)
		}
	}
	var out []TeamRanking
	for k, r := range recs {
		if r.Matches < minMatches {
			continue
		}
		out = append(out, TeamRanking{Team: s.DisplayName(k), Record: *r, GoalDiff: r.GoalDifference()})
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("no team has at least %d matches in this scope", minMatches)
	}
	less := func(i, j int) bool { return out[i].Points > out[j].Points }
	switch strings.ToLower(strings.TrimSpace(metric)) {
	case "wins":
		less = func(i, j int) bool { return out[i].Wins > out[j].Wins }
	case "win_rate", "winrate":
		less = func(i, j int) bool { return out[i].WinRate > out[j].WinRate }
	case "goals_for", "goals", "scored":
		less = func(i, j int) bool { return out[i].GoalsFor > out[j].GoalsFor }
	case "goals_against", "conceded":
		less = func(i, j int) bool { return out[i].GoalsAgainst < out[j].GoalsAgainst }
	case "goal_diff", "goal_difference":
		less = func(i, j int) bool { return out[i].GoalDiff > out[j].GoalDiff }
	}
	sort.Slice(out, func(i, j int) bool {
		if less(i, j) != less(j, i) {
			return less(i, j)
		}
		return out[i].Team < out[j].Team
	})
	return out, nil
}

// PlayerFilter selects FIFA player records.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	MaxAge      int
	MinAge      int
	SortBy      string // overall (default), potential, age, name
	Limit       int
}

// SearchPlayers returns players matching the filter, best rated first.
func (s *Store) SearchPlayers(f PlayerFilter) []*Player {
	var out []*Player
	for _, p := range s.Players {
		if f.Name != "" && !NameMatches(f.Name, p.Name) {
			continue
		}
		if f.Nationality != "" && !NameMatches(f.Nationality, p.Nationality) {
			continue
		}
		if f.Club != "" && !(NameMatches(f.Club, p.Club) || TeamMatches(f.Club, p.ClubKey)) {
			continue
		}
		if !PositionMatches(f.Position, p.Position) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MinAge > 0 && p.Age < f.MinAge {
			continue
		}
		if f.MaxAge > 0 && p.Age > f.MaxAge {
			continue
		}
		out = append(out, p)
	}
	switch strings.ToLower(f.SortBy) {
	case "potential":
		sort.SliceStable(out, func(i, j int) bool { return out[i].Potential > out[j].Potential })
	case "age":
		sort.SliceStable(out, func(i, j int) bool { return out[i].Age < out[j].Age })
	case "name":
		sort.SliceStable(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	default:
		sort.SliceStable(out, func(i, j int) bool { return out[i].Overall > out[j].Overall })
	}
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// ClubSquad summarises the players a club has in the FIFA dataset.
type ClubSquad struct {
	Club       string    `json:"club"`
	Players    int       `json:"players"`
	AvgOverall float64   `json:"avg_overall"`
	Brazilians int       `json:"brazilians"`
	Top        []*Player `json:"top_players,omitempty"`
}

// ClubSquads reports, for every club that also appears in the match data (i.e.
// the Brazilian clubs), how many players it has and their average rating. This
// is the cross-file query joining the FIFA data to the match datasets.
func (s *Store) ClubSquads(nationality string, limit int) []ClubSquad {
	var out []ClubSquad
	for key, players := range s.playersByClub {
		if _, playsHere := s.matchesByTeam[key]; !playsHere {
			continue // not a club we have matches for
		}
		sq := ClubSquad{Club: s.DisplayName(key)}
		total := 0
		var kept []*Player
		for _, p := range players {
			if nationality != "" && !NameMatches(nationality, p.Nationality) {
				continue
			}
			kept = append(kept, p)
			total += p.Overall
			if p.IsBrazilian() {
				sq.Brazilians++
			}
		}
		if len(kept) == 0 {
			continue
		}
		sort.SliceStable(kept, func(i, j int) bool { return kept[i].Overall > kept[j].Overall })
		sq.Players = len(kept)
		sq.AvgOverall = round1(float64(total) / float64(len(kept)))
		if n := 3; len(kept) < n {
			sq.Top = kept
		} else {
			sq.Top = kept[:n]
		}
		out = append(out, sq)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Players != out[j].Players {
			return out[i].Players > out[j].Players
		}
		return out[i].Club < out[j].Club
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// TeamSummary lists a club and how much data exists for it.
type TeamSummary struct {
	Team         string   `json:"team"`
	Key          string   `json:"key"`
	Matches      int      `json:"matches"`
	Competitions []string `json:"competitions"`
	FirstSeason  int      `json:"first_season,omitempty"`
	LastSeason   int      `json:"last_season,omitempty"`
}

// ListTeams returns the clubs in the dataset, optionally filtered by a name
// fragment, ordered by how many matches they have.
func (s *Store) ListTeams(query string, limit int) []TeamSummary {
	var out []TeamSummary
	for key, ms := range s.matchesByTeam {
		disp := s.DisplayName(key)
		if query != "" && !NameMatches(query, disp) && !TeamMatches(query, key) {
			continue
		}
		ts := TeamSummary{Team: disp, Key: key, Matches: len(ms)}
		comps := map[string]bool{}
		for _, m := range ms {
			comps[m.Competition] = true
			if m.Season != 0 && (ts.FirstSeason == 0 || m.Season < ts.FirstSeason) {
				ts.FirstSeason = m.Season
			}
			if m.Season > ts.LastSeason {
				ts.LastSeason = m.Season
			}
		}
		for c := range comps {
			ts.Competitions = append(ts.Competitions, c)
		}
		sort.Strings(ts.Competitions)
		out = append(out, ts)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Matches != out[j].Matches {
			return out[i].Matches > out[j].Matches
		}
		return out[i].Team < out[j].Team
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// CompetitionSummary describes the coverage of one competition.
type CompetitionSummary struct {
	Competition string `json:"competition"`
	Matches     int    `json:"matches"`
	Teams       int    `json:"teams"`
	FirstSeason int    `json:"first_season"`
	LastSeason  int    `json:"last_season"`
}

// ListCompetitions describes every competition present in the data.
func (s *Store) ListCompetitions() []CompetitionSummary {
	agg := map[string]*CompetitionSummary{}
	teams := map[string]map[string]bool{}
	for _, m := range s.Matches {
		c, ok := agg[m.Competition]
		if !ok {
			c = &CompetitionSummary{Competition: m.Competition}
			agg[m.Competition] = c
			teams[m.Competition] = map[string]bool{}
		}
		c.Matches++
		if m.Season != 0 {
			if c.FirstSeason == 0 || m.Season < c.FirstSeason {
				c.FirstSeason = m.Season
			}
			if m.Season > c.LastSeason {
				c.LastSeason = m.Season
			}
		}
		teams[m.Competition][m.HomeKey] = true
		teams[m.Competition][m.AwayKey] = true
	}
	var out []CompetitionSummary
	for name, c := range agg {
		c.Teams = len(teams[name])
		out = append(out, *c)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Matches > out[j].Matches })
	return out
}

// describeFilter renders the active parts of a filter as readable text.
func describeFilter(f MatchFilter) string {
	var parts []string
	if f.Competition != "" {
		c := ResolveCompetition(f.Competition)
		if c == "" {
			c = f.Competition
		}
		parts = append(parts, c)
	}
	if f.Season != 0 {
		parts = append(parts, fmt.Sprintf("season %d", f.Season))
	}
	if f.From != "" || f.To != "" {
		parts = append(parts, strings.TrimSpace(fmt.Sprintf("%s to %s", or(f.From, "start"), or(f.To, "end"))))
	}
	if f.Stage != "" {
		parts = append(parts, "stage "+f.Stage)
	}
	if f.Round != "" {
		parts = append(parts, "round "+f.Round)
	}
	if f.Venue != "" {
		parts = append(parts, strings.ToLower(f.Venue)+" matches")
	}
	return strings.Join(parts, ", ")
}

func or(a, b string) string {
	if a != "" {
		return a
	}
	return b
}

func suffixFilter(desc string) string {
	if desc == "" {
		return ""
	}
	return " (" + desc + ")"
}
