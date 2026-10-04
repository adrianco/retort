package soccer

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"time"
)

// NotFoundError says that a team, player or competition is not in the data.
type NotFoundError struct {
	Kind, Name  string
	Suggestions []string
}

func (e *NotFoundError) Error() string {
	msg := fmt.Sprintf("No %s called %q was found in the data.", e.Kind, e.Name)
	if len(e.Suggestions) > 0 {
		msg += " Did you mean: " + strings.Join(e.Suggestions, ", ") + "?"
	}
	return msg
}

// ResolveTeam finds the team a user means, however they spell it.
func (s *Store) ResolveTeam(name string) (string, error) {
	if strings.TrimSpace(name) == "" {
		return "", fmt.Errorf("a team name is needed")
	}
	if key := NormalizeTeam(name).Key; s.Teams[key] != nil {
		return key, nil
	}
	candidates := s.similarTeams(name)
	if len(candidates) > 0 {
		return candidates[0].Key, nil
	}
	return "", &NotFoundError{Kind: "team", Name: name}
}

// similarTeams finds teams whose names contain the words asked for,
// major clubs and frequently recorded teams first.
func (s *Store) similarTeams(name string) []*Team {
	q := Fold(name)
	if len(q) < 3 {
		return nil
	}
	var found []*Team
	for _, t := range s.Teams {
		match := strings.Contains(Fold(t.Display), q)
		for v := range t.Variants {
			match = match || strings.Contains(Fold(v), q)
		}
		if match {
			found = append(found, t)
		}
	}
	sort.Slice(found, func(i, j int) bool {
		if found[i].Known != found[j].Known {
			return found[i].Known
		}
		ci, cj := total(found[i].Variants), total(found[j].Variants)
		if ci != cj {
			return ci > cj
		}
		return found[i].Key < found[j].Key
	})
	return found
}

func total(m map[string]int) int {
	n := 0
	for _, c := range m {
		n += c
	}
	return n
}

// MatchQuery selects matches. Zero values mean "any".
type MatchQuery struct {
	Team        string // team key
	Opponent    string // team key
	Venue       string // "home" or "away", from the team's point of view
	Competition Competition
	Season      int
	From, To    time.Time
	Stage       string
	DerbiesOnly bool
}

// FindMatches returns the matches meeting the query, oldest first.
func (s *Store) FindMatches(q MatchQuery) []*Match {
	stage := NormalizeStage(q.Stage)
	var out []*Match
	for _, m := range s.Matches {
		if q.Team != "" {
			switch q.Venue {
			case "home":
				if m.HomeKey != q.Team {
					continue
				}
			case "away":
				if m.AwayKey != q.Team {
					continue
				}
			default:
				if !m.Involves(q.Team) {
					continue
				}
			}
			if q.Opponent != "" && m.Opponent(q.Team) != q.Opponent {
				continue
			}
		} else if q.Opponent != "" && !m.Involves(q.Opponent) {
			continue
		}
		if q.Competition != "" && m.Competition != q.Competition {
			continue
		}
		if q.Season != 0 && m.Season != q.Season {
			continue
		}
		if !q.From.IsZero() && m.Date.Before(q.From) {
			continue
		}
		if !q.To.IsZero() && !m.Date.Before(q.To.AddDate(0, 0, 1)) {
			continue
		}
		if stage != "" && m.Stage != stage {
			continue
		}
		if q.DerbiesOnly && DerbyName(m.HomeKey, m.AwayKey) == "" {
			continue
		}
		out = append(out, m)
	}
	return out
}

// NormalizeStage maps the ways people name a knockout stage to the names
// the data uses.
func NormalizeStage(stage string) string {
	s := strings.ReplaceAll(Fold(stage), "-", "")
	switch s {
	case "":
		return ""
	case "final", "finals", "the final":
		return "final"
	case "semifinal", "semifinals", "semis", "semi finals", "semi final":
		return "semifinals"
	case "quarterfinal", "quarterfinals", "quarter finals", "quarter final":
		return "quarterfinals"
	case "round of 16", "last 16", "round of sixteen", "eighth finals", "eighthfinals":
		return "round of 16"
	case "group", "groups", "group stage", "group phase":
		return "group stage"
	}
	return s
}

var stageLabels = map[string]string{
	"final": "Final", "semifinals": "Semi-finals", "quarterfinals": "Quarter-finals",
	"round of 16": "Round of 16", "group stage": "Group stage",
}

// StageLabel is how a stage is written in answers.
func StageLabel(stage string) string {
	if l, ok := stageLabels[stage]; ok {
		return l
	}
	return titleCase(stage)
}

type rivalry struct{ a, b, name string }

var rivalries = []rivalry{
	{"flamengo", "fluminense", "Fla-Flu"},
	{"flamengo", "vasco", "Clássico dos Milhões"},
	{"botafogo-rj", "flamengo", "Clássico da Rivalidade"},
	{"fluminense", "vasco", "Clássico dos Gigantes"},
	{"botafogo-rj", "fluminense", "Clássico Vovô"},
	{"botafogo-rj", "vasco", "Clássico da Amizade"},
	{"corinthians", "palmeiras", "Derby Paulista"},
	{"palmeiras", "sao paulo", "Choque-Rei"},
	{"corinthians", "sao paulo", "Majestoso"},
	{"santos", "sao paulo", "San-São"},
	{"corinthians", "santos", "Clássico Alvinegro"},
	{"palmeiras", "santos", "Clássico da Saudade"},
	{"gremio", "internacional", "Grenal"},
	{"atletico-mg", "cruzeiro", "Clássico Mineiro"},
	{"athletico-pr", "coritiba", "Atletiba"},
	{"bahia", "vitoria", "Ba-Vi"},
	{"ceara", "fortaleza", "Clássico-Rei"},
	{"santa cruz", "sport", "Clássico das Multidões"},
	{"nautico", "sport", "Clássico dos Clássicos"},
	{"goias", "vila nova", "Derby Goiano"},
	{"avai", "figueirense", "Clássico da Ilha"},
	{"paysandu", "remo", "Re-Pa"},
	{"boca juniors", "river plate", "Superclásico"},
}

// DerbyName names the traditional rivalry between two teams, if any.
func DerbyName(a, b string) string {
	for _, r := range rivalries {
		if (r.a == a && r.b == b) || (r.a == b && r.b == a) {
			return r.name
		}
	}
	return ""
}

// MatchView is a match as presented to the user.
type MatchView struct {
	Date        string     `json:"date"`
	Competition string     `json:"competition"`
	Season      int        `json:"season"`
	Round       int        `json:"round,omitempty"`
	Stage       string     `json:"stage,omitempty"`
	Home        string     `json:"home"`
	Away        string     `json:"away"`
	HomeGoals   int        `json:"home_goals"`
	AwayGoals   int        `json:"away_goals"`
	Derby       string     `json:"derby,omitempty"`
	Arena       string     `json:"arena,omitempty"`
	Stats       *StatsView `json:"stats,omitempty"`
	Sources     []string   `json:"sources"`
}

// StatsView holds the extended statistics of a match, where recorded.
type StatsView struct {
	HomeCorners *int `json:"home_corners,omitempty"`
	AwayCorners *int `json:"away_corners,omitempty"`
	HomeShots   *int `json:"home_shots,omitempty"`
	AwayShots   *int `json:"away_shots,omitempty"`
	HomeAttacks *int `json:"home_attacks,omitempty"`
	AwayAttacks *int `json:"away_attacks,omitempty"`
}

func (s *Store) view(m *Match) MatchView {
	v := MatchView{
		Date: m.Date.Format("2006-01-02"), Competition: string(m.Competition), Season: m.Season,
		Round: m.Round, Stage: m.Stage, Home: s.Display(m.HomeKey), Away: s.Display(m.AwayKey),
		HomeGoals: m.HomeGoals, AwayGoals: m.AwayGoals, Derby: DerbyName(m.HomeKey, m.AwayKey),
		Arena: m.Arena, Sources: m.Sources,
	}
	if m.Stats != nil {
		v.Stats = &StatsView{m.Stats.HomeCorners, m.Stats.AwayCorners, m.Stats.HomeShots, m.Stats.AwayShots, m.Stats.HomeAttacks, m.Stats.AwayAttacks}
	}
	return v
}

func (s *Store) views(ms []*Match) []MatchView {
	out := make([]MatchView, 0, len(ms))
	for _, m := range ms {
		out = append(out, s.view(m))
	}
	return out
}

// Line is the one-line description of a match used in answers, e.g.
// "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)".
func (v MatchView) Line() string {
	context := v.Competition
	switch {
	case v.Stage != "":
		context += ", " + StageLabel(v.Stage)
	case v.Round > 0:
		context += fmt.Sprintf(", Round %d", v.Round)
	}
	line := fmt.Sprintf("%s: %s %d-%d %s (%s)", v.Date, v.Home, v.HomeGoals, v.AwayGoals, v.Away, context)
	if v.Derby != "" {
		line += " — " + v.Derby
	}
	if v.Stats != nil {
		var extra []string
		if v.Stats.HomeCorners != nil && v.Stats.AwayCorners != nil {
			extra = append(extra, fmt.Sprintf("corners %d-%d", *v.Stats.HomeCorners, *v.Stats.AwayCorners))
		}
		if v.Stats.HomeShots != nil && v.Stats.AwayShots != nil {
			extra = append(extra, fmt.Sprintf("shots %d-%d", *v.Stats.HomeShots, *v.Stats.AwayShots))
		}
		if len(extra) > 0 {
			line += " [" + strings.Join(extra, ", ") + "]"
		}
	}
	return line
}

// MatchList is a list of matches found.
type MatchList struct {
	Description string      `json:"description"`
	Total       int         `json:"total"`
	Returned    int         `json:"returned"`
	Matches     []MatchView `json:"matches"`
	HeadToHead  *HeadToHead `json:"head_to_head,omitempty"`
}

func (l MatchList) Text() string {
	var b strings.Builder
	if l.Total == 0 {
		fmt.Fprintf(&b, "%s: no matches found in the dataset.\n", l.Description)
		return b.String()
	}
	fmt.Fprintf(&b, "%s — %d %s found:\n", l.Description, l.Total, plural(l.Total, "match", "matches"))
	for _, m := range l.Matches {
		b.WriteString("- " + m.Line() + "\n")
	}
	if l.Total > l.Returned {
		fmt.Fprintf(&b, "- ... (%d more %s in dataset)\n", l.Total-l.Returned, plural(l.Total-l.Returned, "match", "matches"))
	}
	if h := l.HeadToHead; h != nil {
		fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws (goals %d-%d)\n",
			h.TeamA, h.TeamAWins, h.TeamB, h.TeamBWins, h.Draws, h.TeamAGoals, h.TeamBGoals)
	}
	return b.String()
}

func plural(n int, one, many string) string {
	if n == 1 {
		return one
	}
	return many
}

// SearchMatches lists matches, most recent first unless oldest first is asked for.
func (s *Store) SearchMatches(q MatchQuery, limit int, oldestFirst bool) MatchList {
	found := s.FindMatches(q)
	list := MatchList{Description: s.describe(q), Total: len(found)}
	ordered := make([]*Match, len(found))
	copy(ordered, found)
	if !oldestFirst {
		for i, j := 0, len(ordered)-1; i < j; i, j = i+1, j-1 {
			ordered[i], ordered[j] = ordered[j], ordered[i]
		}
	}
	if limit > 0 && len(ordered) > limit {
		ordered = ordered[:limit]
	}
	list.Matches = s.views(ordered)
	list.Returned = len(list.Matches)
	if q.Team != "" && q.Opponent != "" {
		h := s.headToHead(q.Team, q.Opponent, found)
		list.HeadToHead = &h
	}
	return list
}

// describe writes a query out in words, e.g. "Flamengo vs Fluminense (Fla-Flu)".
func (s *Store) describe(q MatchQuery) string {
	var parts []string
	switch {
	case q.Team != "" && q.Opponent != "":
		d := s.Display(q.Team) + " vs " + s.Display(q.Opponent)
		if name := DerbyName(q.Team, q.Opponent); name != "" {
			d += " (" + name + ")"
		}
		parts = append(parts, d)
	case q.Team != "":
		d := s.Display(q.Team)
		if q.Venue != "" {
			d += " " + q.Venue
		}
		parts = append(parts, d+" matches")
	case q.Opponent != "":
		parts = append(parts, "Matches against "+s.Display(q.Opponent))
	case q.DerbiesOnly:
		parts = append(parts, "Derbies")
	default:
		parts = append(parts, "Matches")
	}
	if q.DerbiesOnly && q.Team != "" {
		parts = append(parts, "derbies only")
	}
	if q.Competition != "" {
		parts = append(parts, "in "+string(q.Competition))
	}
	if q.Stage != "" {
		parts = append(parts, "("+StageLabel(NormalizeStage(q.Stage))+")")
	}
	if q.Season != 0 {
		parts = append(parts, fmt.Sprintf("in %d", q.Season))
	}
	if !q.From.IsZero() {
		parts = append(parts, "from "+q.From.Format("2006-01-02"))
	}
	if !q.To.IsZero() {
		parts = append(parts, "to "+q.To.Format("2006-01-02"))
	}
	return strings.Join(parts, " ")
}

// LastMeeting finds the most recent match between two teams.
func (s *Store) LastMeeting(team, opponent string) MatchList {
	found := s.FindMatches(MatchQuery{Team: team, Opponent: opponent})
	list := MatchList{Description: fmt.Sprintf("Last meeting of %s and %s", s.Display(team), s.Display(opponent))}
	if len(found) > 0 {
		list.Matches = []MatchView{s.view(found[len(found)-1])}
		list.Total, list.Returned = 1, 1
	}
	return list
}

// HeadToHead summarises all meetings between two teams.
type HeadToHead struct {
	TeamA         string           `json:"team_a"`
	TeamB         string           `json:"team_b"`
	Derby         string           `json:"derby,omitempty"`
	Meetings      int              `json:"meetings"`
	TeamAWins     int              `json:"team_a_wins"`
	TeamBWins     int              `json:"team_b_wins"`
	Draws         int              `json:"draws"`
	TeamAGoals    int              `json:"team_a_goals"`
	TeamBGoals    int              `json:"team_b_goals"`
	ByCompetition []HeadToHeadPart `json:"by_competition,omitempty"`
	RecentMatches []MatchView      `json:"recent_matches,omitempty"`
	BiggestWin    *MatchView       `json:"biggest_win,omitempty"`
}

// HeadToHeadPart is the head-to-head within one competition.
type HeadToHeadPart struct {
	Competition string `json:"competition"`
	Meetings    int    `json:"meetings"`
	TeamAWins   int    `json:"team_a_wins"`
	TeamBWins   int    `json:"team_b_wins"`
	Draws       int    `json:"draws"`
}

func (s *Store) headToHead(a, b string, matches []*Match) HeadToHead {
	h := HeadToHead{TeamA: s.Display(a), TeamB: s.Display(b), Derby: DerbyName(a, b)}
	parts := map[Competition]*HeadToHeadPart{}
	var order []Competition
	var biggest *Match
	for _, m := range matches {
		ga, gb := m.GoalsFor(a)
		h.Meetings++
		h.TeamAGoals += ga
		h.TeamBGoals += gb
		p, ok := parts[m.Competition]
		if !ok {
			p = &HeadToHeadPart{Competition: string(m.Competition)}
			parts[m.Competition] = p
			order = append(order, m.Competition)
		}
		p.Meetings++
		switch {
		case ga > gb:
			h.TeamAWins++
			p.TeamAWins++
		case gb > ga:
			h.TeamBWins++
			p.TeamBWins++
		default:
			h.Draws++
			p.Draws++
		}
		if biggest == nil || m.Margin() > biggest.Margin() {
			biggest = m
		}
	}
	for _, c := range order {
		h.ByCompetition = append(h.ByCompetition, *parts[c])
	}
	for i := len(matches) - 1; i >= 0 && len(h.RecentMatches) < 5; i-- {
		h.RecentMatches = append(h.RecentMatches, s.view(matches[i]))
	}
	if biggest != nil && biggest.Margin() > 0 {
		v := s.view(biggest)
		h.BiggestWin = &v
	}
	return h
}

// HeadToHead compares two teams across every competition.
func (s *Store) HeadToHead(a, b string, competition Competition) HeadToHead {
	return s.headToHead(a, b, s.FindMatches(MatchQuery{Team: a, Opponent: b, Competition: competition}))
}

func (h HeadToHead) Text() string {
	var b strings.Builder
	title := h.TeamA + " vs " + h.TeamB
	if h.Derby != "" {
		title += " (" + h.Derby + ")"
	}
	fmt.Fprintf(&b, "%s head-to-head:\n", title)
	if h.Meetings == 0 {
		b.WriteString("- These teams have not met in the dataset.\n")
		return b.String()
	}
	fmt.Fprintf(&b, "- Meetings: %d\n- %s wins: %d, %s wins: %d, Draws: %d\n- Goals: %s %d, %s %d\n",
		h.Meetings, h.TeamA, h.TeamAWins, h.TeamB, h.TeamBWins, h.Draws, h.TeamA, h.TeamAGoals, h.TeamB, h.TeamBGoals)
	for _, p := range h.ByCompetition {
		fmt.Fprintf(&b, "- %s: %d meetings (%s %d, %s %d, draws %d)\n", p.Competition, p.Meetings, h.TeamA, p.TeamAWins, h.TeamB, p.TeamBWins, p.Draws)
	}
	if h.BiggestWin != nil {
		fmt.Fprintf(&b, "- Biggest win: %s\n", h.BiggestWin.Line())
	}
	if len(h.RecentMatches) > 0 {
		b.WriteString("Recent meetings:\n")
		for _, m := range h.RecentMatches {
			b.WriteString("- " + m.Line() + "\n")
		}
	}
	return b.String()
}

func percent(part, whole int) float64 {
	if whole == 0 {
		return 0
	}
	return math.Round(float64(part)*1000/float64(whole)) / 10
}

func round2(x float64) float64 { return math.Round(x*100) / 100 }
