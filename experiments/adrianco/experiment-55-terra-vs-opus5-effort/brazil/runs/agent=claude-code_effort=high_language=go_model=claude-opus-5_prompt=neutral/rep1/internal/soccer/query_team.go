// query_team.go implements the "Team Queries" section of the specification:
// per-club records, home/away splits, per-competition and per-season breakdowns.
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// CompetitionRecord is a club's record inside one competition.
type CompetitionRecord struct {
	Competition string `json:"competition"`
	FirstSeason int    `json:"first_season"`
	LastSeason  int    `json:"last_season"`
	Record      Record `json:"record"`
}

// SeasonRecord is a club's record inside one season.
type SeasonRecord struct {
	Season int    `json:"season"`
	Record Record `json:"record"`
}

// TeamStatsResult is the full statistical profile of a club.
type TeamStatsResult struct {
	Team          TeamView            `json:"team"`
	Scope         string              `json:"scope"`
	Overall       Record              `json:"overall"`
	Home          Record              `json:"home"`
	Away          Record              `json:"away"`
	ByCompetition []CompetitionRecord `json:"by_competition"`
	BySeason      []SeasonRecord      `json:"by_season"`
	BiggestWin    *MatchView          `json:"biggest_win,omitempty"`
	BiggestLoss   *MatchView          `json:"biggest_loss,omitempty"`
	RecentForm    []string            `json:"recent_form,omitempty"`
	RecentMatches []MatchView         `json:"recent_matches,omitempty"`
	Note          string              `json:"note,omitempty"`
}

// TeamStats computes a club's record, optionally narrowed to a competition
// and/or a season (or season range).
func (g *Graph) TeamStats(team, competition string, season, seasonFrom, seasonTo int, venue string) (*TeamStatsResult, error) {
	t, err := g.ResolveTeam(team)
	if err != nil {
		return nil, err
	}
	compID := ""
	if strings.TrimSpace(competition) != "" {
		if compID, err = ResolveCompetition(competition); err != nil {
			return nil, err
		}
	}

	var ms []*Match
	for _, m := range g.byTeam[t.ID] {
		if compID != "" && m.Competition != compID {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if seasonFrom != 0 && m.Season < seasonFrom {
			continue
		}
		if seasonTo != 0 && m.Season > seasonTo {
			continue
		}
		switch strings.ToLower(venue) {
		case "home":
			if m.HomeTeamID != t.ID {
				continue
			}
		case "away":
			if m.AwayTeamID != t.ID {
				continue
			}
		}
		ms = append(ms, m)
	}

	res := &TeamStatsResult{
		Team:  t.ToView(),
		Scope: describeScope(compID, season, seasonFrom, seasonTo, venue),
	}
	if len(ms) == 0 {
		res.Note = fmt.Sprintf("no matches for %s within %s", t.Name, res.Scope)
		res.ByCompetition = []CompetitionRecord{}
		res.BySeason = []SeasonRecord{}
		return res, nil
	}

	byComp := map[string]*CompetitionRecord{}
	bySeason := map[int]*Record{}
	var biggestWin, biggestLoss *Match

	for _, m := range ms {
		gf, ga := m.HomeGoals, m.AwayGoals
		if m.AwayTeamID == t.ID {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		res.Overall.add(gf, ga)
		if m.HomeTeamID == t.ID {
			res.Home.add(gf, ga)
		} else {
			res.Away.add(gf, ga)
		}

		cr, ok := byComp[m.Competition]
		if !ok {
			cr = &CompetitionRecord{Competition: CompetitionName(m.Competition), FirstSeason: m.Season, LastSeason: m.Season}
			byComp[m.Competition] = cr
		}
		if m.Season < cr.FirstSeason {
			cr.FirstSeason = m.Season
		}
		if m.Season > cr.LastSeason {
			cr.LastSeason = m.Season
		}
		cr.Record.add(gf, ga)

		sr, ok := bySeason[m.Season]
		if !ok {
			sr = &Record{}
			bySeason[m.Season] = sr
		}
		sr.add(gf, ga)

		diff := gf - ga
		if diff > 0 && (biggestWin == nil || diff > winMargin(biggestWin, t.ID)) {
			biggestWin = m
		}
		if diff < 0 && (biggestLoss == nil || diff < winMargin(biggestLoss, t.ID)) {
			biggestLoss = m
		}
	}

	res.Overall.finalize()
	res.Home.finalize()
	res.Away.finalize()
	for _, id := range sortedKeys(byComp) {
		byComp[id].Record.finalize()
		res.ByCompetition = append(res.ByCompetition, *byComp[id])
	}
	sort.SliceStable(res.ByCompetition, func(i, j int) bool {
		return res.ByCompetition[i].Record.Played > res.ByCompetition[j].Record.Played
	})
	seasons := make([]int, 0, len(bySeason))
	for s := range bySeason {
		seasons = append(seasons, s)
	}
	sort.Ints(seasons)
	for _, s := range seasons {
		bySeason[s].finalize()
		res.BySeason = append(res.BySeason, SeasonRecord{Season: s, Record: *bySeason[s]})
	}
	if biggestWin != nil {
		v := g.ToView(biggestWin)
		res.BiggestWin = &v
	}
	if biggestLoss != nil {
		v := g.ToView(biggestLoss)
		res.BiggestLoss = &v
	}

	// Recent form: last five matches, newest first.
	recent := make([]*Match, len(ms))
	copy(recent, ms)
	sort.SliceStable(recent, func(i, j int) bool { return recent[i].Date.After(recent[j].Date) })
	if len(recent) > 5 {
		recent = recent[:5]
	}
	for _, m := range recent {
		switch m.WinnerID() {
		case t.ID:
			res.RecentForm = append(res.RecentForm, "W")
		case "":
			res.RecentForm = append(res.RecentForm, "D")
		default:
			res.RecentForm = append(res.RecentForm, "L")
		}
	}
	res.RecentMatches = g.ToViews(recent)
	return res, nil
}

func winMargin(m *Match, teamID string) int {
	if m.HomeTeamID == teamID {
		return m.HomeGoals - m.AwayGoals
	}
	return m.AwayGoals - m.HomeGoals
}

func describeScope(compID string, season, from, to int, venue string) string {
	var parts []string
	if compID != "" {
		parts = append(parts, CompetitionName(compID))
	} else {
		parts = append(parts, "all competitions")
	}
	switch {
	case season != 0:
		parts = append(parts, fmt.Sprintf("season %d", season))
	case from != 0 && to != 0:
		parts = append(parts, fmt.Sprintf("seasons %d-%d", from, to))
	case from != 0:
		parts = append(parts, fmt.Sprintf("from %d", from))
	case to != 0:
		parts = append(parts, fmt.Sprintf("until %d", to))
	default:
		parts = append(parts, "all seasons")
	}
	switch strings.ToLower(venue) {
	case "home":
		parts = append(parts, "home matches only")
	case "away":
		parts = append(parts, "away matches only")
	}
	return strings.Join(parts, ", ")
}

// TeamCompetitions answers "what competitions has X played in?".
type TeamCompetitionsResult struct {
	Team         TeamView            `json:"team"`
	Competitions []CompetitionRecord `json:"competitions"`
	TotalMatches int                 `json:"total_matches"`
}

// TeamCompetitions lists every competition a club appears in.
func (g *Graph) TeamCompetitions(team string) (*TeamCompetitionsResult, error) {
	stats, err := g.TeamStats(team, "", 0, 0, 0, "")
	if err != nil {
		return nil, err
	}
	return &TeamCompetitionsResult{
		Team:         stats.Team,
		Competitions: stats.ByCompetition,
		TotalMatches: stats.Overall.Played,
	}, nil
}
