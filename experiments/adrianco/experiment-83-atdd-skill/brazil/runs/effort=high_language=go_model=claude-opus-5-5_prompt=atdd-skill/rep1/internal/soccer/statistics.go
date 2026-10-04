package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// Summary holds aggregate figures over a set of matches.
type Summary struct {
	Description    string   `json:"description"`
	Competition    string   `json:"competition,omitempty"`
	Season         int      `json:"season,omitempty"`
	Matches        int      `json:"matches"`
	Goals          int      `json:"goals"`
	AverageGoals   float64  `json:"average_goals"`
	HomeWins       int      `json:"home_wins"`
	Draws          int      `json:"draws"`
	AwayWins       int      `json:"away_wins"`
	HomeWinRate    float64  `json:"home_win_rate"`
	DrawRate       float64  `json:"draw_rate"`
	AwayWinRate    float64  `json:"away_win_rate"`
	AverageCorners *float64 `json:"average_corners,omitempty"`
	AverageShots   *float64 `json:"average_shots,omitempty"`
	Champion       string   `json:"champion,omitempty"`
	ChampionPoints int      `json:"champion_points,omitempty"`
	TopScoringTeam string   `json:"top_scoring_team,omitempty"`
}

func summarise(matches []*Match) Summary {
	var s Summary
	corners, cornerMatches, shots, shotMatches := 0, 0, 0, 0
	for _, m := range matches {
		s.Matches++
		s.Goals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			s.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			s.AwayWins++
		default:
			s.Draws++
		}
		if st := m.Stats; st != nil {
			if st.HomeCorners != nil && st.AwayCorners != nil {
				corners += *st.HomeCorners + *st.AwayCorners
				cornerMatches++
			}
			if st.HomeShots != nil && st.AwayShots != nil {
				shots += *st.HomeShots + *st.AwayShots
				shotMatches++
			}
		}
	}
	if s.Matches > 0 {
		s.AverageGoals = round2(float64(s.Goals) / float64(s.Matches))
	}
	s.HomeWinRate = percent(s.HomeWins, s.Matches)
	s.DrawRate = percent(s.Draws, s.Matches)
	s.AwayWinRate = percent(s.AwayWins, s.Matches)
	if cornerMatches > 0 {
		v := round2(float64(corners) / float64(cornerMatches))
		s.AverageCorners = &v
	}
	if shotMatches > 0 {
		v := round2(float64(shots) / float64(shotMatches))
		s.AverageShots = &v
	}
	return s
}

// CompetitionStats summarises the matches selected by the query.
func (s *Store) CompetitionStats(q MatchQuery) Summary {
	sum := summarise(s.FindMatches(q))
	sum.Description = "Statistics for " + strings.TrimPrefix(s.describe(q), "Matches ")
	if q.Team == "" && q.Competition == "" && q.Season == 0 {
		sum.Description = "Statistics for all matches in the dataset"
	}
	sum.Competition = string(q.Competition)
	sum.Season = q.Season
	return sum
}

func (s Summary) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", s.Description)
	if s.Matches == 0 {
		b.WriteString("- No matches found.\n")
		return b.String()
	}
	fmt.Fprintf(&b, "- Matches: %d\n- Goals: %d\n- Average goals per match: %.2f\n", s.Matches, s.Goals, s.AverageGoals)
	fmt.Fprintf(&b, "- Home win rate: %.1f%% (%d)\n- Draw rate: %.1f%% (%d)\n- Away win rate: %.1f%% (%d)\n",
		s.HomeWinRate, s.HomeWins, s.DrawRate, s.Draws, s.AwayWinRate, s.AwayWins)
	if s.AverageCorners != nil {
		fmt.Fprintf(&b, "- Average corners per match: %.2f (where recorded)\n", *s.AverageCorners)
	}
	if s.AverageShots != nil {
		fmt.Fprintf(&b, "- Average shots per match: %.2f (where recorded)\n", *s.AverageShots)
	}
	if s.Champion != "" {
		fmt.Fprintf(&b, "- Champion (calculated): %s, %d pts\n", s.Champion, s.ChampionPoints)
	}
	if s.TopScoringTeam != "" {
		fmt.Fprintf(&b, "- Top scoring team: %s\n", s.TopScoringTeam)
	}
	return b.String()
}

// BiggestWins lists the most one-sided results, largest margin first.
func (s *Store) BiggestWins(q MatchQuery, limit int) MatchList {
	var wins []*Match
	for _, m := range s.FindMatches(q) {
		if m.Margin() > 0 {
			wins = append(wins, m)
		}
	}
	sort.SliceStable(wins, func(i, j int) bool {
		if wins[i].Margin() != wins[j].Margin() {
			return wins[i].Margin() > wins[j].Margin()
		}
		ti, tj := wins[i].HomeGoals+wins[i].AwayGoals, wins[j].HomeGoals+wins[j].AwayGoals
		if ti != tj {
			return ti > tj
		}
		return wins[i].Date.Before(wins[j].Date)
	})
	if limit <= 0 {
		limit = 10
	}
	total := len(wins)
	if len(wins) > limit {
		wins = wins[:limit]
	}
	desc := "Biggest victories"
	if rest := strings.TrimPrefix(s.describe(q), "Matches"); rest != "" {
		desc += " —" + rest
	}
	return MatchList{Description: desc, Total: total, Returned: len(wins), Matches: s.views(wins)}
}

// SeasonComparison compares several seasons of a competition.
type SeasonComparison struct {
	Competition string    `json:"competition"`
	Seasons     []Summary `json:"seasons"`
}

// CompareSeasons summarises each season, naming the league champion.
func (s *Store) CompareSeasons(c Competition, seasons []int) SeasonComparison {
	if c == "" {
		c = SerieA
	}
	out := SeasonComparison{Competition: string(c)}
	for _, season := range seasons {
		q := MatchQuery{Competition: c, Season: season}
		sum := s.CompetitionStats(q)
		sum.Description = fmt.Sprintf("%d %s", season, c)
		if st, err := s.Standings(c, season); err == nil && c.IsLeague() {
			sum.Champion = st.Champion
			sum.ChampionPoints = st.Table[0].Points
			best := st.Table[0]
			for _, r := range st.Table {
				if r.GoalsFor > best.GoalsFor {
					best = r
				}
			}
			sum.TopScoringTeam = fmt.Sprintf("%s (%d goals)", best.Team, best.GoalsFor)
		}
		out.Seasons = append(out.Seasons, sum)
	}
	return out
}

func (c SeasonComparison) Text() string {
	var b strings.Builder
	fmt.Fprintf(&b, "%s season comparison:\n", c.Competition)
	for _, s := range c.Seasons {
		b.WriteString("\n" + s.Text())
	}
	return b.String()
}

// Overview describes the loaded datasets.
type Overview struct {
	Datasets     []Dataset `json:"datasets"`
	Matches      int       `json:"unique_matches"`
	Teams        int       `json:"teams"`
	Players      int       `json:"players"`
	Competitions []string  `json:"competitions"`
}

// Overview reports what was loaded from each provided dataset.
func (s *Store) Overview() Overview {
	o := Overview{Datasets: s.Datasets, Matches: len(s.Matches), Teams: len(s.Teams), Players: len(s.Players)}
	for _, c := range []Competition{SerieA, SerieB, SerieC, CopaDoBrasil, Libertadores} {
		if seasons := s.Seasons(c); len(seasons) > 0 {
			o.Competitions = append(o.Competitions, fmt.Sprintf("%s (%s)", c, seasonSpan(seasons)))
		}
	}
	return o
}

func (o Overview) Text() string {
	var b strings.Builder
	b.WriteString("Datasets loaded:\n")
	for _, d := range o.Datasets {
		if d.Error != "" {
			fmt.Fprintf(&b, "- %s (%s): NOT LOADED — %s\n", d.Name, d.File, d.Error)
			continue
		}
		fmt.Fprintf(&b, "- %s (%s): %d records", d.Name, d.File, d.Records)
		if d.Seasons != "" {
			fmt.Fprintf(&b, ", seasons %s", d.Seasons)
		}
		if d.Merged > 0 {
			fmt.Fprintf(&b, ", %d already recorded by another dataset", d.Merged)
		}
		if d.Skipped > 0 {
			fmt.Fprintf(&b, ", %d rows without a result (unplayed or abandoned) skipped", d.Skipped)
		}
		b.WriteString("\n")
	}
	fmt.Fprintf(&b, "\nUnique matches: %d\nTeams: %d\nPlayers: %d\nCompetitions: %s\n",
		o.Matches, o.Teams, o.Players, strings.Join(o.Competitions, ", "))
	return b.String()
}
