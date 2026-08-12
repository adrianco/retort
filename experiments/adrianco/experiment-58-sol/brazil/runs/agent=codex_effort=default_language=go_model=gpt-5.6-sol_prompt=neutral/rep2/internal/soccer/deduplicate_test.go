package soccer

import (
	"testing"
	"time"
)

func completedMatch(source, date, home, away string, homeGoals, awayGoals int) Match {
	t, err := parseDate(date)
	if err != nil {
		panic(err)
	}
	return Match{
		Date:        date,
		date:        t,
		HomeTeam:    home,
		AwayTeam:    away,
		homeKey:     NormalizeTeam(home),
		awayKey:     NormalizeTeam(away),
		HomeGoals:   homeGoals,
		AwayGoals:   awayGoals,
		Completed:   true,
		Competition: "Brasileirão Série A",
		Season:      t.Year(),
		Source:      source,
	}
}

func TestAnalyticalMatchesDeduplicateOverlappingSourcesWithinOneDay(t *testing.T) {
	primary := completedMatch(sourceBrasileirao, "2019-05-01", "Flamengo-RJ", "Corinthians-SP", 2, 0)
	shiftedDuplicate := completedMatch(sourceExtended, "2019-05-02", "Flamengo", "Sport Club Corinthians Paulista", 1, 0)
	returnFixture := completedMatch(sourceExtended, "2019-09-01", "Flamengo", "Corinthians", 1, 1)
	c := &Catalog{Matches: []Match{shiftedDuplicate, returnFixture, primary}}

	got := c.analyticalMatches("Brasileirão", 2019)
	if len(got) != 2 {
		t.Fatalf("analyticalMatches returned %d fixtures, want 2: %+v", len(got), got)
	}
	if got[0].Source != sourceBrasileirao || got[0].HomeGoals != 2 {
		t.Fatalf("deduplication did not retain the authoritative source row: %+v", got[0])
	}
}

func TestAnalyticalMatchesDoNotMergeFixturesMoreThanOneDayApart(t *testing.T) {
	first := completedMatch(sourceBrasileirao, "2019-05-01", "Flamengo", "Corinthians", 2, 0)
	second := completedMatch(sourceExtended, "2019-05-03", "Flamengo", "Corinthians", 1, 0)
	c := &Catalog{Matches: []Match{first, second}}

	if got := c.analyticalMatches("Brasileirão", 2019); len(got) != 2 {
		t.Fatalf("analyticalMatches merged distinct fixtures: %+v", got)
	}
}

func TestAnalyticalMatchesIgnoreUnplayedRows(t *testing.T) {
	played := completedMatch(sourceBrasileirao, "2023-05-01", "Palmeiras", "Santos", 2, 1)
	unplayed := played
	unplayed.date = unplayed.date.Add(7 * 24 * time.Hour)
	unplayed.Date = unplayed.date.Format("2006-01-02")
	unplayed.Completed = false
	c := &Catalog{Matches: []Match{played, unplayed}}

	if got := c.analyticalMatches("Brasileirão", 2023); len(got) != 1 {
		t.Fatalf("analyticalMatches included an unplayed row: %+v", got)
	}
}
