package soccer

import (
	"fmt"
	"math"
	"sort"
	"strings"
)

// Record is a team's results over a set of matches.
type Record struct {
	Team           string   `json:"team"`
	Competition    string   `json:"competition,omitempty"`
	Season         int      `json:"season,omitempty"`
	Venue          string   `json:"venue,omitempty"`
	Matches        int      `json:"matches"`
	Wins           int      `json:"wins"`
	Draws          int      `json:"draws"`
	Losses         int      `json:"losses"`
	GoalsFor       int      `json:"goals_for"`
	GoalsAgainst   int      `json:"goals_against"`
	GoalDifference int      `json:"goal_difference"`
	Points         int      `json:"points"`
	WinRate        float64  `json:"win_rate"`
	ByCompetition  []Record `json:"by_competition,omitempty"`
}

func (r *Record) add(scored, conceded int) {
	r.Matches++
	r.GoalsFor += scored
	r.GoalsAgainst += conceded
	switch {
	case scored > conceded:
		r.Wins++
		r.Points += 3
	case scored == conceded:
		r.Draws++
		r.Points++
	default:
		r.Losses++
	}
	r.GoalDifference = r.GoalsFor - r.GoalsAgainst
	r.WinRate = percent(r.Wins, r.Matches)
}

// TeamRecord tallies a team's results, overall and per competition.
func (s *Store) TeamRecord(q MatchQuery) Record {
	r := Record{Team: s.Display(q.Team), Competition: string(q.Competition), Season: q.Season, Venue: q.Venue}
	parts := map[Competition]*Record{}
	var order []Competition
	for _, m := range s.FindMatches(q) {
		scored, conceded := m.GoalsFor(q.Team)
		r.add(scored, conceded)
		p, ok := parts[m.Competition]
		if !ok {
			p = &Record{Team: r.Team, Competition: string(m.Competition)}
			parts[m.Competition] = p
			order = append(order, m.Competition)
		}
		p.add(scored, conceded)
	}
	sort.Slice(order, func(i, j int) bool { return competitionOrder(order[i]) < competitionOrder(order[j]) })
	for _, c := range order {
		r.ByCompetition = append(r.ByCompetition, *parts[c])
	}
	return r
}

func competitionOrder(c Competition) int {
	for i, x := range []Competition{SerieA, SerieB, SerieC, CopaDoBrasil, Libertadores} {
		if x == c {
			return i
		}
	}
	return 99
}

func (r Record) Text() string {
	var b strings.Builder
	title := r.Team
	if r.Venue != "" {
		title += " " + r.Venue
	}
	title += " record"
	var scope []string
	if r.Season != 0 {
		scope = append(scope, fmt.Sprint(r.Season))
	}
	if r.Competition != "" {
		scope = append(scope, r.Competition)
	}
	if len(scope) > 0 {
		title += " (" + strings.Join(scope, " ") + ")"
	} else {
		title += " (all competitions in dataset)"
	}
	fmt.Fprintf(&b, "%s:\n", title)
	if r.Matches == 0 {
		b.WriteString("- No matches found.\n")
		return b.String()
	}
	fmt.Fprintf(&b, "- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d (difference %+d)\n- Points: %d\n- Win rate: %.1f%%\n",
		r.Matches, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDifference, r.Points, r.WinRate)
	if len(r.ByCompetition) > 1 {
		b.WriteString("By competition:\n")
		for _, p := range r.ByCompetition {
			fmt.Fprintf(&b, "- %s: %d matches, %dW %dD %dL, goals %d-%d, win rate %.1f%%\n",
				p.Competition, p.Matches, p.Wins, p.Draws, p.Losses, p.GoalsFor, p.GoalsAgainst, p.WinRate)
		}
	}
	return b.String()
}

// tallyAll builds a record for every team in the matches.
func (s *Store) tallyAll(matches []*Match, venue string) map[string]*Record {
	records := map[string]*Record{}
	add := func(key string, scored, conceded int) {
		r, ok := records[key]
		if !ok {
			r = &Record{Team: s.Display(key)}
			records[key] = r
		}
		r.add(scored, conceded)
	}
	for _, m := range matches {
		if venue != "away" {
			add(m.HomeKey, m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			add(m.AwayKey, m.AwayGoals, m.HomeGoals)
		}
	}
	return records
}

// Ranking metrics.
var metrics = map[string]struct {
	label     string
	ascending bool
	value     func(r *Record) float64
	format    func(v float64) string
}{
	"win_rate":        {"win rate", false, func(r *Record) float64 { return r.WinRate }, func(v float64) string { return fmt.Sprintf("%.1f%%", v) }},
	"points":          {"points", false, func(r *Record) float64 { return float64(r.Points) }, integer},
	"points_per_game": {"points per game", false, func(r *Record) float64 { return round2(float64(r.Points) / float64(r.Matches)) }, func(v float64) string { return fmt.Sprintf("%.2f", v) }},
	"goals_for":       {"goals scored", false, func(r *Record) float64 { return float64(r.GoalsFor) }, integer},
	"goals_against":   {"goals conceded (fewest first)", true, func(r *Record) float64 { return float64(r.GoalsAgainst) }, integer},
	"goal_difference": {"goal difference", false, func(r *Record) float64 { return float64(r.GoalDifference) }, integer},
	"wins":            {"wins", false, func(r *Record) float64 { return float64(r.Wins) }, integer},
}

func integer(v float64) string { return fmt.Sprintf("%d", int(v)) }

// MetricNames lists the ways teams can be ranked.
func MetricNames() []string {
	names := make([]string, 0, len(metrics))
	for n := range metrics {
		names = append(names, n)
	}
	sort.Strings(names)
	return names
}

// RankedTeam is one line of a ranking.
type RankedTeam struct {
	Rank         int     `json:"rank"`
	Team         string  `json:"team"`
	Value        float64 `json:"value"`
	DisplayValue string  `json:"display_value"`
	Matches      int     `json:"matches"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	Points       int     `json:"points"`
}

// Ranking ranks teams by a metric.
type Ranking struct {
	Metric      string       `json:"metric"`
	Description string       `json:"description"`
	MinMatches  int          `json:"min_matches"`
	Ranking     []RankedTeam `json:"ranking"`
}

// RankTeams ranks the teams in the matches selected by the query. Rates
// are only compared between teams with a reasonable number of matches:
// by default a quarter of the most matches any team played.
func (s *Store) RankTeams(q MatchQuery, metric string, minMatches, limit int) (Ranking, error) {
	if metric == "" {
		metric = "win_rate"
	}
	m, ok := metrics[metric]
	if !ok {
		return Ranking{}, fmt.Errorf("teams cannot be ranked by %q; choose one of %s", metric, strings.Join(MetricNames(), ", "))
	}
	team := q.Team
	q.Team = ""
	records := s.tallyAll(s.FindMatches(q), q.Venue)
	if minMatches <= 0 && (metric == "win_rate" || metric == "points_per_game") {
		most := 0
		for _, r := range records {
			most = max(most, r.Matches)
		}
		minMatches = max(1, int(math.Ceil(float64(most)/4)))
	}
	var rows []RankedTeam
	for key, r := range records {
		if r.Matches < minMatches || (team != "" && key != team) {
			continue
		}
		v := m.value(r)
		rows = append(rows, RankedTeam{Team: r.Team, Value: v, DisplayValue: m.format(v), Matches: r.Matches,
			Wins: r.Wins, Draws: r.Draws, Losses: r.Losses, GoalsFor: r.GoalsFor, GoalsAgainst: r.GoalsAgainst, Points: r.Points})
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].Value != rows[j].Value {
			return (rows[i].Value < rows[j].Value) == m.ascending
		}
		if rows[i].Matches != rows[j].Matches {
			return rows[i].Matches > rows[j].Matches
		}
		return rows[i].Team < rows[j].Team
	})
	if limit <= 0 {
		limit = 10
	}
	if len(rows) > limit {
		rows = rows[:limit]
	}
	for i := range rows {
		rows[i].Rank = i + 1
	}
	desc := "Teams ranked by " + m.label
	if q.Venue != "" {
		desc += " (" + q.Venue + " matches)"
	}
	if q.Competition != "" {
		desc += " in " + string(q.Competition)
	}
	if q.Season != 0 {
		desc += fmt.Sprintf(" %d", q.Season)
	}
	return Ranking{Metric: metric, Description: desc, MinMatches: max(minMatches, 1), Ranking: rows}, nil
}

func (r Ranking) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", r.Description)
	if len(r.Ranking) == 0 {
		b.WriteString("- No teams found.\n")
	}
	for _, t := range r.Ranking {
		fmt.Fprintf(&b, "%d. %s - %s (%d matches: %dW %dD %dL, goals %d-%d)\n",
			t.Rank, t.Team, t.DisplayValue, t.Matches, t.Wins, t.Draws, t.Losses, t.GoalsFor, t.GoalsAgainst)
	}
	if r.MinMatches > 1 {
		fmt.Fprintf(&b, "(Only teams with at least %d matches are ranked.)\n", r.MinMatches)
	}
	return b.String()
}

// CompetitionHistory is what a team has played in.
type CompetitionHistory struct {
	Team         string                `json:"team"`
	Competitions []CompetitionPlayedIn `json:"competitions"`
}

// CompetitionPlayedIn is one competition a team played in.
type CompetitionPlayedIn struct {
	Competition string `json:"competition"`
	Matches     int    `json:"matches"`
	Seasons     []int  `json:"seasons"`
	Wins        int    `json:"wins"`
	Draws       int    `json:"draws"`
	Losses      int    `json:"losses"`
}

// TeamCompetitions lists every competition the team played in.
func (s *Store) TeamCompetitions(team string) CompetitionHistory {
	r := s.TeamRecord(MatchQuery{Team: team})
	h := CompetitionHistory{Team: r.Team}
	for _, p := range r.ByCompetition {
		seasons := map[int]bool{}
		for _, m := range s.FindMatches(MatchQuery{Team: team, Competition: Competition(p.Competition)}) {
			seasons[m.Season] = true
		}
		var list []int
		for season := range seasons {
			list = append(list, season)
		}
		sort.Ints(list)
		h.Competitions = append(h.Competitions, CompetitionPlayedIn{Competition: p.Competition, Matches: p.Matches,
			Seasons: list, Wins: p.Wins, Draws: p.Draws, Losses: p.Losses})
	}
	return h
}

func (h CompetitionHistory) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "Competitions %s has played in (dataset):\n", h.Team)
	for _, c := range h.Competitions {
		fmt.Fprintf(&b, "- %s: %d matches over %d %s (%s), %dW %dD %dL\n", c.Competition, c.Matches,
			len(c.Seasons), plural(len(c.Seasons), "season", "seasons"), seasonSpan(c.Seasons), c.Wins, c.Draws, c.Losses)
	}
	return b.String()
}

func seasonSpan(seasons []int) string {
	if len(seasons) == 0 {
		return ""
	}
	if len(seasons) == 1 {
		return fmt.Sprint(seasons[0])
	}
	return fmt.Sprintf("%d-%d", seasons[0], seasons[len(seasons)-1])
}

// TeamIdentity tells which team a name refers to and how the data names it.
type TeamIdentity struct {
	Name         string   `json:"name"`
	Variants     []string `json:"variants"`
	Matches      int      `json:"matches"`
	Competitions []string `json:"competitions"`
}

// TeamSearch is the answer to "which team is this?".
type TeamSearch struct {
	Query string         `json:"query"`
	Teams []TeamIdentity `json:"teams"`
}

// FindTeams identifies the teams a name may refer to, best match first.
func (s *Store) FindTeams(name string) TeamSearch {
	result := TeamSearch{Query: name}
	var teams []*Team
	if t := s.Teams[NormalizeTeam(name).Key]; t != nil {
		teams = append(teams, t)
	}
	for _, t := range s.similarTeams(name) {
		if len(teams) < 10 && (len(teams) == 0 || t != teams[0]) {
			teams = append(teams, t)
		}
	}
	for _, t := range teams {
		variants := make([]string, 0, len(t.Variants))
		for v := range t.Variants {
			variants = append(variants, v)
		}
		sort.Strings(variants)
		h := s.TeamCompetitions(t.Key)
		id := TeamIdentity{Name: t.Display, Variants: variants}
		for _, c := range h.Competitions {
			id.Matches += c.Matches
			id.Competitions = append(id.Competitions, c.Competition)
		}
		result.Teams = append(result.Teams, id)
	}
	return result
}

func (r TeamSearch) Text() string {
	var b strings.Builder
	if len(r.Teams) == 0 {
		fmt.Fprintf(&b, "No team matching %q was found.\n", r.Query)
		return b.String()
	}
	fmt.Fprintf(&b, "Teams matching %q:\n", r.Query)
	for _, t := range r.Teams {
		fmt.Fprintf(&b, "- %s: %d matches in %s; written in the data as %s\n", t.Name, t.Matches,
			strings.Join(t.Competitions, ", "), strings.Join(quoteAll(t.Variants), ", "))
	}
	return b.String()
}

func quoteAll(items []string) []string {
	out := make([]string, len(items))
	for i, s := range items {
		out[i] = fmt.Sprintf("%q", s)
	}
	return out
}

// ClubProfile combines what the player data and match data say about a club.
type ClubProfile struct {
	Team           string       `json:"team"`
	SquadSize      int          `json:"squad_size"`
	AverageOverall float64      `json:"average_overall"`
	Squad          []PlayerView `json:"squad"`
	Record         *Record      `json:"record,omitempty"`
}

// ClubProfile describes a club by its squad and its results.
func (s *Store) ClubProfile(name string) (ClubProfile, error) {
	key := NormalizeTeam(name).Key
	squad := s.playersAt(key, name)
	if s.Teams[key] == nil && len(squad) == 0 {
		resolved, err := s.ResolveTeam(name)
		if err != nil {
			return ClubProfile{}, err
		}
		key = resolved
		squad = s.playersAt(key, name)
	}
	p := ClubProfile{Team: s.Display(key), SquadSize: len(squad)}
	if s.Teams[key] == nil && len(squad) > 0 {
		p.Team = squad[0].Club
	}
	total := 0
	for _, pl := range squad {
		total += pl.Overall
		p.Squad = append(p.Squad, viewPlayer(pl, false))
	}
	if len(squad) > 0 {
		p.AverageOverall = math.Round(float64(total)*10/float64(len(squad))) / 10
	}
	if s.Teams[key] != nil {
		r := s.TeamRecord(MatchQuery{Team: key})
		p.Record = &r
	}
	return p, nil
}

func (p ClubProfile) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s club profile\n", p.Team)
	if p.SquadSize == 0 {
		b.WriteString("\nSquad: no players for this club in the FIFA player data.\n")
	} else {
		fmt.Fprintf(&b, "\nSquad (FIFA data): %d players, average rating %.1f\n", p.SquadSize, p.AverageOverall)
		for i, pl := range p.Squad {
			if i == 15 {
				fmt.Fprintf(&b, "- ... and %d more\n", p.SquadSize-15)
				break
			}
			fmt.Fprintf(&b, "- %s - Overall: %d, Position: %s, Age: %d, Nationality: %s\n", pl.Name, pl.Overall, pl.Position, pl.Age, pl.Nationality)
		}
	}
	if p.Record != nil {
		b.WriteString("\n" + p.Record.Text())
	} else {
		b.WriteString("\nResults: this club does not appear in the match data.\n")
	}
	return b.String()
}
