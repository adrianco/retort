package soccer

import (
	"sort"
	"strconv"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/normalize"
)

// StandingRow is one line of a league table.
type StandingRow struct {
	Position     int    `json:"position"`
	Team         string `json:"team"`
	TeamID       string `json:"team_id"`
	Played       int    `json:"played"`
	Wins         int    `json:"wins"`
	Draws        int    `json:"draws"`
	Losses       int    `json:"losses"`
	GoalsFor     int    `json:"goals_for"`
	GoalsAgainst int    `json:"goals_against"`
	GoalDiff     int    `json:"goal_difference"`
	Points       int    `json:"points"`
	Note         string `json:"note,omitempty"` // Champion / Relegated / etc.
}

// Standings is a computed league table for one season.
type Standings struct {
	Competition string        `json:"competition"`
	Season      int           `json:"season"`
	Matches     int           `json:"matches_counted"`
	Complete    bool          `json:"complete_season"`
	Table       []StandingRow `json:"table"`
	Champion    string        `json:"champion,omitempty"`
	Relegated   []string      `json:"relegated,omitempty"`
	Summary     string        `json:"summary"`
	Note        string        `json:"note"`
}

// LeagueStandings computes a table from match results. Only round-robin
// league competitions (Série A/B/C) produce a meaningful table; cups return an
// error pointing at find_matches instead.
func (g *Graph) LeagueStandings(competition string, season int, relegationSpots int) (*Standings, error) {
	comp := g.resolveCompetition(competition)
	if comp == "" {
		return nil, &ErrNoData{What: "competition " + strconv.Quote(competition)}
	}
	switch comp {
	case SerieA, SerieB, SerieC:
	default:
		return nil, &ErrNoData{
			What: "a league table for " + comp + " (knockout competition — use find_matches with round=\"final\")",
		}
	}
	if season == 0 {
		return nil, &ErrNoData{What: "standings without a season"}
	}

	type agg struct {
		team string
		rec  Record
	}
	byTeam := map[string]*agg{}
	counted := 0
	for i := range g.Matches {
		m := &g.Matches[i]
		if m.Competition != comp || m.Season != season {
			continue
		}
		counted++
		for _, side := range []struct {
			ref    TeamRef
			gf, ga int
		}{
			{m.Home, m.HomeGoals, m.AwayGoals},
			{m.Away, m.AwayGoals, m.HomeGoals},
		} {
			a := byTeam[side.ref.ID]
			if a == nil {
				a = &agg{team: side.ref.Name}
				byTeam[side.ref.ID] = a
			}
			a.rec.add(side.gf, side.ga)
		}
	}
	if counted == 0 {
		return nil, &ErrNoData{What: comp + " " + strconv.Itoa(season)}
	}

	rows := make([]StandingRow, 0, len(byTeam))
	for id, a := range byTeam {
		a.rec.finish()
		rows = append(rows, StandingRow{
			Team: a.team, TeamID: id, Played: a.rec.Matches,
			Wins: a.rec.Wins, Draws: a.rec.Draws, Losses: a.rec.Losses,
			GoalsFor: a.rec.GoalsFor, GoalsAgainst: a.rec.GoalsAgainst,
			GoalDiff: a.rec.GoalDiff, Points: a.rec.Points,
		})
	}
	// CBF tie-break order: points, wins, goal difference, goals for, name.
	sort.Slice(rows, func(i, j int) bool {
		a, b := rows[i], rows[j]
		switch {
		case a.Points != b.Points:
			return a.Points > b.Points
		case a.Wins != b.Wins:
			return a.Wins > b.Wins
		case a.GoalDiff != b.GoalDiff:
			return a.GoalDiff > b.GoalDiff
		case a.GoalsFor != b.GoalsFor:
			return a.GoalsFor > b.GoalsFor
		default:
			return a.Team < b.Team
		}
	})

	st := &Standings{Competition: comp, Season: season, Matches: counted}
	teams := len(rows)
	expected := teams * (teams - 1)
	st.Complete = teams > 2 && counted == expected

	if relegationSpots < 0 {
		relegationSpots = 0
	}
	if relegationSpots == 0 && st.Complete && teams == 20 {
		relegationSpots = 4 // Série A/B format since 2006
	}
	for i := range rows {
		rows[i].Position = i + 1
		if i == 0 && st.Complete {
			rows[i].Note = "Champion"
		}
		if relegationSpots > 0 && i >= teams-relegationSpots && st.Complete {
			rows[i].Note = "Relegated"
			st.Relegated = append(st.Relegated, rows[i].Team)
		}
	}
	st.Table = rows
	if st.Complete {
		st.Champion = rows[0].Team
	}
	st.Note = "Table calculated from match results in the provided datasets (3 points per win)."
	if !st.Complete {
		st.Note += " Season looks incomplete: " + strconv.Itoa(counted) + " of an expected " +
			strconv.Itoa(expected) + " matches for " + strconv.Itoa(teams) + " teams."
	}
	st.Summary = standingsSummary(st)
	return st, nil
}

func standingsSummary(st *Standings) string {
	var b strings.Builder
	b.WriteString(strconv.Itoa(st.Season) + " " + st.Competition + " (calculated): ")
	n := 3
	if len(st.Table) < n {
		n = len(st.Table)
	}
	for i := 0; i < n; i++ {
		if i > 0 {
			b.WriteString(", ")
		}
		r := st.Table[i]
		b.WriteString(strconv.Itoa(r.Position) + ". " + r.Team + " " + strconv.Itoa(r.Points) + " pts")
	}
	if st.Champion != "" {
		b.WriteString(". Champion: " + st.Champion)
	}
	if len(st.Relegated) > 0 {
		b.WriteString(". Relegated: " + strings.Join(st.Relegated, ", "))
	}
	return b.String()
}

// resolveCompetition maps loose user text ("brasileirao", "libertadores",
// "serie b") onto a canonical competition name present in the data.
func (g *Graph) resolveCompetition(q string) string {
	needle := normalize.Deaccent(strings.TrimSpace(q))
	if needle == "" {
		return SerieA
	}
	for comp := range g.competitions {
		if normalize.Deaccent(comp) == needle {
			return comp
		}
	}
	// Common shorthands.
	switch {
	case strings.Contains(needle, "libertadores"):
		return Libertadores
	case strings.Contains(needle, "copa do brasil"), needle == "cup", needle == "copa":
		return CopaDoBrasil
	case strings.Contains(needle, "serie b"), strings.Contains(needle, "série b"):
		return SerieB
	case strings.Contains(needle, "serie c"):
		return SerieC
	case strings.Contains(needle, "serie a"), strings.Contains(needle, "brasileirao"),
		strings.Contains(needle, "brasileiro"):
		return SerieA
	}
	for comp := range g.competitions {
		if strings.Contains(normalize.Deaccent(comp), needle) {
			return comp
		}
	}
	return ""
}
