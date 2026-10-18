// Query layer: match filtering, team records, standings, rankings and player
// search. Everything here is a pure function of the Store.

package main

import (
	"sort"
	"strings"
	"time"
)

// matchQuery is a conjunction of optional filters over matches.
// Zero values mean "no constraint".
type matchQuery struct {
	Team        map[string]bool // team IDs; nil means any team
	Opponent    map[string]bool // with Team, restricts to fixtures against Opponent
	Venue       string          // "home", "away" or "" (either side); applies to Team
	Competition string
	Season      int
	From        time.Time // inclusive
	To          time.Time // exclusive
	Round       string
	FinalsOnly  bool
}

func (q matchQuery) matches(m Match) bool {
	if q.Competition != "" && m.Competition != q.Competition {
		return false
	}
	if q.Season != 0 && m.Season != q.Season {
		return false
	}
	if !q.From.IsZero() && m.Date.Before(q.From) {
		return false
	}
	if !q.To.IsZero() && !m.Date.Before(q.To) {
		return false
	}
	if q.Round != "" && !strings.EqualFold(m.Round, q.Round) {
		return false
	}
	if q.FinalsOnly && !m.IsFinal {
		return false
	}
	if q.Team == nil {
		return true
	}

	inHome, inAway := q.Team[m.Home], q.Team[m.Away]
	if q.Opponent != nil {
		// Head-to-head: the two sides must be one team from each group.
		oppHome, oppAway := q.Opponent[m.Home], q.Opponent[m.Away]
		if !((inHome && oppAway) || (inAway && oppHome)) {
			return false
		}
	} else if !inHome && !inAway {
		return false
	}
	switch q.Venue {
	case "home":
		return inHome
	case "away":
		return inAway
	}
	return true
}

// selectMatches returns matching fixtures, newest first.
func (st *Store) selectMatches(q matchQuery) []Match {
	var out []Match
	for _, m := range st.Matches {
		if q.matches(m) {
			out = append(out, m)
		}
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	return out
}

// record is a win/draw/loss tally with goals.
type record struct {
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

func (r *record) add(goalsFor, goalsAgainst int) {
	r.Played++
	r.GoalsFor += goalsFor
	r.GoalsAgainst += goalsAgainst
	switch {
	case goalsFor > goalsAgainst:
		r.Wins++
	case goalsFor == goalsAgainst:
		r.Draws++
	default:
		r.Losses++
	}
}

func (r record) Points() int         { return 3*r.Wins + r.Draws }
func (r record) GoalDifference() int { return r.GoalsFor - r.GoalsAgainst }

func (r record) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Played) * 100
}

// sideRecord tallies one group of teams over matches. venue "home" or "away"
// counts only games played on that side.
func sideRecord(matches []Match, ids map[string]bool, venue string) record {
	var r record
	for _, m := range matches {
		switch {
		case ids[m.Home] && venue != "away":
			r.add(m.HomeGoals, m.AwayGoals)
		case ids[m.Away] && venue != "home":
			r.add(m.AwayGoals, m.HomeGoals)
		}
	}
	return r
}

// teamRecords tallies every team in matches. venue works as in sideRecord.
func teamRecords(matches []Match, venue string) map[string]*record {
	out := map[string]*record{}
	get := func(id string) *record {
		if out[id] == nil {
			out[id] = &record{}
		}
		return out[id]
	}
	for _, m := range matches {
		if venue != "away" {
			get(m.Home).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			get(m.Away).add(m.AwayGoals, m.HomeGoals)
		}
	}
	return out
}

type standingRow struct {
	TeamID string
	Name   string
	record
}

// standings builds a league table from the matches of one competition season.
// Sorted by points, then goal difference, goals for, then name.
func (st *Store) standings(competition string, season int) []standingRow {
	matches := st.selectMatches(matchQuery{Competition: competition, Season: season})
	var rows []standingRow
	for id, r := range teamRecords(matches, "") {
		rows = append(rows, standingRow{TeamID: id, Name: st.teamLabel(id), record: *r})
	}
	sort.Slice(rows, func(i, j int) bool {
		a, b := rows[i], rows[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.GoalDifference() != b.GoalDifference() {
			return a.GoalDifference() > b.GoalDifference()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Name < b.Name
	})
	return rows
}

// latestSeason returns the most recent season in which competition was played.
func (st *Store) latestSeason(competition string) int {
	latest := 0
	for _, m := range st.Matches {
		if m.Competition == competition && m.Season > latest {
			latest = m.Season
		}
	}
	return latest
}

// competitionSummary aggregates results over a set of matches.
type competitionSummary struct {
	Matches  int
	Goals    int
	HomeWins int
	Draws    int
	AwayWins int
}

func summarize(matches []Match) competitionSummary {
	var s competitionSummary
	for _, m := range matches {
		s.Matches++
		s.Goals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			s.HomeWins++
		case m.HomeGoals == m.AwayGoals:
			s.Draws++
		default:
			s.AwayWins++
		}
	}
	return s
}

// biggestWins returns the matches with the largest margins, widest first and
// newest first among equal margins. Drawn matches are excluded.
func biggestWins(matches []Match, limit int) []Match {
	var wins []Match
	for _, m := range matches {
		if m.HomeGoals != m.AwayGoals {
			wins = append(wins, m)
		}
	}
	margin := func(m Match) int {
		d := m.HomeGoals - m.AwayGoals
		if d < 0 {
			return -d
		}
		return d
	}
	sort.SliceStable(wins, func(i, j int) bool {
		if margin(wins[i]) != margin(wins[j]) {
			return margin(wins[i]) > margin(wins[j])
		}
		return wins[i].Date.After(wins[j].Date)
	})
	if limit > 0 && len(wins) > limit {
		wins = wins[:limit]
	}
	return wins
}

var positionGroups = map[string][]string{
	"forward":    {"LW", "RW", "ST", "CF", "LF", "RF", "LS", "RS"},
	"midfielder": {"CAM", "CM", "CDM", "LM", "RM", "LAM", "RAM", "LCM", "RCM", "LDM", "RDM"},
	"defender":   {"LB", "RB", "CB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
}

// positionMatches accepts a group name ("forwards", "midfielder", ...) or a
// position code ("ST", "cdm").
func positionMatches(position, query string) bool {
	key := strings.TrimSuffix(strings.ToLower(strings.TrimSpace(query)), "s")
	if group, ok := positionGroups[key]; ok {
		for _, p := range group {
			if strings.EqualFold(p, position) {
				return true
			}
		}
		return false
	}
	return strings.EqualFold(strings.TrimSpace(position), strings.TrimSpace(query))
}

// clubRunMatches reports whether match accepts any run of consecutive words in
// club, with each run folded. So "CR Flamengo" yields "flamengo", and
// "São Paulo FC" yields "saopaulo". Matching whole words avoids "sport" matching
// "Sporting CP".
func clubRunMatches(club string, match func(run string) bool) bool {
	words := strings.Fields(club)
	for i := range words {
		run := ""
		for j := i; j < len(words); j++ {
			run += foldKey(words[j])
			if match(run) {
				return true
			}
		}
	}
	return false
}

// searchPlayers filters FIFA players. Results are sorted by overall, then name.
func (st *Store) searchPlayers(name, nationality, club, position string, minOverall int) []Player {
	wantName := foldKey(name)
	wantClub := foldKey(club)
	var out []Player
	for _, p := range st.Players {
		if wantName != "" && !strings.Contains(foldKey(p.Name), wantName) {
			continue
		}
		if nationality != "" && foldKey(p.Nationality) != foldKey(nationality) {
			continue
		}
		if wantClub != "" && !clubRunMatches(p.Club, func(run string) bool { return run == wantClub }) {
			continue
		}
		if position != "" && !positionMatches(p.Position, position) {
			continue
		}
		if p.Overall < minOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Name < out[j].Name
	})
	return out
}

// isBrazilianClub reports whether a FIFA club name matches a club from the
// domestic match data. The whole name must match, so "Santos Laguna" or
// "Vitória Guimarães" do not count. Matching is attempted with the alias table
// applied and again with the generic words removed.
func (st *Store) isBrazilianClub(club string) bool {
	tn := parseTeamName(club)
	if st.brazilianBases[tn.Base] {
		return true
	}
	var kept []string
	for _, w := range strings.Fields(tn.Display) {
		if !clubNoiseWords[foldKey(w)] {
			kept = append(kept, w)
		}
	}
	return st.brazilianBases[foldKey(strings.Join(kept, " "))]
}

type clubSummary struct {
	Club       string
	Players    int
	AvgOverall float64
}

// brazilianClubSummary groups Brazilian-national players by their club, keeping
// only clubs that appear in the domestic match data.
func (st *Store) brazilianClubSummary() []clubSummary {
	totals := map[string]*clubSummary{}
	sums := map[string]int{}
	for _, p := range st.Players {
		if foldKey(p.Nationality) != "brazil" {
			continue
		}
		if !st.isBrazilianClub(p.Club) {
			continue
		}
		if totals[p.Club] == nil {
			totals[p.Club] = &clubSummary{Club: p.Club}
		}
		totals[p.Club].Players++
		sums[p.Club] += p.Overall
	}
	out := make([]clubSummary, 0, len(totals))
	for club, s := range totals {
		s.AvgOverall = float64(sums[club]) / float64(s.Players)
		out = append(out, *s)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Players != out[j].Players {
			return out[i].Players > out[j].Players
		}
		return out[i].Club < out[j].Club
	})
	return out
}
