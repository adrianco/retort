// teams.go answers club-shaped questions: "what is Corinthians' home record in
// 2022", "compare Palmeiras and Santos", "what competitions has Palmeiras played
// in", "who plays for Fluminense".
//
// Record is the single accumulator used everywhere a win/draw/loss tally is
// needed - team stats, standings rows, leaderboards - so points, goal difference
// and win rate are always computed the same way.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// Record is a win/draw/loss tally with goals. Points use the modern three points
// for a win, which is what the Brasileirão has awarded throughout the covered
// period.
type Record struct {
	Played        int     `json:"played"`
	Wins          int     `json:"wins"`
	Draws         int     `json:"draws"`
	Losses        int     `json:"losses"`
	GoalsFor      int     `json:"goals_for"`
	GoalsAgainst  int     `json:"goals_against"`
	GoalDiff      int     `json:"goal_difference"`
	Points        int     `json:"points"`
	WinRate       float64 `json:"win_rate_percent"`
	PointsPerGame float64 `json:"points_per_game"`
	CleanSheets   int     `json:"clean_sheets"`
}

// add folds one match into the record, from the point of view of a club that
// scored gf and conceded ga.
func (r *Record) add(gf, ga int) {
	r.Played++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
	case gf == ga:
		r.Draws++
	default:
		r.Losses++
	}
	if ga == 0 {
		r.CleanSheets++
	}
}

// finish computes the derived fields; call once after the last add.
func (r *Record) finish() {
	r.GoalDiff = r.GoalsFor - r.GoalsAgainst
	r.Points = r.Wins*3 + r.Draws
	if r.Played > 0 {
		r.WinRate = round1(float64(r.Wins) * 100 / float64(r.Played))
		r.PointsPerGame = round2(float64(r.Points) / float64(r.Played))
	}
}

// Summary renders the record the way the specification's examples do.
func (r Record) Summary() string {
	return fmt.Sprintf("%d matches: %dW %dD %dL, GF %d, GA %d (%+d), %d pts, win rate %.1f%%",
		r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff, r.Points, r.WinRate)
}

func round1(f float64) float64 { return float64(int(f*10+0.5)) / 10 }
func round2(f float64) float64 { return float64(int(f*100+0.5)) / 100 }

// TeamRef identifies a club in tool output.
type TeamRef struct {
	ID        string   `json:"id"`
	Name      string   `json:"name"`
	Display   string   `json:"display"`
	State     string   `json:"state,omitempty"`
	StateName string   `json:"state_name,omitempty"`
	Country   string   `json:"country,omitempty"`
	Nicknames []string `json:"nicknames,omitempty"`
	Aliases   []string `json:"aliases,omitempty"`
}

// Ref builds the reference form of a club.
func Ref(t *Team) TeamRef {
	return TeamRef{
		ID: t.ID, Name: t.Name, Display: t.Display,
		State: t.State, StateName: t.StateName(), Country: t.Country,
		Nicknames: t.Nicknames, Aliases: t.Aliases,
	}
}

// NamedRecord attaches a label to a record, used for per-competition and
// per-season breakdowns.
type NamedRecord struct {
	Label  string `json:"label"`
	Season int    `json:"season,omitempty"`
	Record Record `json:"record"`
}

// TeamStatsResult is the payload of the team_stats tool.
type TeamStatsResult struct {
	Team            TeamRef       `json:"team"`
	Scope           string        `json:"scope"`
	Overall         Record        `json:"overall"`
	Home            Record        `json:"home"`
	Away            Record        `json:"away"`
	ByCompetition   []NamedRecord `json:"by_competition,omitempty"`
	BySeason        []NamedRecord `json:"by_season,omitempty"`
	BiggestWin      *MatchView    `json:"biggest_win,omitempty"`
	BiggestDefeat   *MatchView    `json:"biggest_defeat,omitempty"`
	LongestUnbeaten int           `json:"longest_unbeaten_run"`
	RecentForm      string        `json:"recent_form,omitempty"`
	TopOpponents    []string      `json:"most_played_opponents,omitempty"`
	Alternatives    []string      `json:"other_clubs_matching_query,omitempty"`
	Note            string        `json:"note,omitempty"`
}

// Venue restricts a query to home or away matches.
type Venue string

// Venue selectors.
const (
	VenueAll  Venue = ""
	VenueHome Venue = "home"
	VenueAway Venue = "away"
)

// ParseVenue accepts "home", "away", "all" or "".
func ParseVenue(s string) (Venue, error) {
	switch foldKey(s) {
	case "", "all", "both", "any":
		return VenueAll, nil
	case "home":
		return VenueHome, nil
	case "away":
		return VenueAway, nil
	}
	return VenueAll, fmt.Errorf("unknown venue %q: use home, away or all", s)
}

// TeamStats computes the full record of a club under a filter.
func (g *Graph) TeamStats(team string, f MatchFilter, venue Venue) (*TeamStatsResult, error) {
	f.Team = team
	switch venue {
	case VenueHome:
		f.HomeTeam, f.Team = team, ""
	case VenueAway:
		f.AwayTeam, f.Team = team, ""
	}
	ms, rf, err := g.FindMatches(f)
	if err != nil {
		return nil, err
	}
	subject := rf.team
	if subject == nil {
		subject = rf.home
	}
	if subject == nil {
		subject = rf.away
	}
	scope := rf.scope
	if venue != VenueAll {
		scope += fmt.Sprintf(" (%s matches only)", venue)
	}
	res := &TeamStatsResult{Team: Ref(subject), Scope: scope}
	for _, t := range rf.alternatives {
		res.Alternatives = append(res.Alternatives, t.Display)
	}

	byComp := map[Competition]*Record{}
	bySeason := map[int]*Record{}
	opponents := map[string]int{}
	var best, worst *Match
	for _, m := range ms {
		gf, ga := m.HomeGoals, m.AwayGoals
		home := m.HomeID == subject.ID
		if !home {
			gf, ga = ga, gf
		}
		res.Overall.add(gf, ga)
		if home {
			res.Home.add(gf, ga)
		} else {
			res.Away.add(gf, ga)
		}
		rc := byComp[m.Competition]
		if rc == nil {
			rc = &Record{}
			byComp[m.Competition] = rc
		}
		rc.add(gf, ga)
		rs := bySeason[m.Season]
		if rs == nil {
			rs = &Record{}
			bySeason[m.Season] = rs
		}
		rs.add(gf, ga)
		opponents[m.OpponentOf(subject.ID)]++
		if gf > ga && (best == nil || gf-ga > diffFor(best, subject.ID) ||
			(gf-ga == diffFor(best, subject.ID) && gf > goalsFor(best, subject.ID))) {
			best = m
		}
		if ga > gf && (worst == nil || ga-gf > -diffFor(worst, subject.ID)) {
			worst = m
		}
	}
	res.Overall.finish()
	res.Home.finish()
	res.Away.finish()
	for comp, rec := range byComp {
		rec.finish()
		res.ByCompetition = append(res.ByCompetition, NamedRecord{Label: string(comp), Record: *rec})
	}
	sort.Slice(res.ByCompetition, func(i, j int) bool {
		return res.ByCompetition[i].Record.Played > res.ByCompetition[j].Record.Played
	})
	for season, rec := range bySeason {
		rec.finish()
		res.BySeason = append(res.BySeason, NamedRecord{Label: fmt.Sprintf("%d", season), Season: season, Record: *rec})
	}
	sort.Slice(res.BySeason, func(i, j int) bool { return res.BySeason[i].Season > res.BySeason[j].Season })
	if best != nil {
		v := g.View(best)
		res.BiggestWin = &v
	}
	if worst != nil {
		v := g.View(worst)
		res.BiggestDefeat = &v
	}
	res.LongestUnbeaten = longestUnbeaten(ms, subject.ID)
	res.RecentForm = recentForm(ms, subject.ID, 10)
	res.TopOpponents = g.topOpponents(opponents, 5)
	if res.Overall.Played == 0 {
		res.Note = "No matches for this club under the given filters. " + g.coverageHint(f)
	}
	return res, nil
}

func goalsFor(m *Match, teamID string) int {
	if m.HomeID == teamID {
		return m.HomeGoals
	}
	return m.AwayGoals
}

// longestUnbeaten walks the matches oldest first and returns the longest run
// without a defeat.
func longestUnbeaten(ms []*Match, teamID string) int {
	ordered := make([]*Match, len(ms))
	copy(ordered, ms)
	sort.SliceStable(ordered, func(i, j int) bool { return ordered[i].Date.Before(ordered[j].Date) })
	best, run := 0, 0
	for _, m := range ordered {
		if w := m.WinnerID(); w == "" || w == teamID {
			run++
			if run > best {
				best = run
			}
		} else {
			run = 0
		}
	}
	return best
}

// topOpponents renders the most frequently played opponents.
func (g *Graph) topOpponents(counts map[string]int, n int) []string {
	type kv struct {
		id string
		n  int
	}
	var list []kv
	for id, c := range counts {
		list = append(list, kv{id, c})
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].n != list[j].n {
			return list[i].n > list[j].n
		}
		return list[i].id < list[j].id
	})
	var out []string
	for i := 0; i < len(list) && i < n; i++ {
		if t, ok := g.Team(list[i].id); ok {
			out = append(out, fmt.Sprintf("%s (%d)", t.Display, list[i].n))
		}
	}
	return out
}

// CompetitionCoverage describes a club's presence in one competition.
type CompetitionCoverage struct {
	Competition string `json:"competition"`
	Matches     int    `json:"matches"`
	Seasons     []int  `json:"seasons"`
	SeasonRange string `json:"season_range"`
	Record      Record `json:"record"`
}

// Title is a competition won, computed from the match data.
type Title struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Detail      string `json:"detail,omitempty"`
}

// TeamProfileResult is the payload of the team_profile tool: everything the
// graph knows about one club, across matches and players.
type TeamProfileResult struct {
	Team         TeamRef               `json:"team"`
	TotalMatches int                   `json:"total_matches"`
	FirstMatch   *MatchView            `json:"first_match,omitempty"`
	LastMatch    *MatchView            `json:"last_match,omitempty"`
	Overall      Record                `json:"overall_record"`
	Competitions []CompetitionCoverage `json:"competitions"`
	Titles       []Title               `json:"titles_won"`
	Rivalries    []string              `json:"rivalries,omitempty"`
	Stadiums     []string              `json:"stadiums,omitempty"`
	SquadSize    int                   `json:"squad_size"`
	Squad        []PlayerView          `json:"squad,omitempty"`
	SquadNote    string                `json:"squad_note,omitempty"`
	Alternatives []string              `json:"other_clubs_matching_query,omitempty"`
}

// TeamProfile builds the cross-dataset overview of a club.
func (g *Graph) TeamProfile(name string, squadLimit int) (*TeamProfileResult, error) {
	t, alts, err := g.ResolveTeam(name)
	if err != nil {
		return nil, err
	}
	ms := g.teamMatches(t)
	res := &TeamProfileResult{Team: Ref(t), TotalMatches: len(ms)}
	for _, a := range alts {
		res.Alternatives = append(res.Alternatives, a.Display)
	}
	if len(ms) > 0 {
		first := g.View(ms[0])
		last := g.View(ms[len(ms)-1])
		res.FirstMatch, res.LastMatch = &first, &last
	}
	perComp := map[Competition]*CompetitionCoverage{}
	seasons := map[Competition]map[int]bool{}
	venues := map[string]int{}
	for _, m := range ms {
		gf, ga := m.HomeGoals, m.AwayGoals
		if m.AwayID == t.ID {
			gf, ga = ga, gf
		} else if m.Venue != "" {
			venues[m.Venue]++
		}
		res.Overall.add(gf, ga)
		cc := perComp[m.Competition]
		if cc == nil {
			cc = &CompetitionCoverage{Competition: string(m.Competition)}
			perComp[m.Competition] = cc
			seasons[m.Competition] = map[int]bool{}
		}
		cc.Matches++
		cc.Record.add(gf, ga)
		seasons[m.Competition][m.Season] = true
	}
	res.Overall.finish()
	for comp, cc := range perComp {
		cc.Record.finish()
		for s := range seasons[comp] {
			cc.Seasons = append(cc.Seasons, s)
		}
		sort.Ints(cc.Seasons)
		if len(cc.Seasons) > 0 {
			cc.SeasonRange = fmt.Sprintf("%d-%d", cc.Seasons[0], cc.Seasons[len(cc.Seasons)-1])
		}
		res.Competitions = append(res.Competitions, *cc)
	}
	sort.Slice(res.Competitions, func(i, j int) bool {
		return res.Competitions[i].Matches > res.Competitions[j].Matches
	})
	res.Titles = g.TitlesFor(t)
	for _, r := range rivalriesFor(t.ID) {
		other := r.TeamA
		if other == t.ID {
			other = r.TeamB
		}
		if ot, ok := g.Team(other); ok {
			res.Rivalries = append(res.Rivalries, fmt.Sprintf("%s (vs %s)", r.Name, ot.Display))
		}
	}
	res.Stadiums = topKeys(venues, 5)
	squad := g.playersByClub[t.ID]
	res.SquadSize = len(squad)
	res.Squad = playerViews(squad, squadLimit)
	if len(squad) == 0 {
		res.SquadNote = "The FIFA player database in this repository (FIFA 19) only licenses 15 Brazilian clubs, so this club has no squad rows. Use list_teams or search_players with group_by_club to see which clubs do."
	}
	return res, nil
}

// topKeys returns the n most frequent keys of a counter, ties broken by name.
func topKeys(counts map[string]int, n int) []string {
	type kv struct {
		k string
		n int
	}
	var list []kv
	for k, c := range counts {
		if k == "" {
			continue
		}
		list = append(list, kv{k, c})
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].n != list[j].n {
			return list[i].n > list[j].n
		}
		return list[i].k < list[j].k
	})
	var out []string
	for i := 0; i < len(list) && i < n; i++ {
		out = append(out, fmt.Sprintf("%s (%d)", list[i].k, list[i].n))
	}
	return out
}

// TeamListEntry is one row of the list_teams tool.
type TeamListEntry struct {
	TeamRef
	Matches      int      `json:"matches"`
	Competitions []string `json:"competitions,omitempty"`
	SquadSize    int      `json:"squad_size,omitempty"`
}

// ListTeams returns the clubs matching a free-text query (or all of them), most
// active first.
func (g *Graph) ListTeams(query string, limit int) []TeamListEntry {
	q := foldKey(query)
	var out []TeamListEntry
	for _, t := range g.teamList {
		if q != "" && !teamMatchesQuery(t, q) {
			continue
		}
		entry := TeamListEntry{TeamRef: Ref(t), Matches: len(t.matchIdx), SquadSize: len(g.playersByClub[t.ID])}
		comps := map[Competition]bool{}
		for _, i := range t.matchIdx {
			comps[g.matches[i].Competition] = true
		}
		for _, c := range AllCompetitions {
			if comps[c] {
				entry.Competitions = append(entry.Competitions, string(c))
			}
		}
		out = append(out, entry)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Matches != out[j].Matches {
			return out[i].Matches > out[j].Matches
		}
		return out[i].ID < out[j].ID
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// teamMatchesQuery reports whether any of a club's names contains the query.
func teamMatchesQuery(t *Team, q string) bool {
	if strings.Contains(foldKey(t.Display), q) || strings.Contains(t.ID, q) {
		return true
	}
	for _, a := range t.Aliases {
		if strings.Contains(foldKey(a), q) {
			return true
		}
	}
	for _, n := range t.Nicknames {
		if strings.Contains(foldKey(n), q) {
			return true
		}
	}
	return strings.Contains(foldKey(t.StateName()), q)
}
