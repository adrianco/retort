package main

import (
	"strings"
	"testing"
	"time"
)

// soccerDSL is the domain-language layer between specs and the protocol driver.
// Arguments are "name: value" pairs; unspecified ones take defaults.
type soccerDSL struct {
	t       *testing.T
	driver  *mcpDriver
	answer  string
	elapsed time.Duration
}

func newSoccerDSL(t *testing.T) *soccerDSL {
	t.Helper()
	return &soccerDSL{t: t, driver: sharedDriver(t)}
}

func params(args []string) map[string]any {
	out := map[string]any{}
	for _, a := range args {
		k, v, ok := strings.Cut(a, ":")
		if !ok {
			continue
		}
		out[strings.TrimSpace(k)] = strings.TrimSpace(v)
	}
	return out
}

func (s *soccerDSL) ask(tool string, p map[string]any) {
	s.t.Helper()
	start := time.Now()
	s.answer = s.driver.callTool(s.t, tool, p)
	s.elapsed = time.Since(start)
}

func (s *soccerDSL) WhenAskingForMatchesBetween(a, b string) {
	s.ask("head_to_head", map[string]any{"team_a": a, "team_b": b})
}
func (s *soccerDSL) WhenAskingForLastMatchBetween(a, b string) {
	s.ask("head_to_head", map[string]any{"team_a": a, "team_b": b, "limit": "1"})
}
func (s *soccerDSL) WhenAskingForMatches(args ...string)    { s.ask("search_matches", params(args)) }
func (s *soccerDSL) WhenAskingForTeamRecord(args ...string) { s.ask("team_record", params(args)) }
func (s *soccerDSL) WhenAskingForStandings(args ...string)  { s.ask("standings", params(args)) }
func (s *soccerDSL) WhenSearchingForPlayers(args ...string) { s.ask("search_players", params(args)) }
func (s *soccerDSL) WhenAskingForBrazilianPlayersByClub() {
	s.ask("players_by_club", map[string]any{"nationality": "Brazil"})
}
func (s *soccerDSL) WhenAskingForStatistics(args ...string)  { s.ask("statistics", params(args)) }
func (s *soccerDSL) WhenAskingForBiggestWins(args ...string) { s.ask("biggest_wins", params(args)) }
func (s *soccerDSL) WhenAskingForBestRecord(args ...string)  { s.ask("rank_teams", params(args)) }
func (s *soccerDSL) WhenAskingForCompetitionsOf(team string) {
	s.ask("team_profile", map[string]any{"team": team})
}
func (s *soccerDSL) WhenAskingForTeamProfile(team string) {
	s.ask("team_profile", map[string]any{"team": team})
}
func (s *soccerDSL) WhenAskingForDerbies(args ...string) { s.ask("derbies", params(args)) }
func (s *soccerDSL) WhenAskingWhatDataIsAvailable()      { s.ask("data_summary", map[string]any{}) }

func (s *soccerDSL) ThenAnswerMentions(texts ...string) {
	s.t.Helper()
	s.driver.assertMentions(s.t, s.answer, texts...)
}
func (s *soccerDSL) ThenAnswerDoesNotMention(texts ...string) {
	s.t.Helper()
	s.driver.assertNotMentions(s.t, s.answer, texts...)
}
func (s *soccerDSL) ThenAnswerEquals(expected string) {
	s.t.Helper()
	if s.answer != expected {
		s.t.Fatalf("expected the same answer, got:\n%s\n---\n%s", expected, s.answer)
	}
}
func (s *soccerDSL) ThenAnswerArrivedWithinSeconds(n int) {
	s.t.Helper()
	if s.elapsed > time.Duration(n)*time.Second {
		s.t.Fatalf("answer took %v, limit %ds", s.elapsed, n)
	}
}
