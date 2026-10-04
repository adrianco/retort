// Package driver holds the protocol drivers for the acceptance specs.
// A protocol driver is the only part of the test infrastructure that
// knows how the soccer knowledge server works: that it is an MCP server
// run as a separate process, that it reads CSV files, and what its tools
// are called. Each driver step either succeeds or fails the spec.
package driver

import (
	"testing"
	"time"
)

// MatchFixture is a match the spec has established.
type MatchFixture struct {
	Home, Away           string
	HomeGoals, AwayGoals int
	Date                 time.Time
	Season, Round        int
	Competition, Stage   string
	Source               string
	Corners, Shots       *[2]int
}

// PlayerFixture is a player the spec has established.
type PlayerFixture struct {
	ID                              int
	Name, Nationality, Club         string
	Position                        string
	Overall, Potential, Age, Jersey int
}

// SoccerDriver is the contract between the DSL and any way of reaching
// the soccer knowledge server. Criteria and expectations are passed as
// the named values the spec used.
type SoccerDriver interface {
	UseTest(t testing.TB)

	RecordMatch(m MatchFixture)
	RecordPlayer(p PlayerFixture)

	SearchMatches(criteria map[string]string)
	FindLastMeeting(team, opponent string)
	SearchDerbies(criteria map[string]string)
	ConfirmMatchesFound(descriptions []string)
	ConfirmMatchCount(count int, exactly bool)
	ConfirmHeadToHead(expected map[string]string)
	ConfirmMatchStatistics(expected map[string]string)

	TeamRecord(criteria map[string]string)
	ConfirmTeamRecord(expected map[string]string)
	ConfirmCompetitionRecord(expected map[string]string)
	CompareHeadToHead(team, opponent string)
	ConfirmHeadToHeadMeetingsAtLeast(count int)
	CompetitionsPlayedBy(team string)
	ConfirmPlayedIn(competitions []string)
	RankTeams(criteria map[string]string)
	ConfirmRankedFirst(expected map[string]string)
	FindTeam(name string)
	ConfirmKnownAs(names []string)
	ProfileClub(team string)
	ConfirmSquadIncludes(players []string)
	ConfirmSquadSizeAtLeast(count int)

	SearchPlayers(criteria map[string]string)
	LookUpPlayer(name string)
	ConfirmPlayerProfile(expected map[string]string)
	ConfirmPlayersInOrder(names []string)
	ConfirmPlayersFound(names []string)
	ConfirmPlayerCount(count int, exactly bool)
	ConfirmPlayerTotal(count int)
	SummariseBrazilianPlayersAtBrazilianClubs()
	ConfirmClubSummary(expected map[string]string)
	ConfirmClubNotInSummary(club string)

	Standings(criteria map[string]string)
	ConfirmStanding(expected map[string]string)
	ConfirmChampionNamed(team string)
	ConfirmRelegated(teams []string)
	Bracket(criteria map[string]string)
	ConfirmTie(expected map[string]string)
	ConfirmNoStage(stage string)

	SummariseCompetition(criteria map[string]string)
	ConfirmSummary(expected map[string]string)
	ConfirmAverageGoalsBetween(low, high float64)
	BiggestWins(criteria map[string]string)
	ConfirmBiggestWinsInOrder(results []string)
	ConfirmBiggestWinMarginAtLeast(goals int)
	CompareSeasons(seasons []string)
	ConfirmSeasonComparison(expected map[string]string)

	DescribeDatasets()
	ConfirmDatasetsLoaded(datasets []string)
	DiscoverCapabilities()
	ConfirmCapabilities(kinds []string)
	ConfirmAnswerContains(line string)
	ConfirmAnsweredWithin(limit time.Duration)
	ConfirmToldUnknown(name string)
}
