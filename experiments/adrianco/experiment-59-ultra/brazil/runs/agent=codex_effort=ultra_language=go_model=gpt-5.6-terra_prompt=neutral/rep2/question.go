package main

import (
	"fmt"
	"regexp"
	"sort"
	"strings"
	"sync"
)

// SoccerService owns the tiny amount of conversational state needed to answer
// a follow-up such as "What was the score?" after a previous match lookup.
// The underlying Store remains immutable.
type SoccerService struct {
	Store *Store
	mu    sync.RWMutex
	last  []Match
}

func NewSoccerService(store *Store) *SoccerService { return &SoccerService{Store: store} }

type QuestionAnswer struct {
	Question string `json:"question"`
	Answer   string `json:"answer"`
	Data     any    `json:"data,omitempty"`
	Note     string `json:"note,omitempty"`
}

func (s *SoccerService) Ask(question string) (QuestionAnswer, error) {
	question = strings.TrimSpace(question)
	if question == "" {
		return QuestionAnswer{}, fmt.Errorf("question is required")
	}
	q := normalizeText(question)
	competition := competitionInQuestion(q)
	season := seasonInQuestion(q)
	teams := s.mentionedTeams(q)

	switch {
	case strings.Contains(q, "top scorer") || strings.Contains(q, "top goalscorer"):
		return QuestionAnswer{
			Question: question,
			Answer:   "Top scorers cannot be calculated from the supplied data because it contains match scores but no goal-scorer events.",
			Note:     "The server will not invent player scoring statistics.",
		}, nil
	case strings.Contains(q, "what was the score") || strings.Contains(q, "what was score"):
		return s.answerLastScore(question)
	case strings.Contains(q, "last play") || strings.Contains(q, "last played"):
		if len(teams) < 2 {
			return QuestionAnswer{Question: question, Answer: "Please name both teams for a last-meeting lookup."}, nil
		}
		result, err := s.Store.SearchMatches(MatchFilter{Team: teams[0], Opponent: teams[1], Competition: competition, Limit: 1})
		if err != nil {
			return QuestionAnswer{}, err
		}
		s.remember(result.Matches)
		if len(result.Matches) == 0 {
			return QuestionAnswer{Question: question, Answer: fmt.Sprintf("No %s vs %s match was found in the supplied datasets.", displayTeam(teams[0]), displayTeam(teams[1])), Data: result}, nil
		}
		match := result.Matches[0]
		return QuestionAnswer{Question: question, Answer: matchSummary(match), Data: result}, nil
	case strings.Contains(q, "which players play for") || strings.Contains(q, "players at"):
		club := trailingEntity(q, []string{"which players play for", "players at"})
		result, err := s.Store.SearchPlayers(PlayerFilter{Club: club, Limit: 50})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Found %d players at %s in the FIFA snapshot.", result.Total, displayTeam(club)), Data: result, Note: "FIFA club data is a snapshot and is not a historical roster."}, nil
	case strings.HasPrefix(q, "who is ") || strings.HasPrefix(q, "find player ") || strings.HasPrefix(q, "find all players named "):
		name := trailingEntity(q, []string{"who is", "find player", "find all players named"})
		result, err := s.Store.SearchPlayers(PlayerFilter{Name: name, Limit: 20})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Found %d FIFA player record(s) matching %q.", result.Total, name), Data: result}, nil
	case strings.Contains(q, "derbies") || strings.Contains(q, "derby"):
		matches, err := s.Store.Derbies(season, 100)
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Found %d known traditional-rivalry match(es).", len(matches)), Data: map[string]any{"matches": matches, "season": season}, Note: "Derbies use the server's documented traditional-rivalry list; they are not labelled in the source data."}, nil
	case strings.Contains(q, "competitions has") || strings.Contains(q, "competitions have") || strings.Contains(q, "competitions did"):
		if len(teams) == 0 {
			return QuestionAnswer{Question: question, Answer: "Please name a team to list its competitions."}, nil
		}
		result, err := s.Store.TeamCompetitions(teams[0])
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("%s appears in %d competition(s) across the supplied match sources.", displayTeam(teams[0]), len(result)), Data: result}, nil
	case strings.Contains(q, "best home record"):
		result, err := s.Store.Analyze(StatisticsQuery{Metric: "best_home_record", Competition: competition, Season: season, Limit: 10})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: "Teams are ranked by home win rate, then points and goal difference.", Data: result}, nil
	case strings.Contains(q, "best away record"):
		result, err := s.Store.Analyze(StatisticsQuery{Metric: "best_away_record", Competition: competition, Season: season, Limit: 10})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: "Teams are ranked by away win rate, then points and goal difference.", Data: result}, nil
	case len(teams) > 0 && strings.Contains(q, "home record"):
		result, err := s.Store.TeamStatistics(TeamStatsQuery{Team: teams[0], Competition: competition, Season: season, Venue: "home"})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Calculated %s's home record from deduplicated completed matches.", displayTeam(teams[0])), Data: result}, nil
	case len(teams) > 0 && strings.Contains(q, "away record"):
		result, err := s.Store.TeamStatistics(TeamStatsQuery{Team: teams[0], Competition: competition, Season: season, Venue: "away"})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Calculated %s's away record from deduplicated completed matches.", displayTeam(teams[0])), Data: result}, nil
	case strings.Contains(q, "scored the most goals") || strings.Contains(q, "most goals"):
		result, err := s.Store.Analyze(StatisticsQuery{Metric: "top_scoring_teams", Competition: competition, Season: season, Limit: 10})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: "Teams are ranked by total goals, then goals per match.", Data: result}, nil
	case strings.Contains(q, "top brazilian players") || strings.Contains(q, "highest rated brazilian"):
		result, err := s.Store.SearchPlayers(PlayerFilter{Nationality: "Brazil", Sort: "overall_desc", Limit: 20})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Found %d Brazilian players, ordered by FIFA overall rating.", result.Total), Data: result}, nil
	case strings.Contains(q, "brazilian players") || strings.Contains(q, "players from brazil"):
		result, err := s.Store.SearchPlayers(PlayerFilter{Nationality: "Brazil", Sort: "overall_desc", Limit: 50})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Found %d Brazilian players in the FIFA snapshot.", result.Total), Data: result}, nil
	case len(teams) > 0 && (strings.Contains(q, "forwards") || strings.Contains(q, "forward")):
		result, err := s.Store.SearchPlayers(PlayerFilter{Club: teams[0], PositionGroup: "forwards", Sort: "overall_desc", Limit: 50})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Found %d forward(s) at %s in the FIFA snapshot.", result.Total, displayTeam(teams[0])), Data: result, Note: "FIFA club data is a snapshot and is not a historical roster."}, nil
	case strings.Contains(q, "who won") || strings.Contains(q, "champion"):
		if strings.TrimSpace(competition) == "" {
			competition = "Brasileirão"
		}
		result, err := s.Store.Standings(competition, season, "")
		if err != nil {
			return QuestionAnswer{}, err
		}
		if len(result.Standings) == 0 {
			return QuestionAnswer{Question: question, Answer: "No completed league table can be calculated for that competition and season from the supplied data.", Data: result}, nil
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("%s leads the calculated %d %s table.", result.Standings[0].Team, season, result.Competition), Data: result, Note: "This is derived from the documented points and tie-break calculation."}, nil
	case strings.Contains(q, "relegated") || strings.Contains(q, "relegation"):
		result, err := s.Store.Analyze(StatisticsQuery{Metric: "relegation_candidates", Competition: competition, Season: season})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: "Returned the bottom four from the calculated table; the source does not explicitly label relegation.", Data: result}, nil
	case strings.Contains(q, "bracket"):
		if strings.TrimSpace(competition) == "" {
			return QuestionAnswer{Question: question, Answer: "Please name a competition and season to inspect its available stages."}, nil
		}
		result, err := s.Store.SearchMatches(MatchFilter{Competition: competition, Season: season, Limit: 500})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: "Returned the available stage-labelled match rows. A complete knockout bracket is not inferred when the supplied rows lack aggregate and tie-break data.", Data: result}, nil
	case strings.Contains(q, "compare") && len(allSeasonsInQuestion(q)) >= 2:
		seasons := allSeasonsInQuestion(q)
		result, err := s.Store.CompareSeasons(competition, "", seasons...)
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Compared %d seasons using deduplicated completed matches.", len(seasons)), Data: result}, nil
	case strings.Contains(q, "average goals") || strings.Contains(q, "goals per match"):
		result, err := s.Store.Analyze(StatisticsQuery{Metric: "summary", Competition: competition, Season: season})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: "Calculated completed-match scoring averages and home/away rates.", Data: result}, nil
	case strings.Contains(q, "biggest win") || strings.Contains(q, "biggest vict"):
		result, err := s.Store.Analyze(StatisticsQuery{Metric: "biggest_wins", Competition: competition, Season: season, Limit: 20})
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: "Matches are ordered by winning margin, then most recent date.", Data: result}, nil
	case strings.Contains(q, "final") && canonicalCompetition(competition) == "Copa do Brasil":
		return QuestionAnswer{Question: question, Answer: "The supplied Copa do Brasil data labels rounds only with numbers, so it cannot reliably identify a final without inventing a round mapping.", Note: "Use search_matches with a numeric round to inspect the available data."}, nil
	case len(teams) >= 2 && (strings.Contains(q, "compare") || strings.Contains(q, "head to head") || strings.Contains(q, "headtohead")):
		result, err := s.Store.CompareTeams(teams[0], teams[1], competition, "", season)
		if err != nil {
			return QuestionAnswer{}, err
		}
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Compared %s and %s, including their head-to-head record.", displayTeam(teams[0]), displayTeam(teams[1])), Data: result}, nil
	case len(teams) >= 1 && (strings.Contains(q, "match") || strings.Contains(q, "played") || strings.Contains(q, "game")):
		filter := MatchFilter{Team: teams[0], Competition: competition, Season: season, Limit: 100}
		if len(teams) >= 2 {
			filter.Opponent = teams[1]
		}
		result, err := s.Store.SearchMatches(filter)
		if err != nil {
			return QuestionAnswer{}, err
		}
		s.remember(result.Matches)
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("Found %d matching match row(s).", result.Total), Data: result}, nil
	default:
		return QuestionAnswer{Question: question, Answer: "I could not safely map that question to a deterministic query. Try naming a team, season, competition, or one of: matches, player, standings, head-to-head, average goals, biggest wins, or best home/away record."}, nil
	}
}

func (s *SoccerService) answerLastScore(question string) (QuestionAnswer, error) {
	s.mu.RLock()
	last := append([]Match(nil), s.last...)
	s.mu.RUnlock()
	if len(last) == 0 {
		return QuestionAnswer{Question: question, Answer: "I need a preceding match search before I can resolve this score follow-up."}, nil
	}
	match := last[0]
	if !match.HasResult() {
		return QuestionAnswer{Question: question, Answer: fmt.Sprintf("%s has no recorded final score in the source data.", matchSummary(match)), Data: match}, nil
	}
	return QuestionAnswer{Question: question, Answer: fmt.Sprintf("%s %d–%d %s.", match.HomeTeam, *match.HomeGoals, *match.AwayGoals, match.AwayTeam), Data: match}, nil
}

func (s *SoccerService) remember(matches []Match) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.last = append([]Match(nil), matches...)
}

func (s *SoccerService) mentionedTeams(question string) []string {
	question = " " + normalizeText(question) + " "
	type hit struct {
		key   string
		index int
	}
	hits := make([]hit, 0)
	keys := make(map[string]struct{})
	for _, match := range s.Store.Matches {
		keys[match.HomeKey] = struct{}{}
		keys[match.AwayKey] = struct{}{}
	}
	for key := range keys {
		if index := phraseIndex(question, key); index >= 0 {
			hits = append(hits, hit{key, index})
		}
	}
	for alias, canonical := range teamAliases {
		if index := phraseIndex(question, alias); index >= 0 {
			hits = append(hits, hit{canonical, index})
		}
	}
	sort.Slice(hits, func(i, j int) bool {
		if hits[i].index != hits[j].index {
			return hits[i].index < hits[j].index
		}
		return len(hits[i].key) > len(hits[j].key)
	})
	result := make([]string, 0, len(hits))
	seen := make(map[string]struct{})
	for _, hit := range hits {
		if _, ok := seen[hit.key]; !ok {
			seen[hit.key] = struct{}{}
			result = append(result, hit.key)
		}
	}
	return result
}

func phraseIndex(haystack, needle string) int {
	needle = " " + normalizeText(needle) + " "
	return strings.Index(haystack, needle)
}

func competitionInQuestion(question string) string {
	switch {
	case strings.Contains(question, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(question, "copa do brasil") || strings.Contains(question, "brazilian cup"):
		return "Copa do Brasil"
	case strings.Contains(question, "brasileirao") || strings.Contains(question, "brasileiro") || strings.Contains(question, "serie a"):
		return "Brasileirão Série A"
	case strings.Contains(question, "serie b"):
		return "Brasileirão Série B"
	case strings.Contains(question, "serie c"):
		return "Brasileirão Série C"
	default:
		return ""
	}
}

var yearPattern = regexp.MustCompile(`\b(?:19|20)\d{2}\b`)

func seasonInQuestion(question string) int {
	values := allSeasonsInQuestion(question)
	if len(values) == 0 {
		return 0
	}
	return values[0]
}

func allSeasonsInQuestion(question string) []int {
	matches := yearPattern.FindAllString(question, -1)
	result := make([]int, 0, len(matches))
	seen := make(map[int]struct{})
	for _, value := range matches {
		var year int
		_, _ = fmt.Sscanf(value, "%d", &year)
		if _, ok := seen[year]; !ok {
			seen[year] = struct{}{}
			result = append(result, year)
		}
	}
	return result
}

func trailingEntity(question string, prefixes []string) string {
	for _, prefix := range prefixes {
		if strings.HasPrefix(question, prefix+" ") {
			return strings.TrimSpace(strings.TrimPrefix(question, prefix))
		}
	}
	return question
}

func matchSummary(match Match) string {
	date := "an unknown date"
	if match.Date != "" {
		date = match.Date[:10]
	}
	if match.HasResult() {
		return fmt.Sprintf("%s: %s %d–%d %s (%s)", date, match.HomeTeam, *match.HomeGoals, *match.AwayGoals, match.AwayTeam, match.Competition)
	}
	return fmt.Sprintf("%s: %s vs %s (%s; score unavailable)", date, match.HomeTeam, match.AwayTeam, match.Competition)
}
