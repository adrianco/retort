package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// StandingRow is one line of a league table.
type StandingRow struct {
	Position       int    `json:"position"`
	Team           string `json:"team"`
	Played         int    `json:"played"`
	Wins           int    `json:"wins"`
	Draws          int    `json:"draws"`
	Losses         int    `json:"losses"`
	GoalsFor       int    `json:"goals_for"`
	GoalsAgainst   int    `json:"goals_against"`
	GoalDifference int    `json:"goal_difference"`
	Points         int    `json:"points"`
	Status         string `json:"status,omitempty"`
}

// Standings is a league table calculated from match results.
type Standings struct {
	Competition string        `json:"competition"`
	Season      int           `json:"season"`
	Matches     int           `json:"matches"`
	Complete    bool          `json:"complete"`
	Note        string        `json:"note,omitempty"`
	Leader      string        `json:"leader,omitempty"`
	Champion    string        `json:"champion,omitempty"`
	Relegated   []string      `json:"relegated"`
	Promoted    []string      `json:"promoted,omitempty"`
	Table       []StandingRow `json:"table"`
}

// Seasons lists the seasons of a competition in the data.
func (s *Store) Seasons(c Competition) []int {
	seen := map[int]bool{}
	for _, m := range s.Matches {
		if m.Competition == c {
			seen[m.Season] = true
		}
	}
	var out []int
	for season := range seen {
		out = append(out, season)
	}
	sort.Ints(out)
	return out
}

// Teams relegated from and promoted out of a full-size league.
const (
	relegationPlaces = 4
	fullLeagueSize   = 16
)

// Standings calculates the table: 3 points a win, 1 a draw, ranked by
// points, then wins, then goal difference, then goals scored. A full-size
// league season the data does not completely cover gets a provisional
// table: it names the leader and the relegation zone, but no champion
// and no relegated teams.
func (s *Store) Standings(c Competition, season int) (Standings, error) {
	if c == "" {
		c = SerieA
	}
	if !c.IsLeague() {
		return Standings{}, fmt.Errorf("%s is a knockout competition; ask for its knockout bracket instead", c)
	}
	if season == 0 {
		seasons := s.Seasons(c)
		if len(seasons) == 0 {
			return Standings{}, &NotFoundError{Kind: "competition", Name: string(c)}
		}
		season = seasons[len(seasons)-1]
	}
	matches := s.FindMatches(MatchQuery{Competition: c, Season: season})
	if len(matches) == 0 {
		return Standings{}, fmt.Errorf("no %s matches were found for the %d season; seasons in the data: %s",
			c, season, joinInts(s.Seasons(c)))
	}
	records := s.tallyAll(matches, "")
	st := Standings{Competition: string(c), Season: season, Matches: len(matches), Relegated: []string{}}
	for _, r := range records {
		st.Table = append(st.Table, StandingRow{Team: r.Team, Played: r.Matches, Wins: r.Wins, Draws: r.Draws,
			Losses: r.Losses, GoalsFor: r.GoalsFor, GoalsAgainst: r.GoalsAgainst, GoalDifference: r.GoalDifference, Points: r.Points})
	}
	sort.Slice(st.Table, func(i, j int) bool {
		a, b := st.Table[i], st.Table[j]
		switch {
		case a.Points != b.Points:
			return a.Points > b.Points
		case a.Wins != b.Wins:
			return a.Wins > b.Wins
		case a.GoalDifference != b.GoalDifference:
			return a.GoalDifference > b.GoalDifference
		case a.GoalsFor != b.GoalsFor:
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	n := len(st.Table)
	fullSize := n >= fullLeagueSize
	st.Complete = !fullSize || st.Matches >= n*(n-1)
	if !st.Complete {
		st.Note = fmt.Sprintf("The dataset holds only %d of the %d matches of this season, so this table is provisional.", st.Matches, n*(n-1))
	}
	st.Leader = st.Table[0].Team
	for i := range st.Table {
		row := &st.Table[i]
		row.Position = i + 1
		top, bottom := i < relegationPlaces, i >= n-relegationPlaces
		switch {
		case c == SerieC:
			// Played in groups, so the table decides nothing on its own.
		case i == 0 && st.Complete:
			row.Status = "Champion"
			st.Champion = row.Team
		case i == 0:
			row.Status = "Leader"
		case c == SerieB && fullSize && top && st.Complete:
			row.Status = "Promoted"
			st.Promoted = append(st.Promoted, row.Team)
		case fullSize && bottom && st.Complete:
			row.Status = "Relegated"
			st.Relegated = append(st.Relegated, row.Team)
		case fullSize && bottom:
			row.Status = "Relegation zone"
		}
		if c == SerieB && i == 0 && fullSize && st.Complete {
			st.Promoted = append(st.Promoted, row.Team)
		}
	}
	return st, nil
}

func joinInts(xs []int) string {
	parts := make([]string, len(xs))
	for i, x := range xs {
		parts[i] = fmt.Sprint(x)
	}
	return strings.Join(parts, ", ")
}

func (st Standings) Text() string {
	var b strings.Builder
	kind := "Final Standings"
	if !st.Complete {
		kind = "Provisional Standings"
	}
	fmt.Fprintf(&b, "%d %s %s (calculated from %d matches):\n", st.Season, st.Competition, kind, st.Matches)
	if st.Note != "" {
		b.WriteString(st.Note + "\n")
	}
	for _, r := range st.Table {
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d, GD %+d)", r.Position, r.Team, r.Points,
			r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDifference)
		if r.Status != "" {
			b.WriteString(" - " + r.Status)
		}
		b.WriteString("\n")
	}
	if len(st.Relegated) > 0 {
		fmt.Fprintf(&b, "\nRelegated: %s\n", strings.Join(st.Relegated, ", "))
	}
	return b.String()
}

// Tie is a knockout tie of one or two legs.
type Tie struct {
	TeamA      string      `json:"team_a"`
	TeamB      string      `json:"team_b"`
	TeamAGoals int         `json:"team_a_goals"`
	TeamBGoals int         `json:"team_b_goals"`
	Aggregate  string      `json:"aggregate"`
	Winner     string      `json:"winner"`
	Decided    string      `json:"decided_by,omitempty"`
	Legs       []MatchView `json:"legs"`
}

// BracketStage is one stage of a knockout bracket.
type BracketStage struct {
	Stage string `json:"stage"`
	Ties  []Tie  `json:"ties"`
}

// Bracket is the knockout part of a cup season.
type Bracket struct {
	Competition string         `json:"competition"`
	Season      int            `json:"season"`
	Stages      []BracketStage `json:"stages"`
}

var stageOrder = map[string]int{"round of 16": 1, "quarterfinals": 2, "semifinals": 3, "final": 4}

// Bracket assembles the knockout ties of a cup season from its matches.
func (s *Store) Bracket(c Competition, season int) (Bracket, error) {
	if c == "" {
		c = Libertadores
	}
	if c.IsLeague() {
		return Bracket{}, fmt.Errorf("%s is a league; ask for its standings instead", c)
	}
	if season == 0 {
		seasons := s.Seasons(c)
		if len(seasons) == 0 {
			return Bracket{}, &NotFoundError{Kind: "competition", Name: string(c)}
		}
		season = seasons[len(seasons)-1]
	}
	byStage := map[string][]*Match{}
	for _, m := range s.FindMatches(MatchQuery{Competition: c, Season: season}) {
		if _, knockout := stageOrder[m.Stage]; knockout {
			byStage[m.Stage] = append(byStage[m.Stage], m)
		}
	}
	if len(byStage) == 0 {
		return Bracket{}, fmt.Errorf("no knockout matches of %s were found for %d; seasons in the data: %s",
			c, season, joinInts(s.Seasons(c)))
	}
	b := Bracket{Competition: string(c), Season: season}
	for stage, matches := range byStage {
		b.Stages = append(b.Stages, BracketStage{Stage: stage, Ties: s.ties(matches)})
	}
	sort.Slice(b.Stages, func(i, j int) bool { return stageOrder[b.Stages[i].Stage] < stageOrder[b.Stages[j].Stage] })
	return b, nil
}

// ties groups the matches of one stage into ties, in order of first leg.
func (s *Store) ties(matches []*Match) []Tie {
	legs := map[string][]*Match{}
	var order []string
	for _, m := range matches {
		k := pairingKey(m)
		if _, ok := legs[k]; !ok {
			order = append(order, k)
		}
		legs[k] = append(legs[k], m)
	}
	var out []Tie
	for _, k := range order {
		ms := legs[k]
		a, b := ms[0].HomeKey, ms[0].AwayKey
		tie := Tie{TeamA: s.Display(a), TeamB: s.Display(b)}
		awayA, awayB := 0, 0
		for _, m := range ms {
			ga, gb := m.GoalsFor(a)
			tie.TeamAGoals += ga
			tie.TeamBGoals += gb
			if m.AwayKey == a {
				awayA += ga
			} else {
				awayB += gb
			}
			tie.Legs = append(tie.Legs, s.view(m))
		}
		tie.Aggregate = fmt.Sprintf("%d-%d", tie.TeamAGoals, tie.TeamBGoals)
		switch {
		case tie.TeamAGoals > tie.TeamBGoals:
			tie.Winner = tie.TeamA
		case tie.TeamBGoals > tie.TeamAGoals:
			tie.Winner = tie.TeamB
		case len(ms) == 2 && awayA > awayB:
			tie.Winner, tie.Decided = tie.TeamA, "away goals"
		case len(ms) == 2 && awayB > awayA:
			tie.Winner, tie.Decided = tie.TeamB, "away goals"
		default:
			tie.Decided = "level on aggregate; shoot-out result not in data"
		}
		out = append(out, tie)
	}
	return out
}

func (b Bracket) Text() string {
	var sb strings.Builder
	fmt.Fprintf(&sb, "%d %s knockout bracket:\n", b.Season, b.Competition)
	for _, st := range b.Stages {
		outcome := "advance"
		if st.Stage == "final" {
			outcome = "win the title"
		}
		fmt.Fprintf(&sb, "\n%s:\n", StageLabel(st.Stage))
		for _, t := range st.Ties {
			fmt.Fprintf(&sb, "- %s v %s: aggregate %s", t.TeamA, t.TeamB, t.Aggregate)
			if t.Winner != "" {
				fmt.Fprintf(&sb, " — %s %s", t.Winner, outcome)
			}
			if t.Decided != "" {
				fmt.Fprintf(&sb, " (%s)", t.Decided)
			}
			sb.WriteString("\n")
			for _, leg := range t.Legs {
				sb.WriteString("    " + leg.Line() + "\n")
			}
		}
	}
	return sb.String()
}
