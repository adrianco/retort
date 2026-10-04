// Executable specifications against the provided Kaggle datasets.
//
// These specs cover data coverage, query performance and the sample
// questions from the requirements. They rely on well-known historical
// facts (who won a season, who was relegated) rather than on the
// internal shape of the files.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestShouldLoadEveryProvidedDataset(t *testing.T) {
	s := dsl.NewWithProvidedData(t)

	s.Datasets.Describe()

	s.Datasets.ConfirmLoaded(
		"Brasileirão Série A matches",
		"Copa do Brasil matches",
		"Copa Libertadores matches",
		"Extended match statistics",
		"Historical Brasileirão matches",
		"FIFA players")
}

func TestShouldCalculateTheReal2019ChampionFromTheProvidedResults(t *testing.T) {
	s := dsl.NewWithProvidedData(t)

	s.Competitions.Standings("season: 2019")

	s.Competitions.ConfirmChampion("team: Flamengo", "points: 90", "wins: 28", "draws: 6", "losses: 4")
}

func TestShouldIdentifyTheTeamsReallyRelegatedIn2020(t *testing.T) {
	s := dsl.NewWithProvidedData(t)

	s.Competitions.Standings("season: 2020")

	s.Competitions.ConfirmRelegated("Vasco", "Goiás", "Coritiba", "Botafogo")
}

func TestShouldShowTheReal2018LibertadoresFinal(t *testing.T) {
	s := dsl.NewWithProvidedData(t)

	s.Competitions.Bracket("competition: Libertadores", "season: 2018")

	s.Competitions.ConfirmTie("stage: final", "teams: Boca Juniors v River Plate", "aggregate: 3-5", "winner: River Plate")
}

func TestShouldAnswerSimpleLookupsWithinTwoSeconds(t *testing.T) {
	s := dsl.NewWithProvidedData(t)

	s.Matches.FindLastMeeting("Flamengo", "Corinthians")

	s.ConfirmAnsweredWithin("2s")
}

func TestShouldAnswerAggregateQueriesWithinFiveSeconds(t *testing.T) {
	s := dsl.NewWithProvidedData(t)

	s.Teams.Rank("by: win rate", "venue: home")

	s.ConfirmAnsweredWithin("5s")
}

func TestShouldAnswerQuestionsThatCombinePlayerAndMatchData(t *testing.T) {
	s := dsl.NewWithProvidedData(t)

	s.Players.SummariseBrazilianPlayersAtBrazilianClubs()

	s.Players.ConfirmClubSummary("club: Grêmio", "players: 20")
}

// The sample questions from the requirements, each answered from the
// provided data. Every question must produce a substantive answer.
func TestShouldAnswerTheSampleQuestions(t *testing.T) {
	s := dsl.NewWithProvidedData(t)

	questions := []struct {
		question string
		ask      func()
		confirm  func()
	}{
		{"Show me all Flamengo vs Fluminense matches",
			func() { s.Matches.Search("team: Flamengo", "opponent: Fluminense") },
			func() { s.Matches.ConfirmFoundAtLeast(20) }},
		{"What matches did Palmeiras play in 2023?",
			func() { s.Matches.Search("team: Palmeiras", "season: 2023") },
			func() { s.Matches.ConfirmFoundAtLeast(38) }},
		{"Find all Copa do Brasil finals",
			func() { s.Matches.Search("competition: Copa do Brasil", "stage: final") },
			func() { s.Matches.ConfirmFound("Palmeiras 2-0 Grêmio on 2021-03-07") }},
		{"When did Flamengo last play Corinthians, and what was the score?",
			func() { s.Matches.FindLastMeeting("Flamengo", "Corinthians") },
			func() { s.Matches.ConfirmFoundExactly(1) }},
		{"Show me all derbies in 2023",
			func() { s.Matches.SearchDerbies("season: 2023") },
			func() { s.Matches.ConfirmFoundAtLeast(10) }},
		{"What is Corinthians' home record in 2022?",
			func() {
				s.Teams.RecordFor("team: Corinthians", "season: 2022", "venue: home", "competition: Brasileirão")
			},
			func() { s.Teams.ConfirmRecord("matches: 19") }},
		{"Which team scored the most goals in Serie A 2023?",
			func() { s.Teams.Rank("by: goals scored", "season: 2023", "competition: Brasileirão") },
			func() { s.Teams.ConfirmSomeTeamRankedFirst() }},
		{"Compare Palmeiras and Santos head-to-head",
			func() { s.Teams.CompareHeadToHead("Palmeiras", "Santos") },
			func() { s.Teams.ConfirmHeadToHeadMeetingsAtLeast(30) }},
		{"What competitions has Palmeiras played in?",
			func() { s.Teams.CompetitionsPlayedBy("Palmeiras") },
			func() { s.Teams.ConfirmPlayedIn("Brasileirão Série A", "Copa do Brasil", "Copa Libertadores") }},
		{"Which team has the best home record?",
			func() { s.Teams.Rank("by: win rate", "venue: home", "competition: Brasileirão") },
			func() { s.Teams.ConfirmSomeTeamRankedFirst() }},
		{"Which team has the best away record?",
			func() { s.Teams.Rank("by: win rate", "venue: away", "competition: Brasileirão") },
			func() { s.Teams.ConfirmSomeTeamRankedFirst() }},
		{"Find all Brazilian players in the dataset",
			func() { s.Players.Search("nationality: Brazil") },
			func() { s.Players.ConfirmTotal(827) }},
		{"Who are the top Brazilian players?",
			func() { s.Players.Search("nationality: Brazil") },
			func() { s.Players.ConfirmFoundInOrder("Neymar Jr") }},
		{"Who are the highest-rated players at Santos?",
			func() { s.Players.Search("club: Santos FC") },
			func() { s.Players.ConfirmFoundAtLeast(20) }},
		{"Show me all forwards at Grêmio",
			func() { s.Players.Search("club: Grêmio", "position: forward") },
			func() { s.Players.ConfirmFoundAtLeast(1) }},
		{"Who is Neymar?",
			func() { s.Players.LookUp("Neymar") },
			func() { s.Players.ConfirmProfile("name: Neymar Jr", "club: Paris Saint-Germain", "overall: 92") }},
		{"Who won the 2019 Brasileirão?",
			func() { s.Competitions.Standings("season: 2019") },
			func() { s.Competitions.ConfirmChampion("team: Flamengo") }},
		{"Which teams were relegated in 2020?",
			func() { s.Competitions.Standings("season: 2020") },
			func() { s.Competitions.ConfirmRelegated("Botafogo") }},
		{"Show the 2018 Copa Libertadores bracket",
			func() { s.Competitions.Bracket("competition: Libertadores", "season: 2018") },
			func() {
				s.Competitions.ConfirmTie("stage: semifinals", "teams: River Plate v Grêmio", "winner: River Plate")
			}},
		{"What's the average goals per match in the Brasileirão?",
			func() { s.Statistics.Summarise("competition: Brasileirão") },
			func() { s.Statistics.ConfirmAverageGoalsBetween(2.0, 3.0) }},
		{"Show me the biggest wins in the dataset",
			func() { s.Statistics.BiggestWins() },
			func() { s.Statistics.ConfirmBiggestWinMarginAtLeast(6) }},
		{"Compare the 2018 and 2019 seasons",
			func() { s.Statistics.CompareSeasons("2018", "2019") },
			func() { s.Statistics.ConfirmSeason("season: 2019", "matches: 380", "champion: Flamengo") }},
		{"Tell me about Grêmio's squad and results",
			func() { s.Teams.ProfileClub("Grêmio") },
			func() { s.Teams.ConfirmSquadSizeAtLeast(20) }},
	}

	for _, q := range questions {
		t.Run(q.question, func(t *testing.T) {
			s.Within(t)
			q.ask()
			q.confirm()
		})
	}
}
