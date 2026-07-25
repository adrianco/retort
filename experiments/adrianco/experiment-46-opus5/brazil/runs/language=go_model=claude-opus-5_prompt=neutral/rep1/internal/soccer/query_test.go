// query_test.go - BDD scenarios for the five required capability areas:
// match queries, team queries, player queries, competition queries and
// statistical analysis.
package soccer

import (
	"strings"
	"testing"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/bdd"
)

func TestFeatureMatchQueries(t *testing.T) {
	bdd.Feature(t, "Match Queries")
	g := testGraph(t)

	bdd.Scenario(t, "Find matches between two teams", func(s *bdd.S) {
		var matches []*Match
		var fla, flu *Club
		s.Given("the match data is loaded", func() {
			fla = mustClub(s.T, g, "Flamengo")
			flu = mustClub(s.T, g, "Fluminense")
		})
		s.When(`I search for matches between "Flamengo" and "Fluminense"`, func() {
			matches = g.FindMatches(MatchFilter{ClubID: fla.ID, OpponentID: flu.ID, Newest: true})
		})
		s.Then("I should receive a list of matches", func() {
			if len(matches) < 20 {
				s.Fatalf("got %d Fla-Flu matches, expected at least 20", len(matches))
			}
		})
		s.And("each match should have date, scores and competition", func() {
			for _, m := range matches {
				if !m.HasDate {
					s.Errorf("match %s has no date", m.ID)
				}
				if m.Competition == "" {
					s.Errorf("match %s has no competition", m.ID)
				}
				if m.Season == 0 {
					s.Errorf("match %s has no season", m.ID)
				}
				if !m.Involves(fla.ID) || !m.Involves(flu.ID) {
					s.Errorf("match %s does not involve both clubs", m.ID)
				}
			}
		})
		s.And("the results are ordered newest first", func() {
			for i := 1; i < len(matches); i++ {
				if matches[i].Date.After(matches[i-1].Date) {
					s.Fatalf("match %d (%s) is newer than match %d (%s)",
						i, matches[i].DateString(), i-1, matches[i-1].DateString())
				}
			}
		})
	})

	bdd.Scenario(t, "What matches did Palmeiras play in 2022", func(s *bdd.S) {
		var matches []*Match
		s.Given("the match data is loaded", nil)
		s.When("I search for Palmeiras matches in season 2022", func() {
			matches = g.FindMatches(MatchFilter{ClubID: mustClub(s.T, g, "Palmeiras").ID, Season: 2022})
		})
		s.Then("all matches are from that season and involve Palmeiras", func() {
			if len(matches) < 38 {
				s.Fatalf("got %d matches, expected at least the 38 league fixtures", len(matches))
			}
			for _, m := range matches {
				if m.Season != 2022 {
					s.Errorf("match %s is from season %d", m.ID, m.Season)
				}
			}
		})
		s.And("they span more than one competition", func() {
			comps := map[Competition]bool{}
			for _, m := range matches {
				comps[m.Competition] = true
			}
			if len(comps) < 2 {
				s.Errorf("competitions = %v, expected league plus cup football", comps)
			}
		})
	})

	bdd.Scenario(t, "Find all Copa do Brasil finals", func(s *bdd.S) {
		var finals []*Match
		s.Given("the Copa do Brasil data is loaded", nil)
		s.When(`I search for matches with stage "final"`, func() {
			finals = g.FindMatches(MatchFilter{Competition: CopaDoBrasil, Stage: "final", Newest: true})
		})
		s.Then("every result is labelled as a final", func() {
			if len(finals) < 10 {
				s.Fatalf("got %d finals, expected at least 10", len(finals))
			}
			for _, m := range finals {
				if !strings.Contains(strings.ToLower(m.Stage), "final") {
					s.Errorf("match %s has stage %q", m.ID, m.Stage)
				}
			}
		})
		s.And("the finals are spread across seasons", func() {
			seasons := map[int]bool{}
			for _, m := range finals {
				seasons[m.Season] = true
			}
			if len(seasons) < 5 {
				s.Errorf("finals cover %d seasons, expected several", len(seasons))
			}
		})
	})

	bdd.Scenario(t, "matches can be filtered by date range and venue", func(s *bdd.S) {
		var matches []*Match
		club := mustClub(t, g, "Corinthians")
		from, _ := ParseDateArg("2022-04", false)
		to, _ := ParseDateArg("2022-06", true)
		s.Given("a club, a date range and a home-only filter", nil)
		s.When("the filter is applied", func() {
			matches = g.FindMatches(MatchFilter{
				ClubID: club.ID, Venue: VenueHome, DateFrom: from, DateTo: to,
			})
		})
		s.Then("only home matches inside the range come back", func() {
			if len(matches) == 0 {
				s.Fatal("no matches found")
			}
			for _, m := range matches {
				if m.HomeClubID != club.ID {
					s.Errorf("match %s is not a Corinthians home match", m.ID)
				}
				if m.Date.Before(from) || m.Date.After(to) {
					s.Errorf("match %s dated %s is outside the range", m.ID, m.DateString())
				}
			}
		})
	})

	bdd.Scenario(t, "When did Flamengo last play Corinthians and what was the score", func(s *bdd.S) {
		var latest *Match
		s.Given("the match data is loaded", nil)
		s.When("I ask for the most recent meeting", func() {
			matches := g.FindMatches(MatchFilter{
				ClubID:     mustClub(s.T, g, "Flamengo").ID,
				OpponentID: mustClub(s.T, g, "Corinthians").ID,
				Newest:     true, OnlyPlayed: true, Limit: 1,
			})
			if len(matches) > 0 {
				latest = matches[0]
			}
		})
		s.Then("a single match with a score is returned", func() {
			if latest == nil {
				s.Fatal("no meeting found")
			}
			if !latest.HasScore {
				s.Error("the match has no score")
			}
			if !strings.Contains(latest.ScoreLine(), "-") {
				s.Errorf("score line %q is not readable", latest.ScoreLine())
			}
		})
		s.And("it is the newest meeting in the data", func() {
			all := g.FindMatches(MatchFilter{
				ClubID:     mustClub(s.T, g, "Flamengo").ID,
				OpponentID: mustClub(s.T, g, "Corinthians").ID,
				OnlyPlayed: true,
			})
			for _, m := range all {
				if m.Date.After(latest.Date) {
					s.Fatalf("%s is newer than the reported latest %s", m.DateString(), latest.DateString())
				}
			}
		})
	})
}

func TestFeatureTeamQueries(t *testing.T) {
	bdd.Feature(t, "Team Queries")
	g := testGraph(t)

	bdd.Scenario(t, "Get team statistics", func(s *bdd.S) {
		var ts TeamStats
		s.Given("the match data is loaded", nil)
		s.When(`I request statistics for "Palmeiras" in season "2022"`, func() {
			ts = g.TeamStats(mustClub(s.T, g, "Palmeiras"), SerieA, 2022, VenueAny)
		})
		s.Then("I should receive wins, losses, draws and goals", func() {
			if ts.Overall.Played != 38 {
				s.Errorf("played = %d, want 38", ts.Overall.Played)
			}
			if ts.Overall.Wins+ts.Overall.Draws+ts.Overall.Losses != ts.Overall.Played {
				s.Error("wins + draws + losses does not equal matches played")
			}
			if ts.Overall.GoalsFor == 0 || ts.Overall.GoalsAgainst == 0 {
				s.Error("goals for/against were not calculated")
			}
			if ts.Overall.Points != ts.Overall.Wins*3+ts.Overall.Draws {
				s.Error("points do not follow the three-points-for-a-win rule")
			}
		})
		s.And("Palmeiras are the 2022 champions with 81 points", func() {
			if ts.Overall.Points != 81 {
				s.Errorf("points = %d, want the historical 81", ts.Overall.Points)
			}
		})
		s.And("home and away splits add up to the overall record", func() {
			if ts.Home.Played+ts.Away.Played != ts.Overall.Played {
				s.Errorf("home %d + away %d != overall %d", ts.Home.Played, ts.Away.Played, ts.Overall.Played)
			}
			if ts.Home.GoalsFor+ts.Away.GoalsFor != ts.Overall.GoalsFor {
				s.Error("home and away goals do not add up")
			}
		})
	})

	bdd.Scenario(t, "What is Corinthians home record in 2022", func(s *bdd.S) {
		var ts TeamStats
		s.Given("the match data is loaded", nil)
		s.When("I request the Corinthians home record for Série A 2022", func() {
			ts = g.TeamStats(mustClub(s.T, g, "Corinthians"), SerieA, 2022, VenueHome)
		})
		s.Then("the record covers the 19 home fixtures only", func() {
			if ts.Overall.Played != 19 {
				s.Errorf("played = %d, want 19", ts.Overall.Played)
			}
			if ts.Away.Played != 0 {
				s.Errorf("away matches leaked into a home-only query: %d", ts.Away.Played)
			}
		})
		s.And("a win rate is reported as a percentage", func() {
			if ts.Overall.WinRate <= 0 || ts.Overall.WinRate > 100 {
				s.Errorf("win rate = %.1f", ts.Overall.WinRate)
			}
		})
	})

	bdd.Scenario(t, "Compare Palmeiras and Santos head-to-head", func(s *bdd.S) {
		var h HeadToHead
		s.Given("the match data is loaded", nil)
		s.When("I compare the two clubs", func() {
			h = g.HeadToHead(mustClub(s.T, g, "Palmeiras"), mustClub(s.T, g, "Santos"), "", 0, 10)
		})
		s.Then("wins, draws and goals are reported for both sides", func() {
			if h.Played == 0 {
				s.Fatal("no meetings found")
			}
			if h.AWins+h.BWins+h.Draws != h.Played {
				s.Errorf("%d + %d + %d != %d", h.AWins, h.BWins, h.Draws, h.Played)
			}
			if h.AGoals == 0 || h.BGoals == 0 {
				s.Error("goal totals missing")
			}
		})
		s.And("the fixture is recognised as a classic", func() {
			if h.Nickname == "" {
				s.Error("expected the Clássico da Saudade nickname")
			}
		})
		s.And("reversing the arguments mirrors the result", func() {
			rev := g.HeadToHead(mustClub(s.T, g, "Santos"), mustClub(s.T, g, "Palmeiras"), "", 0, 10)
			if rev.AWins != h.BWins || rev.BWins != h.AWins || rev.Draws != h.Draws {
				s.Errorf("mirrored head-to-head disagrees: %+v vs %+v", rev, h)
			}
		})
	})

	bdd.Scenario(t, "Which team scored the most goals in Serie A 2019", func(s *bdd.S) {
		var lb Leaderboard
		var err error
		s.Given("the match data is loaded", nil)
		s.When("I rank clubs by goals scored in Série A 2019", func() {
			lb, err = g.Leaderboard("goals_for", SerieA, 2019, VenueAny, 10, 5)
		})
		s.Then("Flamengo top the list with 86 goals", func() {
			if err != nil {
				s.Fatalf("leaderboard: %v", err)
			}
			if len(lb.Rows) == 0 {
				s.Fatal("empty leaderboard")
			}
			if lb.Rows[0].Club != "Flamengo" || lb.Rows[0].GoalsFor != 86 {
				s.Errorf("top scorer = %s with %d, want Flamengo with 86", lb.Rows[0].Club, lb.Rows[0].GoalsFor)
			}
		})
		s.And("the list is sorted descending", func() {
			for i := 1; i < len(lb.Rows); i++ {
				if lb.Rows[i].GoalsFor > lb.Rows[i-1].GoalsFor {
					s.Fatal("leaderboard is not sorted by goals scored")
				}
			}
		})
	})

	bdd.Scenario(t, "What competitions has Palmeiras played in", func(s *bdd.S) {
		var ts TeamStats
		s.Given("the match data is loaded", nil)
		s.When("I ask for the Palmeiras profile", func() {
			ts = g.TeamStats(mustClub(s.T, g, "Palmeiras"), "", 0, VenueAny)
		})
		s.Then("the answer breaks the record down by competition", func() {
			if len(ts.ByCompetition) < 3 {
				s.Fatalf("only %d competitions reported", len(ts.ByCompetition))
			}
			seen := map[Competition]bool{}
			for _, cr := range ts.ByCompetition {
				seen[cr.Competition] = true
				if cr.Record.Played == 0 {
					s.Errorf("%s has no played matches", cr.Competition)
				}
				if len(cr.Seasons) == 0 {
					s.Errorf("%s lists no seasons", cr.Competition)
				}
			}
			for _, want := range []Competition{SerieA, CopaDoBrasil, Libertadores} {
				if !seen[want] {
					s.Errorf("expected Palmeiras to appear in %s", want)
				}
			}
		})
	})
}

func TestFeaturePlayerQueries(t *testing.T) {
	bdd.Feature(t, "Player Queries")
	g := testGraph(t)

	bdd.Scenario(t, "Find all Brazilian players in the dataset", func(s *bdd.S) {
		var players []*Player
		s.Given("the FIFA player data is loaded", nil)
		s.When("I filter by nationality Brazil", func() {
			players = g.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
		})
		s.Then("hundreds of Brazilian players are returned", func() {
			if len(players) != 827 {
				s.Errorf("got %d Brazilian players, want 827", len(players))
			}
			for _, p := range players {
				if p.Nationality != "Brazil" {
					s.Fatalf("player %s has nationality %q", p.Name, p.Nationality)
				}
			}
		})
		s.And("they are ranked by overall rating with Neymar first", func() {
			if players[0].Name != "Neymar Jr" {
				s.Errorf("top Brazilian = %s, want Neymar Jr", players[0].Name)
			}
			for i := 1; i < len(players); i++ {
				if players[i].Overall > players[i-1].Overall {
					s.Fatal("players are not sorted by overall rating")
				}
			}
		})
	})

	bdd.Scenario(t, "Who is a named player", func(s *bdd.S) {
		var p *Player
		var others []*Player
		s.Given("the FIFA player data is loaded", nil)
		s.When(`I search for "Gabriel Jesus"`, func() { p, others = g.FindPlayer("Gabriel Jesus") })
		s.Then("a complete profile is returned", func() {
			if p == nil {
				s.Fatal("player not found")
			}
			if p.Name != "Gabriel Jesus" {
				s.Errorf("found %q, want Gabriel Jesus", p.Name)
			}
			if p.Nationality != "Brazil" || p.Overall == 0 || p.Club == "" || p.Position == "" {
				s.Errorf("incomplete profile: %+v", p)
			}
			if len(p.Skills) < 20 {
				s.Errorf("only %d skill attributes captured", len(p.Skills))
			}
		})
		s.And("an exact name match outranks other players containing the query", func() {
			for _, o := range others {
				if o.Name == "Gabriel Jesus" {
					s.Error("the exact match was not ranked first")
				}
			}
		})
		s.And("a partial name returns every candidate", func() {
			hits := g.SearchPlayers(PlayerFilter{Name: "Gabriel"})
			if len(hits) < 5 {
				s.Errorf("searching Gabriel returned %d players", len(hits))
			}
			for _, h := range hits {
				if !strings.Contains(normalizeText(h.Name), "gabriel") {
					s.Errorf("%q does not contain the query", h.Name)
				}
			}
		})
	})

	bdd.Scenario(t, "a player absent from the FIFA 19 snapshot is not invented", func(s *bdd.S) {
		var p *Player
		s.Given("the FIFA player data, which is a 2019 snapshot", nil)
		s.When(`I search for "Gabriel Barbosa", who is not in it`, func() {
			p, _ = g.FindPlayer("Gabriel Barbosa")
		})
		s.Then("nothing is returned rather than a wrong player", func() {
			if p != nil {
				s.Errorf("unexpectedly matched %q", p.Name)
			}
		})
	})

	bdd.Scenario(t, "Who are the highest-rated players at a Brazilian club", func(s *bdd.S) {
		var players []*Player
		var club *Club
		s.Given("the FIFA data links 15 Brazilian clubs into the graph", nil)
		s.When("I ask for the Grêmio squad", func() {
			club = mustClub(s.T, g, "Grêmio")
			players = g.PlayersAtClub(club.ID)
		})
		s.Then("a squad ranked by rating is returned", func() {
			if len(players) == 0 {
				s.Fatal("no players linked to Grêmio")
			}
			for i := 1; i < len(players); i++ {
				if players[i].Overall > players[i-1].Overall {
					s.Fatal("squad is not sorted by rating")
				}
			}
			for _, p := range players {
				if p.ClubID != club.ID {
					s.Errorf("player %s is linked to %q", p.Name, p.ClubID)
				}
			}
		})
	})

	bdd.Scenario(t, "Show me all forwards from a club", func(s *bdd.S) {
		var players []*Player
		s.Given("the FIFA player data is loaded", nil)
		s.When("I filter by club and position group Forward", func() {
			players = g.SearchPlayers(PlayerFilter{
				ClubID: mustClub(s.T, g, "Santos").ID, PositionGroup: "Forward",
			})
		})
		s.Then("only forwards from that club are returned", func() {
			if len(players) == 0 {
				s.Fatal("no forwards found")
			}
			for _, p := range players {
				if p.PositionGroup != "Forward" {
					s.Errorf("player %s is a %s", p.Name, p.PositionGroup)
				}
				if p.ClubID != "santos-sp" {
					s.Errorf("player %s belongs to %q", p.Name, p.ClubID)
				}
			}
		})
	})

	bdd.Scenario(t, "a club missing from the FIFA snapshot is reported honestly", func(s *bdd.S) {
		var squad []*Player
		var linked []*Club
		s.Given("the FIFA 19 snapshot, which licenses only some Brazilian clubs", nil)
		s.When("I ask for the Flamengo squad", func() {
			squad = g.PlayersAtClub(mustClub(s.T, g, "Flamengo").ID)
			linked = g.LinkedFIFAClubs()
		})
		s.Then("the squad is empty rather than wrong", func() {
			if len(squad) != 0 {
				s.Errorf("expected no Flamengo players in the FIFA data, got %d", len(squad))
			}
		})
		s.And("the clubs that are covered can be listed instead", func() {
			if len(linked) != 15 {
				s.Errorf("linked FIFA clubs = %d, want 15", len(linked))
			}
			for _, c := range linked {
				if len(g.PlayersAtClub(c.ID)) == 0 {
					s.Errorf("club %s is listed as linked but has no players", c.Name)
				}
			}
		})
	})

	bdd.Scenario(t, "Brazilian players can be grouped by club", func(s *bdd.S) {
		var rows []ClubPlayerSummary
		s.Given("all Brazilian players", nil)
		s.When("they are grouped by club", func() {
			rows = SummarizeByClub(g.SearchPlayers(PlayerFilter{Nationality: "Brazil"}))
		})
		s.Then("each group reports a squad size and average rating", func() {
			if len(rows) == 0 {
				s.Fatal("no groups")
			}
			for _, r := range rows {
				if r.Players == 0 || r.AvgOverall <= 0 || r.TopPlayer == "" {
					s.Errorf("incomplete group: %+v", r)
				}
			}
		})
		s.And("groups are ordered by squad size", func() {
			for i := 1; i < len(rows); i++ {
				if rows[i].Players > rows[i-1].Players {
					s.Fatal("groups are not sorted")
				}
			}
		})
	})
}

func TestFeatureCompetitionQueries(t *testing.T) {
	bdd.Feature(t, "Competition Queries")
	g := testGraph(t)

	// knownChampions is independent ground truth: the Brasileirão winners and
	// their points totals from 2003 to 2022.
	knownChampions := []struct {
		season int
		club   string
		points int
	}{
		{2003, "Cruzeiro", 100}, {2004, "Santos", 89}, {2005, "Corinthians", 81},
		{2006, "São Paulo", 78}, {2007, "São Paulo", 77}, {2008, "São Paulo", 75},
		{2009, "Flamengo", 67}, {2010, "Fluminense", 71}, {2011, "Corinthians", 71},
		{2012, "Fluminense", 77}, {2013, "Cruzeiro", 76}, {2014, "Cruzeiro", 80},
		{2015, "Corinthians", 81}, {2016, "Palmeiras", 80}, {2017, "Corinthians", 72},
		{2018, "Palmeiras", 80}, {2019, "Flamengo", 90}, {2020, "Flamengo", 71},
		{2021, "Atlético Mineiro", 84}, {2022, "Palmeiras", 81},
	}

	bdd.Scenario(t, "Who won the 2019 Brasileirao", func(s *bdd.S) {
		var st Standings
		var err error
		s.Given("the match data is loaded", nil)
		s.When("I request the 2019 Série A standings", func() { st, err = g.Standings(SerieA, 2019) })
		s.Then("Flamengo are champions with 90 points from 28 wins", func() {
			if err != nil {
				s.Fatalf("standings: %v", err)
			}
			top := st.Rows[0]
			if top.Record.Club != "Flamengo" || top.Record.Points != 90 || top.Record.Wins != 28 {
				s.Errorf("champion = %s with %d pts and %d wins", top.Record.Club, top.Record.Points, top.Record.Wins)
			}
			if top.Status != "Champion" {
				s.Errorf("status = %q, want Champion", top.Status)
			}
		})
		s.And("the table is ordered by points then wins then goal difference", func() {
			for i := 1; i < len(st.Rows); i++ {
				a, b := st.Rows[i-1].Record, st.Rows[i].Record
				if !lessStanding(a, b) {
					s.Fatalf("rows %d and %d are out of order: %+v then %+v", i-1, i, a, b)
				}
			}
		})
	})

	bdd.Scenario(t, "every calculated champion matches the historical record", func(s *bdd.S) {
		s.Given("the Brasileirão champions from 2003 to 2022 as independent ground truth", nil)
		s.Then("the calculated table agrees for all 20 seasons", func() {
			for _, want := range knownChampions {
				st, err := g.Standings(SerieA, want.season)
				if err != nil {
					s.Errorf("season %d: %v", want.season, err)
					continue
				}
				got := st.Rows[0].Record
				if got.Club != want.club {
					s.Errorf("%d champion = %s, want %s", want.season, got.Club, want.club)
				}
				if got.Points != want.points {
					s.Errorf("%d %s = %d points, want %d", want.season, got.Club, got.Points, want.points)
				}
			}
		})
	})

	bdd.Scenario(t, "Which teams were relegated in 2020", func(s *bdd.S) {
		var relegated []string
		s.Given("the completed 2020 Série A season", nil)
		s.When("I read the relegation places off the calculated table", func() {
			st, err := g.Standings(SerieA, 2020)
			if err != nil {
				s.Fatalf("standings: %v", err)
			}
			for _, row := range st.Rows {
				if row.Status == "Relegated" {
					relegated = append(relegated, row.Record.Club)
				}
			}
		})
		s.Then("the bottom four are Vasco, Goiás, Coritiba and Botafogo", func() {
			want := map[string]bool{"Vasco da Gama": true, "Goiás": true, "Coritiba": true, "Botafogo": true}
			if len(relegated) != 4 {
				s.Fatalf("relegated = %v, want 4 clubs", relegated)
			}
			for _, club := range relegated {
				if !want[club] {
					s.Errorf("unexpected relegated club %q (got %v)", club, relegated)
				}
			}
		})
	})

	bdd.Scenario(t, "an unavailable season is refused with the available ones listed", func(s *bdd.S) {
		var err error
		s.Given("a season that predates the datasets", nil)
		s.When("standings are requested for 1999", func() { _, err = g.Standings(SerieA, 1999) })
		s.Then("the error lists the seasons that do exist", func() {
			if err == nil {
				s.Fatal("expected an error")
			}
			if !strings.Contains(err.Error(), "2003") {
				s.Errorf("error %q should list the available seasons", err)
			}
		})
	})

	bdd.Scenario(t, "knockout competitions are ranked but flagged as not a real table", func(s *bdd.S) {
		var st Standings
		s.Given("the 2019 Copa Libertadores", nil)
		s.When("standings are requested", func() {
			var err error
			st, err = g.Standings(Libertadores, 2019)
			if err != nil {
				s.Fatalf("standings: %v", err)
			}
		})
		s.Then("a caveat explains that it is not an official standing", func() {
			if !strings.Contains(st.Note, "knockout") {
				s.Errorf("note = %q", st.Note)
			}
			if len(st.Rows) == 0 {
				s.Error("no rows")
			}
		})
	})
}

func TestFeatureStatisticalAnalysis(t *testing.T) {
	bdd.Feature(t, "Statistical Analysis")
	g := testGraph(t)

	bdd.Scenario(t, "What is the average goals per match in the Brasileirao", func(s *bdd.S) {
		var agg Aggregate
		s.Given("all Série A matches", nil)
		s.When("aggregate statistics are calculated", func() { agg = g.AggregateStats(SerieA, 0) })
		s.Then("a plausible goals-per-match average is reported", func() {
			if agg.GoalsPerMatch < 2.0 || agg.GoalsPerMatch > 3.5 {
				s.Errorf("goals per match = %.2f, expected roughly 2.2-2.8", agg.GoalsPerMatch)
			}
			if agg.Played < 7000 {
				s.Errorf("only %d matches with scores", agg.Played)
			}
		})
		s.And("the average is consistent with the goal totals", func() {
			want := round2(float64(agg.TotalGoals) / float64(agg.Played))
			if agg.GoalsPerMatch != want {
				s.Errorf("goals per match = %.2f, recomputed %.2f", agg.GoalsPerMatch, want)
			}
			if agg.TotalGoals != agg.HomeGoals+agg.AwayGoals {
				s.Error("home and away goals do not sum to the total")
			}
		})
		s.And("home advantage is quantified and the outcomes sum to 100%", func() {
			if agg.HomeWinPct <= agg.AwayWinPct {
				s.Errorf("home win rate %.1f%% should exceed away %.1f%%", agg.HomeWinPct, agg.AwayWinPct)
			}
			total := agg.HomeWins + agg.AwayWins + agg.Draws
			if total != agg.Played {
				s.Errorf("outcomes sum to %d but %d matches were played", total, agg.Played)
			}
		})
	})

	bdd.Scenario(t, "Which team has the best away record", func(s *bdd.S) {
		var lb Leaderboard
		s.Given("all Série A matches", nil)
		s.When("clubs are ranked by win rate in away matches only", func() {
			var err error
			lb, err = g.Leaderboard("win_rate", SerieA, 0, VenueAway, 50, 5)
			if err != nil {
				s.Fatalf("leaderboard: %v", err)
			}
		})
		s.Then("a ranked list of clubs is returned", func() {
			if len(lb.Rows) == 0 {
				s.Fatal("empty leaderboard")
			}
			for i := 1; i < len(lb.Rows); i++ {
				if lb.Rows[i].WinRate > lb.Rows[i-1].WinRate {
					s.Fatal("not sorted by win rate")
				}
			}
		})
		s.And("only clubs with enough away matches are considered", func() {
			for _, r := range lb.Rows {
				if r.Played < 50 {
					s.Errorf("%s has only %d matches but passed the min_matches filter", r.Club, r.Played)
				}
			}
		})
		s.And("the away leaderboard differs from the home one", func() {
			home, err := g.Leaderboard("win_rate", SerieA, 0, VenueHome, 50, 5)
			if err != nil {
				s.Fatalf("leaderboard: %v", err)
			}
			if home.Rows[0].Played == lb.Rows[0].Played && home.Rows[0].Wins == lb.Rows[0].Wins {
				s.Error("home and away leaderboards produced identical records")
			}
		})
	})

	bdd.Scenario(t, "Show me the biggest wins in the dataset", func(s *bdd.S) {
		var matches []*Match
		s.Given("all matches", nil)
		s.When("matches are ranked by margin of victory", func() {
			matches = g.BiggestWins("", 0, 10)
		})
		s.Then("the largest margins come first and all have scores", func() {
			if len(matches) != 10 {
				s.Fatalf("got %d matches, want 10", len(matches))
			}
			if matches[0].GoalDifference() < 5 {
				s.Errorf("biggest margin is only %d goals", matches[0].GoalDifference())
			}
			for i := 1; i < len(matches); i++ {
				if matches[i].GoalDifference() > matches[i-1].GoalDifference() {
					s.Fatal("not sorted by margin")
				}
				if !matches[i].HasScore {
					s.Fatal("a match without a score was ranked")
				}
			}
		})
	})

	bdd.Scenario(t, "Compare the 2018 and 2019 seasons", func(s *bdd.S) {
		var sc SeasonComparison
		var err error
		s.Given("two Série A seasons", nil)
		s.When("they are compared", func() { sc, err = g.CompareSeasons(SerieA, 2018, 2019) })
		s.Then("both seasons are summarised with their champions", func() {
			if err != nil {
				s.Fatalf("compare: %v", err)
			}
			if sc.ChampionA != "Palmeiras" || sc.ChampionB != "Flamengo" {
				s.Errorf("champions = %q and %q, want Palmeiras and Flamengo", sc.ChampionA, sc.ChampionB)
			}
			if sc.A.Played != 380 || sc.B.Played != 380 {
				s.Errorf("matches = %d and %d, want 380 each", sc.A.Played, sc.B.Played)
			}
		})
		s.And("the deltas are consistent with the two summaries", func() {
			want := round2(sc.B.GoalsPerMatch - sc.A.GoalsPerMatch)
			if sc.Deltas["goals_per_match"] != want {
				s.Errorf("delta = %.2f, want %.2f", sc.Deltas["goals_per_match"], want)
			}
		})
	})

	bdd.Scenario(t, "Show me all derbies in a season", func(s *bdd.S) {
		var derbies []Derby
		s.Given("the table of traditional rivalries", nil)
		s.When("derbies are searched for Série A 2022", func() {
			derbies = g.Derbies(SerieA, 2022, "", 5)
		})
		s.Then("several classic fixtures are found", func() {
			if len(derbies) < 5 {
				s.Fatalf("found %d derbies, expected several", len(derbies))
			}
			for _, d := range derbies {
				if d.Name == "" || len(d.Matches) == 0 {
					s.Errorf("incomplete derby %+v", d)
				}
				for _, m := range d.Matches {
					if m.Season != 2022 || m.Competition != SerieA {
						s.Errorf("derby match %s is outside the requested scope", m.ID)
					}
				}
			}
		})
		s.And("filtering by club narrows the list", func() {
			flaDerbies := g.Derbies(SerieA, 2022, mustClub(s.T, g, "Flamengo").ID, 5)
			if len(flaDerbies) == 0 || len(flaDerbies) >= len(derbies) {
				s.Errorf("club filter returned %d of %d derbies", len(flaDerbies), len(derbies))
			}
			for _, d := range flaDerbies {
				if d.ClubA != "Flamengo" && d.ClubB != "Flamengo" {
					s.Errorf("derby %s does not involve Flamengo", d.Name)
				}
			}
		})
	})
}

func TestQueryPerformanceBudget(t *testing.T) {
	bdd.Feature(t, "Query performance")
	g := testGraph(t)

	bdd.Scenario(t, "simple lookups answer well inside two seconds", func(s *bdd.S) {
		s.Given("the loaded knowledge graph", nil)
		s.Then("each simple query completes quickly", func() {
			checks := map[string]func(){
				"resolve a club":     func() { g.ResolveClub("Flamengo") },
				"club match list":    func() { g.FindMatches(MatchFilter{ClubID: "flamengo-rj"}) },
				"head to head":       func() { g.HeadToHead(g.Club("flamengo-rj"), g.Club("fluminense-rj"), "", 0, 10) },
				"player name search": func() { g.SearchPlayers(PlayerFilter{Name: "Gabriel", Limit: 20}) },
			}
			for name, fn := range checks {
				start := time.Now()
				fn()
				if d := time.Since(start); d > 2*time.Second {
					s.Errorf("%s took %s, budget is 2s", name, d)
				}
			}
		})
	})

	bdd.Scenario(t, "aggregate queries answer well inside five seconds", func(s *bdd.S) {
		s.Given("the loaded knowledge graph", nil)
		s.Then("each aggregate query completes quickly", func() {
			checks := map[string]func(){
				"all-time Série A aggregate": func() { g.AggregateStats(SerieA, 0) },
				"all-competition leaderboard": func() {
					if _, err := g.Leaderboard("points", "", 0, VenueAny, 10, 20); err != nil {
						s.Error(err)
					}
				},
				"standings":    func() { g.Standings(SerieA, 2019) },
				"biggest wins": func() { g.BiggestWins("", 0, 20) },
				"all derbies":  func() { g.Derbies("", 0, "", 5) },
			}
			for name, fn := range checks {
				start := time.Now()
				fn()
				if d := time.Since(start); d > 5*time.Second {
					s.Errorf("%s took %s, budget is 5s", name, d)
				}
			}
		})
	})
}
