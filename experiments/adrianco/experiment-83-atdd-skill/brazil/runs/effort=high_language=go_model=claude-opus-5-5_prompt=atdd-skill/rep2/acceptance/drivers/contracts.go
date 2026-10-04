package drivers

import "time"

// Expectation is one fact a test case expects to see in an answer.
type Expectation struct {
	Fact  string
	Value string
}

// MatchRecord is one match as it appears in one of the source datasets.
type MatchRecord struct {
	Source      string // which dataset records it, in domain terms
	Competition string
	Season      int
	Date        time.Time
	Round       int
	Stage       string
	Home, Away  string
	HomeGoals   int
	AwayGoals   int
	ScoreKnown  bool
	Corners     [2]int
	Shots       [2]int
	HasStats    bool
}

// PlayerRecord is one player as recorded in the FIFA ratings.
type PlayerRecord struct {
	ID          int
	Name        string
	Nationality string
	Club        string
	Position    string
	Overall     int
	Age         int
}

// RecordsDriver programs the source datasets the system answers from.
// It plays the role of a stub: the DSL loads it before the system is asked
// anything.
type RecordsDriver interface {
	AddMatch(MatchRecord)
	AddPlayer(PlayerRecord)
}

// SystemDriver is the contract every protocol driver for the soccer
// knowledge system must fulfil. Each method passes or fails; if control
// returns, the step happened.
type SystemDriver interface {
	FindMatches(criteria map[string]string)
	ConfirmMatchesShown(lines ...string)
	ConfirmMatchCount(n int)
	ConfirmCompetitionsInMatches(names ...string)
	ConfirmHeadToHeadSummary(teamA, teamB string, expected []Expectation)
	ConfirmMatchStatistics(expected []Expectation)
	ConfirmNoMatchesFound()
	ConfirmNoDuplicateMatches()

	TeamRecord(team string, criteria map[string]string)
	TeamOverview(team string)
	HeadToHead(teamA, teamB string, criteria map[string]string)
	RankTeams(criteria map[string]string)
	CompetitionsPlayed(team string)
	ConfirmRecord(expected []Expectation)
	ConfirmHeadToHead(expected []Expectation)
	ConfirmRankedFirst(team string, expected []Expectation)
	ConfirmCompetitionsPlayed(names ...string)
	ConfirmSquad(expected []Expectation)

	FindPlayers(criteria map[string]string)
	BrazilianPlayersAtBrazilianClubs()
	ConfirmPlayersListed(names ...string)
	ConfirmPlayersNotListed(names ...string)
	ConfirmPlayersInOrder(names ...string)
	ConfirmPlayerDetails(name string, expected []Expectation)
	ConfirmPlayersSuggested(names ...string)
	ConfirmClubSummary(club string, expected []Expectation)
	ConfirmClubNotSummarised(club string)

	Standings(criteria map[string]string)
	Bracket(criteria map[string]string)
	ConfirmChampion(team string, expected []Expectation)
	ConfirmFinishingOrder(teams ...string)
	ConfirmRelegated(teams ...string)
	ConfirmTeamsInTable(n int)
	ConfirmTie(stage string, expected []Expectation)
	ConfirmNoStage(stage string)

	CompetitionStatistics(criteria map[string]string)
	BiggestWins(criteria map[string]string)
	CompareSeasons(criteria map[string]string, seasons ...string)
	Derbies(criteria map[string]string)
	ConfirmStatistics(expected []Expectation)
	ConfirmWinsInOrder(lines ...string)
	ConfirmSeason(season string, expected []Expectation)
	ConfirmDerbies(names ...string)
	ConfirmDerbyCount(n int)

	ListDatasets()
	ConfirmDatasetLoaded(dataset string, expected []Expectation)

	ConfirmAnsweredWithin(limit time.Duration)
}
