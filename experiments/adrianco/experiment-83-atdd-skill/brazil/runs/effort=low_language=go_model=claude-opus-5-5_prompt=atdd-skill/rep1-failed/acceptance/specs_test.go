package acceptance

// Executable specifications for the Brazilian Soccer knowledge server.
// Written in the language of the problem domain; how the questions reach the
// system is the protocol driver's business.

import "testing"

func TestMatchQueries(t *testing.T) {
	t.Run("shouldFindMatchesBetweenTwoRivals", func(t *testing.T) {
		s := NewSoccer(t)
		s.Matches.Find(Team("Flamengo"), Opponent("Fluminense"))
		s.Matches.ShouldInclude("Flamengo", "Fluminense")
		s.Matches.ShouldReportHeadToHead()
	})
	t.Run("shouldFindATeamsMatchesInASeason", func(t *testing.T) {
		s := NewSoccer(t)
		s.Matches.Find(Team("Palmeiras"), Season(2023))
		s.Matches.ShouldAllBeIn(2023)
	})
	t.Run("shouldFindMatchesWithinADateRange", func(t *testing.T) {
		s := NewSoccer(t)
		s.Matches.Find(Team("Santos"), From("2015-01-01"), To("2015-12-31"))
		s.Matches.ShouldAllBeIn(2015)
	})
	t.Run("shouldFindCopaDoBrasilFinals", func(t *testing.T) {
		s := NewSoccer(t)
		s.Matches.FindFinals("Copa do Brasil")
		s.Matches.ShouldAllBeFrom("Copa do Brasil")
	})
	t.Run("shouldFindMatchesInEveryCompetition", func(t *testing.T) {
		s := NewSoccer(t)
		for _, c := range []string{"Brasileirão Série A", "Brasileirão Série B", "Série C", "Copa do Brasil", "Libertadores"} {
			s.Matches.Find(Competition(c))
			s.Matches.ShouldAllBeFrom(c)
		}
	})
	t.Run("shouldFindHistoricalMatchesFrom2003", func(t *testing.T) {
		s := NewSoccer(t)
		s.Matches.Find(Team("Guarani"), Opponent("Vasco"), Season(2003))
		s.Matches.ShouldInclude("Guarani 4-2 Vasco")
	})
	t.Run("shouldTreatTeamNameVariationsAsTheSameTeam", func(t *testing.T) {
		s := NewSoccer(t)
		s.Matches.Find(Team("São Paulo"), Season(2018), Competition("Brasileirão Série A"))
		count := s.Matches.Count()
		s.Matches.Find(Team("Sao Paulo-SP"), Season(2018), Competition("Brasileirão Série A"))
		s.Matches.ShouldCount(count)
	})
	t.Run("shouldReportTheMostRecentMeeting", func(t *testing.T) {
		s := NewSoccer(t)
		s.Matches.FindLastMeeting("Flamengo", "Corinthians")
		s.Matches.ShouldInclude("Flamengo", "Corinthians", "-")
	})
}

func TestTeamQueries(t *testing.T) {
	t.Run("shouldReportAHomeRecordForASeason", func(t *testing.T) {
		s := NewSoccer(t)
		s.Teams.Record(Team("Corinthians"), Season(2022), Venue("home"), Competition("Brasileirão Série A"))
		s.Teams.ShouldHavePlayed(19)
	})
	t.Run("shouldCompareTwoTeamsHeadToHead", func(t *testing.T) {
		s := NewSoccer(t)
		s.Teams.HeadToHead("Palmeiras", "Santos")
		s.Teams.ShouldShow("Palmeiras", "Santos", "wins", "draws")
	})
	t.Run("shouldListCompetitionsATeamHasPlayedIn", func(t *testing.T) {
		s := NewSoccer(t)
		s.Teams.Competitions("Palmeiras")
		s.Teams.ShouldShow("Brasileirão Série A", "Copa do Brasil", "Libertadores")
	})
	t.Run("shouldFindTheTopScoringTeamOfASeason", func(t *testing.T) {
		s := NewSoccer(t)
		s.Teams.Ranking(Season(2019), Competition("Brasileirão Série A"), By("goals_for"))
		s.Teams.ShouldRankFirst("Flamengo")
	})
	t.Run("shouldFindTheBestHomeRecord", func(t *testing.T) {
		s := NewSoccer(t)
		s.Teams.Ranking(Competition("Brasileirão Série A"), By("home_win_rate"))
		s.Teams.ShouldShow("Win rate")
	})
}

func TestPlayerQueries(t *testing.T) {
	t.Run("shouldFindAPlayerByName", func(t *testing.T) {
		s := NewSoccer(t)
		s.Players.Find(Name("Gabriel Jesus"))
		s.Players.ShouldInclude("Gabriel Jesus", "Manchester City")
	})
	t.Run("shouldListTopRatedBrazilians", func(t *testing.T) {
		s := NewSoccer(t)
		s.Players.Find(Nationality("Brazil"))
		s.Players.ShouldRankFirst("Neymar Jr")
	})
	t.Run("shouldFindPlayersAtABrazilianClubIgnoringAccents", func(t *testing.T) {
		s := NewSoccer(t)
		s.Players.Find(Club("Gremio"))
		s.Players.ShouldInclude("Grêmio")
	})
	t.Run("shouldFilterPlayersByPosition", func(t *testing.T) {
		s := NewSoccer(t)
		s.Players.Find(Nationality("Brazil"), Position("GK"))
		s.Players.ShouldRankFirst("Ederson")
	})
	t.Run("shouldSummariseBraziliansAtBrazilianClubs", func(t *testing.T) {
		s := NewSoccer(t)
		s.Players.ClubSummary(Nationality("Brazil"))
		s.Players.ShouldInclude("Santos", "avg rating")
	})
}

func TestCompetitionQueries(t *testing.T) {
	t.Run("shouldCrownTheBrasileiraoChampion", func(t *testing.T) {
		s := NewSoccer(t)
		s.Competitions.Standings(Season(2019))
		s.Competitions.ShouldHaveChampion("Flamengo", 90)
	})
	t.Run("shouldCalculateStandingsFromHistoricalData", func(t *testing.T) {
		s := NewSoccer(t)
		s.Competitions.Standings(Season(2003))
		s.Competitions.ShouldHaveChampion("Cruzeiro", 100)
	})
	t.Run("shouldShowRelegatedTeams", func(t *testing.T) {
		s := NewSoccer(t)
		s.Competitions.Standings(Season(2020))
		s.Competitions.ShouldShow("Relegated")
	})
	t.Run("shouldRelegateTheBottomFourOfTheRealLeagueTable", func(t *testing.T) {
		s := NewSoccer(t)
		s.Competitions.Standings(Season(2015))
		s.Competitions.ShouldRelegate("Avaí", "Vasco", "Goiás", "Joinville")
	})
	t.Run("shouldShowTheLibertadoresKnockoutBracket", func(t *testing.T) {
		s := NewSoccer(t)
		s.Competitions.Bracket(Season(2018))
		s.Competitions.ShouldShow("final", "semifinals", "River Plate")
	})
}

func TestStatisticalAnalysis(t *testing.T) {
	t.Run("shouldReportAverageGoalsPerMatch", func(t *testing.T) {
		s := NewSoccer(t)
		s.Stats.Summary(Competition("Brasileirão Série A"))
		s.Stats.ShouldShow("Average goals per match", "Home win rate")
	})
	t.Run("shouldCompareTwoSeasons", func(t *testing.T) {
		s := NewSoccer(t)
		s.Stats.Summary(Competition("Brasileirão Série A"), Season(2018))
		s.Stats.Summary(Competition("Brasileirão Série A"), Season(2019))
		s.Stats.ShouldShow("2019")
	})
	t.Run("shouldListTheBiggestWins", func(t *testing.T) {
		s := NewSoccer(t)
		s.Stats.BiggestWins()
		s.Stats.ShouldShow("1. ")
	})
}

func TestServiceQuality(t *testing.T) {
	t.Run("shouldAnswerAggregateQuestionsQuickly", func(t *testing.T) {
		s := NewSoccer(t)
		s.Stats.ShouldAnswerWithin(5, func() { s.Stats.Summary() })
		s.Stats.ShouldAnswerWithin(2, func() { s.Players.Find(Name("Casemiro")) })
	})
	t.Run("shouldExplainWhenNothingMatches", func(t *testing.T) {
		s := NewSoccer(t)
		s.Players.Find(Name("Nobody At All Xyz"))
		s.Players.ShouldShow("No players found")
	})
}
