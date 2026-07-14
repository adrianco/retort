package main

import (
	"sort"
	"strings"
)

func clampLimit(limit, def, max int) int {
	if limit <= 0 {
		return def
	}
	if limit > max {
		return max
	}
	return limit
}

// competitionMatches does a loose, accent/case-insensitive substring match
// in either direction so callers can pass "Brasileirao", "brasileirão",
// "libertadores" or "cup" and hit the right competition tag.
func competitionMatches(actual, filter string) bool {
	if filter == "" {
		return true
	}
	a, f := normalizeKey(actual), normalizeKey(filter)
	return strings.Contains(a, f) || strings.Contains(f, a)
}

func dateInRange(m Match, from, to string) bool {
	if m.DateStr == "" {
		return false
	}
	if from != "" && m.DateStr < from {
		return false
	}
	if to != "" && m.DateStr > to {
		return false
	}
	return true
}

// teamKeySet resolves a free-form team name into the set of full team keys
// it plausibly refers to (see Store.resolveTeam).
func (s *Store) teamKeySet(input string) (map[string]bool, []string) {
	keys := s.resolveTeam(input)
	set := make(map[string]bool, len(keys))
	for _, k := range keys {
		set[k] = true
	}
	return set, keys
}

func matchTeam(m Match, set map[string]bool, venue string) bool {
	if set == nil {
		return true
	}
	switch venue {
	case "home":
		return set[m.homeKey.Full]
	case "away":
		return set[m.awayKey.Full]
	default:
		return set[m.homeKey.Full] || set[m.awayKey.Full]
	}
}

func sortMatchesRecentFirst(matches []Match) {
	sort.SliceStable(matches, func(i, j int) bool {
		return matches[i].Date.After(matches[j].Date)
	})
}

// ---------------------------------------------------------------------
// search_matches
// ---------------------------------------------------------------------

type SearchMatchesResult struct {
	ResolvedTeam     []string           `json:"resolved_team,omitempty"`
	ResolvedOpponent []string           `json:"resolved_opponent,omitempty"`
	TotalMatches     int                `json:"total_matches"`
	ReturnedCount    int                `json:"returned_count"`
	Matches          []Match            `json:"matches"`
	HeadToHead       *HeadToHeadSummary `json:"head_to_head,omitempty"`
	Note             string             `json:"note,omitempty"`
}

func (s *Store) SearchMatches(team, opponent, competition string, season int, dateFrom, dateTo string, limit int) SearchMatchesResult {
	var teamSet, oppSet map[string]bool
	var teamKeys, oppKeys []string
	if team != "" {
		teamSet, teamKeys = s.teamKeySet(team)
	}
	if opponent != "" {
		oppSet, oppKeys = s.teamKeySet(opponent)
	}

	var filtered []Match
	for _, m := range s.Matches {
		if team != "" && !matchTeam(m, teamSet, "") {
			continue
		}
		if opponent != "" && !matchTeam(m, oppSet, "") {
			continue
		}
		if team != "" && opponent != "" {
			homeIsTeam, awayIsTeam := teamSet[m.homeKey.Full], teamSet[m.awayKey.Full]
			homeIsOpp, awayIsOpp := oppSet[m.homeKey.Full], oppSet[m.awayKey.Full]
			if !((homeIsTeam && awayIsOpp) || (awayIsTeam && homeIsOpp)) {
				continue
			}
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if (dateFrom != "" || dateTo != "") && !dateInRange(m, dateFrom, dateTo) {
			continue
		}
		filtered = append(filtered, m)
	}
	sortMatchesRecentFirst(filtered)

	result := SearchMatchesResult{ResolvedTeam: teamKeys, ResolvedOpponent: oppKeys, TotalMatches: len(filtered)}
	if team != "" && len(teamKeys) == 0 {
		result.Note = "no team in the dataset matched \"" + team + "\""
	} else if opponent != "" && len(oppKeys) == 0 {
		result.Note = "no team in the dataset matched \"" + opponent + "\""
	}

	limit = clampLimit(limit, 20, 200)
	page := filtered
	if len(page) > limit {
		page = page[:limit]
	}
	result.Matches = page
	result.ReturnedCount = len(page)

	if team != "" && opponent != "" && len(teamKeys) > 0 && len(oppKeys) > 0 {
		h := computeH2H(filtered, teamSet, oppSet, s.displayNames(teamKeys), s.displayNames(oppKeys))
		result.HeadToHead = &h
	}
	return result
}

// ---------------------------------------------------------------------
// head_to_head
// ---------------------------------------------------------------------

type HeadToHeadSummary struct {
	TeamA           string `json:"team_a"`
	TeamB           string `json:"team_b"`
	MatchesPlayed   int    `json:"matches_played"`
	TeamAWins       int    `json:"team_a_wins"`
	TeamBWins       int    `json:"team_b_wins"`
	Draws           int    `json:"draws"`
	TeamAGoals      int    `json:"team_a_goals"`
	TeamBGoals      int    `json:"team_b_goals"`
	BiggestTeamAWin *Match `json:"biggest_team_a_win,omitempty"`
	BiggestTeamBWin *Match `json:"biggest_team_b_win,omitempty"`
}

func computeH2H(matches []Match, aSet, bSet map[string]bool, teamAName, teamBName string) HeadToHeadSummary {
	sum := HeadToHeadSummary{TeamA: teamAName, TeamB: teamBName}
	for _, m := range matches {
		if !m.HasGoals {
			continue
		}
		sum.MatchesPlayed++
		aIsHome := aSet[m.homeKey.Full]
		var aGoals, bGoals int
		if aIsHome {
			aGoals, bGoals = m.HomeGoals, m.AwayGoals
		} else {
			aGoals, bGoals = m.AwayGoals, m.HomeGoals
		}
		sum.TeamAGoals += aGoals
		sum.TeamBGoals += bGoals
		diff := aGoals - bGoals
		switch {
		case diff > 0:
			sum.TeamAWins++
			mm := m
			if sum.BiggestTeamAWin == nil || abs(diff) > abs(biggestDiff(sum.BiggestTeamAWin, aIsHome0(aSet, *sum.BiggestTeamAWin))) {
				sum.BiggestTeamAWin = &mm
			}
		case diff < 0:
			sum.TeamBWins++
			mm := m
			if sum.BiggestTeamBWin == nil || abs(diff) > abs(biggestDiff(sum.BiggestTeamBWin, aIsHome0(aSet, *sum.BiggestTeamBWin))) {
				sum.BiggestTeamBWin = &mm
			}
		default:
			sum.Draws++
		}
	}
	return sum
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}

func aIsHome0(aSet map[string]bool, m Match) bool { return aSet[m.homeKey.Full] }

func biggestDiff(m *Match, aWasHome bool) int {
	if aWasHome {
		return m.HomeGoals - m.AwayGoals
	}
	return m.AwayGoals - m.HomeGoals
}

type HeadToHeadResult struct {
	TeamAVariants []string          `json:"team_a_variants"`
	TeamBVariants []string          `json:"team_b_variants"`
	Summary       HeadToHeadSummary `json:"summary"`
	RecentMatches []Match           `json:"recent_matches"`
}

func (s *Store) HeadToHead(teamA, teamB, competition string, season, limit int) (HeadToHeadResult, bool) {
	aSet, aKeys := s.teamKeySet(teamA)
	bSet, bKeys := s.teamKeySet(teamB)
	if len(aKeys) == 0 || len(bKeys) == 0 {
		return HeadToHeadResult{TeamAVariants: aKeys, TeamBVariants: bKeys}, false
	}

	var filtered []Match
	for _, m := range s.Matches {
		homeA, awayA := aSet[m.homeKey.Full], aSet[m.awayKey.Full]
		homeB, awayB := bSet[m.homeKey.Full], bSet[m.awayKey.Full]
		if !((homeA && awayB) || (awayA && homeB)) {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		filtered = append(filtered, m)
	}
	sortMatchesRecentFirst(filtered)

	summary := computeH2H(filtered, aSet, bSet, s.displayNames(aKeys), s.displayNames(bKeys))
	limit = clampLimit(limit, 50, 200)
	recent := filtered
	if len(recent) > limit {
		recent = recent[:limit]
	}
	return HeadToHeadResult{
		TeamAVariants: aKeys,
		TeamBVariants: bKeys,
		Summary:       summary,
		RecentMatches: recent,
	}, true
}

// ---------------------------------------------------------------------
// team_record
// ---------------------------------------------------------------------

type CompetitionCount struct {
	Competition string `json:"competition"`
	Matches     int    `json:"matches"`
}

type TeamRecordResult struct {
	Team                 string             `json:"team"`
	TeamVariantsIncluded []string           `json:"team_variants_included"`
	Season               int                `json:"season,omitempty"`
	Competition          string             `json:"competition,omitempty"`
	Venue                string             `json:"venue"`
	Played               int                `json:"played"`
	Won                  int                `json:"won"`
	Drawn                int                `json:"drawn"`
	Lost                 int                `json:"lost"`
	GoalsFor             int                `json:"goals_for"`
	GoalsAgainst         int                `json:"goals_against"`
	WinRatePct           float64            `json:"win_rate_pct"`
	CompetitionsPlayed   []CompetitionCount `json:"competitions_played"`
	SquadPlayers         []Player           `json:"squad_players,omitempty"`
}

func (s *Store) TeamRecord(team string, season int, competition, venue string) (TeamRecordResult, bool) {
	set, keys := s.teamKeySet(team)
	if len(keys) == 0 {
		return TeamRecordResult{}, false
	}
	if venue == "" {
		venue = "all"
	}

	compCounts := map[string]int{}
	res := TeamRecordResult{
		Team:                 s.displayNames(keys),
		TeamVariantsIncluded: keys,
		Season:               season,
		Competition:          competition,
		Venue:                venue,
	}

	for _, m := range s.Matches {
		if !matchTeam(m, set, venue) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		compCounts[m.Competition]++
		if competition != "" && !competitionMatches(m.Competition, competition) {
			continue
		}
		if !m.HasGoals {
			continue
		}
		isHome := set[m.homeKey.Full]
		var gf, ga int
		if isHome {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		res.Played++
		res.GoalsFor += gf
		res.GoalsAgainst += ga
		switch {
		case gf > ga:
			res.Won++
		case gf < ga:
			res.Lost++
		default:
			res.Drawn++
		}
	}
	if res.Played > 0 {
		res.WinRatePct = round2(100 * float64(res.Won) / float64(res.Played))
	}
	for comp, n := range compCounts {
		res.CompetitionsPlayed = append(res.CompetitionsPlayed, CompetitionCount{Competition: comp, Matches: n})
	}
	sort.Slice(res.CompetitionsPlayed, func(i, j int) bool {
		return res.CompetitionsPlayed[i].Matches > res.CompetitionsPlayed[j].Matches
	})

	tn := parseTeamName(team)
	var squad []Player
	for _, p := range s.Players {
		if p.clubKey.Base == tn.Base {
			squad = append(squad, p)
		}
	}
	sort.Slice(squad, func(i, j int) bool { return squad[i].Overall > squad[j].Overall })
	if len(squad) > 15 {
		squad = squad[:15]
	}
	res.SquadPlayers = squad

	return res, true
}

func round2(f float64) float64 {
	return float64(int(f*100+0.5)) / 100
}

func (s *Store) displayNames(keys []string) string {
	names := make([]string, 0, len(keys))
	seen := map[string]bool{}
	for _, k := range keys {
		d := s.displayName(k)
		if !seen[d] {
			seen[d] = true
			names = append(names, d)
		}
	}
	return strings.Join(names, " / ")
}

// ---------------------------------------------------------------------
// standings
// ---------------------------------------------------------------------

type StandingsRow struct {
	Position     int    `json:"position"`
	Team         string `json:"team"`
	Played       int    `json:"played"`
	Won          int    `json:"won"`
	Drawn        int    `json:"drawn"`
	Lost         int    `json:"lost"`
	GoalsFor     int    `json:"goals_for"`
	GoalsAgainst int    `json:"goals_against"`
	GoalDiff     int    `json:"goal_diff"`
	Points       int    `json:"points"`
}

type StandingsResult struct {
	Season      int            `json:"season"`
	Competition string         `json:"competition"`
	Table       []StandingsRow `json:"table"`
	Champion    string         `json:"champion,omitempty"`
	Note        string         `json:"note,omitempty"`
}

func (s *Store) Standings(season int, competition string) StandingsResult {
	if competition == "" {
		competition = "Brasileirão"
	}
	rows := map[string]*StandingsRow{}
	for _, m := range s.Matches {
		if m.Season != season || !m.HasGoals || !competitionMatches(m.Competition, competition) {
			continue
		}
		for _, side := range []struct {
			key    string
			gf, ga int
		}{
			{m.homeKey.Full, m.HomeGoals, m.AwayGoals},
			{m.awayKey.Full, m.AwayGoals, m.HomeGoals},
		} {
			row, ok := rows[side.key]
			if !ok {
				row = &StandingsRow{Team: s.displayName(side.key)}
				rows[side.key] = row
			}
			row.Played++
			row.GoalsFor += side.gf
			row.GoalsAgainst += side.ga
			switch {
			case side.gf > side.ga:
				row.Won++
				row.Points += 3
			case side.gf < side.ga:
				row.Lost++
			default:
				row.Drawn++
				row.Points++
			}
		}
	}
	table := make([]StandingsRow, 0, len(rows))
	for _, r := range rows {
		r.GoalDiff = r.GoalsFor - r.GoalsAgainst
		table = append(table, *r)
	}
	sort.Slice(table, func(i, j int) bool {
		if table[i].Points != table[j].Points {
			return table[i].Points > table[j].Points
		}
		if table[i].GoalDiff != table[j].GoalDiff {
			return table[i].GoalDiff > table[j].GoalDiff
		}
		if table[i].GoalsFor != table[j].GoalsFor {
			return table[i].GoalsFor > table[j].GoalsFor
		}
		return table[i].Team < table[j].Team
	})
	for i := range table {
		table[i].Position = i + 1
	}
	res := StandingsResult{Season: season, Competition: competition, Table: table}
	if len(table) > 0 {
		res.Champion = table[0].Team
	}
	if !strings.Contains(normalizeKey(competition), "brasileir") {
		res.Note = "this competition is not a single round-robin league; the table is an informational points tally (3/1/0) and does not represent an official knockout/group bracket result"
	}
	return res
}

// ---------------------------------------------------------------------
// stats_overview
// ---------------------------------------------------------------------

type BiggestWin struct {
	Match          Match `json:"match"`
	GoalDifference int   `json:"goal_difference"`
}

type TeamRateEntry struct {
	Team       string  `json:"team"`
	Played     int     `json:"played"`
	Won        int     `json:"won"`
	WinRatePct float64 `json:"win_rate_pct"`
}

type StatsOverviewResult struct {
	Competition      string         `json:"competition,omitempty"`
	Season           int            `json:"season,omitempty"`
	TotalMatches     int            `json:"total_matches"`
	AvgGoalsPerMatch float64        `json:"avg_goals_per_match"`
	HomeWinRatePct   float64        `json:"home_win_rate_pct"`
	AwayWinRatePct   float64        `json:"away_win_rate_pct"`
	DrawRatePct      float64        `json:"draw_rate_pct"`
	BiggestWins      []BiggestWin   `json:"biggest_wins"`
	BestHomeRecord   *TeamRateEntry `json:"best_home_record,omitempty"`
	BestAwayRecord   *TeamRateEntry `json:"best_away_record,omitempty"`
}

func (s *Store) StatsOverview(competition string, season int) StatsOverviewResult {
	var filtered []Match
	for _, m := range s.Matches {
		if !m.HasGoals {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		filtered = append(filtered, m)
	}

	res := StatsOverviewResult{Competition: competition, Season: season, TotalMatches: len(filtered)}
	if len(filtered) == 0 {
		return res
	}

	totalGoals, homeWins, awayWins, draws := 0, 0, 0, 0
	homeStats := map[string]*TeamRateEntry{}
	awayStats := map[string]*TeamRateEntry{}
	for _, m := range filtered {
		totalGoals += m.HomeGoals + m.AwayGoals
		switch m.Result() {
		case "home":
			homeWins++
		case "away":
			awayWins++
		default:
			draws++
		}

		he := homeStats[m.homeKey.Full]
		if he == nil {
			he = &TeamRateEntry{Team: s.displayName(m.homeKey.Full)}
			homeStats[m.homeKey.Full] = he
		}
		he.Played++
		if m.Result() == "home" {
			he.Won++
		}

		ae := awayStats[m.awayKey.Full]
		if ae == nil {
			ae = &TeamRateEntry{Team: s.displayName(m.awayKey.Full)}
			awayStats[m.awayKey.Full] = ae
		}
		ae.Played++
		if m.Result() == "away" {
			ae.Won++
		}
	}

	n := float64(len(filtered))
	res.AvgGoalsPerMatch = round2(float64(totalGoals) / n)
	res.HomeWinRatePct = round2(100 * float64(homeWins) / n)
	res.AwayWinRatePct = round2(100 * float64(awayWins) / n)
	res.DrawRatePct = round2(100 * float64(draws) / n)

	sorted := append([]Match(nil), filtered...)
	sort.Slice(sorted, func(i, j int) bool {
		di := abs(sorted[i].HomeGoals - sorted[i].AwayGoals)
		dj := abs(sorted[j].HomeGoals - sorted[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		return (sorted[i].HomeGoals + sorted[i].AwayGoals) > (sorted[j].HomeGoals + sorted[j].AwayGoals)
	})
	top := 5
	if len(sorted) < top {
		top = len(sorted)
	}
	for _, m := range sorted[:top] {
		res.BiggestWins = append(res.BiggestWins, BiggestWin{Match: m, GoalDifference: abs(m.HomeGoals - m.AwayGoals)})
	}

	res.BestHomeRecord = bestRate(homeStats)
	res.BestAwayRecord = bestRate(awayStats)
	return res
}

func bestRate(stats map[string]*TeamRateEntry) *TeamRateEntry {
	var best *TeamRateEntry
	for _, e := range stats {
		if e.Played < 5 {
			continue
		}
		e.WinRatePct = round2(100 * float64(e.Won) / float64(e.Played))
		if best == nil || e.WinRatePct > best.WinRatePct {
			best = e
		}
	}
	return best
}

// ---------------------------------------------------------------------
// search_players
// ---------------------------------------------------------------------

type SearchPlayersResult struct {
	TotalFound    int      `json:"total_found"`
	ReturnedCount int      `json:"returned_count"`
	Players       []Player `json:"players"`
}

func (s *Store) SearchPlayers(name, nationality, club, position string, minOverall, limit int) SearchPlayersResult {
	nameKey := normalizeKey(name)
	natKey := normalizeKey(nationality)
	posKey := normalizeKey(position)
	clubBase := ""
	clubKey := ""
	if club != "" {
		clubBase = parseTeamName(club).Base
		clubKey = normalizeKey(club)
	}

	var found []Player
	for _, p := range s.Players {
		if nameKey != "" && !strings.Contains(p.nameKey, nameKey) {
			continue
		}
		if natKey != "" && !strings.Contains(p.nationalityKey, natKey) {
			continue
		}
		if posKey != "" && !strings.Contains(p.positionKey, posKey) {
			continue
		}
		if club != "" && p.clubKey.Base != clubBase && !strings.Contains(normalizeKey(p.Club), clubKey) {
			continue
		}
		if minOverall > 0 && p.Overall < minOverall {
			continue
		}
		found = append(found, p)
	}
	sort.Slice(found, func(i, j int) bool {
		if found[i].Overall != found[j].Overall {
			return found[i].Overall > found[j].Overall
		}
		return found[i].Name < found[j].Name
	})

	limit = clampLimit(limit, 20, 200)
	page := found
	if len(page) > limit {
		page = page[:limit]
	}
	return SearchPlayersResult{TotalFound: len(found), ReturnedCount: len(page), Players: page}
}
