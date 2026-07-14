// Context: Core domain types for the Brazilian Soccer MCP server — the in-memory
// representation of a Match and a Player after a CSV row has been parsed and its
// team/club names normalized. These structs are deliberately source-agnostic:
// every match from every CSV file collapses into the same Match shape (carrying
// a canonical Competition label and a Source tag), which lets the query layer
// treat all six datasets uniformly.
package main

import "time"

// Match is a single game from any of the bundled competition datasets.
type Match struct {
	Date        time.Time
	HasDate     bool
	Season      int
	Round       string
	Competition string // canonical: Brasileirão / Copa do Brasil / Copa Libertadores / Serie B / Serie C
	Stage       string // e.g. "group stage" (Libertadores)
	Source      string // originating file name

	HomeTeam     string // display form (suffix stripped, accents kept)
	AwayTeam     string
	HomeTeamNorm string // base comparison key (no state)
	AwayTeamNorm string
	HomeState    string // state/country code, e.g. "rj" ("" if none)
	AwayState    string

	HomeGoals int
	AwayGoals int
	HasScore  bool
}

// homeIdentity / awayIdentity are the full grouping keys that keep clubs sharing
// a base name (Atlético-MG vs Atlético-PR) distinct.
func (m Match) homeIdentity() string { return m.HomeTeamNorm + "|" + m.HomeState }
func (m Match) awayIdentity() string { return m.AwayTeamNorm + "|" + m.AwayState }

// dateString renders the match date as YYYY-MM-DD, or a placeholder if unknown.
func (m Match) dateString() string {
	if !m.HasDate {
		return "????-??-??"
	}
	return m.Date.Format("2006-01-02")
}

// involves reports whether the given team query played in this match.
func (m Match) involves(q teamQuery) bool {
	return q.matchesSide(m.HomeTeamNorm, m.HomeState) || q.matchesSide(m.AwayTeamNorm, m.AwayState)
}

// dedupKey identifies the same real fixture across overlapping source files so
// it survives only once after canonicalization. It deliberately uses the base
// team names (no state) plus the match date, because one source may carry a
// state suffix ("Flamengo-RJ") where another does not ("Flamengo") for the very
// same game; the date keeps genuinely different fixtures apart.
func (m Match) dedupKey() string {
	date := "s" + itoa(m.Season)
	if m.HasDate {
		date = m.Date.Format("2006-01-02")
	}
	return m.Competition + "|" + date + "|" +
		m.HomeTeamNorm + "|" + m.AwayTeamNorm + "|" +
		itoa(m.HomeGoals) + "-" + itoa(m.AwayGoals)
}

// Player is a single entry from the FIFA player dataset.
type Player struct {
	ID          string
	Name        string
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	Position    string

	NameNorm        string
	ClubNorm        string
	NationalityNorm string
}
