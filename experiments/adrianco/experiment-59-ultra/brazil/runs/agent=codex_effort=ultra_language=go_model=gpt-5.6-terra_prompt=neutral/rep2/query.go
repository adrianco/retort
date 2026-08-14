package main

import (
	"errors"
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
	"time"
)

var ErrUnsupported = errors.New("unsupported by the supplied datasets")

type MatchFilter struct {
	Team        string
	Opponent    string
	Competition string
	Source      string
	Venue       string
	Season      int
	DateFrom    string
	DateTo      string
	Round       string
	Stage       string
	Limit       int
	Offset      int
}

type MatchSearchResult struct {
	Matches []Match `json:"matches"`
	Total   int     `json:"total"`
	Limit   int     `json:"limit"`
	Offset  int     `json:"offset"`
}

type TeamStatsQuery struct {
	Team        string
	Competition string
	Source      string
	Season      int
	Venue       string
}

type TeamStatistics struct {
	Team           string   `json:"team"`
	Competition    string   `json:"competition,omitempty"`
	Season         int      `json:"season,omitempty"`
	Venue          string   `json:"venue"`
	Matches        int      `json:"matches"`
	Scheduled      int      `json:"scheduled_matches"`
	Wins           int      `json:"wins"`
	Draws          int      `json:"draws"`
	Losses         int      `json:"losses"`
	GoalsFor       int      `json:"goals_for"`
	GoalsAgainst   int      `json:"goals_against"`
	GoalDifference int      `json:"goal_difference"`
	Points         int      `json:"points"`
	WinRate        float64  `json:"win_rate"`
	Sources        []string `json:"sources"`
}

type HeadToHead struct {
	TeamA      string   `json:"team_a"`
	TeamB      string   `json:"team_b"`
	Matches    int      `json:"matches"`
	Scheduled  int      `json:"scheduled_matches"`
	TeamAWins  int      `json:"team_a_wins"`
	TeamBWins  int      `json:"team_b_wins"`
	Draws      int      `json:"draws"`
	TeamAGoals int      `json:"team_a_goals"`
	TeamBGoals int      `json:"team_b_goals"`
	Sources    []string `json:"sources"`
}

type TeamComparison struct {
	TeamA      TeamStatistics `json:"team_a_statistics"`
	TeamB      TeamStatistics `json:"team_b_statistics"`
	HeadToHead HeadToHead     `json:"head_to_head"`
}

type PlayerFilter struct {
	Name          string
	Nationality   string
	Club          string
	Position      string
	PositionGroup string
	MinOverall    int
	MaxOverall    int
	Sort          string
	Limit         int
	Offset        int
}

type PlayerSearchResult struct {
	Players []Player `json:"players"`
	Total   int      `json:"total"`
	Limit   int      `json:"limit"`
	Offset  int      `json:"offset"`
}

type Standing struct {
	Rank           int    `json:"rank"`
	Team           string `json:"team"`
	Played         int    `json:"played"`
	Wins           int    `json:"wins"`
	Draws          int    `json:"draws"`
	Losses         int    `json:"losses"`
	GoalsFor       int    `json:"goals_for"`
	GoalsAgainst   int    `json:"goals_against"`
	GoalDifference int    `json:"goal_difference"`
	Points         int    `json:"points"`
}

type StandingsResult struct {
	Competition string     `json:"competition"`
	Season      int        `json:"season"`
	Standings   []Standing `json:"standings"`
	Calculation string     `json:"calculation"`
	Sources     []string   `json:"sources"`
}

type CompetitionInfo struct {
	Competition string   `json:"competition"`
	Seasons     []int    `json:"seasons"`
	MatchRows   int      `json:"match_rows"`
	Sources     []string `json:"sources"`
}

type StatisticsQuery struct {
	Metric      string
	Competition string
	Source      string
	Season      int
	Team        string
	Opponent    string
	Limit       int
}

type SummaryStatistics struct {
	Matches              int     `json:"matches"`
	ScheduledMatches     int     `json:"scheduled_matches"`
	TotalGoals           int     `json:"total_goals"`
	AverageGoalsPerMatch float64 `json:"average_goals_per_match"`
	HomeWins             int     `json:"home_wins"`
	Draws                int     `json:"draws"`
	AwayWins             int     `json:"away_wins"`
	HomeWinRate          float64 `json:"home_win_rate"`
	DrawRate             float64 `json:"draw_rate"`
	AwayWinRate          float64 `json:"away_win_rate"`
}

type BiggestWin struct {
	Match          Match `json:"match"`
	GoalDifference int   `json:"goal_difference"`
}

type TeamGoals struct {
	Rank          int     `json:"rank"`
	Team          string  `json:"team"`
	Matches       int     `json:"matches"`
	Goals         int     `json:"goals"`
	GoalsPerMatch float64 `json:"goals_per_match"`
}

type SeasonSummary struct {
	Season               int     `json:"season"`
	Matches              int     `json:"matches"`
	TotalGoals           int     `json:"total_goals"`
	AverageGoalsPerMatch float64 `json:"average_goals_per_match"`
	HomeWinRate          float64 `json:"home_win_rate"`
}

func (s *Store) SearchMatches(filter MatchFilter) (MatchSearchResult, error) {
	matches, err := s.matchingMatches(filter)
	if err != nil {
		return MatchSearchResult{}, err
	}
	total := len(matches)
	limit, offset := normalizePage(filter.Limit, filter.Offset)
	matches = pageMatches(matches, limit, offset)
	return MatchSearchResult{Matches: matches, Total: total, Limit: limit, Offset: offset}, nil
}

func (s *Store) matchingMatches(filter MatchFilter) ([]Match, error) {
	venue := strings.ToLower(strings.TrimSpace(filter.Venue))
	if venue == "" {
		venue = "either"
	}
	if venue != "either" && venue != "home" && venue != "away" {
		return nil, fmt.Errorf("venue must be home, away, or either")
	}
	from, err := parseFilterDate(filter.DateFrom, false)
	if err != nil {
		return nil, fmt.Errorf("invalid date_from: %w", err)
	}
	to, err := parseFilterDate(filter.DateTo, true)
	if err != nil {
		return nil, fmt.Errorf("invalid date_to: %w", err)
	}
	if !from.IsZero() && !to.IsZero() && from.After(to) {
		return nil, fmt.Errorf("date_from must not be after date_to")
	}
	teamKey := normalizeTeam(filter.Team)
	opponentKey := normalizeTeam(filter.Opponent)
	result := make([]Match, 0)
	for _, match := range s.Matches {
		if !competitionMatches(match.Competition, filter.Competition) || !sourceMatches(match.SourceFile, filter.Source) {
			continue
		}
		if filter.Season != 0 && match.Season != filter.Season {
			continue
		}
		if !from.IsZero() && (match.PlayedAt.IsZero() || match.PlayedAt.Before(from)) {
			continue
		}
		if !to.IsZero() && (match.PlayedAt.IsZero() || match.PlayedAt.After(to)) {
			continue
		}
		if strings.TrimSpace(filter.Round) != "" && normalizeText(match.Round) != normalizeText(filter.Round) {
			continue
		}
		if strings.TrimSpace(filter.Stage) != "" && !strings.Contains(normalizeText(match.Stage), normalizeText(filter.Stage)) {
			continue
		}
		if !matchTeamsFilter(match, teamKey, opponentKey, venue) {
			continue
		}
		result = append(result, match)
	}
	sort.SliceStable(result, func(i, j int) bool {
		return result[i].PlayedAt.After(result[j].PlayedAt)
	})
	return result, nil
}

func matchTeamsFilter(match Match, teamKey, opponentKey, venue string) bool {
	if teamKey == "" && opponentKey == "" {
		return true
	}
	if teamKey == "" {
		return teamKeysMatch(match.HomeKey, opponentKey) || teamKeysMatch(match.AwayKey, opponentKey)
	}
	teamHome := teamKeysMatch(match.HomeKey, teamKey)
	teamAway := teamKeysMatch(match.AwayKey, teamKey)
	if venue == "home" && !teamHome {
		return false
	}
	if venue == "away" && !teamAway {
		return false
	}
	if !teamHome && !teamAway {
		return false
	}
	if opponentKey == "" {
		return true
	}
	if teamHome {
		return teamKeysMatch(match.AwayKey, opponentKey)
	}
	return teamKeysMatch(match.HomeKey, opponentKey)
}

func (s *Store) TeamStatistics(query TeamStatsQuery) (TeamStatistics, error) {
	if strings.TrimSpace(query.Team) == "" {
		return TeamStatistics{}, fmt.Errorf("team is required")
	}
	venue := strings.ToLower(strings.TrimSpace(query.Venue))
	if venue == "" {
		venue = "either"
	}
	matches, err := s.analyticsMatches(MatchFilter{
		Team: query.Team, Competition: query.Competition, Source: query.Source,
		Season: query.Season, Venue: venue, Limit: 500,
	})
	if err != nil {
		return TeamStatistics{}, err
	}
	teamKey := normalizeTeam(query.Team)
	result := TeamStatistics{
		Team:        displayTeam(query.Team),
		Competition: canonicalCompetition(query.Competition),
		Season:      query.Season,
		Venue:       venue,
		Sources:     uniqueSources(matches),
	}
	if strings.TrimSpace(query.Competition) == "" {
		result.Competition = ""
	}
	for _, match := range matches {
		if !match.HasResult() {
			result.Scheduled++
			continue
		}
		isHome := teamKeysMatch(match.HomeKey, teamKey)
		goalsFor, goalsAgainst := *match.AwayGoals, *match.HomeGoals
		if isHome {
			goalsFor, goalsAgainst = *match.HomeGoals, *match.AwayGoals
		}
		result.Matches++
		result.GoalsFor += goalsFor
		result.GoalsAgainst += goalsAgainst
		switch {
		case goalsFor > goalsAgainst:
			result.Wins++
			result.Points += 3
		case goalsFor == goalsAgainst:
			result.Draws++
			result.Points++
		default:
			result.Losses++
		}
	}
	result.GoalDifference = result.GoalsFor - result.GoalsAgainst
	if result.Matches > 0 {
		result.WinRate = round(float64(result.Wins) / float64(result.Matches))
	}
	return result, nil
}

func (s *Store) HeadToHead(teamA, teamB, competition, source string, season int) (HeadToHead, error) {
	if strings.TrimSpace(teamA) == "" || strings.TrimSpace(teamB) == "" {
		return HeadToHead{}, fmt.Errorf("team_a and team_b are required")
	}
	matches, err := s.analyticsMatches(MatchFilter{
		Team: teamA, Opponent: teamB, Competition: competition, Source: source, Season: season, Limit: 500,
	})
	if err != nil {
		return HeadToHead{}, err
	}
	keyA := normalizeTeam(teamA)
	result := HeadToHead{TeamA: displayTeam(teamA), TeamB: displayTeam(teamB), Sources: uniqueSources(matches)}
	for _, match := range matches {
		if !match.HasResult() {
			result.Scheduled++
			continue
		}
		result.Matches++
		aHome := teamKeysMatch(match.HomeKey, keyA)
		aGoals, bGoals := *match.AwayGoals, *match.HomeGoals
		if aHome {
			aGoals, bGoals = *match.HomeGoals, *match.AwayGoals
		}
		result.TeamAGoals += aGoals
		result.TeamBGoals += bGoals
		switch {
		case aGoals > bGoals:
			result.TeamAWins++
		case bGoals > aGoals:
			result.TeamBWins++
		default:
			result.Draws++
		}
	}
	return result, nil
}

func (s *Store) CompareTeams(teamA, teamB, competition, source string, season int) (TeamComparison, error) {
	statsA, err := s.TeamStatistics(TeamStatsQuery{Team: teamA, Competition: competition, Source: source, Season: season})
	if err != nil {
		return TeamComparison{}, err
	}
	statsB, err := s.TeamStatistics(TeamStatsQuery{Team: teamB, Competition: competition, Source: source, Season: season})
	if err != nil {
		return TeamComparison{}, err
	}
	head, err := s.HeadToHead(teamA, teamB, competition, source, season)
	if err != nil {
		return TeamComparison{}, err
	}
	return TeamComparison{TeamA: statsA, TeamB: statsB, HeadToHead: head}, nil
}

func (s *Store) SearchPlayers(filter PlayerFilter) (PlayerSearchResult, error) {
	if filter.MinOverall < 0 || filter.MaxOverall < 0 {
		return PlayerSearchResult{}, fmt.Errorf("rating filters must be positive")
	}
	if filter.MaxOverall > 0 && filter.MinOverall > filter.MaxOverall {
		return PlayerSearchResult{}, fmt.Errorf("min_overall must not exceed max_overall")
	}
	name, nationality, club, position, positionGroup := normalizeText(filter.Name), normalizeText(filter.Nationality), normalizeText(filter.Club), normalizeText(filter.Position), normalizeText(filter.PositionGroup)
	if positionGroup != "" && !isKnownPositionGroup(positionGroup) {
		return PlayerSearchResult{}, fmt.Errorf("position_group must be forwards, midfielders, defenders, or goalkeepers")
	}
	players := make([]Player, 0)
	for _, player := range s.Players {
		if name != "" && !strings.Contains(normalizeText(player.Name), name) {
			continue
		}
		if nationality != "" && !strings.Contains(normalizeText(player.Nationality), nationality) {
			continue
		}
		if club != "" && !playerClubMatches(player.Club, club) {
			continue
		}
		if position != "" && !strings.Contains(normalizeText(player.Position), position) {
			continue
		}
		if positionGroup != "" && !positionInGroup(player.Position, positionGroup) {
			continue
		}
		if filter.MinOverall > 0 && player.Overall < filter.MinOverall {
			continue
		}
		if filter.MaxOverall > 0 && player.Overall > filter.MaxOverall {
			continue
		}
		players = append(players, player)
	}
	sortOrder := strings.ToLower(strings.TrimSpace(filter.Sort))
	if sortOrder == "" || sortOrder == "overall_desc" {
		sort.SliceStable(players, func(i, j int) bool {
			if players[i].Overall != players[j].Overall {
				return players[i].Overall > players[j].Overall
			}
			return normalizeText(players[i].Name) < normalizeText(players[j].Name)
		})
	} else if sortOrder == "name_asc" {
		sort.SliceStable(players, func(i, j int) bool { return normalizeText(players[i].Name) < normalizeText(players[j].Name) })
	} else {
		return PlayerSearchResult{}, fmt.Errorf("sort must be overall_desc or name_asc")
	}
	total := len(players)
	limit, offset := normalizePage(filter.Limit, filter.Offset)
	if offset >= len(players) {
		players = []Player{}
	} else {
		end := offset + limit
		if end > len(players) {
			end = len(players)
		}
		players = players[offset:end]
	}
	return PlayerSearchResult{Players: players, Total: total, Limit: limit, Offset: offset}, nil
}

func playerClubMatches(club, normalizedNeedle string) bool {
	clubKey := normalizeText(club)
	if strings.Contains(clubKey, normalizedNeedle) {
		return true
	}
	return teamKeysMatch(normalizeTeam(club), normalizeTeam(normalizedNeedle))
}

func isKnownPositionGroup(group string) bool {
	return group == "forward" || group == "forwards" || group == "midfielder" || group == "midfielders" || group == "defender" || group == "defenders" || group == "goalkeeper" || group == "goalkeepers"
}

func positionInGroup(position, group string) bool {
	position = strings.ToUpper(strings.TrimSpace(position))
	switch group {
	case "forward", "forwards":
		return map[string]bool{"ST": true, "CF": true, "LF": true, "RF": true, "LW": true, "RW": true}[position]
	case "midfielder", "midfielders":
		return map[string]bool{"CAM": true, "CM": true, "CDM": true, "LM": true, "RM": true}[position]
	case "defender", "defenders":
		return map[string]bool{"CB": true, "LCB": true, "RCB": true, "LB": true, "RB": true, "LWB": true, "RWB": true}[position]
	case "goalkeeper", "goalkeepers":
		return position == "GK"
	default:
		return false
	}
}

func (s *Store) Standings(competition string, season int, source string) (StandingsResult, error) {
	if season == 0 {
		return StandingsResult{}, fmt.Errorf("season is required")
	}
	canonical := canonicalCompetition(competition)
	if canonical != "Brasileirão Série A" && canonical != "Brasileirão Série B" && canonical != "Brasileirão Série C" {
		return StandingsResult{}, fmt.Errorf("%w: standings are only calculated for league competitions", ErrUnsupported)
	}
	matches, err := s.analyticsMatches(MatchFilter{Competition: canonical, Source: source, Season: season, Limit: 1000})
	if err != nil {
		return StandingsResult{}, err
	}
	byTeam := make(map[string]*Standing)
	for _, match := range matches {
		if !match.HasResult() {
			continue
		}
		home := standingFor(byTeam, match.HomeKey, match.HomeTeam)
		away := standingFor(byTeam, match.AwayKey, match.AwayTeam)
		home.Played++
		away.Played++
		home.GoalsFor += *match.HomeGoals
		home.GoalsAgainst += *match.AwayGoals
		away.GoalsFor += *match.AwayGoals
		away.GoalsAgainst += *match.HomeGoals
		switch {
		case *match.HomeGoals > *match.AwayGoals:
			home.Wins++
			home.Points += 3
			away.Losses++
		case *match.HomeGoals < *match.AwayGoals:
			away.Wins++
			away.Points += 3
			home.Losses++
		default:
			home.Draws++
			home.Points++
			away.Draws++
			away.Points++
		}
	}
	standings := make([]Standing, 0, len(byTeam))
	for _, row := range byTeam {
		row.GoalDifference = row.GoalsFor - row.GoalsAgainst
		standings = append(standings, *row)
	}
	sort.SliceStable(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].GoalDifference != standings[j].GoalDifference {
			return standings[i].GoalDifference > standings[j].GoalDifference
		}
		if standings[i].GoalsFor != standings[j].GoalsFor {
			return standings[i].GoalsFor > standings[j].GoalsFor
		}
		if standings[i].Wins != standings[j].Wins {
			return standings[i].Wins > standings[j].Wins
		}
		return normalizeText(standings[i].Team) < normalizeText(standings[j].Team)
	})
	for i := range standings {
		standings[i].Rank = i + 1
	}
	return StandingsResult{
		Competition: canonical, Season: season, Standings: standings, Sources: uniqueSources(matches),
		Calculation: "Calculated from deduplicated completed rows: 3 points for a win, 1 for a draw; ties sort by points, goal difference, goals scored, wins, then team name.",
	}, nil
}

func standingFor(rows map[string]*Standing, key, display string) *Standing {
	if row, ok := rows[key]; ok {
		return row
	}
	row := &Standing{Team: display}
	rows[key] = row
	return row
}

func (s *Store) ListCompetitions() []CompetitionInfo {
	type accumulator struct {
		seasons map[int]struct{}
		sources map[string]struct{}
		count   int
	}
	byCompetition := make(map[string]*accumulator)
	for _, match := range s.Matches {
		row := byCompetition[match.Competition]
		if row == nil {
			row = &accumulator{seasons: make(map[int]struct{}), sources: make(map[string]struct{})}
			byCompetition[match.Competition] = row
		}
		row.count++
		if match.Season != 0 {
			row.seasons[match.Season] = struct{}{}
		}
		row.sources[match.SourceFile] = struct{}{}
	}
	result := make([]CompetitionInfo, 0, len(byCompetition))
	for competition, row := range byCompetition {
		seasons := make([]int, 0, len(row.seasons))
		for season := range row.seasons {
			seasons = append(seasons, season)
		}
		sort.Ints(seasons)
		sources := make([]string, 0, len(row.sources))
		for source := range row.sources {
			sources = append(sources, source)
		}
		sort.Strings(sources)
		result = append(result, CompetitionInfo{Competition: competition, Seasons: seasons, MatchRows: row.count, Sources: sources})
	}
	sort.Slice(result, func(i, j int) bool { return result[i].Competition < result[j].Competition })
	return result
}

func (s *Store) Analyze(query StatisticsQuery) (any, error) {
	metric := normalizeText(query.Metric)
	if metric == "" || metric == "summary" || metric == "average goals" || metric == "average goals per match" || metric == "home away rates" {
		matches, err := s.analyticsMatches(MatchFilter{Team: query.Team, Opponent: query.Opponent, Competition: query.Competition, Source: query.Source, Season: query.Season, Limit: 1000})
		if err != nil {
			return nil, err
		}
		return summarize(matches), nil
	}
	if metric == "head to head" || metric == "head_to_head" {
		return s.HeadToHead(query.Team, query.Opponent, query.Competition, query.Source, query.Season)
	}
	if metric == "biggest wins" || metric == "biggest_wins" {
		matches, err := s.analyticsMatches(MatchFilter{Team: query.Team, Competition: query.Competition, Source: query.Source, Season: query.Season, Limit: 1000})
		if err != nil {
			return nil, err
		}
		return biggestWins(matches, query.Limit), nil
	}
	if metric == "top scoring teams" || metric == "top_scoring_teams" || metric == "most goals" || metric == "most_goals" {
		return s.TopScoringTeams(query.Competition, query.Source, query.Season, query.Limit)
	}
	if metric == "relegation candidates" || metric == "relegation_candidates" || metric == "relegated teams" {
		competition := query.Competition
		if strings.TrimSpace(competition) == "" {
			competition = "Brasileirão"
		}
		standings, err := s.Standings(competition, query.Season, query.Source)
		if err != nil {
			return nil, err
		}
		start := len(standings.Standings) - 4
		if start < 0 {
			start = 0
		}
		return map[string]any{
			"derived": true,
			"teams":   standings.Standings[start:],
			"note":    "These are the bottom four by the documented calculated table; the source data does not explicitly label relegation.",
		}, nil
	}
	if metric == "best home record" || metric == "best_home_record" || metric == "best away record" || metric == "best_away_record" {
		venue := "home"
		if strings.Contains(metric, "away") {
			venue = "away"
		}
		return s.bestVenueRecords(query, venue)
	}
	return nil, fmt.Errorf("unknown metric %q; use summary, head_to_head, biggest_wins, top_scoring_teams, best_home_record, best_away_record, or relegation_candidates", query.Metric)
}

func (s *Store) TopScoringTeams(competition, source string, season, requestedLimit int) ([]TeamGoals, error) {
	matches, err := s.analyticsMatches(MatchFilter{Competition: competition, Source: source, Season: season, Limit: 1000})
	if err != nil {
		return nil, err
	}
	type total struct {
		display string
		matches int
		goals   int
	}
	byTeam := make(map[string]*total)
	for _, match := range matches {
		if !match.HasResult() {
			continue
		}
		home := byTeam[match.HomeKey]
		if home == nil {
			home = &total{display: match.HomeTeam}
			byTeam[match.HomeKey] = home
		}
		away := byTeam[match.AwayKey]
		if away == nil {
			away = &total{display: match.AwayTeam}
			byTeam[match.AwayKey] = away
		}
		home.matches++
		home.goals += *match.HomeGoals
		away.matches++
		away.goals += *match.AwayGoals
	}
	result := make([]TeamGoals, 0, len(byTeam))
	for _, value := range byTeam {
		row := TeamGoals{Team: value.display, Matches: value.matches, Goals: value.goals}
		if row.Matches > 0 {
			row.GoalsPerMatch = round(float64(row.Goals) / float64(row.Matches))
		}
		result = append(result, row)
	}
	sort.SliceStable(result, func(i, j int) bool {
		if result[i].Goals != result[j].Goals {
			return result[i].Goals > result[j].Goals
		}
		if result[i].GoalsPerMatch != result[j].GoalsPerMatch {
			return result[i].GoalsPerMatch > result[j].GoalsPerMatch
		}
		return normalizeText(result[i].Team) < normalizeText(result[j].Team)
	})
	for i := range result {
		result[i].Rank = i + 1
	}
	limit, _ := normalizePage(requestedLimit, 0)
	if len(result) > limit {
		result = result[:limit]
	}
	return result, nil
}

func (s *Store) bestVenueRecords(query StatisticsQuery, venue string) ([]TeamStatistics, error) {
	matches, err := s.analyticsMatches(MatchFilter{Competition: query.Competition, Source: query.Source, Season: query.Season, Limit: 1000})
	if err != nil {
		return nil, err
	}
	keys := make(map[string]string)
	for _, match := range matches {
		if venue == "home" {
			keys[match.HomeKey] = match.HomeTeam
		} else {
			keys[match.AwayKey] = match.AwayTeam
		}
	}
	rows := make([]TeamStatistics, 0, len(keys))
	for key, display := range keys {
		row, err := s.TeamStatistics(TeamStatsQuery{Team: key, Competition: query.Competition, Source: query.Source, Season: query.Season, Venue: venue})
		if err != nil {
			return nil, err
		}
		row.Team = display
		if row.Matches > 0 {
			rows = append(rows, row)
		}
	}
	sort.SliceStable(rows, func(i, j int) bool {
		if rows[i].WinRate != rows[j].WinRate {
			return rows[i].WinRate > rows[j].WinRate
		}
		if rows[i].Points != rows[j].Points {
			return rows[i].Points > rows[j].Points
		}
		if rows[i].GoalDifference != rows[j].GoalDifference {
			return rows[i].GoalDifference > rows[j].GoalDifference
		}
		return normalizeText(rows[i].Team) < normalizeText(rows[j].Team)
	})
	limit, _ := normalizePage(query.Limit, 0)
	if len(rows) > limit {
		rows = rows[:limit]
	}
	return rows, nil
}

func (s *Store) CompareSeasons(competition, source string, seasons ...int) ([]SeasonSummary, error) {
	if len(seasons) < 2 {
		return nil, fmt.Errorf("at least two seasons are required")
	}
	result := make([]SeasonSummary, 0, len(seasons))
	for _, season := range seasons {
		matches, err := s.analyticsMatches(MatchFilter{Competition: competition, Source: source, Season: season, Limit: 1000})
		if err != nil {
			return nil, err
		}
		summary := summarize(matches)
		result = append(result, SeasonSummary{Season: season, Matches: summary.Matches, TotalGoals: summary.TotalGoals, AverageGoalsPerMatch: summary.AverageGoalsPerMatch, HomeWinRate: summary.HomeWinRate})
	}
	return result, nil
}

func (s *Store) TeamCompetitions(team string) ([]CompetitionInfo, error) {
	if strings.TrimSpace(team) == "" {
		return nil, fmt.Errorf("team is required")
	}
	matches, err := s.matchingMatches(MatchFilter{Team: team, Limit: 1000})
	if err != nil {
		return nil, err
	}
	byCompetition := make(map[string][]Match)
	for _, match := range matches {
		byCompetition[match.Competition] = append(byCompetition[match.Competition], match)
	}
	result := make([]CompetitionInfo, 0, len(byCompetition))
	for competition, group := range byCompetition {
		seasons := make(map[int]struct{})
		for _, match := range group {
			if match.Season != 0 {
				seasons[match.Season] = struct{}{}
			}
		}
		values := make([]int, 0, len(seasons))
		for season := range seasons {
			values = append(values, season)
		}
		sort.Ints(values)
		result = append(result, CompetitionInfo{Competition: competition, Seasons: values, MatchRows: len(group), Sources: uniqueSources(group)})
	}
	sort.Slice(result, func(i, j int) bool { return result[i].Competition < result[j].Competition })
	return result, nil
}

func (s *Store) Derbies(season int, limit int) ([]Match, error) {
	matches, err := s.analyticsMatches(MatchFilter{Season: season, Limit: 1000})
	if err != nil {
		return nil, err
	}
	result := make([]Match, 0)
	for _, match := range matches {
		if _, ok := knownRivalries[pairKey(match.HomeKey, match.AwayKey)]; ok {
			result = append(result, match)
		}
	}
	limit, _ = normalizePage(limit, 0)
	if len(result) > limit {
		result = result[:limit]
	}
	return result, nil
}

var knownRivalries = func() map[string]struct{} {
	pairs := [][2]string{
		{"flamengo", "fluminense"}, {"flamengo", "vasco da gama"}, {"flamengo", "botafogo"},
		{"fluminense", "vasco da gama"}, {"fluminense", "botafogo"}, {"vasco da gama", "botafogo"},
		{"corinthians", "palmeiras"}, {"corinthians", "sao paulo"}, {"corinthians", "santos"},
		{"palmeiras", "sao paulo"}, {"palmeiras", "santos"}, {"sao paulo", "santos"},
		{"gremio", "internacional"}, {"atletico mineiro", "cruzeiro"}, {"athletico paranaense", "coritiba"}, {"bahia", "vitoria"},
	}
	result := make(map[string]struct{}, len(pairs))
	for _, pair := range pairs {
		result[pairKey(pair[0], pair[1])] = struct{}{}
	}
	return result
}()

func pairKey(a, b string) string {
	if a < b {
		return a + "|" + b
	}
	return b + "|" + a
}

func (s *Store) analyticsMatches(filter MatchFilter) ([]Match, error) {
	matches, err := s.matchingMatches(filter)
	if err != nil {
		return nil, err
	}
	// Match search deliberately keeps each source row so callers can inspect
	// provenance. Analytics instead operates on fixtures. The three league
	// sources describe many of the same fixtures, but disagree by a calendar
	// day when one records local kick-off and another records UTC. Group by the
	// stable fixture identity, then merge records whose calendar dates differ by
	// at most one day. Scores are not part of the identity: a more authoritative
	// source wins a discrepancy rather than allowing it to double-count a game.
	//
	// The per-fixture slices remain tiny (a home/away pairing normally occurs
	// once in a league season), avoiding an O(n²) comparison across all rows.
	selected := make([]Match, 0, len(matches))
	byFixture := make(map[string][]int, len(matches))
	for _, match := range matches {
		key := analyticsFixtureKey(match)
		if key == "" {
			// A row without a usable date cannot safely be reconciled with a
			// different source, so retain its source-level provenance.
			selected = append(selected, match)
			continue
		}
		duplicate := -1
		for _, index := range byFixture[key] {
			if sameFixtureDate(selected[index], match) {
				duplicate = index
				break
			}
		}
		if duplicate < 0 {
			selected = append(selected, match)
			byFixture[key] = append(byFixture[key], len(selected)-1)
			continue
		}
		if preferAnalyticsMatch(match, selected[duplicate]) {
			selected[duplicate] = match
		}
	}
	result := selected
	sort.SliceStable(result, func(i, j int) bool { return result[i].PlayedAt.After(result[j].PlayedAt) })
	return result, nil
}

func analyticsFixtureKey(match Match) string {
	if match.PlayedAt.IsZero() || match.HomeKey == "" || match.AwayKey == "" {
		return ""
	}
	return strings.Join([]string{
		match.Competition, strconv.Itoa(match.Season), match.HomeKey, match.AwayKey,
	}, "|")
}

func sameFixtureDate(a, b Match) bool {
	if a.PlayedAt.IsZero() || b.PlayedAt.IsZero() {
		return false
	}
	aDay := time.Date(a.PlayedAt.Year(), a.PlayedAt.Month(), a.PlayedAt.Day(), 0, 0, 0, 0, time.UTC)
	bDay := time.Date(b.PlayedAt.Year(), b.PlayedAt.Month(), b.PlayedAt.Day(), 0, 0, 0, 0, time.UTC)
	days := aDay.Sub(bDay) / (24 * time.Hour)
	return days >= -1 && days <= 1
}

func preferAnalyticsMatch(candidate, current Match) bool {
	candidatePriority, currentPriority := sourcePriority(candidate.SourceFile), sourcePriority(current.SourceFile)
	if candidatePriority != currentPriority {
		return candidatePriority < currentPriority
	}
	if candidate.HasResult() != current.HasResult() {
		return candidate.HasResult()
	}
	// Keep tie-breaking deterministic even when the same source supplies two
	// equivalent rows. IDs include the source row number and are stable.
	return candidate.ID < current.ID
}

func sourcePriority(source string) int {
	switch source {
	case brasileiraoFile, cupFile, libertadoresFile:
		return 1
	case historicalFile:
		return 2
	case extendedFile:
		return 3
	default:
		return 4
	}
}

func summarize(matches []Match) SummaryStatistics {
	result := SummaryStatistics{}
	for _, match := range matches {
		if !match.HasResult() {
			result.ScheduledMatches++
			continue
		}
		result.Matches++
		result.TotalGoals += *match.HomeGoals + *match.AwayGoals
		switch {
		case *match.HomeGoals > *match.AwayGoals:
			result.HomeWins++
		case *match.HomeGoals < *match.AwayGoals:
			result.AwayWins++
		default:
			result.Draws++
		}
	}
	if result.Matches > 0 {
		matchesCount := float64(result.Matches)
		result.AverageGoalsPerMatch = round(float64(result.TotalGoals) / matchesCount)
		result.HomeWinRate = round(float64(result.HomeWins) / matchesCount)
		result.DrawRate = round(float64(result.Draws) / matchesCount)
		result.AwayWinRate = round(float64(result.AwayWins) / matchesCount)
	}
	return result
}

func biggestWins(matches []Match, requestedLimit int) []BiggestWin {
	result := make([]BiggestWin, 0)
	for _, match := range matches {
		if !match.HasResult() {
			continue
		}
		difference := int(math.Abs(float64(*match.HomeGoals - *match.AwayGoals)))
		result = append(result, BiggestWin{Match: match, GoalDifference: difference})
	}
	sort.SliceStable(result, func(i, j int) bool {
		if result[i].GoalDifference != result[j].GoalDifference {
			return result[i].GoalDifference > result[j].GoalDifference
		}
		return result[i].Match.PlayedAt.After(result[j].Match.PlayedAt)
	})
	limit, _ := normalizePage(requestedLimit, 0)
	if len(result) > limit {
		result = result[:limit]
	}
	return result
}

func parseFilterDate(value string, endOfDay bool) (time.Time, error) {
	value = strings.TrimSpace(value)
	if value == "" {
		return time.Time{}, nil
	}
	parsed, ok := parseMatchDate(value, "")
	if !ok {
		return time.Time{}, fmt.Errorf("expected YYYY-MM-DD, timestamp, or DD/MM/YYYY")
	}
	if endOfDay && len(value) == len("2006-01-02") {
		parsed = parsed.Add(24*time.Hour - time.Nanosecond)
	}
	return parsed, nil
}

func sourceMatches(actual, requested string) bool {
	if strings.TrimSpace(requested) == "" {
		return true
	}
	key := normalizeText(requested)
	if normalizeText(actual) == key {
		return true
	}
	switch key {
	case "brasileirao", "brasileirao matches":
		return actual == brasileiraoFile
	case "cup", "copa do brasil", "brazilian cup":
		return actual == cupFile
	case "libertadores":
		return actual == libertadoresFile
	case "extended", "br football", "br football dataset":
		return actual == extendedFile
	case "historical", "historical brasileirao":
		return actual == historicalFile
	case "fifa", "players":
		return actual == playersFile
	default:
		return strings.Contains(normalizeText(actual), key)
	}
}

func uniqueSources(matches []Match) []string {
	set := make(map[string]struct{})
	for _, match := range matches {
		set[match.SourceFile] = struct{}{}
	}
	result := make([]string, 0, len(set))
	for source := range set {
		result = append(result, source)
	}
	sort.Strings(result)
	return result
}

func normalizePage(limit, offset int) (int, int) {
	if limit <= 0 {
		limit = 50
	}
	if limit > 500 {
		limit = 500
	}
	if offset < 0 {
		offset = 0
	}
	return limit, offset
}

func pageMatches(matches []Match, limit, offset int) []Match {
	if offset >= len(matches) {
		return []Match{}
	}
	end := offset + limit
	if end > len(matches) {
		end = len(matches)
	}
	return matches[offset:end]
}

func round(value float64) float64 { return math.Round(value*10000) / 10000 }
