// Executable specifications: an LLM assistant connecting to the server
// can discover which kinds of soccer question it is able to answer.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestShouldTellAnAssistantWhichKindsOfQuestionItCanAnswer(t *testing.T) {
	s := dsl.New(t)

	s.Assistant.DiscoverCapabilities()

	s.Assistant.ConfirmCanAnswer(
		"match search", "head-to-head", "team record", "team rankings",
		"standings", "knockout bracket", "player search", "player profile",
		"competition statistics", "biggest wins", "season comparison",
		"derbies", "club profile", "dataset overview")
}

func TestShouldGiveTheAssistantAReadableAnswer(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Flamengo", "away: Fluminense", "score: 2-1", "date: 2023-09-03", "round: 22")

	s.Matches.Search("team: Flamengo", "opponent: Fluminense")

	s.Assistant.ConfirmAnswerReads("2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)")
}
