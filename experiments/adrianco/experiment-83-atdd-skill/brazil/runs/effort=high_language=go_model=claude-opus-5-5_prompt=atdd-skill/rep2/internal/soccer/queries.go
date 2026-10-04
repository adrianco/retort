package soccer

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"time"
)

// MatchView is a match as presented in answers.
type MatchView struct {
	Date        string      `json:"date"`
	Competition string      `json:"competition"`
	Season      int         `json:"season"`
	Round       int         `json:"round,omitempty"`
	Stage       string      `json:"stage,omitempty"`
	Home        string      `json:"home"`
	Away        string      `json:"away"`
	HomeGoals   int         `json:"home_goals"`
	AwayGoals   int         `json:"away_goals"`
	Arena       string      `json:"arena,omitempty"`
	Statistics  *MatchStats `json:"statistics,omitempty"`
	Sources     []string    `json:"sources"`
}

func (s *Store) view(m *Match) MatchView {
	return MatchView{
		Date: m.Date.Format("2006-01-02"), Competition: m.Competition, Season: m.Season, Round: m.Round,
		Stage: m.Stage, Home: s.Teams.Name(m.Home), Away: s.Teams.Name(m.Away), HomeGoals: m.HomeGoals,
		AwayGoals: m.AwayGoals, Arena: m.Arena, Statistics: m.Stats, Sources: m.Sources,
	}
}

func (s *Store) views(ms []*Match) []MatchView {
	out := make([]MatchView, 0, len(ms))
	for _, m := range ms {
		out = append(out, s.view(m))
	}
	return out
}

// Record is a win/draw/loss record.
type Record struct {
	Team           string  `json:"team,omitempty"`
	Matches        int     `json:"matches"`
	Wins           int     `json:"wins"`
	Draws          int     `json:"draws"`
	Losses         int     `json:"losses"`
	GoalsFor       int     `json:"goals_for"`
	GoalsAgainst   int     `json:"goals_against"`
	GoalDifference int     `json:"goal_difference"`
	Points         int     `json:"points"`
	WinRate        float64 `json:"win_rate"`
}

func (r *Record) add(gf, ga int) {
	r.Matches++
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
	r.GoalDifference = r.GoalsFor - r.GoalsAgainst
	r.Points = 3*r.Wins + r.Draws
	r.WinRate = percent(r.Wins, r.Matches)
}

func percent(n, of int) float64 {
	if of == 0 {
		return 0
	}
	return round(100*float64(n)/float64(of), 1)
}

func round(f float64, places int) float64 {
	p := math.Pow(10, float64(places))
	return math.Round(f*p) / p
}

// UnknownTeamError says a fan named a club the data does not know.
type UnknownTeamError struct{ Name string }

func (e UnknownTeamError) Error() string {
	return fmt.Sprintf("no club called %q appears in the match data", e.Name)
}

func (s *Store) resolve(name string) (TeamID, error) {
	id, ok := s.Teams.Resolve(name)
	if !ok {
		return "", UnknownTeamError{name}
	}
	return id, nil
}

// ---- finding matches ---------------------------------------------------------

// MatchQuery selects matches. Empty fields mean "any".
type MatchQuery struct {
	Team, Opponent string
	Competition    string
	Season         int
	From, To       time.Time
	Venue          string // "home" or "away", relative to Team
	Stage          string
	Limit          int
	Oldest         bool
}

type HeadToHeadSummary struct {
	Team          string `json:"team"`
	Opponent      string `json:"opponent"`
	Matches       int    `json:"matches"`
	TeamWins      int    `json:"team_wins"`
	OpponentWins  int    `json:"opponent_wins"`
	Draws         int    `json:"draws"`
	TeamGoals     int    `json:"team_goals"`
	OpponentGoals int    `json:"opponent_goals"`
}

type MatchesAnswer struct {
	Total      int                `json:"total"`
	Shown      int                `json:"shown"`
	Matches    []MatchView        `json:"matches"`
	HeadToHead *HeadToHeadSummary `json:"head_to_head,omitempty"`
	Message    string             `json:"message,omitempty"`
	criteria   MatchQuery
}

func (s *Store) FindMatches(q MatchQuery) MatchesAnswer {
	ans := MatchesAnswer{Matches: []MatchView{}, criteria: q}
	var team, opp TeamID
	var err error
	if q.Team != "" {
		if team, err = s.resolve(q.Team); err != nil {
			ans.Message = err.Error()
			return ans
		}
	}
	if q.Opponent != "" {
		if opp, err = s.resolve(q.Opponent); err != nil {
			ans.Message = err.Error()
			return ans
		}
	}
	found := s.selectMatches(team, opp, q)
	if team != "" && opp != "" {
		h := &HeadToHeadSummary{Team: s.Teams.Name(team), Opponent: s.Teams.Name(opp)}
		for _, m := range found {
			tg, og := goalsFor(m, team), goalsFor(m, opp)
			h.Matches++
			h.TeamGoals += tg
			h.OpponentGoals += og
			switch {
			case tg > og:
				h.TeamWins++
			case og > tg:
				h.OpponentWins++
			default:
				h.Draws++
			}
		}
		ans.HeadToHead = h
	}
	if !q.Oldest {
		reverse(found)
	}
	ans.Total = len(found)
	limit := q.Limit
	if limit <= 0 {
		limit = 20
	}
	if len(found) > limit {
		found = found[:limit]
	}
	ans.Shown = len(found)
	ans.Matches = s.views(found)
	return ans
}

func (s *Store) selectMatches(team, opp TeamID, q MatchQuery) []*Match {
	pool := s.Matches
	if team != "" {
		pool = s.byTeam[team]
	}
	stage := Fold(q.Stage)
	var out []*Match
	for _, m := range pool {
		if q.Competition != "" && m.Competition != q.Competition {
			continue
		}
		if q.Season != 0 && m.Season != q.Season {
			continue
		}
		if !q.From.IsZero() && m.Date.Before(q.From) {
			continue
		}
		if !q.To.IsZero() && m.Date.After(q.To.Add(24*time.Hour-time.Second)) {
			continue
		}
		if stage != "" && !stageMatches(m.Stage, stage) {
			continue
		}
		if team != "" {
			switch q.Venue {
			case "home":
				if m.Home != team {
					continue
				}
			case "away":
				if m.Away != team {
					continue
				}
			}
		}
		if opp != "" && m.Home != opp && m.Away != opp {
			continue
		}
		out = append(out, m)
	}
	return out
}

func stageMatches(stage, want string) bool {
	st := Fold(stage)
	switch want {
	case "final", "finals":
		return st == "final"
	case "semifinal", "semifinals", "semi-final", "semi-finals", "semis":
		return st == "semifinals"
	case "quarterfinal", "quarterfinals", "quarter-finals", "quarter-final":
		return st == "quarterfinals"
	case "knockout", "knockouts":
		return st != "" && st != "group stage"
	}
	return strings.Contains(st, want)
}

func goalsFor(m *Match, team TeamID) int {
	if m.Home == team {
		return m.HomeGoals
	}
	return m.AwayGoals
}

func goalsAgainst(m *Match, team TeamID) int {
	if m.Home == team {
		return m.AwayGoals
	}
	return m.HomeGoals
}

func reverse(ms []*Match) {
	for i, j := 0, len(ms)-1; i < j; i, j = i+1, j-1 {
		ms[i], ms[j] = ms[j], ms[i]
	}
}

// ---- teams -------------------------------------------------------------------

type TeamRecordAnswer struct {
	Record
	Competition string `json:"competition,omitempty"`
	Season      int    `json:"season,omitempty"`
	Venue       string `json:"venue"`
}

func (s *Store) TeamRecord(team, competition string, season int, venue string) (TeamRecordAnswer, error) {
	id, err := s.resolve(team)
	if err != nil {
		return TeamRecordAnswer{}, err
	}
	if venue == "" {
		venue = "all"
	}
	ans := TeamRecordAnswer{Record: Record{Team: s.Teams.Name(id)}, Competition: competition, Season: season, Venue: venue}
	for _, m := range s.selectMatches(id, "", MatchQuery{Competition: competition, Season: season, Venue: venue}) {
		ans.add(goalsFor(m, id), goalsAgainst(m, id))
	}
	return ans, nil
}

type HeadToHeadAnswer struct {
	TeamA         string      `json:"team_a"`
	TeamB         string      `json:"team_b"`
	Competition   string      `json:"competition,omitempty"`
	Season        int         `json:"season,omitempty"`
	Matches       int         `json:"matches"`
	TeamAWins     int         `json:"team_a_wins"`
	TeamBWins     int         `json:"team_b_wins"`
	Draws         int         `json:"draws"`
	TeamAGoals    int         `json:"team_a_goals"`
	TeamBGoals    int         `json:"team_b_goals"`
	RecentMatches []MatchView `json:"recent_matches"`
	BiggestWins   []MatchView `json:"biggest_wins"`
}

func (s *Store) HeadToHead(a, b, competition string, season int) (HeadToHeadAnswer, error) {
	ida, err := s.resolve(a)
	if err != nil {
		return HeadToHeadAnswer{}, err
	}
	idb, err := s.resolve(b)
	if err != nil {
		return HeadToHeadAnswer{}, err
	}
	ans := HeadToHeadAnswer{TeamA: s.Teams.Name(ida), TeamB: s.Teams.Name(idb), Competition: competition, Season: season}
	ms := s.selectMatches(ida, idb, MatchQuery{Competition: competition, Season: season})
	for _, m := range ms {
		ga, gb := goalsFor(m, ida), goalsFor(m, idb)
		ans.Matches++
		ans.TeamAGoals += ga
		ans.TeamBGoals += gb
		switch {
		case ga > gb:
			ans.TeamAWins++
		case gb > ga:
			ans.TeamBWins++
		default:
			ans.Draws++
		}
	}
	recent := append([]*Match(nil), ms...)
	reverse(recent)
	if len(recent) > 10 {
		recent = recent[:10]
	}
	ans.RecentMatches = s.views(recent)
	ans.BiggestWins = s.views(biggest(ms, 3))
	return ans, nil
}

// RankEntry is one line of a team ranking.
type RankEntry struct {
	Position int     `json:"position"`
	Team     string  `json:"team"`
	Value    float64 `json:"value"`
	Record
}

type RankingAnswer struct {
	Metric      string      `json:"metric"`
	Competition string      `json:"competition,omitempty"`
	Season      int         `json:"season,omitempty"`
	Venue       string      `json:"venue"`
	MinMatches  int         `json:"min_matches"`
	Ranking     []RankEntry `json:"ranking"`
}

var rankMetrics = map[string]func(Record) float64{
	"goals_for":       func(r Record) float64 { return float64(r.GoalsFor) },
	"goals_against":   func(r Record) float64 { return float64(r.GoalsAgainst) },
	"win_rate":        func(r Record) float64 { return r.WinRate },
	"points":          func(r Record) float64 { return float64(r.Points) },
	"wins":            func(r Record) float64 { return float64(r.Wins) },
	"goal_difference": func(r Record) float64 { return float64(r.GoalDifference) },
	"points_per_game": func(r Record) float64 {
		if r.Matches == 0 {
			return 0
		}
		return round(float64(r.Points)/float64(r.Matches), 2)
	},
}

// RankTeams orders clubs by a metric. Goals conceded ranks fewest first.
func (s *Store) RankTeams(metric, competition string, season int, venue string, minMatches, limit int) (RankingAnswer, error) {
	value, ok := rankMetrics[metric]
	if !ok {
		return RankingAnswer{}, fmt.Errorf("cannot rank by %q; choose one of goals_for, goals_against, win_rate, points, wins, goal_difference, points_per_game", metric)
	}
	if venue == "" {
		venue = "all"
	}
	if minMatches <= 0 {
		minMatches = 1
	}
	if limit <= 0 {
		limit = 10
	}
	records := s.records(competition, season, venue)
	var entries []RankEntry
	for id, r := range records {
		if r.Matches < minMatches {
			continue
		}
		r.Team = s.Teams.Name(id)
		entries = append(entries, RankEntry{Team: r.Team, Value: value(*r), Record: *r})
	}
	ascending := metric == "goals_against"
	sort.Slice(entries, func(i, j int) bool {
		if entries[i].Value != entries[j].Value {
			return (entries[i].Value < entries[j].Value) == ascending
		}
		if entries[i].Matches != entries[j].Matches {
			return entries[i].Matches > entries[j].Matches
		}
		return entries[i].Team < entries[j].Team
	})
	if len(entries) > limit {
		entries = entries[:limit]
	}
	for i := range entries {
		entries[i].Position = i + 1
	}
	return RankingAnswer{Metric: metric, Competition: competition, Season: season, Venue: venue, MinMatches: minMatches, Ranking: entries}, nil
}

// records builds every club's record over the selected matches.
func (s *Store) records(competition string, season int, venue string) map[TeamID]*Record {
	out := map[TeamID]*Record{}
	get := func(id TeamID) *Record {
		if out[id] == nil {
			out[id] = &Record{}
		}
		return out[id]
	}
	for _, m := range s.selectMatches("", "", MatchQuery{Competition: competition, Season: season}) {
		if venue != "away" {
			get(m.Home).add(m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			get(m.Away).add(m.AwayGoals, m.HomeGoals)
		}
	}
	return out
}

type CompetitionPlayed struct {
	Competition string `json:"competition"`
	Matches     int    `json:"matches"`
	Seasons     []int  `json:"seasons"`
	Record
}

type TeamCompetitionsAnswer struct {
	Team         string              `json:"team"`
	Competitions []CompetitionPlayed `json:"competitions"`
}

func (s *Store) TeamCompetitions(team string) (TeamCompetitionsAnswer, error) {
	id, err := s.resolve(team)
	if err != nil {
		return TeamCompetitionsAnswer{}, err
	}
	ans := TeamCompetitionsAnswer{Team: s.Teams.Name(id), Competitions: []CompetitionPlayed{}}
	for _, c := range AllCompetitions {
		cp := CompetitionPlayed{Competition: c}
		seasons := map[int]bool{}
		for _, m := range s.byTeam[id] {
			if m.Competition == c {
				cp.add(goalsFor(m, id), goalsAgainst(m, id))
				seasons[m.Season] = true
			}
		}
		if cp.Record.Matches == 0 {
			continue
		}
		cp.Matches = cp.Record.Matches
		for y := range seasons {
			cp.Seasons = append(cp.Seasons, y)
		}
		sort.Ints(cp.Seasons)
		ans.Competitions = append(ans.Competitions, cp)
	}
	return ans, nil
}

type SquadSummary struct {
	Players        int      `json:"players"`
	AverageOverall float64  `json:"average_overall"`
	BestPlayer     string   `json:"best_player,omitempty"`
	TopPlayers     []Player `json:"top_players"`
	FIFAClub       string   `json:"fifa_club,omitempty"`
}

type TeamOverviewAnswer struct {
	Team          string              `json:"team"`
	Record        Record              `json:"record"`
	HomeRecord    Record              `json:"home_record"`
	AwayRecord    Record              `json:"away_record"`
	Competitions  []CompetitionPlayed `json:"competitions"`
	RecentMatches []MatchView         `json:"recent_matches"`
	Squad         SquadSummary        `json:"squad"`
}

// TeamOverview combines a club's results from the match data with its
// squad from the FIFA ratings.
func (s *Store) TeamOverview(team string) (TeamOverviewAnswer, error) {
	id, err := s.resolve(team)
	if err != nil {
		return TeamOverviewAnswer{}, err
	}
	ans := TeamOverviewAnswer{Team: s.Teams.Name(id)}
	ans.Record.Team = ans.Team
	for _, m := range s.byTeam[id] {
		gf, ga := goalsFor(m, id), goalsAgainst(m, id)
		ans.Record.add(gf, ga)
		if m.Home == id {
			ans.HomeRecord.add(gf, ga)
		} else {
			ans.AwayRecord.add(gf, ga)
		}
	}
	comps, _ := s.TeamCompetitions(team)
	ans.Competitions = comps.Competitions
	recent := append([]*Match(nil), s.byTeam[id]...)
	reverse(recent)
	if len(recent) > 5 {
		recent = recent[:5]
	}
	ans.RecentMatches = s.views(recent)

	var squad []*Player
	for _, p := range s.Players {
		if cid, ok := s.ClubTeam(p.Club); ok && cid == id {
			squad = append(squad, p)
			ans.Squad.FIFAClub = p.Club
		}
	}
	sortPlayers(squad)
	ans.Squad.Players = len(squad)
	ans.Squad.TopPlayers = []Player{}
	total := 0
	for i, p := range squad {
		total += p.Overall
		if i < 5 {
			ans.Squad.TopPlayers = append(ans.Squad.TopPlayers, *p)
		}
	}
	if len(squad) > 0 {
		ans.Squad.BestPlayer = squad[0].Name
		ans.Squad.AverageOverall = round(float64(total)/float64(len(squad)), 1)
	}
	return ans, nil
}

// ---- competitions --------------------------------------------------------------

type StandingRow struct {
	Position int `json:"position"`
	Played   int `json:"played"`
	Record
}

type StandingsAnswer struct {
	Competition string        `json:"competition"`
	Season      int           `json:"season"`
	Table       []StandingRow `json:"table"`
	Champion    string        `json:"champion"`
	Relegated   []string      `json:"relegated"`
	Matches     int           `json:"matches"`
}

// Standings calculates a league table from results: three points for a
// win, one for a draw; ties broken by wins, goal difference, goals scored.
// In the Série A the bottom four of a full table are relegated.
func (s *Store) Standings(competition string, season int) (StandingsAnswer, error) {
	if competition == "" {
		competition = SerieA
	}
	if season == 0 {
		season = s.latestSeason(competition)
	}
	ans := StandingsAnswer{Competition: competition, Season: season, Table: []StandingRow{}, Relegated: []string{}}
	ans.Matches = len(s.selectMatches("", "", MatchQuery{Competition: competition, Season: season}))
	if ans.Matches == 0 {
		return ans, fmt.Errorf("no %s results for %d in the data", competition, season)
	}
	for id, r := range s.records(competition, season, "all") {
		r.Team = s.Teams.Name(id)
		ans.Table = append(ans.Table, StandingRow{Played: r.Matches, Record: *r})
	}
	sort.Slice(ans.Table, func(i, j int) bool {
		a, b := ans.Table[i], ans.Table[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDifference != b.GoalDifference {
			return a.GoalDifference > b.GoalDifference
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	for i := range ans.Table {
		ans.Table[i].Position = i + 1
	}
	ans.Champion = ans.Table[0].Team
	if competition == SerieA && len(ans.Table) >= 8 {
		for _, r := range ans.Table[len(ans.Table)-4:] {
			ans.Relegated = append(ans.Relegated, r.Team)
		}
	}
	return ans, nil
}

func (s *Store) latestSeason(competition string) int {
	latest := 0
	for _, m := range s.Matches {
		if (competition == "" || m.Competition == competition) && m.Season > latest {
			latest = m.Season
		}
	}
	return latest
}

type Tie struct {
	TeamA      string      `json:"team_a"`
	TeamB      string      `json:"team_b"`
	TeamAGoals int         `json:"team_a_goals"`
	TeamBGoals int         `json:"team_b_goals"`
	Winner     string      `json:"winner"`
	Legs       []MatchView `json:"legs"`
}

type Stage struct {
	Stage string `json:"stage"`
	Ties  []Tie  `json:"ties"`
}

type BracketAnswer struct {
	Competition string  `json:"competition"`
	Season      int     `json:"season"`
	Stages      []Stage `json:"stages"`
}

var stageOrder = map[string]int{"round of 16": 100, "quarterfinals": 101, "semifinals": 102, "final": 103}

// Bracket groups a season's knockout matches into ties, aggregating the
// legs. A level aggregate has no winner in the data (decided on penalties
// or away goals).
func (s *Store) Bracket(competition string, season int) (BracketAnswer, error) {
	if competition == "" {
		competition = Libertadores
	}
	if season == 0 {
		season = s.latestSeason(competition)
	}
	ans := BracketAnswer{Competition: competition, Season: season, Stages: []Stage{}}
	byStage := map[string][]*Match{}
	for _, m := range s.selectMatches("", "", MatchQuery{Competition: competition, Season: season}) {
		if m.Stage == "" || m.Stage == "group stage" {
			continue
		}
		byStage[m.Stage] = append(byStage[m.Stage], m)
	}
	if len(byStage) == 0 {
		return ans, fmt.Errorf("no knockout matches for %s %d in the data", competition, season)
	}
	var names []string
	for n := range byStage {
		names = append(names, n)
	}
	sort.Slice(names, func(i, j int) bool { return stageRank(names[i]) < stageRank(names[j]) })
	for _, n := range names {
		st := Stage{Stage: n}
		ties := map[string]*Tie{}
		var order []string
		for _, m := range byStage[n] {
			a, b := s.Teams.Name(m.Home), s.Teams.Name(m.Away)
			key := pairKey(a, b)
			t := ties[key]
			if t == nil {
				t = &Tie{TeamA: a, TeamB: b}
				ties[key] = t
				order = append(order, key)
			}
			if t.TeamA == a {
				t.TeamAGoals += m.HomeGoals
				t.TeamBGoals += m.AwayGoals
			} else {
				t.TeamAGoals += m.AwayGoals
				t.TeamBGoals += m.HomeGoals
			}
			t.Legs = append(t.Legs, s.view(m))
		}
		for _, k := range order {
			t := ties[k]
			switch {
			case t.TeamAGoals > t.TeamBGoals:
				t.Winner = t.TeamA
			case t.TeamBGoals > t.TeamAGoals:
				t.Winner = t.TeamB
			}
			st.Ties = append(st.Ties, *t)
		}
		ans.Stages = append(ans.Stages, st)
	}
	return ans, nil
}

func stageRank(s string) int {
	if r, ok := stageOrder[s]; ok {
		return r
	}
	var n int
	fmt.Sscanf(s, "round %d", &n)
	return n
}

func pairKey(a, b string) string {
	if a > b {
		a, b = b, a
	}
	return a + "|" + b
}

// ---- statistics ------------------------------------------------------------------

type CompetitionStats struct {
	Competition          string  `json:"competition,omitempty"`
	Season               int     `json:"season,omitempty"`
	Matches              int     `json:"matches"`
	Goals                int     `json:"goals"`
	AverageGoalsPerMatch float64 `json:"average_goals_per_match"`
	HomeWins             int     `json:"home_wins"`
	Draws                int     `json:"draws"`
	AwayWins             int     `json:"away_wins"`
	HomeWinRate          float64 `json:"home_win_rate"`
	DrawRate             float64 `json:"draw_rate"`
	AwayWinRate          float64 `json:"away_win_rate"`
	Champion             string  `json:"champion,omitempty"`
	ChampionPoints       int     `json:"champion_points,omitempty"`
	TopScoringTeam       string  `json:"top_scoring_team,omitempty"`
	TopScoringTeamGoals  int     `json:"top_scoring_team_goals,omitempty"`
}

func (s *Store) CompetitionStats(competition string, season int) CompetitionStats {
	st := CompetitionStats{Competition: competition, Season: season}
	for _, m := range s.selectMatches("", "", MatchQuery{Competition: competition, Season: season}) {
		st.Matches++
		st.Goals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			st.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			st.AwayWins++
		default:
			st.Draws++
		}
	}
	if st.Matches > 0 {
		st.AverageGoalsPerMatch = round(float64(st.Goals)/float64(st.Matches), 2)
	}
	st.HomeWinRate = percent(st.HomeWins, st.Matches)
	st.DrawRate = percent(st.Draws, st.Matches)
	st.AwayWinRate = percent(st.AwayWins, st.Matches)
	return st
}

type SeasonComparison struct {
	Competition string             `json:"competition"`
	Seasons     []CompetitionStats `json:"seasons"`
}

func (s *Store) CompareSeasons(competition string, seasons []int) SeasonComparison {
	if competition == "" {
		competition = SerieA
	}
	ans := SeasonComparison{Competition: competition, Seasons: []CompetitionStats{}}
	for _, y := range seasons {
		st := s.CompetitionStats(competition, y)
		if table, err := s.Standings(competition, y); err == nil {
			st.Champion, st.ChampionPoints = table.Champion, table.Table[0].Points
			best := table.Table[0]
			for _, r := range table.Table {
				if r.GoalsFor > best.GoalsFor {
					best = r
				}
			}
			st.TopScoringTeam, st.TopScoringTeamGoals = best.Team, best.GoalsFor
		}
		ans.Seasons = append(ans.Seasons, st)
	}
	return ans
}

type BiggestWinsAnswer struct {
	Competition string      `json:"competition,omitempty"`
	Season      int         `json:"season,omitempty"`
	Team        string      `json:"team,omitempty"`
	Matches     []MatchView `json:"matches"`
}

func (s *Store) BiggestWins(competition string, season int, team string, limit int) (BiggestWinsAnswer, error) {
	ans := BiggestWinsAnswer{Competition: competition, Season: season}
	var id TeamID
	if team != "" {
		var err error
		if id, err = s.resolve(team); err != nil {
			return ans, err
		}
		ans.Team = s.Teams.Name(id)
	}
	if limit <= 0 {
		limit = 10
	}
	ms := s.selectMatches(id, "", MatchQuery{Competition: competition, Season: season})
	if id != "" {
		var won []*Match
		for _, m := range ms {
			if goalsFor(m, id) > goalsAgainst(m, id) {
				won = append(won, m)
			}
		}
		ms = won
	}
	ans.Matches = s.views(biggest(ms, limit))
	return ans, nil
}

func biggest(ms []*Match, limit int) []*Match {
	var wins []*Match
	for _, m := range ms {
		if m.HomeGoals != m.AwayGoals {
			wins = append(wins, m)
		}
	}
	margin := func(m *Match) int { return abs(m.HomeGoals - m.AwayGoals) }
	sort.SliceStable(wins, func(i, j int) bool {
		a, b := wins[i], wins[j]
		if margin(a) != margin(b) {
			return margin(a) > margin(b)
		}
		if a.HomeGoals+a.AwayGoals != b.HomeGoals+b.AwayGoals {
			return a.HomeGoals+a.AwayGoals > b.HomeGoals+b.AwayGoals
		}
		return a.Date.Before(b.Date)
	})
	if len(wins) > limit {
		wins = wins[:limit]
	}
	return wins
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}

// Rivalries are the traditional derbies of Brazilian football.
var Rivalries = []struct{ Name, A, B string }{
	{"Fla-Flu", "Flamengo", "Fluminense"},
	{"Clássico dos Milhões", "Flamengo", "Vasco da Gama"},
	{"Clássico da Rivalidade", "Flamengo", "Botafogo"},
	{"Clássico dos Gigantes", "Fluminense", "Vasco da Gama"},
	{"Clássico Vovô", "Botafogo", "Fluminense"},
	{"Clássico da Amizade", "Botafogo", "Vasco da Gama"},
	{"Derby Paulista", "Corinthians", "Palmeiras"},
	{"Choque-Rei", "Palmeiras", "São Paulo"},
	{"Majestoso", "Corinthians", "São Paulo"},
	{"San-São", "Santos", "São Paulo"},
	{"Clássico Alvinegro", "Santos", "Corinthians"},
	{"Clássico da Saudade", "Santos", "Palmeiras"},
	{"Grenal", "Grêmio", "Internacional"},
	{"Clássico Mineiro", "Atlético Mineiro", "Cruzeiro"},
	{"Ba-Vi", "Bahia", "Vitória"},
	{"Atletiba", "Athletico Paranaense", "Coritiba"},
	{"Clássico-Rei", "Ceará", "Fortaleza"},
	{"Clássico dos Clássicos", "Sport Recife", "Náutico"},
	{"Clássico das Multidões", "Sport Recife", "Santa Cruz"},
	{"Derby Campineiro", "Guarani", "Ponte Preta"},
	{"Superclásico", "Boca Juniors", "River Plate"},
}

type DerbyMatch struct {
	Derby string    `json:"derby"`
	Match MatchView `json:"match"`
}

type DerbiesAnswer struct {
	Season      int          `json:"season,omitempty"`
	Competition string       `json:"competition,omitempty"`
	Total       int          `json:"total"`
	Derbies     []DerbyMatch `json:"derbies"`
}

func (s *Store) Derbies(competition string, season int, team string) DerbiesAnswer {
	ans := DerbiesAnswer{Season: season, Competition: competition, Derbies: []DerbyMatch{}}
	names := map[string]string{}
	for _, r := range Rivalries {
		a, okA := s.Teams.Resolve(r.A)
		b, okB := s.Teams.Resolve(r.B)
		if okA && okB {
			names[pairKey(string(a), string(b))] = r.Name
		}
	}
	var only TeamID
	if team != "" {
		only, _ = s.Teams.Resolve(team)
	}
	for _, m := range s.selectMatches(only, "", MatchQuery{Competition: competition, Season: season}) {
		if name, ok := names[pairKey(string(m.Home), string(m.Away))]; ok {
			ans.Derbies = append(ans.Derbies, DerbyMatch{Derby: name, Match: s.view(m)})
		}
	}
	ans.Total = len(ans.Derbies)
	return ans
}

// ---- players -------------------------------------------------------------------------

type PlayerQuery struct {
	Name, Nationality, Club, Position string
	MinOverall, Limit                 int
}

type PlayersAnswer struct {
	Total       int      `json:"total"`
	Players     []Player `json:"players"`
	Suggestions []Player `json:"suggestions,omitempty"`
	Message     string   `json:"message,omitempty"`
}

var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"},
	"striker":    {"ST", "CF", "LS", "RS"},
	"winger":     {"LW", "RW", "LM", "RM"},
	"midfielder": {"CAM", "CM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"},
	"defender":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
}

var demonyms = map[string]string{
	"brazilian": "brazil", "argentine": "argentina", "argentinian": "argentina", "portuguese": "portugal",
	"uruguayan": "uruguay", "colombian": "colombia", "chilean": "chile", "paraguayan": "paraguay",
	"spanish": "spain", "french": "france", "german": "germany", "english": "england", "italian": "italy",
	"brasil": "brazil", "brasileiro": "brazil",
}

func (s *Store) SearchPlayers(q PlayerQuery) PlayersAnswer {
	ans := PlayersAnswer{Players: []Player{}}
	positions := map[string]bool{}
	if q.Position != "" {
		key := strings.TrimSuffix(Fold(q.Position), "s")
		if group, ok := positionGroups[key]; ok {
			for _, p := range group {
				positions[p] = true
			}
		} else {
			for _, p := range strings.FieldsFunc(strings.ToUpper(q.Position), func(r rune) bool { return r == ',' || r == ' ' || r == '/' }) {
				positions[p] = true
			}
		}
	}
	nationality := Fold(q.Nationality)
	if n, ok := demonyms[nationality]; ok {
		nationality = n
	}
	clubs := s.matchingClubs(q.Club)
	nameTokens := Tokens(q.Name)

	var found []*Player
	for _, p := range s.Players {
		if nationality != "" && Fold(p.Nationality) != nationality {
			continue
		}
		if q.Club != "" && !clubs[p.Club] {
			continue
		}
		if len(positions) > 0 && !positions[p.Position] {
			continue
		}
		if q.MinOverall > 0 && p.Overall < q.MinOverall {
			continue
		}
		if len(nameTokens) > 0 && !nameMatches(p.Name, q.Name, nameTokens) {
			continue
		}
		found = append(found, p)
	}
	sortPlayers(found)
	ans.Total = len(found)
	limit := q.Limit
	if limit <= 0 {
		limit = 25
	}
	for i, p := range found {
		if i >= limit {
			break
		}
		ans.Players = append(ans.Players, *p)
	}
	if len(found) == 0 && len(nameTokens) > 0 {
		ans.Suggestions = s.similarPlayers(nameTokens)
		ans.Message = fmt.Sprintf("no player called %q in the FIFA ratings", q.Name)
	}
	if q.Club != "" && len(clubs) == 0 {
		ans.Message = fmt.Sprintf("no club matching %q in the FIFA 19 ratings (most Brazilian clubs are not licensed there); "+
			"Brazilian clubs it does include: %s", q.Club, strings.Join(s.brazilianFIFAClubs(), ", "))
	}
	return ans
}

func nameMatches(name, query string, tokens []string) bool {
	if strings.Contains(Fold(name), Fold(query)) {
		return true
	}
	return containsWords(Tokens(name), tokens)
}

// similarPlayers suggests players who share words with the name asked for,
// preferring a shared surname, then higher ratings.
func (s *Store) similarPlayers(tokens []string) []Player {
	type scored struct {
		p     *Player
		score int
	}
	last := tokens[len(tokens)-1]
	var cands []scored
	for _, p := range s.Players {
		have := map[string]bool{}
		for _, t := range Tokens(p.Name) {
			have[t] = true
		}
		score := 0
		for _, t := range tokens {
			if len(t) >= 3 && have[t] {
				score++
			}
		}
		if score == 0 {
			continue
		}
		if have[last] {
			score++
		}
		cands = append(cands, scored{p, score})
	}
	sort.SliceStable(cands, func(i, j int) bool {
		if cands[i].score != cands[j].score {
			return cands[i].score > cands[j].score
		}
		return cands[i].p.Overall > cands[j].p.Overall
	})
	out := []Player{}
	for i := 0; i < len(cands) && i < 10; i++ {
		out = append(out, *cands[i].p)
	}
	return out
}

// matchingClubs finds the FIFA club names a fan's club name refers to:
// exact names first, then the same club under another name, then names
// containing the text.
func (s *Store) matchingClubs(query string) map[string]bool {
	out := map[string]bool{}
	if query == "" {
		return out
	}
	f := Fold(query)
	target, hasTarget := s.Teams.ResolveExact(query)
	for club := range s.clubTeams {
		if Fold(club) == f {
			out[club] = true
		}
		if id, ok := s.ClubTeam(club); hasTarget && ok && id == target {
			out[club] = true
		}
	}
	if len(out) > 0 {
		return out
	}
	for club := range s.clubTeams {
		if strings.Contains(Fold(club), f) {
			out[club] = true
		}
	}
	return out
}

func (s *Store) brazilianFIFAClubs() []string {
	var out []string
	for club := range s.clubTeams {
		if id, ok := s.ClubTeam(club); ok && s.IsBrazilianTopFlightClub(id) {
			out = append(out, club)
		}
	}
	sort.Strings(out)
	return out
}

func sortPlayers(ps []*Player) {
	sort.SliceStable(ps, func(i, j int) bool {
		if ps[i].Overall != ps[j].Overall {
			return ps[i].Overall > ps[j].Overall
		}
		if ps[i].Potential != ps[j].Potential {
			return ps[i].Potential > ps[j].Potential
		}
		return ps[i].Name < ps[j].Name
	})
}

type ClubPlayers struct {
	Club           string  `json:"club"`
	Players        int     `json:"players"`
	AverageOverall float64 `json:"average_overall"`
	BestPlayer     string  `json:"best_player"`
	BestOverall    int     `json:"best_overall"`
}

type ClubsAnswer struct {
	Nationality        string        `json:"nationality,omitempty"`
	BrazilianClubsOnly bool          `json:"brazilian_clubs_only"`
	Clubs              []ClubPlayers `json:"clubs"`
	TotalPlayers       int           `json:"total_players"`
	TotalClubs         int           `json:"total_clubs"`
}

// PlayersByClub counts players per club, optionally only at clubs that have
// played in the Brasileirão Série A (linking the FIFA ratings to the match
// data).
func (s *Store) PlayersByClub(nationality string, brazilianClubsOnly bool, limit int) ClubsAnswer {
	ans := ClubsAnswer{Nationality: nationality, BrazilianClubsOnly: brazilianClubsOnly, Clubs: []ClubPlayers{}}
	nat := Fold(nationality)
	if n, ok := demonyms[nat]; ok {
		nat = n
	}
	by := map[string][]*Player{}
	for _, p := range s.Players {
		if p.Club == "" || (nat != "" && Fold(p.Nationality) != nat) {
			continue
		}
		if brazilianClubsOnly {
			id, ok := s.ClubTeam(p.Club)
			if !ok || !s.IsBrazilianTopFlightClub(id) {
				continue
			}
		}
		by[p.Club] = append(by[p.Club], p)
	}
	for club, ps := range by {
		sortPlayers(ps)
		total := 0
		for _, p := range ps {
			total += p.Overall
		}
		ans.TotalPlayers += len(ps)
		ans.Clubs = append(ans.Clubs, ClubPlayers{Club: club, Players: len(ps),
			AverageOverall: round(float64(total)/float64(len(ps)), 1), BestPlayer: ps[0].Name, BestOverall: ps[0].Overall})
	}
	sort.Slice(ans.Clubs, func(i, j int) bool {
		a, b := ans.Clubs[i], ans.Clubs[j]
		if a.Players != b.Players {
			return a.Players > b.Players
		}
		if a.AverageOverall != b.AverageOverall {
			return a.AverageOverall > b.AverageOverall
		}
		return a.Club < b.Club
	})
	ans.TotalClubs = len(ans.Clubs)
	if limit > 0 && len(ans.Clubs) > limit {
		ans.Clubs = ans.Clubs[:limit]
	}
	return ans
}
