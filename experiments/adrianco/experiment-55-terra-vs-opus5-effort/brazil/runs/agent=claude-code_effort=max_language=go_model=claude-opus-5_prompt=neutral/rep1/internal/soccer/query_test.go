package soccer

import (
	"fmt"
	"strings"
	"testing"
	"time"
)

func TestFindMatchesByTeam(t *testing.T) {
	s := testStore(t)
	page := s.FindMatches(MatchFilter{TeamID: "palmeiras-sp", Season: 2023, Limit: 5})
	if page.Total == 0 {
		t.Fatal("Palmeiras played no matches in 2023")
	}
	if len(page.Matches) != 5 {
		t.Errorf("limit ignored: %d matches", len(page.Matches))
	}
	for _, m := range page.Matches {
		if !m.Involves("palmeiras-sp") || m.Season != 2023 {
			t.Errorf("filter leaked: %s %d", m.Label(), m.Season)
		}
	}
	// Default ordering is most recent first.
	for i := 1; i < len(page.Matches); i++ {
		if page.Matches[i-1].Date.Before(page.Matches[i].Date) {
			t.Error("matches are not sorted newest first")
		}
	}
}

func TestFindMatchesVenueAndResult(t *testing.T) {
	s := testStore(t)
	home := s.FindMatches(MatchFilter{TeamID: "gremio-rs", CompetitionID: CompBrasileirao, Season: 2019, Venue: VenueHome})
	if home.Total != 19 {
		t.Errorf("Grêmio played %d home league matches in 2019, want 19", home.Total)
	}
	for _, m := range home.Matches {
		if m.HomeTeamID != "gremio-rs" {
			t.Errorf("away match in a home-only search: %s", m.Label())
		}
	}
	wins := s.FindMatches(MatchFilter{TeamID: "gremio-rs", CompetitionID: CompBrasileirao, Season: 2019, Venue: VenueAway, Result: "win"})
	for _, m := range wins.Matches {
		if m.AwayTeamID != "gremio-rs" || m.ResultFor("gremio-rs") != "W" {
			t.Errorf("result filter leaked: %s", m.Label())
		}
	}
}

func TestFindMatchesByDateRange(t *testing.T) {
	s := testStore(t)
	from := time.Date(2019, 5, 1, 0, 0, 0, 0, time.UTC)
	to := time.Date(2019, 5, 31, 0, 0, 0, 0, time.UTC)
	page := s.FindMatches(MatchFilter{CompetitionID: CompBrasileirao, From: from, To: to})
	if page.Total == 0 {
		t.Fatal("no May 2019 fixtures")
	}
	for _, m := range page.Matches {
		if m.Date.Before(from) || m.Date.After(to) {
			t.Errorf("%s is outside the range", m.DateString())
		}
	}
}

func TestFindMatchesPaging(t *testing.T) {
	s := testStore(t)
	first := s.FindMatches(MatchFilter{TeamID: "flamengo-rj", Limit: 10})
	second := s.FindMatches(MatchFilter{TeamID: "flamengo-rj", Limit: 10, Offset: 10})
	if first.Total != second.Total {
		t.Error("paging changed the total")
	}
	if len(second.Matches) != 10 {
		t.Fatalf("second page has %d matches", len(second.Matches))
	}
	for _, a := range first.Matches {
		for _, b := range second.Matches {
			if a.ID == b.ID {
				t.Errorf("match %s appears on both pages", a.ID)
			}
		}
	}
	beyond := s.FindMatches(MatchFilter{TeamID: "flamengo-rj", Offset: 100000})
	if len(beyond.Matches) != 0 {
		t.Error("offset past the end should return nothing")
	}
}

func TestFindMatchesSorting(t *testing.T) {
	s := testStore(t)
	byGoals := s.FindMatches(MatchFilter{CompetitionID: CompBrasileirao, Sort: "goals_desc", Limit: 10})
	for i := 1; i < len(byGoals.Matches); i++ {
		if byGoals.Matches[i-1].TotalGoals() < byGoals.Matches[i].TotalGoals() {
			t.Error("goals_desc is not sorted")
		}
	}
	byDate := s.FindMatches(MatchFilter{CompetitionID: CompBrasileirao, Sort: "date_asc", Limit: 3})
	if byDate.Matches[0].Date.Year() != 2003 {
		t.Errorf("oldest Brasileirão match is from %d", byDate.Matches[0].Date.Year())
	}
}

func TestFindMatchesOpponentOnly(t *testing.T) {
	s := testStore(t)
	page := s.FindMatches(MatchFilter{OpponentID: "santos-sp", Season: 2019, CompetitionID: CompBrasileirao})
	if page.Total == 0 {
		t.Fatal("no Santos matches")
	}
	for _, m := range page.Matches {
		if !m.Involves("santos-sp") {
			t.Errorf("%s does not involve Santos", m.Label())
		}
	}
}

func TestFindPlayers(t *testing.T) {
	s := testStore(t)
	brazilians := s.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 10})
	if brazilians.Total < 800 {
		t.Errorf("only %d Brazilian players", brazilians.Total)
	}
	for _, p := range brazilians.Players {
		if p.Nationality != "Brazil" {
			t.Errorf("%s is %s", p.Name, p.Nationality)
		}
	}
	if brazilians.Players[0].Name != "Neymar Jr" {
		t.Errorf("best rated Brazilian = %s, want Neymar Jr", brazilians.Players[0].Name)
	}
	for i := 1; i < len(brazilians.Players); i++ {
		if brazilians.Players[i-1].Overall < brazilians.Players[i].Overall {
			t.Error("players are not sorted by rating")
		}
	}
}

func TestFindPlayersByPositionGroup(t *testing.T) {
	s := testStore(t)
	page := s.FindPlayers(PlayerFilter{TeamID: "cruzeiro-mg", Position: "forward", Limit: 20})
	if page.Total == 0 {
		t.Fatal("Cruzeiro has no forwards in the player file")
	}
	for _, p := range page.Players {
		if p.PositionGroup() != "forward" {
			t.Errorf("%s plays %s, which is not a forward", p.Name, p.Position)
		}
	}
	keepers := s.FindPlayers(PlayerFilter{Position: "GK", Limit: 5})
	for _, p := range keepers.Players {
		if !p.IsGoalkeeper() {
			t.Errorf("%s is not a goalkeeper", p.Name)
		}
	}
}

func TestFindPlayersByName(t *testing.T) {
	s := testStore(t)
	for _, query := range []string{"Neymar", "neymar jr", "NEYMAR"} {
		page := s.FindPlayers(PlayerFilter{Name: query, Limit: 3})
		if page.Total == 0 {
			t.Errorf("searching %q found nobody", query)
			continue
		}
		if !strings.Contains(page.Players[0].Name, "Neymar") {
			t.Errorf("searching %q found %s", query, page.Players[0].Name)
		}
	}
	if got := s.FindPlayers(PlayerFilter{Name: "Zzzznotaplayer"}); got.Total != 0 {
		t.Errorf("nonsense name matched %d players", got.Total)
	}
}

func TestFindPlayersRatingAndAge(t *testing.T) {
	s := testStore(t)
	page := s.FindPlayers(PlayerFilter{MinOverall: 88, Limit: 50})
	for _, p := range page.Players {
		if p.Overall < 88 {
			t.Errorf("%s is rated %d", p.Name, p.Overall)
		}
	}
	young := s.FindPlayers(PlayerFilter{MaxAge: 20, MinOverall: 80, Limit: 10})
	for _, p := range young.Players {
		if p.Age > 20 || p.Overall < 80 {
			t.Errorf("%s is %d years old and rated %d", p.Name, p.Age, p.Overall)
		}
	}
}

func TestSuggestPlayers(t *testing.T) {
	s := testStore(t)
	got := s.SuggestPlayers("Neymer", 5)
	if len(got) == 0 {
		t.Fatal("no suggestions for a misspelt player")
	}
	found := false
	for _, name := range got {
		if strings.Contains(name, "Neymar") {
			found = true
		}
	}
	if !found {
		t.Errorf("suggestions for \"Neymer\" = %v", got)
	}
}

func TestClubSummaries(t *testing.T) {
	s := testStore(t)
	brazilian := s.ClubSummaries(ClubFilter{Country: "BRA", MinPlayers: 1})
	if len(brazilian) < 10 {
		t.Errorf("only %d Brazilian clubs have squads", len(brazilian))
	}
	for _, c := range brazilian {
		if c.TeamID == "" {
			t.Errorf("%s is not linked to the match data", c.Club)
		}
		team := s.Teams.Team(c.TeamID)
		if team == nil || team.Country != "BRA" {
			t.Errorf("%s is linked to a non-Brazilian club", c.Club)
		}
		if c.Players == 0 || c.AvgOverall == 0 {
			t.Errorf("%s has an empty summary", c.Club)
		}
	}
	for i := 1; i < len(brazilian); i++ {
		if brazilian[i-1].AvgOverall < brazilian[i].AvgOverall {
			t.Error("club summaries are not sorted by average rating")
		}
	}
	all := s.ClubSummaries(ClubFilter{MinPlayers: 25})
	for _, c := range all {
		if c.Players < 25 {
			t.Errorf("%s has %d players, below the minimum", c.Club, c.Players)
		}
	}
}

func TestMatchAccessors(t *testing.T) {
	m := &Match{
		HomeTeamID: "a", AwayTeamID: "b", HomeName: "A", AwayName: "B",
		HomeGoals: 3, AwayGoals: 1, Season: 2019, CompetitionID: CompBrasileirao,
		Date: time.Date(2019, 9, 3, 0, 0, 0, 0, time.UTC), Round: 22,
	}
	if m.Outcome() != HomeWin || m.TotalGoals() != 4 || m.GoalMargin() != 2 {
		t.Errorf("outcome=%s total=%d margin=%d", m.Outcome(), m.TotalGoals(), m.GoalMargin())
	}
	if m.GoalsFor("b") != 1 || m.GoalsAgainst("b") != 3 {
		t.Error("goals from the away point of view are wrong")
	}
	if m.ResultFor("a") != "W" || m.ResultFor("b") != "L" {
		t.Error("results are wrong")
	}
	if m.Opponent("a") != "b" || m.Opponent("c") != "" {
		t.Error("opponent lookup is wrong")
	}
	if m.Label() != "A 3-1 B" || m.DateString() != "2019-09-03" || m.RoundLabel() != "Round 22" {
		t.Errorf("labels: %q %q %q", m.Label(), m.DateString(), m.RoundLabel())
	}
	draw := &Match{HomeGoals: 2, AwayGoals: 2, HomeTeamID: "a", AwayTeamID: "b"}
	if draw.Outcome() != Draw || draw.ResultFor("a") != "D" {
		t.Error("draw handling is wrong")
	}
}

func TestOptIntJSON(t *testing.T) {
	present := NewOptInt(7)
	if b, _ := present.MarshalJSON(); string(b) != "7" {
		t.Errorf("present OptInt marshalled as %s", b)
	}
	var absent OptInt
	if b, _ := absent.MarshalJSON(); string(b) != "null" {
		t.Errorf("absent OptInt marshalled as %s", b)
	}
	if absent.String() != "-" || present.String() != "7" {
		t.Errorf("OptInt strings: %q %q", absent.String(), present.String())
	}
	if err := absent.UnmarshalJSON([]byte("12")); err != nil || !absent.Valid || absent.Value != 12 {
		t.Errorf("UnmarshalJSON: %v %+v", err, absent)
	}
}

func TestFormattersProduceTheSpecShapes(t *testing.T) {
	s := testStore(t)

	h := s.HeadToHead("flamengo-rj", "fluminense-rj", MatchFilter{Limit: 3})
	text := FormatHeadToHead(h, 3)
	for _, want := range []string{"Flamengo vs Fluminense", "Fla-Flu derby", "Head-to-head in dataset"} {
		if !strings.Contains(text, want) {
			t.Errorf("head-to-head text is missing %q:\n%s", want, text)
		}
	}

	rec := s.TeamRecord("corinthians-sp", MatchFilter{CompetitionID: CompBrasileirao, Season: 2022, Venue: VenueHome})
	text = FormatRecord("Corinthians home record (2022 Brasileirão)", rec)
	for _, want := range []string{"Matches:", "Wins:", "Goals For:", "Win rate:"} {
		if !strings.Contains(text, want) {
			t.Errorf("record text is missing %q:\n%s", want, text)
		}
	}

	text = FormatStandings(s.Standings(CompBrasileirao, 2019, StandingsOptions{}), 5)
	for _, want := range []string{"2019 Brasileirão standings", "Flamengo", "pts", "Champion"} {
		if !strings.Contains(text, want) {
			t.Errorf("standings text is missing %q:\n%s", want, text)
		}
	}

	players := s.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 3})
	text = FormatPlayers("Top-rated Brazilian players in dataset:", players.Players, players.Total, 0)
	for _, want := range []string{"1. Neymar Jr", "Overall:", "Position:", "Club:"} {
		if !strings.Contains(text, want) {
			t.Errorf("player text is missing %q:\n%s", want, text)
		}
	}

	text = MatchLine(s.SeasonMatches(CompBrasileirao, 2019)[0])
	if !strings.HasPrefix(text, "- 2019-") || !strings.Contains(text, "Brasileirão") {
		t.Errorf("match line = %q", text)
	}
}

// The "N more" line must count what is still to come, not everything that is
// not on the page, and a page past the end must not read as "nothing found".
func TestPagingNoticesAreHonest(t *testing.T) {
	s := testStore(t)
	page := s.FindMatches(MatchFilter{TeamID: "flamengo-rj", Season: 2019, Limit: 3, Offset: 0})
	total := page.Total
	if total < 10 {
		t.Fatalf("Flamengo played only %d matches in 2019", total)
	}

	last := s.FindMatches(MatchFilter{TeamID: "flamengo-rj", Season: 2019, Limit: 3, Offset: total - 2})
	text := FormatMatches("", last.Matches, last.Total, total-2)
	if strings.Contains(text, "more matches match these filters") {
		t.Errorf("the last page claims there is more to come:\n%s", text)
	}

	middle := s.FindMatches(MatchFilter{TeamID: "flamengo-rj", Season: 2019, Limit: 3, Offset: 3})
	text = FormatMatches("", middle.Matches, middle.Total, 3)
	want := fmt.Sprintf("(%d more matches", total-6)
	if !strings.Contains(text, want) {
		t.Errorf("a middle page should promise %q:\n%s", want, text)
	}

	beyond := s.FindMatches(MatchFilter{TeamID: "flamengo-rj", Season: 2019, Limit: 3, Offset: total + 10})
	text = FormatMatches("", beyond.Matches, beyond.Total, total+10)
	if strings.Contains(text, "No matches found") {
		t.Errorf("paging past the end must not read as an empty result set:\n%s", text)
	}
	if !strings.Contains(text, "past the end") {
		t.Errorf("paging past the end should explain itself:\n%s", text)
	}

	players := s.FindPlayers(PlayerFilter{Nationality: "Brazil", Limit: 5, Offset: 2})
	text = FormatPlayers("", players.Players, players.Total, 2)
	want = fmt.Sprintf("(%d more players", players.Total-7)
	if !strings.Contains(text, want) {
		t.Errorf("player paging should promise %q:\n%s", want, text)
	}
}

// A goalless draw is two clean sheets, not one.
func TestCleanSheetsCountBothDefences(t *testing.T) {
	s := testStore(t)
	f := MatchFilter{CompetitionID: CompBrasileirao, Season: 2019}
	a := s.Aggregate(f)
	want := 0
	for _, m := range s.SeasonMatches(CompBrasileirao, 2019) {
		if m.HomeGoals == 0 {
			want++
		}
		if m.AwayGoals == 0 {
			want++
		}
	}
	if a.CleanSheets != want {
		t.Errorf("clean sheets = %d, want %d (a 0-0 counts twice)", a.CleanSheets, want)
	}
}

func TestResultFilterAcceptsVariants(t *testing.T) {
	s := testStore(t)
	base := MatchFilter{TeamID: "flamengo-rj", CompetitionID: CompBrasileirao, Season: 2019}
	wins := s.FindMatches(MatchFilter{TeamID: base.TeamID, CompetitionID: base.CompetitionID, Season: base.Season, Result: "win"}).Total
	for _, spelling := range []string{"w", "won", "WIN", "victory"} {
		f := base
		f.Result = spelling
		if got := s.FindMatches(f).Total; got != wins {
			t.Errorf("result=%q found %d matches, want %d", spelling, got, wins)
		}
	}
	// Something that is not a result at all matches nothing rather than
	// silently behaving like a different filter.
	f := base
	f.Result = "nonsense"
	if got := s.FindMatches(f).Total; got != 0 {
		t.Errorf("result=nonsense matched %d matches", got)
	}
}
