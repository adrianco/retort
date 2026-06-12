// queries.go: the high-level query API. Each method takes simple parameters,
// resolves fuzzy team/competition names, runs the relevant primitive + analysis
// and returns a formatted, LLM-ready answer string. The MCP tool layer
// (package main) is a thin adapter over these methods.
package soccer

import (
	"fmt"
	"strings"
	"time"
)

// ResolveCompetition maps a user phrase to a canonical competition name. The
// second return is false when the phrase is non-empty but unrecognized.
func ResolveCompetition(input string) (string, bool) {
	in := strings.TrimSpace(input)
	if in == "" {
		return "", true // no filter
	}
	switch FoldAccents(strings.ToLower(in)) {
	case "brasileirao", "brasileirao serie a", "serie a", "campeonato brasileiro",
		"brazilian league", "brasileirao seria a", "brasileiro", "serie a brasileirao":
		return CompSerieA, true
	case "brasileirao serie b", "serie b":
		return CompSerieB, true
	case "brasileirao serie c", "serie c":
		return CompSerieC, true
	case "copa do brasil", "brazilian cup", "cup", "copa brasil":
		return CompCopaBrasil, true
	case "libertadores", "copa libertadores", "conmebol libertadores":
		return CompLibertadores, true
	}
	// Fall back to exact canonical match.
	for _, c := range []string{CompSerieA, CompSerieB, CompSerieC, CompCopaBrasil, CompLibertadores} {
		if FoldAccents(strings.ToLower(c)) == FoldAccents(strings.ToLower(in)) {
			return c, true
		}
	}
	return "", false
}

// teamNotFound builds a helpful error string for an unresolved team.
func (s *Store) teamNotFound(query string, candidates []string) string {
	if len(candidates) > 0 {
		return fmt.Sprintf("Team %q is ambiguous. Did you mean: %s?",
			query, strings.Join(candidates, ", "))
	}
	return fmt.Sprintf("No team matching %q was found in the dataset.", query)
}

// MatchQuery holds the parameters of SearchMatches.
type MatchQuery struct {
	Team        string
	HomeTeam    string
	AwayTeam    string
	Opponent    string
	Competition string
	Season      int
	SeasonMin   int
	SeasonMax   int
	DateFrom    string
	DateTo      string
	Limit       int
}

// SearchMatches finds matches by team/competition/season/date and returns a
// formatted list plus a head-to-head summary when two teams are specified.
func (s *Store) SearchMatches(q MatchQuery) string {
	f := MatchFilter{Season: q.Season, SeasonMin: q.SeasonMin, SeasonMax: q.SeasonMax}

	comp, ok := ResolveCompetition(q.Competition)
	if !ok {
		return fmt.Sprintf("Unknown competition %q. Known competitions: %s.",
			q.Competition, strings.Join(s.Competitions(), ", "))
	}
	f.Competition = comp

	var teamDisp, oppDisp string
	if q.Team != "" {
		key, disp, cands, found := s.ResolveTeam(q.Team)
		if !found {
			return s.teamNotFound(q.Team, cands)
		}
		f.TeamKey, teamDisp = key, disp
	}
	if q.Opponent != "" {
		key, disp, cands, found := s.ResolveTeam(q.Opponent)
		if !found {
			return s.teamNotFound(q.Opponent, cands)
		}
		f.OpponentKey, oppDisp = key, disp
	}
	if q.HomeTeam != "" {
		key, _, cands, found := s.ResolveTeam(q.HomeTeam)
		if !found {
			return s.teamNotFound(q.HomeTeam, cands)
		}
		f.HomeKey = key
	}
	if q.AwayTeam != "" {
		key, _, cands, found := s.ResolveTeam(q.AwayTeam)
		if !found {
			return s.teamNotFound(q.AwayTeam, cands)
		}
		f.AwayKey = key
	}
	if t, err := parseUserDate(q.DateFrom); err != nil {
		return err.Error()
	} else {
		f.DateFrom = t
	}
	if t, err := parseUserDate(q.DateTo); err != nil {
		return err.Error()
	} else if !t.IsZero() {
		f.DateTo = t.Add(24 * time.Hour) // make end date inclusive
	}

	matches := s.FindMatchesClean(f)
	limit := q.Limit
	if limit == 0 {
		limit = 25
	}

	var b strings.Builder
	header := "Matches"
	if teamDisp != "" && oppDisp != "" {
		header = fmt.Sprintf("%s vs %s", teamDisp, oppDisp)
	} else if teamDisp != "" {
		header = fmt.Sprintf("%s matches", teamDisp)
	}
	fmt.Fprintf(&b, "%s — %d found:\n%s", header, len(matches), FormatMatchList(matches, limit))

	// Head-to-head summary when both sides are specified.
	if f.TeamKey != "" && f.OpponentKey != "" && len(matches) > 0 {
		h := HeadToHead(matches, f.TeamKey, f.OpponentKey, teamDisp, oppDisp)
		fmt.Fprintf(&b, "\n\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws (goals %d-%d).",
			h.TeamA, h.WinsA, h.TeamB, h.WinsB, h.Draws, h.GoalsA, h.GoalsB)
	}
	return b.String()
}

// HeadToHeadQuery compares two teams directly.
func (s *Store) HeadToHeadQuery(teamA, teamB, competition string, season int, limit int) string {
	keyA, dispA, candsA, okA := s.ResolveTeam(teamA)
	if !okA {
		return s.teamNotFound(teamA, candsA)
	}
	keyB, dispB, candsB, okB := s.ResolveTeam(teamB)
	if !okB {
		return s.teamNotFound(teamB, candsB)
	}
	comp, ok := ResolveCompetition(competition)
	if !ok {
		return fmt.Sprintf("Unknown competition %q.", competition)
	}
	matches := s.FindMatchesClean(MatchFilter{TeamKey: keyA, OpponentKey: keyB, Competition: comp, Season: season})
	h := HeadToHead(matches, keyA, keyB, dispA, dispB)
	if limit == 0 {
		limit = 10
	}
	scope := "all competitions"
	if comp != "" {
		scope = comp
	}
	if season != 0 {
		scope = fmt.Sprintf("%s, %d", scope, season)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s head-to-head (%s):\n", dispA, dispB, scope)
	fmt.Fprintf(&b, "- Matches: %d\n- %s wins: %d\n- %s wins: %d\n- Draws: %d\n- Goals: %s %d, %s %d\n",
		h.Matches, dispA, h.WinsA, dispB, h.WinsB, h.Draws, dispA, h.GoalsA, dispB, h.GoalsB)
	if h.Matches > 0 {
		b.WriteString("\nMost recent meetings:\n")
		recent := lastN(matches, limit)
		b.WriteString(FormatMatchList(recent, limit))
	}
	return b.String()
}

// TeamRecordQuery reports a team's record, optionally by competition/season/venue.
func (s *Store) TeamRecordQuery(team, competition string, season int, venue Venue) string {
	key, disp, cands, ok := s.ResolveTeam(team)
	if !ok {
		return s.teamNotFound(team, cands)
	}
	comp, okc := ResolveCompetition(competition)
	if !okc {
		return fmt.Sprintf("Unknown competition %q.", competition)
	}
	matches := s.FindMatchesClean(MatchFilter{TeamKey: key, Competition: comp, Season: season})
	rec := TeamRecord(matches, key, disp, venue)

	scopeParts := []string{}
	switch venue {
	case VenueHome:
		scopeParts = append(scopeParts, "home")
	case VenueAway:
		scopeParts = append(scopeParts, "away")
	}
	if season != 0 {
		scopeParts = append(scopeParts, fmt.Sprintf("%d", season))
	}
	if comp != "" {
		scopeParts = append(scopeParts, comp)
	}
	title := disp + " record"
	if len(scopeParts) > 0 {
		title = fmt.Sprintf("%s %s record", disp, strings.Join(scopeParts, " "))
	}
	return FormatRecord(rec, title)
}

// TeamCompetitionsQuery lists which competitions a team appears in.
func (s *Store) TeamCompetitionsQuery(team string) string {
	key, disp, cands, ok := s.ResolveTeam(team)
	if !ok {
		return s.teamNotFound(team, cands)
	}
	type agg struct {
		n        int
		min, max int
	}
	byComp := map[string]*agg{}
	for _, m := range s.FindMatchesClean(MatchFilter{TeamKey: key}) {
		a := byComp[m.Competition]
		if a == nil {
			a = &agg{min: m.Season, max: m.Season}
			byComp[m.Competition] = a
		}
		a.n++
		if m.Season != 0 {
			if a.min == 0 || m.Season < a.min {
				a.min = m.Season
			}
			if m.Season > a.max {
				a.max = m.Season
			}
		}
	}
	if len(byComp) == 0 {
		return fmt.Sprintf("%s has no matches in the dataset.", disp)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s appears in %d competition(s):\n", disp, len(byComp))
	for _, c := range []string{CompSerieA, CompSerieB, CompSerieC, CompCopaBrasil, CompLibertadores} {
		if a, ok := byComp[c]; ok {
			fmt.Fprintf(&b, "- %s: %d matches (%d–%d)\n", c, a.n, a.min, a.max)
		}
	}
	return strings.TrimRight(b.String(), "\n")
}

// StandingsQuery builds a league table for a competition + season.
func (s *Store) StandingsQuery(competition string, season, limit int) string {
	comp, ok := ResolveCompetition(competition)
	if !ok {
		return fmt.Sprintf("Unknown competition %q.", competition)
	}
	if comp == "" {
		comp = CompSerieA // standings default to the top flight
	}
	if season == 0 {
		return "Please specify a season (year) for standings."
	}
	matches := s.FindMatchesClean(MatchFilter{Competition: comp, Season: season})
	if len(matches) == 0 {
		min, max := s.SeasonRange(comp)
		return fmt.Sprintf("No %s matches found for %d (available seasons: %d–%d).", comp, season, min, max)
	}
	table := Standings(matches, s.Display)
	title := fmt.Sprintf("%d %s standings (calculated from %d matches)", season, comp, len(matches))
	out := FormatStandings(table, title, limit)
	// The leader (row 1) is always shown, so always name the champion.
	out += fmt.Sprintf("\n\nChampion: %s (%d pts).", table[0].Team, table[0].Points())
	return out
}

// CompetitionStatsQuery reports aggregate stats for a competition/season.
func (s *Store) CompetitionStatsQuery(competition string, season int) string {
	comp, ok := ResolveCompetition(competition)
	if !ok {
		return fmt.Sprintf("Unknown competition %q.", competition)
	}
	matches := s.FindMatchesClean(MatchFilter{Competition: comp, Season: season})
	if len(matches) == 0 {
		return "No matches found for the given filters."
	}
	c := Summarize(matches)
	scope := "all competitions"
	if comp != "" {
		scope = comp
	}
	if season != 0 {
		scope = fmt.Sprintf("%s %d", scope, season)
	}
	return fmt.Sprintf("Statistics for %s:\n"+
		"- Matches: %d\n- Total goals: %d\n- Average goals per match: %.2f\n"+
		"- Home wins: %d (%.1f%%)\n- Away wins: %d (%.1f%%)\n- Draws: %d (%.1f%%)",
		scope, c.Matches, c.TotalGoals, c.GoalsPerMatch(),
		c.HomeWins, pct(c.HomeWins, c.Matches),
		c.AwayWins, pct(c.AwayWins, c.Matches),
		c.Draws, pct(c.Draws, c.Matches))
}

// BiggestWinsQuery lists the largest-margin matches for a competition/season.
func (s *Store) BiggestWinsQuery(competition string, season, limit int) string {
	comp, ok := ResolveCompetition(competition)
	if !ok {
		return fmt.Sprintf("Unknown competition %q.", competition)
	}
	matches := s.FindMatchesClean(MatchFilter{Competition: comp, Season: season})
	if len(matches) == 0 {
		return "No matches found for the given filters."
	}
	if limit == 0 {
		limit = 10
	}
	top := BiggestWins(matches, limit)
	scope := "all competitions"
	if comp != "" {
		scope = comp
	}
	if season != 0 {
		scope = fmt.Sprintf("%s %d", scope, season)
	}
	return fmt.Sprintf("Biggest victories in %s:\n%s", scope, FormatMatchList(top, limit))
}

// TopScoringTeamsQuery ranks teams by goals scored for a competition/season.
func (s *Store) TopScoringTeamsQuery(competition string, season, limit int) string {
	comp, ok := ResolveCompetition(competition)
	if !ok {
		return fmt.Sprintf("Unknown competition %q.", competition)
	}
	matches := s.FindMatchesClean(MatchFilter{Competition: comp, Season: season})
	if len(matches) == 0 {
		return "No matches found for the given filters."
	}
	if limit == 0 {
		limit = 10
	}
	table := TopScoringTeams(matches, s.Display, limit)
	scope := "all competitions"
	if comp != "" {
		scope = comp
	}
	if season != 0 {
		scope = fmt.Sprintf("%s %d", scope, season)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Top scoring teams in %s:\n", scope)
	for i, r := range table {
		fmt.Fprintf(&b, "%2d. %s - %d goals in %d matches (%.2f per match)\n",
			i+1, r.Team, r.GoalsFor, r.Matches, float64(r.GoalsFor)/float64(max(r.Matches, 1)))
	}
	return strings.TrimRight(b.String(), "\n")
}

// SearchPlayersQuery finds players by name/nationality/club/position/rating.
func (s *Store) SearchPlayersQuery(name, nationality, club, position string, minOverall, limit int) string {
	f := PlayerFilter{
		NameKey:    NormalizeName(name),
		NationKey:  NormalizeName(nationality),
		Position:   position,
		MinOverall: minOverall,
	}
	clubDisp := ""
	if club != "" {
		key, disp, _, ok := s.ResolveTeam(club)
		if ok {
			f.ClubKey, clubDisp = key, disp
		} else {
			f.ClubContains = NormalizeTeam(club) // fall back to a substring match
			clubDisp = club
		}
	}
	players := s.FindPlayers(f)
	if limit == 0 {
		limit = 25
	}
	var crit []string
	if name != "" {
		crit = append(crit, "name~"+name)
	}
	if nationality != "" {
		crit = append(crit, "nationality="+nationality)
	}
	if clubDisp != "" {
		crit = append(crit, "club~"+clubDisp)
	}
	if position != "" {
		crit = append(crit, "position="+position)
	}
	if minOverall != 0 {
		crit = append(crit, fmt.Sprintf("overall>=%d", minOverall))
	}
	header := "Players"
	if len(crit) > 0 {
		header = "Players (" + strings.Join(crit, ", ") + ")"
	}
	return fmt.Sprintf("%s — %d found:\n%s", header, len(players), FormatPlayerList(players, limit))
}

// PlayerInfoQuery returns a detailed card for the best name match.
func (s *Store) PlayerInfoQuery(name string) string {
	players := s.FindPlayers(PlayerFilter{NameKey: NormalizeName(name)})
	if len(players) == 0 {
		return fmt.Sprintf("No player matching %q was found.", name)
	}
	p := players[0]
	var b strings.Builder
	fmt.Fprintf(&b, "%s\n", p.Name)
	fmt.Fprintf(&b, "- Overall: %d  Potential: %d\n", p.Overall, p.Potential)
	fmt.Fprintf(&b, "- Position: %s  Jersey: %s\n", dash(p.Position), dash(p.Jersey))
	fmt.Fprintf(&b, "- Age: %d  Nationality: %s\n", p.Age, p.Nationality)
	fmt.Fprintf(&b, "- Club: %s\n", dash(p.Club))
	fmt.Fprintf(&b, "- Height: %s  Weight: %s  Preferred foot: %s\n", dash(p.Height), dash(p.Weight), dash(p.PreferredFoot))
	if p.Value != "" || p.Wage != "" {
		fmt.Fprintf(&b, "- Value: %s  Wage: %s\n", dash(p.Value), dash(p.Wage))
	}
	if len(players) > 1 {
		fmt.Fprintf(&b, "\n(%d other players also match %q.)", len(players)-1, name)
	}
	return strings.TrimRight(b.String(), "\n")
}

// ClubPlayersQuery lists the (optionally top-rated) players at a club.
func (s *Store) ClubPlayersQuery(club string, limit int) string {
	key, disp, _, ok := s.ResolveTeam(club)
	var f PlayerFilter
	clubDisp := disp
	if ok {
		f.ClubKey = key
	} else {
		f.ClubContains = NormalizeTeam(club)
		clubDisp = club
	}
	players := s.FindPlayers(f)
	if len(players) == 0 {
		return fmt.Sprintf("No players found for club %q.", club)
	}
	if limit == 0 {
		limit = 25
	}
	avg := 0
	for _, p := range players {
		avg += p.Overall
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s squad — %d players (avg overall %.1f):\n",
		clubDisp, len(players), float64(avg)/float64(len(players)))
	b.WriteString(FormatPlayerList(players, limit))
	return b.String()
}

// DatasetOverview summarizes everything loaded — competitions, seasons, counts.
func (s *Store) DatasetOverview() string {
	// Per-competition counts are de-duplicated by source; the headline total is
	// their sum so the numbers are consistent (raw row count is higher because
	// the same fixture can appear in several datasets).
	type comp struct {
		name     string
		n        int
		min, max int
	}
	var comps []comp
	total := 0
	for _, c := range s.Competitions() {
		n := len(s.FindMatchesClean(MatchFilter{Competition: c}))
		min, max := s.SeasonRange(c)
		comps = append(comps, comp{c, n, min, max})
		total += n
	}

	var b strings.Builder
	fmt.Fprintf(&b, "Brazilian Soccer knowledge graph:\n")
	fmt.Fprintf(&b, "- Matches: %d (de-duplicated across sources)\n- Players: %d\n- Teams: %d\n\nCompetitions:\n",
		total, len(s.Players), len(s.teamKeys))
	for _, c := range comps {
		fmt.Fprintf(&b, "- %s: %d matches (%d–%d)\n", c.name, c.n, c.min, c.max)
	}
	return strings.TrimRight(b.String(), "\n")
}

// --- small helpers ----------------------------------------------------------

func parseUserDate(s string) (time.Time, error) {
	s = strings.TrimSpace(s)
	if s == "" {
		return time.Time{}, nil
	}
	if t, _, ok := parseDate(s); ok {
		return t, nil
	}
	return time.Time{}, fmt.Errorf("could not parse date %q (use YYYY-MM-DD)", s)
}

func lastN(matches []Match, n int) []Match {
	if n <= 0 || len(matches) <= n {
		return matches
	}
	return matches[len(matches)-n:]
}

func pct(n, total int) float64 {
	if total == 0 {
		return 0
	}
	return float64(n) / float64(total) * 100
}
