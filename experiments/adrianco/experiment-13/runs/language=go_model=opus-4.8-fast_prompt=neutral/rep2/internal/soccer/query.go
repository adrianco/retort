// Context: query and aggregation layer over the loaded DB. These functions are
// pure (no I/O) and return plain data structures so they can be unit-tested
// directly and formatted by the MCP tool layer. Team matching is done through
// the accent-folded keys computed at load time; callers pass human names and we
// fold them here.
package soccer

import (
	"sort"
	"strings"
)

// MatchQuery describes the filters accepted by SearchMatches. Zero-valued
// fields are ignored.
type MatchQuery struct {
	Team        string // matches home OR away
	HomeTeam    string
	AwayTeam    string
	Opponent    string // used together with Team to find head-to-head style results
	Competition string
	Season      int
	SeasonFrom  int
	SeasonTo    int
	Limit       int
}

// SearchMatches returns matches satisfying the query, most recent first.
func (db *DB) SearchMatches(q MatchQuery) []Match {
	teamK := db.canonicalKey(q.Team)
	homeK := db.canonicalKey(q.HomeTeam)
	awayK := db.canonicalKey(q.AwayTeam)
	oppK := db.canonicalKey(q.Opponent)
	compK := canonComp(q.Competition)
	wantComp := strings.TrimSpace(q.Competition) != ""

	var out []Match
	for _, m := range db.Matches {
		if teamK != "" && m.HomeKey != teamK && m.AwayKey != teamK {
			continue
		}
		if oppK != "" && m.HomeKey != oppK && m.AwayKey != oppK {
			continue
		}
		if homeK != "" && m.HomeKey != homeK {
			continue
		}
		if awayK != "" && m.AwayKey != awayK {
			continue
		}
		if wantComp && m.Competition != compK {
			continue
		}
		if q.Season != 0 && m.Season != q.Season {
			continue
		}
		if q.SeasonFrom != 0 && m.Season < q.SeasonFrom {
			continue
		}
		if q.SeasonTo != 0 && m.Season > q.SeasonTo {
			continue
		}
		out = append(out, m)
	}
	sortMatchesRecent(out)
	if q.Limit > 0 && len(out) > q.Limit {
		out = out[:q.Limit]
	}
	return out
}

func sortMatchesRecent(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		if ms[i].HasDate && ms[j].HasDate {
			return ms[i].Date.After(ms[j].Date)
		}
		if ms[i].Season != ms[j].Season {
			return ms[i].Season > ms[j].Season
		}
		return ms[i].HasDate && !ms[j].HasDate
	})
}

// Record is an aggregate win/draw/loss + goals summary.
type Record struct {
	Matches   int
	Wins      int
	Draws     int
	Losses    int
	GoalsFor  int
	GoalsAgst int
	Points    int // 3 per win, 1 per draw
}

// WinRate returns wins/matches as a percentage (0 if no matches).
func (r Record) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return 100 * float64(r.Wins) / float64(r.Matches)
}

func (r *Record) add(scoredFor, scoredAgainst int) {
	r.Matches++
	r.GoalsFor += scoredFor
	r.GoalsAgst += scoredAgainst
	switch {
	case scoredFor > scoredAgainst:
		r.Wins++
		r.Points += 3
	case scoredFor == scoredAgainst:
		r.Draws++
		r.Points++
	default:
		r.Losses++
	}
}

// TeamRecordOptions filters which matches count toward a team record.
type TeamRecordOptions struct {
	Competition string
	Season      int
	HomeOnly    bool
	AwayOnly    bool
}

// TeamRecord computes a team's aggregate record over the matching games.
func (db *DB) TeamRecord(team string, opt TeamRecordOptions) Record {
	k := db.canonicalKey(team)
	compK := canonComp(opt.Competition)
	wantComp := strings.TrimSpace(opt.Competition) != ""
	var rec Record
	for _, m := range db.Matches {
		if !m.HasScore {
			continue
		}
		if wantComp && m.Competition != compK {
			continue
		}
		if opt.Season != 0 && m.Season != opt.Season {
			continue
		}
		switch {
		case m.HomeKey == k && !opt.AwayOnly:
			rec.add(m.HomeGoals, m.AwayGoals)
		case m.AwayKey == k && !opt.HomeOnly:
			rec.add(m.AwayGoals, m.HomeGoals)
		}
	}
	return rec
}

// HeadToHead summarizes the rivalry between two teams.
type HeadToHead struct {
	TeamA, TeamB string // display names (best-effort from data)
	AWins        int
	BWins        int
	Draws        int
	AGoals       int
	BGoals       int
	Matches      []Match // chronological, most recent first
}

// HeadToHead returns the rivalry record between teamA and teamB, optionally
// restricted to a competition.
func (db *DB) HeadToHead(teamA, teamB, competition string) HeadToHead {
	ka, kb := db.canonicalKey(teamA), db.canonicalKey(teamB)
	compK := canonComp(competition)
	wantComp := strings.TrimSpace(competition) != ""
	h := HeadToHead{TeamA: cleanTeamName(teamA), TeamB: cleanTeamName(teamB)}
	for _, m := range db.Matches {
		if wantComp && m.Competition != compK {
			continue
		}
		var aHome bool
		switch {
		case m.HomeKey == ka && m.AwayKey == kb:
			aHome = true
		case m.HomeKey == kb && m.AwayKey == ka:
			aHome = false
		default:
			continue
		}
		// Prefer display names as they actually appear.
		if aHome {
			h.TeamA, h.TeamB = m.HomeTeam, m.AwayTeam
		} else {
			h.TeamA, h.TeamB = m.AwayTeam, m.HomeTeam
		}
		h.Matches = append(h.Matches, m)
		if !m.HasScore {
			continue
		}
		ag, bg := m.HomeGoals, m.AwayGoals
		if !aHome {
			ag, bg = m.AwayGoals, m.HomeGoals
		}
		h.AGoals += ag
		h.BGoals += bg
		switch {
		case ag > bg:
			h.AWins++
		case bg > ag:
			h.BWins++
		default:
			h.Draws++
		}
	}
	sortMatchesRecent(h.Matches)
	return h
}

// StandingRow is one team's line in a computed league table.
type StandingRow struct {
	Team string
	Record
	GoalDiff int
}

// Standings computes a league table for a competition+season from match
// results, ordered by points, then goal difference, then goals scored.
func (db *DB) Standings(competition string, season int) []StandingRow {
	compK := canonComp(competition)
	byTeam := map[string]*StandingRow{}
	display := map[string]string{}
	for _, m := range db.Matches {
		if m.Competition != compK || m.Season != season || !m.HasScore {
			continue
		}
		hr := byTeam[m.HomeKey]
		if hr == nil {
			hr = &StandingRow{Team: m.HomeTeam}
			byTeam[m.HomeKey] = hr
		}
		ar := byTeam[m.AwayKey]
		if ar == nil {
			ar = &StandingRow{Team: m.AwayTeam}
			byTeam[m.AwayKey] = ar
		}
		display[m.HomeKey] = m.HomeTeam
		display[m.AwayKey] = m.AwayTeam
		hr.Record.add(m.HomeGoals, m.AwayGoals)
		ar.Record.add(m.AwayGoals, m.HomeGoals)
	}
	rows := make([]StandingRow, 0, len(byTeam))
	for k, r := range byTeam {
		r.Team = display[k]
		r.GoalDiff = r.GoalsFor - r.GoalsAgst
		rows = append(rows, *r)
	}
	sort.SliceStable(rows, func(i, j int) bool {
		if rows[i].Points != rows[j].Points {
			return rows[i].Points > rows[j].Points
		}
		if rows[i].GoalDiff != rows[j].GoalDiff {
			return rows[i].GoalDiff > rows[j].GoalDiff
		}
		if rows[i].GoalsFor != rows[j].GoalsFor {
			return rows[i].GoalsFor > rows[j].GoalsFor
		}
		return rows[i].Team < rows[j].Team
	})
	return rows
}

// Stats holds aggregate statistics over a set of matches.
type Stats struct {
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
	BiggestWins []Match // sorted by goal margin desc
}

// AvgGoals returns the mean goals per match.
func (s Stats) AvgGoals() float64 {
	if s.Matches == 0 {
		return 0
	}
	return float64(s.TotalGoals) / float64(s.Matches)
}

// HomeWinRate returns home wins as a percentage of decided matches.
func (s Stats) HomeWinRate() float64 {
	if s.Matches == 0 {
		return 0
	}
	return 100 * float64(s.HomeWins) / float64(s.Matches)
}

// StatsFilter selects the matches included in a statistics calculation.
type StatsFilter struct {
	Competition string
	Season      int
	Team        string
}

// Statistics aggregates over matches matching the filter. topWins controls how
// many biggest-margin matches to retain.
func (db *DB) Statistics(f StatsFilter, topWins int) Stats {
	compK := canonComp(f.Competition)
	wantComp := strings.TrimSpace(f.Competition) != ""
	teamK := db.canonicalKey(f.Team)
	var s Stats
	var scored []Match
	for _, m := range db.Matches {
		if !m.HasScore {
			continue
		}
		if wantComp && m.Competition != compK {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if teamK != "" && m.HomeKey != teamK && m.AwayKey != teamK {
			continue
		}
		s.Matches++
		s.TotalGoals += m.HomeGoals + m.AwayGoals
		switch m.Winner() {
		case "home":
			s.HomeWins++
		case "away":
			s.AwayWins++
		default:
			s.Draws++
		}
		scored = append(scored, m)
	}
	sort.SliceStable(scored, func(i, j int) bool {
		mi := abs(scored[i].HomeGoals - scored[i].AwayGoals)
		mj := abs(scored[j].HomeGoals - scored[j].AwayGoals)
		if mi != mj {
			return mi > mj
		}
		gi := scored[i].HomeGoals + scored[i].AwayGoals
		gj := scored[j].HomeGoals + scored[j].AwayGoals
		return gi > gj
	})
	if topWins <= 0 {
		topWins = 10
	}
	if len(scored) > topWins {
		scored = scored[:topWins]
	}
	s.BiggestWins = scored
	return s
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

// PlayerQuery filters the FIFA player dataset. Zero-valued fields are ignored.
type PlayerQuery struct {
	Name          string // substring match on name
	Nationality   string // exact (case/accent-insensitive)
	Club          string // team-key match (handles suffixes)
	Position      string
	MinOverall    int
	Limit         int
	SortByOverall bool
}

// SearchPlayers returns players matching the query. When SortByOverall is set
// (or any rating filter is used) results are sorted by Overall descending.
func (db *DB) SearchPlayers(q PlayerQuery) []Player {
	nameK := matchKey(q.Name)
	natK := matchKey(q.Nationality)
	clubK := db.canonicalKey(q.Club)
	posK := matchKey(q.Position)

	var out []Player
	for _, p := range db.Players {
		if nameK != "" && !strings.Contains(p.NameKey, nameK) {
			continue
		}
		if natK != "" && matchKey(p.Nationality) != natK {
			continue
		}
		if clubK != "" && p.ClubKey != clubK {
			continue
		}
		if posK != "" && matchKey(p.Position) != posK {
			continue
		}
		if q.MinOverall != 0 && p.Overall < q.MinOverall {
			continue
		}
		out = append(out, p)
	}
	if q.SortByOverall || q.MinOverall != 0 {
		sort.SliceStable(out, func(i, j int) bool {
			if out[i].Overall != out[j].Overall {
				return out[i].Overall > out[j].Overall
			}
			return out[i].Name < out[j].Name
		})
	}
	if q.Limit > 0 && len(out) > q.Limit {
		out = out[:q.Limit]
	}
	return out
}

// ClubSummary aggregates players by club for a nationality filter.
type ClubSummary struct {
	Club      string
	Count     int
	AvgRating float64
}

// PlayersByClub groups players (optionally filtered by nationality) by club and
// returns clubs sorted by player count.
func (db *DB) PlayersByClub(nationality string, limit int) []ClubSummary {
	natK := matchKey(nationality)
	type acc struct {
		club  string
		count int
		sum   int
	}
	m := map[string]*acc{}
	for _, p := range db.Players {
		if p.Club == "" {
			continue
		}
		if natK != "" && matchKey(p.Nationality) != natK {
			continue
		}
		a := m[p.ClubKey]
		if a == nil {
			a = &acc{club: p.Club}
			m[p.ClubKey] = a
		}
		a.count++
		a.sum += p.Overall
	}
	out := make([]ClubSummary, 0, len(m))
	for _, a := range m {
		avg := 0.0
		if a.count > 0 {
			avg = float64(a.sum) / float64(a.count)
		}
		out = append(out, ClubSummary{Club: a.club, Count: a.count, AvgRating: avg})
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Count != out[j].Count {
			return out[i].Count > out[j].Count
		}
		return out[i].Club < out[j].Club
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// Competitions returns the distinct competition labels present in the data.
func (db *DB) Competitions() []string {
	seen := map[string]bool{}
	var out []string
	for _, m := range db.Matches {
		if !seen[m.Competition] {
			seen[m.Competition] = true
			out = append(out, m.Competition)
		}
	}
	sort.Strings(out)
	return out
}
