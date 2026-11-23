package main

import (
	"cmp"
	"fmt"
	"slices"
	"strings"
)

type Filter struct {
	Team        string `json:"team"`
	Opponent    string `json:"opponent"`
	Side        string `json:"side"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	SeasonFrom  int    `json:"season_from"`
	SeasonTo    int    `json:"season_to"`
	DateFrom    string `json:"date_from"`
	DateTo      string `json:"date_to"`
	Round       string `json:"round"`
	Stage       string `json:"stage"`
	Source      string `json:"source"`
	Derby       bool   `json:"derby"`
	Status      string `json:"status"`
}

func (s *Store) findMatches(q Filter) ([]Match, error) {
	team, opponent := words(clubName(q.Team)), words(clubName(q.Opponent))
	if q.Opponent != "" && team == "" {
		return nil, fmt.Errorf("opponent requires team")
	}
	if q.Side != "" && q.Side != "either" && (team == "" || (q.Side != "home" && q.Side != "away")) {
		return nil, fmt.Errorf("side must be either, home, or away; home and away require team")
	}
	if q.Status != "" && q.Status != "played" && q.Status != "unscored" {
		return nil, fmt.Errorf("status must be played or unscored")
	}
	if q.Season < 0 || q.SeasonFrom < 0 || q.SeasonTo < 0 ||
		(q.SeasonTo != 0 && q.SeasonFrom > q.SeasonTo) ||
		(q.Season != 0 && (q.SeasonFrom != 0 || q.SeasonTo != 0)) {
		return nil, fmt.Errorf("specify a positive season or an ordered season range")
	}
	for _, bound := range []*string{&q.DateFrom, &q.DateTo} {
		if *bound != "" {
			date, err := parseDate(*bound)
			if err != nil {
				return nil, err
			}
			*bound = date.Format("2006-01-02")
		}
	}
	if q.DateTo != "" && q.DateFrom > q.DateTo {
		return nil, fmt.Errorf("date_from must be on or before date_to")
	}

	input := s.matches
	if q.Source != "" {
		var ok bool
		input, ok = s.bySource[q.Source]
		if !ok {
			return nil, fmt.Errorf("unknown match source %q", q.Source)
		}
	}
	competition := competitionName(q.Competition)
	stage := stageName(q.Stage)
	result := make([]Match, 0)
	for _, m := range input {
		if (competition != "" && !strings.EqualFold(m.Competition, competition)) ||
			(q.Season != 0 && m.Season != q.Season) ||
			(q.SeasonFrom != 0 && m.Season < q.SeasonFrom) ||
			(q.SeasonTo != 0 && (m.Season == 0 || m.Season > q.SeasonTo)) ||
			(q.DateFrom != "" && m.Date < q.DateFrom) ||
			(q.DateTo != "" && (m.Date == "" || m.Date > q.DateTo)) ||
			(q.Round != "" && !strings.EqualFold(m.Round, q.Round)) ||
			(stage != "" && !matchesStage(m.Stage, stage)) ||
			(q.Status == "played" && !m.played()) || (q.Status == "unscored" && m.played()) {
			continue
		}
		if team != "" {
			home := q.Side != "away" && m.homeKey == team && (opponent == "" || m.awayKey == opponent)
			away := q.Side != "home" && m.awayKey == team && (opponent == "" || m.homeKey == opponent)
			if !home && !away {
				continue
			}
		}
		if !q.Derby || derby(m) {
			result = append(result, m)
		}
	}
	return result, nil
}

type Record struct {
	Played       int     `json:"played"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	WinRate      float64 `json:"win_rate_percent"`
}

func (r *Record) add(scored, conceded int) {
	r.Played++
	r.GoalsFor += scored
	r.GoalsAgainst += conceded
	switch cmp.Compare(scored, conceded) {
	case 1:
		r.Wins++
	case 0:
		r.Draws++
	case -1:
		r.Losses++
	}
	r.WinRate = percentage(r.Wins, r.Played)
}

func percentage(n, total int) float64 {
	if total == 0 {
		return 0
	}
	return 100 * float64(n) / float64(total)
}

type TeamRecord struct {
	Team string `json:"team"`
	Record
	Home Record `json:"home"`
	Away Record `json:"away"`
}

func (r *TeamRecord) add(m Match, home bool) {
	if !m.played() {
		return
	}
	h, a := *m.HomeGoals, *m.AwayGoals
	if home {
		r.Record.add(h, a)
		r.Home.add(h, a)
	} else {
		r.Record.add(a, h)
		r.Away.add(a, h)
	}
}

func teamStats(matches []Match, team string) map[string]any {
	name := clubName(team)
	key := words(name)
	total := TeamRecord{Team: name}
	competitions := make(map[string]TeamRecord)
	seasons := make(map[int]TeamRecord)
	for _, m := range matches {
		home := key == m.homeKey
		total.add(m, home)
		row := competitions[m.Competition]
		row.Team = name
		row.add(m, home)
		competitions[m.Competition] = row
		if m.Season > 0 {
			row = seasons[m.Season]
			row.Team = name
			row.add(m, home)
			seasons[m.Season] = row
		}
	}
	return map[string]any{"record": total, "by_competition": competitions, "by_season": seasons, "fixtures": len(matches)}
}

func teamRecords(matches []Match, side string) []TeamRecord {
	table := make(map[string]*TeamRecord)
	for _, m := range matches {
		if !m.played() {
			continue
		}
		for _, home := range []bool{true, false} {
			if (home && side == "away") || (!home && side == "home") {
				continue
			}
			name, key := m.Away, m.awayKey
			if home {
				name, key = m.Home, m.homeKey
			}
			if table[key] == nil {
				table[key] = &TeamRecord{Team: name}
			}
			table[key].add(m, home)
		}
	}
	result := make([]TeamRecord, 0, len(table))
	for _, row := range table {
		result = append(result, *row)
	}
	return result
}

type Standing struct {
	Rank int `json:"rank"`
	TeamRecord
	Points         int    `json:"points"`
	GoalDifference int    `json:"goal_difference"`
	Status         string `json:"status,omitempty"`
}

func standings(matches []Match, season int, competition string) map[string]any {
	records := teamRecords(matches, "")
	rows := make([]Standing, 0, len(records))
	for _, record := range records {
		rows = append(rows, Standing{TeamRecord: record, Points: 3*record.Wins + record.Draws, GoalDifference: record.GoalsFor - record.GoalsAgainst})
	}
	slices.SortFunc(rows, func(a, b Standing) int {
		return cmp.Or(cmp.Compare(b.Points, a.Points), cmp.Compare(b.Wins, a.Wins),
			cmp.Compare(b.GoalDifference, a.GoalDifference), cmp.Compare(b.GoalsFor, a.GoalsFor),
			cmp.Compare(words(a.Team), words(b.Team)))
	})
	complete := len(rows) >= 2
	for _, row := range rows {
		complete = complete && row.Home.Played == len(rows)-1 && row.Away.Played == len(rows)-1
	}
	for i := range rows {
		rows[i].Rank = i + 1
		if complete && i == 0 {
			rows[i].Status = "champion"
		}
		if complete && ((competition == serieA && season >= 2006) || (competition == serieB && season >= 2007)) && len(rows) == 20 && i >= len(rows)-4 {
			rows[i].Status = "relegation places"
		}
	}
	return map[string]any{"competition": competition, "season": season, "complete_round_robin": complete, "standings": rows,
		"basis": "Recorded results: three points per win and one per draw. Ties use wins, goal difference, goals scored, then team name. Administrative point adjustments are unavailable."}
}

type Summary struct {
	Fixtures      int     `json:"fixtures"`
	Played        int     `json:"played"`
	Goals         int     `json:"goals"`
	HomeWins      int     `json:"home_wins"`
	AwayWins      int     `json:"away_wins"`
	Draws         int     `json:"draws"`
	GoalsPerMatch float64 `json:"goals_per_match"`
	HomeWinRate   float64 `json:"home_win_rate_percent"`
	AwayWinRate   float64 `json:"away_win_rate_percent"`
}

func (s *Summary) add(m Match) {
	s.Fixtures++
	if !m.played() {
		return
	}
	s.Played++
	h, a := *m.HomeGoals, *m.AwayGoals
	s.Goals += h + a
	switch cmp.Compare(h, a) {
	case 1:
		s.HomeWins++
	case -1:
		s.AwayWins++
	case 0:
		s.Draws++
	}
	s.GoalsPerMatch = float64(s.Goals) / float64(s.Played)
	s.HomeWinRate = percentage(s.HomeWins, s.Played)
	s.AwayWinRate = percentage(s.AwayWins, s.Played)
}

func summarize(matches []Match) map[string]any {
	var total Summary
	seasons := make(map[int]Summary)
	for _, m := range matches {
		total.add(m)
		if m.Season > 0 {
			season := seasons[m.Season]
			season.add(m)
			seasons[m.Season] = season
		}
	}
	return map[string]any{"summary": total, "by_season": seasons}
}

type PlayerFilter struct {
	Name              string `json:"name"`
	Nationality       string `json:"nationality"`
	Club              string `json:"club"`
	Position          string `json:"position"`
	BrazilianClubs    bool   `json:"brazilian_clubs"`
	MinOverall        int    `json:"min_overall"`
	IncludeAttributes bool   `json:"include_attributes"`
}

func (s *Store) findPlayers(q PlayerFilter) []Player {
	name, nationality, club := words(q.Name), words(q.Nationality), words(clubName(q.Club))
	if nationality == "brazilian" || nationality == "brasil" {
		nationality = "brazil"
	}
	pos := strings.ToUpper(strings.TrimSpace(q.Position))
	var brazilianClubs map[string]bool
	if q.BrazilianClubs {
		brazilianClubs = make(map[string]bool)
		for _, m := range s.matches {
			if m.Competition != libertadores {
				brazilianClubs[m.homeKey], brazilianClubs[m.awayKey] = true, true
			}
		}
	}
	result := make([]Player, 0)
	for _, p := range s.players {
		if !strings.Contains(p.nameKey, name) || (nationality != "" && p.nationalityKey != nationality) ||
			(club != "" && p.clubKey != club && !strings.Contains(words(p.Club), words(q.Club))) ||
			(q.BrazilianClubs && !brazilianClubs[p.clubKey]) || p.Overall < q.MinOverall ||
			!positionMatches(p.Position, pos) {
			continue
		}
		if !q.IncludeAttributes {
			p.Attributes = nil
		}
		result = append(result, p)
	}
	return result
}

func positionMatches(position, filter string) bool {
	switch filter {
	case "":
		return true
	case "FORWARD", "FORWARDS":
		return slices.Contains([]string{"ST", "CF", "LS", "RS", "LF", "RF", "LW", "RW"}, position)
	case "MIDFIELDER", "MIDFIELDERS":
		return slices.Contains([]string{"CM", "CAM", "CDM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM", "LM", "RM"}, position)
	case "DEFENDER", "DEFENDERS":
		return slices.Contains([]string{"CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB"}, position)
	case "GOALKEEPER", "GOALKEEPERS":
		return position == "GK"
	default:
		return position == filter
	}
}

type ClubRating struct {
	Club           string  `json:"club"`
	Players        int     `json:"players"`
	AverageOverall float64 `json:"average_overall"`
}

func clubRatings(players []Player) []ClubRating {
	rows := make(map[string]ClubRating)
	for _, p := range players {
		if p.clubKey == "" {
			continue
		}
		row := rows[p.clubKey]
		row.Club = clubName(p.Club)
		row.Players++
		row.AverageOverall += float64(p.Overall)
		rows[p.clubKey] = row
	}
	result := make([]ClubRating, 0, len(rows))
	for _, row := range rows {
		row.AverageOverall /= float64(row.Players)
		result = append(result, row)
	}
	slices.SortFunc(result, func(a, b ClubRating) int {
		return cmp.Or(cmp.Compare(b.Players, a.Players), cmp.Compare(a.Club, b.Club))
	})
	return result
}
