// Package main implements a Model Context Protocol (MCP) server that exposes a
// queryable knowledge base of Brazilian soccer data (matches, teams, players
// and competitions) loaded from the bundled Kaggle CSV datasets.
//
// File: model.go
// Responsibility: Core domain types shared across the loader, query engine and
// MCP tool handlers. A `Match` is the canonical, normalized representation of a
// single game from any of the five match datasets; a `Player` is a single row
// from the FIFA player database. Keeping these in one place lets the loader,
// store and tools agree on a single schema regardless of the (very different)
// shapes of the source CSV files.
package main

import "time"

// Match is a single normalized game from any of the match datasets.
//
// Team names are stored twice: HomeTeam/AwayTeam keep a cleaned display name
// (state suffixes and parentheticals removed) while HomeKey/AwayKey hold the
// accent-folded, lower-cased canonical key used for matching across datasets
// that spell the same club differently (e.g. "Palmeiras-SP" vs "Palmeiras").
type Match struct {
	Date        time.Time
	HasDate     bool
	HomeTeam    string // display name
	AwayTeam    string // display name
	HomeKey     string // full canonical key incl. state suffix (e.g. "atletico-mg")
	AwayKey     string // full canonical key incl. state suffix
	HomeBase    string // suffix-stripped key (e.g. "atletico") for loose matching
	AwayBase    string // suffix-stripped key for loose matching
	HomeState   string
	AwayState   string
	HomeGoal    int
	AwayGoal    int
	HasScore    bool
	Season      int
	Round       string
	Competition string // e.g. "Brasileirão Série A", "Copa do Brasil"
	Stage       string // e.g. "group stage", "final" (Libertadores)
	Stadium     string
	Source      string // originating CSV file

	// Optional extended statistics (only present for BR-Football-Dataset rows).
	HomeShots   int
	AwayShots   int
	HomeCorners int
	AwayCorners int
	HasStats    bool
}

// Winner returns "home", "away" or "draw" for a match with a recorded score.
func (m Match) Winner() string {
	switch {
	case !m.HasScore:
		return "unknown"
	case m.HomeGoal > m.AwayGoal:
		return "home"
	case m.AwayGoal > m.HomeGoal:
		return "away"
	default:
		return "draw"
	}
}

// signature returns a stable key used to de-duplicate the same real-world match
// that appears in more than one dataset (the Brasileirão appears in three of
// them). Two rows collide when the date, both canonical team names and the
// scoreline agree.
func (m Match) signature() string {
	d := "?"
	if m.HasDate {
		d = m.Date.Format("2006-01-02")
	}
	// Use suffix-stripped base keys so the same game spelled "Flamengo-RJ" in
	// one dataset and "Flamengo" in another collapses to a single match.
	return d + "|" + m.HomeBase + "|" + m.AwayBase + "|" +
		itoa(m.HomeGoal) + "-" + itoa(m.AwayGoal)
}

// Player is a single row from the FIFA player database.
type Player struct {
	ID          int
	Name        string
	NameKey     string // accent-folded, lower-cased name for searching
	Age         int
	Nationality string
	Overall     int
	Potential   int
	Club        string
	ClubKey     string // canonical club key
	Position    string
	Jersey      string
	Height      string
	Weight      string
	PreferredFt string
}
