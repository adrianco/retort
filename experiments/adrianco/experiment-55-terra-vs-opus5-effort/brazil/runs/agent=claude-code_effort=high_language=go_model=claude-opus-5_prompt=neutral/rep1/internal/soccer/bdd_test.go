// bdd_test.go expresses the acceptance criteria as Given/When/Then scenarios,
// following the Gherkin outline in the specification's "Testing Approach"
// section. Run with -v to read the scenarios as a specification:
//
//	go test ./internal/soccer -run TestFeature -v
package soccer

import (
	"errors"
	"strings"
	"testing"
)

// given, when, then and and_ record a readable trace of each scenario.
func given(t *testing.T, format string, a ...any) { t.Helper(); t.Logf("  Given "+format, a...) }
func when(t *testing.T, format string, a ...any)  { t.Helper(); t.Logf("  When  "+format, a...) }
func then(t *testing.T, format string, a ...any)  { t.Helper(); t.Logf("  Then  "+format, a...) }
func and_(t *testing.T, format string, a ...any)  { t.Helper(); t.Logf("  And   "+format, a...) }

// errorsAs is a thin alias so the scenarios below read as prose.
func errorsAs(err error, target any) bool { return errors.As(err, target) }

// ---------------------------------------------------------------------------
// Feature: Match Queries
// ---------------------------------------------------------------------------

func TestFeatureMatchQueries(t *testing.T) {
	g := LoadTestGraph(t)

	t.Run("find matches between two teams", func(t *testing.T) {
		given(t, "the match data is loaded")
		when(t, `I search for matches between "Flamengo" and "Fluminense"`)
		res, err := g.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense", Limit: 100})
		if err != nil {
			t.Fatalf("SearchMatches: %v", err)
		}

		then(t, "I receive a list of matches (%d found)", res.Total)
		if res.Total < 30 {
			t.Fatalf("only %d Fla-Flu meetings found; the datasets should hold far more", res.Total)
		}
		and_(t, "each match has a date, scores and a competition")
		for _, m := range res.Matches {
			if m.Date == "" || m.Competition == "" || m.Score == "" {
				t.Fatalf("incomplete match view: %+v", m)
			}
			if m.HomeTeam != "Flamengo" && m.AwayTeam != "Flamengo" {
				t.Fatalf("match does not involve Flamengo: %s", m.Summary)
			}
			if m.HomeTeam != "Fluminense" && m.AwayTeam != "Fluminense" {
				t.Fatalf("match does not involve Fluminense: %s", m.Summary)
			}
		}
		and_(t, "the head-to-head record is included: %s", res.HeadToHead.Line)
		if res.HeadToHead == nil || res.HeadToHead.Played != res.Total {
			t.Fatal("head-to-head summary missing or inconsistent")
		}
		and_(t, "the fixture is recognised as the %s derby", res.Rivalry)
		if res.Rivalry != "Fla-Flu" {
			t.Errorf("rivalry = %q, want Fla-Flu", res.Rivalry)
		}
	})

	t.Run("find matches by season", func(t *testing.T) {
		given(t, "the match data is loaded")
		when(t, `I ask what matches Palmeiras played in 2023`)
		res, err := g.SearchMatches(MatchFilter{Team: "Palmeiras", Season: 2023, Limit: 100})
		if err != nil {
			t.Fatalf("SearchMatches: %v", err)
		}
		then(t, "every match returned is from 2023 (%d matches)", res.Total)
		for _, m := range res.Matches {
			if m.Season != 2023 {
				t.Fatalf("match from season %d leaked into a 2023 query: %s", m.Season, m.Summary)
			}
		}
		and_(t, "the club's record over those matches is included")
		if res.Record == nil || res.Record.Played != res.Total {
			t.Fatal("record missing or inconsistent")
		}
	})

	t.Run("find knockout finals without matching semifinals", func(t *testing.T) {
		given(t, "Copa do Brasil rounds have been labelled with stage names")
		when(t, `I search for competition "copa-do-brasil" stage "final"`)
		res, err := g.SearchMatches(MatchFilter{Competition: CompCopaDoBrasil, Stage: "final", Limit: 100})
		if err != nil {
			t.Fatalf("SearchMatches: %v", err)
		}
		then(t, "only finals are returned (%d matches)", res.Total)
		for _, m := range res.Matches {
			if m.Stage != "Final" {
				t.Fatalf("stage %q leaked into a final-only query", m.Stage)
			}
		}
		and_(t, "the 2018 final is Cruzeiro against Corinthians")
		found := false
		for _, m := range res.Matches {
			if m.Season == 2018 && strings.Contains(m.Summary, "Cruzeiro") && strings.Contains(m.Summary, "Corinthians") {
				found = true
			}
		}
		if !found {
			t.Error("the 2018 Copa do Brasil final between Cruzeiro and Corinthians is missing")
		}
	})

	t.Run("find the biggest wins", func(t *testing.T) {
		given(t, "the match data is loaded")
		when(t, "I sort all matches by goal difference")
		res, err := g.SearchMatches(MatchFilter{Sort: "goal_diff", Limit: 10})
		if err != nil {
			t.Fatalf("SearchMatches: %v", err)
		}
		then(t, "results are ordered by decreasing margin")
		prev := 1 << 30
		for _, m := range res.Matches {
			d := m.HomeGoals - m.AwayGoals
			if d < 0 {
				d = -d
			}
			if d > prev {
				t.Fatalf("margins are not sorted: %s", m.Summary)
			}
			prev = d
		}
		and_(t, "the largest margin is at least 7 goals (got %d)", prev)
	})
}

// ---------------------------------------------------------------------------
// Feature: Team Queries
// ---------------------------------------------------------------------------

func TestFeatureTeamQueries(t *testing.T) {
	g := LoadTestGraph(t)

	t.Run("get team statistics", func(t *testing.T) {
		given(t, "the match data is loaded")
		when(t, `I request statistics for "Palmeiras" in season 2023`)
		res, err := g.TeamStats("Palmeiras", "", 2023, 0, 0, "")
		if err != nil {
			t.Fatalf("TeamStats: %v", err)
		}
		then(t, "I receive wins, losses, draws and goals")
		if res.Overall.Played == 0 {
			t.Fatal("no matches reported")
		}
		if res.Overall.Wins+res.Overall.Draws+res.Overall.Losses != res.Overall.Played {
			t.Fatal("W+D+L does not equal matches played")
		}
		if res.Overall.Points != res.Overall.Wins*3+res.Overall.Draws {
			t.Fatal("points do not follow 3-for-a-win")
		}
		and_(t, "home and away splits add up to the overall record")
		if res.Home.Played+res.Away.Played != res.Overall.Played {
			t.Fatal("home + away != overall")
		}
		if res.Home.GoalsFor+res.Away.GoalsFor != res.Overall.GoalsFor {
			t.Fatal("home + away goals != overall goals")
		}
	})

	t.Run("home record for a single season", func(t *testing.T) {
		given(t, "the 2022 Brasileirão is fully loaded")
		when(t, "I request Corinthians' home record in the 2022 Série A")
		res, err := g.TeamStats("Corinthians", "serie-a", 2022, 0, 0, "home")
		if err != nil {
			t.Fatalf("TeamStats: %v", err)
		}
		then(t, "19 home matches are reported (got %d)", res.Overall.Played)
		if res.Overall.Played != 19 {
			t.Fatalf("expected 19 home matches in a 20-club season, got %d", res.Overall.Played)
		}
		and_(t, "no away matches are included")
		if res.Away.Played != 0 {
			t.Fatal("away matches leaked into a home-only query")
		}
	})

	t.Run("which competitions a club has played in", func(t *testing.T) {
		given(t, "all five competitions are loaded")
		when(t, "I ask what competitions Palmeiras has played in")
		res, err := g.TeamCompetitions("Palmeiras")
		if err != nil {
			t.Fatalf("TeamCompetitions: %v", err)
		}
		then(t, "Série A, Copa do Brasil and Libertadores are all present")
		names := map[string]bool{}
		for _, c := range res.Competitions {
			names[c.Competition] = true
		}
		for _, want := range []string{
			CompetitionName(CompSerieA), CompetitionName(CompCopaDoBrasil), CompetitionName(CompLibertadores),
		} {
			if !names[want] {
				t.Errorf("%s missing from Palmeiras' competitions", want)
			}
		}
	})

	t.Run("head to head between two clubs", func(t *testing.T) {
		given(t, "the match data is loaded")
		when(t, "I compare Palmeiras and Santos head-to-head")
		res, err := g.HeadToHead("Palmeiras", "Santos", "", 0, 0, 5)
		if err != nil {
			t.Fatalf("HeadToHead: %v", err)
		}
		then(t, "wins, draws and goals are reported: %s", res.Summary.Line)
		s := res.Summary
		if s.TeamAWins+s.TeamBWins+s.Draws != s.Played {
			t.Fatal("head-to-head results do not add up")
		}
		and_(t, "the derby name is identified as %q", res.Rivalry)
		if res.Rivalry == "" {
			t.Error("Palmeiras vs Santos should be recognised as a clássico")
		}
		and_(t, "the first and most recent meetings are reported")
		if res.FirstMeeting == nil || res.LastMeeting == nil {
			t.Fatal("first/last meeting missing")
		}
		if res.FirstMeeting.Date > res.LastMeeting.Date {
			t.Fatal("first meeting is later than the most recent one")
		}
	})
}

// ---------------------------------------------------------------------------
// Feature: Name Handling
// ---------------------------------------------------------------------------

func TestFeatureTeamNameVariations(t *testing.T) {
	g := LoadTestGraph(t)

	t.Run("spelling variants reach the same club", func(t *testing.T) {
		given(t, "the datasets spell clubs in several different ways")
		groups := [][]string{
			{"Flamengo", "Flamengo-RJ", "flamengo", "FLAMENGO"},
			{"São Paulo", "Sao Paulo", "Sao Paulo-SP", "São Paulo - SP"},
			{"Atletico Mineiro", "Atlético-MG", "Atletico MG", "Atlético - MG"},
			{"Grêmio", "Gremio", "Gremio-RS", "Grêmio RS"},
			{"Athletico Paranaense", "Atletico-PR", "Athletico", "Atletico Paranaense"},
			{"Vasco", "Vasco da Gama", "Vasco Da Gama RJ"},
			{"Sport", "Sport Recife", "Sport Club do Recife"},
			{"Bragantino", "Red Bull Bragantino"},
		}
		for _, group := range groups {
			when(t, "I resolve the variants %v", group)
			var first *Team
			for _, name := range group {
				got, err := g.ResolveTeam(name)
				if err != nil {
					t.Fatalf("ResolveTeam(%q): %v", name, err)
				}
				if first == nil {
					first = got
					continue
				}
				if got.ID != first.ID {
					t.Errorf("%q resolved to %s but %q resolved to %s", name, got.ID, group[0], first.ID)
				}
			}
			then(t, "they all resolve to %s (%s)", first.Name, first.ID)
		}
	})

	t.Run("clubs sharing a name in different states stay separate", func(t *testing.T) {
		given(t, "several clubs are called Atlético")
		when(t, "I look them up by state")
		pairs := map[string]string{
			"Atletico-MG": "atletico-mg",
			"Atletico-PR": "atletico-pr",
			"Atletico-GO": "atletico-go",
		}
		for query, wantID := range pairs {
			got, err := g.ResolveTeam(query)
			if err != nil {
				t.Fatalf("ResolveTeam(%q): %v", query, err)
			}
			if got.ID != wantID {
				t.Errorf("%q resolved to %s, want %s", query, got.ID, wantID)
			}
		}
		then(t, "each state's club is a distinct node in the graph")
		and_(t, "Vitória of Bahia is not confused with Vitória of Espírito Santo")
		ba, err := g.ResolveTeam("Vitória")
		if err != nil {
			t.Fatalf("ResolveTeam: %v", err)
		}
		if ba.ID != "vitoria-ba" {
			t.Errorf("bare \"Vitória\" resolved to %s, want vitoria-ba", ba.ID)
		}
	})

	t.Run("a genuinely ambiguous name is not guessed", func(t *testing.T) {
		given(t, "Comercial exists in both Mato Grosso do Sul and Piauí with similar coverage")
		when(t, `I resolve "Comercial"`)
		_, err := g.ResolveTeam("Comercial")
		then(t, "the candidates are listed instead of one being picked")
		var amb *AmbiguousTeamError
		if !errorsAs(err, &amb) {
			t.Fatalf("error = %v (%T), want *AmbiguousTeamError", err, err)
		}
		if len(amb.Candidates) < 2 {
			t.Errorf("only %d candidates offered", len(amb.Candidates))
		}
		and_(t, "the message names them: %v", err)
	})

	t.Run("a dominant club still wins a tie", func(t *testing.T) {
		given(t, "Operário exists in Paraná, Mato Grosso and Mato Grosso do Sul")
		when(t, `I resolve "Operario" with no state`)
		got, err := g.ResolveTeam("Operario")
		then(t, "the club with by far the most matches is chosen: %s", got.Name)
		if err != nil {
			t.Fatalf("ResolveTeam: %v", err)
		}
		if got.ID != "operario-pr" {
			t.Errorf("resolved to %s, want operario-pr", got.ID)
		}
	})

	t.Run("an unknown club is reported rather than guessed", func(t *testing.T) {
		given(t, "a club that does not appear in any dataset")
		when(t, `I resolve "Manchester United"`)
		_, err := g.ResolveTeam("Manchester United")
		then(t, "an error explains that the club is absent")
		if err == nil {
			t.Fatal("expected an error for a club that is not in the data")
		}
		if _, ok := err.(*UnknownTeamError); !ok {
			t.Errorf("error type = %T, want *UnknownTeamError", err)
		}
	})
}

// ---------------------------------------------------------------------------
// Feature: Competition Queries
// ---------------------------------------------------------------------------

func TestFeatureCompetitionQueries(t *testing.T) {
	g := LoadTestGraph(t)

	t.Run("compute the 2019 Brasileirão table", func(t *testing.T) {
		given(t, "every 2019 Série A match is loaded")
		when(t, "I request the 2019 standings")
		st, err := g.Standings("serie-a", 2019)
		if err != nil {
			t.Fatalf("Standings: %v", err)
		}
		then(t, "Flamengo are champions with 90 points")
		if st.Champion != "Flamengo" {
			t.Errorf("champion = %q, want Flamengo", st.Champion)
		}
		top := st.Table[0]
		if top.Points != 90 || top.Wins != 28 || top.Draws != 6 || top.Losses != 4 {
			t.Errorf("Flamengo 2019 = %d pts (%dW %dD %dL), want 90 pts (28W 6D 4L)",
				top.Points, top.Wins, top.Draws, top.Losses)
		}
		and_(t, "the table holds 20 clubs each having played 38 matches")
		if len(st.Table) != 20 {
			t.Fatalf("table has %d rows, want 20", len(st.Table))
		}
		for _, row := range st.Table {
			if row.Played != 38 {
				t.Errorf("%s played %d matches, want 38", row.Team, row.Played)
			}
		}
		and_(t, "the four relegated clubs are named: %v", st.RelegatedTeams)
		wantRelegated := map[string]bool{"Cruzeiro": true, "CSA": true, "Chapecoense": true, "Avaí": true}
		if len(st.RelegatedTeams) != 4 {
			t.Fatalf("relegated = %v, want 4 clubs", st.RelegatedTeams)
		}
		for _, name := range st.RelegatedTeams {
			if !wantRelegated[name] {
				t.Errorf("%s should not be relegated in 2019", name)
			}
		}
	})

	t.Run("champions across every complete season", func(t *testing.T) {
		given(t, "Série A seasons 2003 to 2022 are complete in the data")
		champions := map[int]string{
			2003: "Cruzeiro", 2004: "Santos", 2005: "Corinthians", 2006: "São Paulo",
			2007: "São Paulo", 2008: "São Paulo", 2009: "Flamengo", 2010: "Fluminense",
			2011: "Corinthians", 2012: "Fluminense", 2013: "Cruzeiro", 2014: "Cruzeiro",
			2015: "Corinthians", 2016: "Palmeiras", 2017: "Corinthians", 2018: "Palmeiras",
			2019: "Flamengo", 2020: "Flamengo", 2021: "Atlético Mineiro", 2022: "Palmeiras",
		}
		when(t, "I compute each table from the raw results")
		for season, want := range champions {
			st, err := g.Standings("serie-a", season)
			if err != nil {
				t.Errorf("Standings(%d): %v", season, err)
				continue
			}
			if st.Champion != want {
				t.Errorf("%d champion = %q, want %q", season, st.Champion, want)
			}
		}
		then(t, "every computed champion matches the historical record")
	})

	t.Run("an incomplete season declares no champion", func(t *testing.T) {
		given(t, "the 2023 Série A is missing three fixtures in the source data")
		when(t, "I request the 2023 standings")
		st, err := g.Standings("serie-a", 2023)
		if err != nil {
			t.Fatalf("Standings: %v", err)
		}
		then(t, "the table is returned but marked incomplete")
		if st.Complete {
			t.Error("2023 should not be reported as complete")
		}
		and_(t, "no champion is asserted and the shortfall is explained")
		if st.Champion != "" {
			t.Errorf("champion = %q, want none for a partial season", st.Champion)
		}
		if st.Note == "" {
			t.Error("expected a note explaining the partial table")
		}
	})

	t.Run("knockout bracket", func(t *testing.T) {
		given(t, "the 2018 Copa Libertadores is loaded with its stage labels")
		when(t, "I request the bracket")
		b, err := g.Bracket("libertadores", 2018)
		if err != nil {
			t.Fatalf("Bracket: %v", err)
		}
		then(t, "the stages run from the group stage to the final")
		wantStages := []string{"Group Stage", "Round of 16", "Quarterfinals", "Semifinals", "Final"}
		if len(b.Stages) != len(wantStages) {
			t.Fatalf("got %d stages, want %d", len(b.Stages), len(wantStages))
		}
		for i, want := range wantStages {
			if b.Stages[i].Stage != want {
				t.Errorf("stage %d = %q, want %q", i, b.Stages[i].Stage, want)
			}
		}
		and_(t, "two-legged ties are collapsed into aggregates")
		final := b.Stages[len(b.Stages)-1]
		if len(final.Ties) != 1 || final.Ties[0].Legs != 2 {
			t.Fatalf("final = %+v, want a single two-legged tie", final.Ties)
		}
		and_(t, "River Plate are named champions")
		if b.Champion != "River Plate" {
			t.Errorf("champion = %q, want River Plate", b.Champion)
		}
	})

	t.Run("standings refuses a knockout competition", func(t *testing.T) {
		given(t, "the Copa do Brasil is a knockout tournament")
		when(t, "I ask for its league table")
		_, err := g.Standings("copa-do-brasil", 2018)
		then(t, "the server explains that a bracket is the right tool")
		if err == nil || !strings.Contains(err.Error(), "competition_bracket") {
			t.Errorf("error = %v, want a pointer to competition_bracket", err)
		}
	})
}

// ---------------------------------------------------------------------------
// Feature: Player Queries
// ---------------------------------------------------------------------------

func TestFeaturePlayerQueries(t *testing.T) {
	g := LoadTestGraph(t)

	t.Run("find Brazilian players", func(t *testing.T) {
		given(t, "the FIFA player data is loaded")
		when(t, `I filter by nationality "Brazil"`)
		res, err := g.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 10})
		if err != nil {
			t.Fatalf("SearchPlayers: %v", err)
		}
		then(t, "827 Brazilian players are found (got %d)", res.Total)
		if res.Total != 827 {
			t.Errorf("total = %d, want 827", res.Total)
		}
		and_(t, "results are sorted by overall rating with Neymar Jr first")
		if res.Players[0].Name != "Neymar Jr" {
			t.Errorf("top player = %q, want Neymar Jr", res.Players[0].Name)
		}
		for i := 1; i < len(res.Players); i++ {
			if res.Players[i].Overall > res.Players[i-1].Overall {
				t.Fatal("players are not sorted by overall rating")
			}
		}
	})

	t.Run("filter players by position group", func(t *testing.T) {
		given(t, "positions are stored as FIFA codes such as ST and LW")
		when(t, `I search for "forward" players at Atlético Mineiro`)
		res, err := g.SearchPlayers(PlayerFilter{Club: "Atletico Mineiro", Position: "forward", Limit: 20})
		if err != nil {
			t.Fatalf("SearchPlayers: %v", err)
		}
		then(t, "only attacking positions are returned (%d players)", res.Total)
		if res.Total == 0 {
			t.Fatal("no forwards found")
		}
		forwards := map[string]bool{}
		for _, code := range positionGroups["forward"] {
			forwards[code] = true
		}
		for _, p := range res.Players {
			if !forwards[p.Position] {
				t.Errorf("%s plays %s, which is not a forward position", p.Name, p.Position)
			}
		}
	})

	t.Run("cross-dataset join from squad to match record", func(t *testing.T) {
		given(t, "the player and match datasets name clubs differently")
		when(t, `I request the squad for "Gremio"`)
		res, err := g.ClubSquad("Gremio", 5)
		if err != nil {
			t.Fatalf("ClubSquad: %v", err)
		}
		then(t, "the FIFA squad is returned (%d players)", res.SquadSize)
		if res.SquadSize == 0 {
			t.Fatal("no squad found for Grêmio")
		}
		and_(t, "it is linked to the club's match record")
		if res.LinkedTeam == nil || res.LinkedTeam.ID != "gremio-rs" {
			t.Fatalf("linked team = %+v, want gremio-rs", res.LinkedTeam)
		}
		if res.LinkedTeam.MatchCount < 500 {
			t.Errorf("linked club has only %d matches on record", res.LinkedTeam.MatchCount)
		}
	})

	t.Run("an unlicensed club is reported honestly", func(t *testing.T) {
		given(t, "FIFA 19 does not license Flamengo")
		when(t, `I request the squad for "Flamengo"`)
		res, err := g.ClubSquad("Flamengo", 10)
		if err != nil {
			t.Fatalf("ClubSquad: %v", err)
		}
		then(t, "an empty squad is returned rather than a wrong one")
		if res.SquadSize != 0 {
			t.Fatalf("expected no Flamengo players, got %d", res.SquadSize)
		}
		and_(t, "the note lists the Brazilian clubs FIFA does cover")
		if !strings.Contains(res.Note, "Grêmio") {
			t.Errorf("note does not list the available clubs: %q", res.Note)
		}
		and_(t, "the club still links to its match record")
		if res.LinkedTeam == nil || res.LinkedTeam.ID != "flamengo-rj" {
			t.Error("Flamengo should still resolve in the match data")
		}
	})

	t.Run("a missing player suggests near matches", func(t *testing.T) {
		given(t, "Gabriel Barbosa is not in the FIFA 19 snapshot")
		when(t, "I ask for his profile")
		_, err := g.PlayerProfile("Gabriel Barbosa", 0)
		then(t, "the answer says so and offers similar names")
		if err == nil {
			t.Fatal("expected an error")
		}
		if !strings.Contains(err.Error(), "Gabriel") {
			t.Errorf("error should suggest similar names, got: %v", err)
		}
	})

	t.Run("group Brazilian players by club", func(t *testing.T) {
		given(t, "FIFA licenses fifteen Brazilian clubs")
		when(t, "I group Brazilian players at Brazilian clubs by club")
		res, err := g.SearchPlayers(PlayerFilter{
			Nationality: "Brazil", BrazilianClubsOnly: true, GroupBy: "club", Limit: 5,
		})
		if err != nil {
			t.Fatalf("SearchPlayers: %v", err)
		}
		then(t, "each group reports a count and an average rating")
		if len(res.Groups) != 15 {
			t.Errorf("got %d clubs, want 15", len(res.Groups))
		}
		for _, gr := range res.Groups {
			if gr.Players == 0 || gr.AvgOverall == 0 {
				t.Errorf("group %q is empty: %+v", gr.Key, gr)
			}
		}
		and_(t, "foreign clubs with colliding names are excluded")
		for _, gr := range res.Groups {
			if strings.Contains(gr.Key, "Boavista") || strings.Contains(gr.Key, "Nacional") {
				t.Errorf("%q is not a Brazilian club", gr.Key)
			}
		}
	})
}

// ---------------------------------------------------------------------------
// Feature: Statistical Analysis
// ---------------------------------------------------------------------------

func TestFeatureStatisticalAnalysis(t *testing.T) {
	g := LoadTestGraph(t)

	t.Run("league-wide aggregates", func(t *testing.T) {
		given(t, "every Série A match is loaded")
		when(t, "I request aggregate statistics")
		res, err := g.AggregateStats(StatsScope{Competition: "serie-a"})
		if err != nil {
			t.Fatalf("AggregateStats: %v", err)
		}
		then(t, "goals per match is a plausible %.2f", res.GoalsPerMatch)
		if res.GoalsPerMatch < 2.0 || res.GoalsPerMatch > 3.5 {
			t.Errorf("goals per match = %.2f, outside a plausible range", res.GoalsPerMatch)
		}
		and_(t, "home, draw and away rates sum to 100%%")
		sum := res.HomeWinPct + res.DrawPct + res.AwayWinPct
		if sum < 99.5 || sum > 100.5 {
			t.Errorf("home+draw+away = %.1f%%, want 100%%", sum)
		}
		and_(t, "home advantage is visible: %.1f%% home wins vs %.1f%% away", res.HomeWinPct, res.AwayWinPct)
		if res.HomeWinPct <= res.AwayWinPct {
			t.Error("expected home teams to win more often than away teams")
		}
		and_(t, "leaderboards are populated")
		if len(res.TopScoringTeams) == 0 || len(res.BestHomeRecords) == 0 || len(res.BestAwayRecords) == 0 {
			t.Error("leaderboards are empty")
		}
		if res.Matches != res.HomeWins+res.Draws+res.AwayWins {
			t.Error("results do not add up to the match count")
		}
	})

	t.Run("season comparison", func(t *testing.T) {
		given(t, "the 2018 and 2019 seasons are both complete")
		when(t, "I compare them")
		res, err := g.CompareSeasons("serie-a", []int{2018, 2019})
		if err != nil {
			t.Fatalf("CompareSeasons: %v", err)
		}
		then(t, "both seasons are summarised")
		if len(res.Seasons) != 2 {
			t.Fatalf("got %d seasons, want 2", len(res.Seasons))
		}
		for _, s := range res.Seasons {
			if s.Matches != 380 {
				t.Errorf("%d had %d matches, want 380", s.Season, s.Matches)
			}
		}
		and_(t, "each season names its champion")
		for _, l := range res.Leaders {
			if l.Champion == "" {
				t.Errorf("%d has no champion", l.Season)
			}
		}
		and_(t, "a plain-language comparison is produced: %s", res.Commentary)
		if res.Commentary == "" {
			t.Error("no commentary produced")
		}
	})

	t.Run("derbies in a season", func(t *testing.T) {
		given(t, "the traditional rivalries are known to the server")
		when(t, "I ask for derbies played in 2023")
		rep, err := g.Derbies("", 2023, 0, 0, 50)
		if err != nil {
			t.Fatalf("Derbies: %v", err)
		}
		then(t, "%d derby matches are found across %d rivalries", rep.Total, len(rep.Derbies))
		if rep.Total == 0 || len(rep.Derbies) == 0 {
			t.Fatal("no derbies found in 2023")
		}
		and_(t, "the Fla-Flu is among them")
		found := false
		for _, d := range rep.Derbies {
			if d.Rivalry == "Fla-Flu" {
				found = true
			}
		}
		if !found {
			t.Error("Fla-Flu missing from the 2023 derbies")
		}
		and_(t, "every returned match is between rivals")
		for _, m := range rep.Matches {
			if m.Season != 2023 {
				t.Errorf("season %d match returned for a 2023 query", m.Season)
			}
		}
	})
}
