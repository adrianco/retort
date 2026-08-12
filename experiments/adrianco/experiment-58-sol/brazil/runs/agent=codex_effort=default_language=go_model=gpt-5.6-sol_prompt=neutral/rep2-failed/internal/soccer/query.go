package soccer

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

func (c *Catalog) SearchMatches(q MatchQuery) (MatchSearchResult, error) {
	if q.HomeOnly && q.AwayOnly {
		return MatchSearchResult{}, fmt.Errorf("home_only and away_only cannot both be true")
	}
	var from, to time.Time
	var err error
	if q.From != "" {
		from, err = parseDate(q.From)
		if err != nil {
			return MatchSearchResult{}, err
		}
	}
	if q.To != "" {
		to, err = parseDate(q.To)
		if err != nil {
			return MatchSearchResult{}, err
		}
	}
	if !from.IsZero() && !to.IsZero() && from.After(to) {
		return MatchSearchResult{}, fmt.Errorf("from must not be after to")
	}
	team, opp := NormalizeTeam(q.Team), NormalizeTeam(q.Opponent)
	stage := searchKey(q.Stage)
	results := make([]Match, 0)
	for _, m := range c.Matches {
		if team != "" && m.homeKey != team && m.awayKey != team {
			continue
		}
		if opp != "" && m.homeKey != opp && m.awayKey != opp {
			continue
		}
		if team != "" && opp != "" && team == opp {
			continue
		}
		if q.HomeOnly && m.homeKey != team {
			continue
		}
		if q.AwayOnly && m.awayKey != team {
			continue
		}
		if q.Season != 0 && m.Season != q.Season {
			continue
		}
		if !competitionMatches(m.Competition, q.Competition) {
			continue
		}
		if !from.IsZero() && m.date.Before(from) {
			continue
		}
		if !to.IsZero() && m.date.After(to) {
			continue
		}
		if stage != "" && !strings.Contains(searchKey(m.Stage+" "+m.Round), stage) {
			continue
		}
		results = append(results, m)
	}
	sort.SliceStable(results, func(i, j int) bool { return results[i].date.After(results[j].date) })
	total := len(results)
	limit := q.Limit
	if limit <= 0 {
		limit = 50
	}
	if limit > 500 {
		limit = 500
	}
	if len(results) > limit {
		results = results[:limit]
	}
	return MatchSearchResult{Matches: results, Returned: len(results), Total: total, Summary: fmt.Sprintf("Returned %d of %d matching matches", len(results), total)}, nil
}

func (c *Catalog) analyticalMatches(competition string, season int) []Match {
	seen := map[string][]time.Time{}
	out := make([]Match, 0)
	priority := func(m Match) int {
		switch m.Source {
		case sourceBrasileirao, sourceCup, sourceLibertadores:
			return 1
		case sourceHistorical:
			return 2
		default:
			return 3
		}
	}
	candidates := make([]Match, 0)
	for _, m := range c.Matches {
		if (season == 0 || m.Season == season) && competitionMatches(m.Competition, competition) {
			candidates = append(candidates, m)
		}
	}
	// A complete dedicated Série A season is authoritative. This prevents the
	// historical and extended overlap from inflating tables while still letting
	// the extended source fill unfinished/incomplete dedicated seasons.
	if competitionMatches("Brasileirão Série A", competition) && competition != "" && season != 0 {
		primary := make([]Match, 0)
		teams := map[string]bool{}
		for _, m := range candidates {
			if m.Source == sourceBrasileirao && m.Completed {
				primary = append(primary, m)
				teams[m.homeKey], teams[m.awayKey] = true, true
			}
		}
		if len(teams) > 1 && len(primary) == len(teams)*(len(teams)-1) {
			return primary
		}
	}
	sort.SliceStable(candidates, func(i, j int) bool { return priority(candidates[i]) < priority(candidates[j]) })
	for _, m := range candidates {
		if !m.Completed {
			continue
		}
		// Overlapping exports can shift a fixture by one day and disagree on its
		// score. Treat same teams/competition within one day as one fixture, while
		// preserving genuine repeated cup ties later in the season.
		key := fmt.Sprintf("%s|%s|%s", m.homeKey, m.awayKey, searchKey(m.Competition))
		duplicate := false
		for _, date := range seen[key] {
			delta := m.date.Sub(date)
			if delta >= -24*time.Hour && delta <= 24*time.Hour {
				duplicate = true
				break
			}
		}
		if !duplicate {
			seen[key] = append(seen[key], m.date)
			out = append(out, m)
		}
	}
	return out
}

func (c *Catalog) TeamStatistics(team string, season int, competition, venue string) (TeamRecord, error) {
	key := NormalizeTeam(team)
	if key == "" {
		return TeamRecord{}, fmt.Errorf("team is required")
	}
	venue = searchKey(venue)
	if venue != "" && venue != "all" && venue != "home" && venue != "away" {
		return TeamRecord{}, fmt.Errorf("venue must be all, home, or away")
	}
	r := TeamRecord{Team: team, Season: season, Competition: normalizeCompetition(competition), Venue: venue}
	if r.Venue == "" {
		r.Venue = "all"
	}
	if competition == "" {
		r.Competition = ""
	}
	for _, m := range c.analyticalMatches(competition, season) {
		isHome := m.homeKey == key
		isAway := m.awayKey == key
		if !isHome && !isAway {
			continue
		}
		if venue == "home" && !isHome {
			continue
		}
		if venue == "away" && !isAway {
			continue
		}
		r.Matches++
		gf, ga := m.AwayGoals, m.HomeGoals
		if isHome {
			gf, ga = m.HomeGoals, m.AwayGoals
		}
		r.GoalsFor += gf
		r.GoalsAgainst += ga
		if gf > ga {
			r.Wins++
		} else if gf == ga {
			r.Draws++
		} else {
			r.Losses++
		}
	}
	if r.Matches == 0 {
		return r, fmt.Errorf("no matches found for %s", team)
	}
	r.Points = r.Wins*3 + r.Draws
	r.WinRate = rounded(float64(r.Wins) * 100 / float64(r.Matches))
	return r, nil
}

func (c *Catalog) HeadToHead(a, b string, season int, competition string, limit int) (HeadToHeadResult, error) {
	ka, kb := NormalizeTeam(a), NormalizeTeam(b)
	if ka == "" || kb == "" || ka == kb {
		return HeadToHeadResult{}, fmt.Errorf("two different teams are required")
	}
	r := HeadToHeadResult{TeamA: a, TeamB: b}
	ms := c.analyticalMatches(competition, season)
	sort.SliceStable(ms, func(i, j int) bool { return ms[i].date.After(ms[j].date) })
	for _, m := range ms {
		if !((m.homeKey == ka && m.awayKey == kb) || (m.homeKey == kb && m.awayKey == ka)) {
			continue
		}
		r.Matches++
		ga, gb := m.AwayGoals, m.HomeGoals
		if m.homeKey == ka {
			ga, gb = m.HomeGoals, m.AwayGoals
		}
		r.GoalsA += ga
		r.GoalsB += gb
		if ga > gb {
			r.TeamAWins++
		} else if gb > ga {
			r.TeamBWins++
		} else {
			r.Draws++
		}
		if limit <= 0 {
			limit = 20
		}
		if len(r.Recent) < limit {
			r.Recent = append(r.Recent, m)
		}
	}
	if r.Matches == 0 {
		return r, fmt.Errorf("no head-to-head matches found")
	}
	return r, nil
}

func positionMatches(actual, query string) bool {
	q := searchKey(query)
	a := strings.ToUpper(strings.TrimSpace(actual))
	if q == "" {
		return true
	}
	groups := map[string][]string{"forward": {"ST", "CF", "LF", "RF", "LW", "RW", "LS", "RS"}, "midfielder": {"CM", "CAM", "CDM", "LM", "RM", "LCM", "RCM", "LAM", "RAM", "LDM", "RDM"}, "defender": {"CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"}, "goalkeeper": {"GK"}}
	if vals, ok := groups[q]; ok {
		for _, v := range vals {
			if a == v {
				return true
			}
		}
		return false
	}
	return strings.EqualFold(a, query)
}

func (c *Catalog) SearchPlayers(q PlayerQuery) PlayerSearchResult {
	name, nat, club := searchKey(q.Name), searchKey(q.Nationality), NormalizeTeam(q.Club)
	all := make([]Player, 0)
	for _, p := range c.Players {
		if name != "" && !strings.Contains(p.nameKey, name) {
			continue
		}
		if nat != "" && !strings.Contains(searchKey(p.Nationality), nat) {
			continue
		}
		if club != "" && p.clubKey != club && !strings.Contains(p.clubKey, club) {
			continue
		}
		if !positionMatches(p.Position, q.Position) || p.Overall < q.MinOverall {
			continue
		}
		all = append(all, p)
	}
	sort.SliceStable(all, func(i, j int) bool {
		if all[i].Overall == all[j].Overall {
			return all[i].Name < all[j].Name
		}
		return all[i].Overall > all[j].Overall
	})
	total := len(all)
	limit := q.Limit
	if limit <= 0 {
		limit = 25
	}
	if limit > 500 {
		limit = 500
	}
	if len(all) > limit {
		all = all[:limit]
	}
	return PlayerSearchResult{Players: all, Returned: len(all), Total: total, Summary: fmt.Sprintf("Returned %d of %d matching players", len(all), total)}
}

func (c *Catalog) Standings(competition string, season int) (StandingsResult, error) {
	if season == 0 {
		return StandingsResult{}, fmt.Errorf("season is required")
	}
	if competition == "" {
		competition = "Brasileirão Série A"
	}
	rows := map[string]*Standing{}
	names := map[string]string{}
	for _, m := range c.analyticalMatches(competition, season) {
		for _, x := range []struct {
			k, n   string
			gf, ga int
		}{{m.homeKey, m.HomeTeam, m.HomeGoals, m.AwayGoals}, {m.awayKey, m.AwayTeam, m.AwayGoals, m.HomeGoals}} {
			r := rows[x.k]
			if r == nil {
				r = &Standing{Team: x.n}
				rows[x.k] = r
				names[x.k] = x.n
			}
			r.Played++
			r.GoalsFor += x.gf
			r.GoalsAgainst += x.ga
			if x.gf > x.ga {
				r.Wins++
				r.Points += 3
			} else if x.gf == x.ga {
				r.Draws++
				r.Points++
			} else {
				r.Losses++
			}
		}
	}
	if len(rows) == 0 {
		return StandingsResult{}, fmt.Errorf("no matches found")
	}
	list := make([]Standing, 0, len(rows))
	for _, r := range rows {
		r.GoalDifference = r.GoalsFor - r.GoalsAgainst
		list = append(list, *r)
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].Points != list[j].Points {
			return list[i].Points > list[j].Points
		}
		if list[i].Wins != list[j].Wins {
			return list[i].Wins > list[j].Wins
		}
		if list[i].GoalDifference != list[j].GoalDifference {
			return list[i].GoalDifference > list[j].GoalDifference
		}
		if list[i].GoalsFor != list[j].GoalsFor {
			return list[i].GoalsFor > list[j].GoalsFor
		}
		return list[i].Team < list[j].Team
	})
	for i := range list {
		list[i].Position = i + 1
	}
	return StandingsResult{Competition: normalizeCompetition(competition), Season: season, Standings: list, Champion: list[0].Team, Note: "Calculated from completed matches in the provided datasets; tie-break order is points, wins, goal difference, then goals scored."}, nil
}

func (c *Catalog) Aggregate(competition string, season, limit int) (AggregateResult, error) {
	ms := c.analyticalMatches(competition, season)
	if len(ms) == 0 {
		return AggregateResult{}, fmt.Errorf("no matches found")
	}
	r := AggregateResult{Competition: normalizeCompetition(competition), Season: season, Matches: len(ms)}
	if competition == "" {
		r.Competition = ""
	}
	wins := make([]BiggestVictory, 0, len(ms))
	for _, m := range ms {
		r.Goals += m.HomeGoals + m.AwayGoals
		if m.HomeGoals > m.AwayGoals {
			r.HomeWins++
		} else if m.HomeGoals < m.AwayGoals {
			r.AwayWins++
		} else {
			r.Draws++
		}
		margin := m.HomeGoals - m.AwayGoals
		if margin < 0 {
			margin = -margin
		}
		wins = append(wins, BiggestVictory{Match: m, Margin: margin})
	}
	r.GoalsPerMatch = rounded(float64(r.Goals) / float64(r.Matches))
	r.HomeWinRate = rounded(float64(r.HomeWins) * 100 / float64(r.Matches))
	sort.SliceStable(wins, func(i, j int) bool {
		if wins[i].Margin == wins[j].Margin {
			return wins[i].Match.date.After(wins[j].Match.date)
		}
		return wins[i].Margin > wins[j].Margin
	})
	if limit <= 0 {
		limit = 10
	}
	if len(wins) > limit {
		wins = wins[:limit]
	}
	r.BiggestVictories = wins
	return r, nil
}

func (c *Catalog) ClubOverview(team string, season int, competition string) (ClubOverview, error) {
	record, err := c.TeamStatistics(team, season, competition, "all")
	if err != nil {
		return ClubOverview{}, err
	}
	players := c.SearchPlayers(PlayerQuery{Club: team, Limit: 500}).Players
	r := ClubOverview{Team: team, Record: record, Players: players, PlayerCount: len(players)}
	for _, p := range players {
		r.AverageRating += float64(p.Overall)
	}
	if len(players) > 0 {
		r.AverageRating = rounded(r.AverageRating / float64(len(players)))
	}
	return r, nil
}
