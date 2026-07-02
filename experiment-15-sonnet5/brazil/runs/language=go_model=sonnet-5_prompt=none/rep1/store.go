package main

import (
	"fmt"
	"sort"
	"time"
)

// ExtendedStats holds the extra per-match statistics only available in the
// BR-Football-Dataset.csv source.
type ExtendedStats struct {
	HomeCorners float64 `json:"home_corners"`
	AwayCorners float64 `json:"away_corners"`
	HomeAttacks float64 `json:"home_attacks"`
	AwayAttacks float64 `json:"away_attacks"`
	HomeShots   float64 `json:"home_shots"`
	AwayShots   float64 `json:"away_shots"`
}

// Match is a single normalized match record, regardless of which source CSV
// it originated from.
type Match struct {
	Competition string         `json:"competition"`
	Season      int            `json:"season"`
	Round       string         `json:"round,omitempty"`
	Stage       string         `json:"stage,omitempty"`
	Date        time.Time      `json:"-"`
	DateStr     string         `json:"date"`
	HomeTeam    string         `json:"home_team"`
	AwayTeam    string         `json:"away_team"`
	HomeState   string         `json:"home_state,omitempty"`
	AwayState   string         `json:"away_state,omitempty"`
	HomeGoals   int            `json:"home_goals"`
	AwayGoals   int            `json:"away_goals"`
	HasGoals    bool           `json:"-"`
	Arena       string         `json:"arena,omitempty"`
	Source      string         `json:"source"`
	Extended    *ExtendedStats `json:"extended_stats,omitempty"`

	homeKey teamName
	awayKey teamName
}

// Result returns "home", "away" or "draw" describing the match outcome.
func (m Match) Result() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return "home"
	case m.AwayGoals > m.HomeGoals:
		return "away"
	default:
		return "draw"
	}
}

// Player is a single normalized FIFA player record.
type Player struct {
	ID           int    `json:"id"`
	Name         string `json:"name"`
	Age          int    `json:"age,omitempty"`
	Nationality  string `json:"nationality,omitempty"`
	Overall      int    `json:"overall"`
	Potential    int    `json:"potential,omitempty"`
	Club         string `json:"club,omitempty"`
	Position     string `json:"position,omitempty"`
	JerseyNumber string `json:"jersey_number,omitempty"`
	Height       string `json:"height,omitempty"`
	Weight       string `json:"weight,omitempty"`
	Value        string `json:"value,omitempty"`
	Wage         string `json:"wage,omitempty"`

	nameKey        string
	nationalityKey string
	clubKey        teamName
	positionKey    string
}

// Store is the in-memory knowledge base built from all six source CSVs.
type Store struct {
	Matches []Match
	Players []Player

	// teamDisplay maps a "full" team key (base|STATE, or just base when no
	// state is known) to the most common raw display name seen for it.
	teamDisplay map[string]string
	// teamsByBase maps a base key (e.g. "america") to the set of full keys
	// sharing that base (e.g. "america|MG", "america|RN").
	teamsByBase map[string][]string

	LoadWarnings []string
}

func newStore() *Store {
	return &Store{
		teamDisplay: map[string]string{},
		teamsByBase: map[string][]string{},
	}
}

func (s *Store) noteTeam(tn teamName, display string) {
	if _, ok := s.teamDisplay[tn.Full]; !ok {
		s.teamDisplay[tn.Full] = display
		found := false
		for _, k := range s.teamsByBase[tn.Base] {
			if k == tn.Full {
				found = true
				break
			}
		}
		if !found {
			s.teamsByBase[tn.Base] = append(s.teamsByBase[tn.Base], tn.Full)
		}
	}
}

func (s *Store) addMatch(m Match) {
	m.homeKey = parseTeamName(m.HomeTeam)
	m.awayKey = parseTeamName(m.AwayTeam)
	s.noteTeam(m.homeKey, m.HomeTeam)
	s.noteTeam(m.awayKey, m.AwayTeam)
	s.Matches = append(s.Matches, m)
}

func (s *Store) addPlayer(p Player) {
	p.nameKey = normalizeKey(p.Name)
	p.nationalityKey = normalizeKey(p.Nationality)
	p.positionKey = normalizeKey(p.Position)
	p.clubKey = parseTeamName(p.Club)
	s.Players = append(s.Players, p)
}

// resolveTeam finds every full team key that plausibly corresponds to the
// given free-form team name. If the input includes a recognizable state
// suffix (e.g. "America-MG") only that exact variant is returned. Otherwise
// every state variant sharing the same base name is returned, since the
// datasets are known to contain genuinely distinct clubs with the same short
// name in different states (see Data Quality Notes in TASK.md).
func (s *Store) resolveTeam(input string) []string {
	tn := parseTeamName(input)
	if tn.State != "" {
		if _, ok := s.teamDisplay[tn.Full]; ok {
			return []string{tn.Full}
		}
	}
	if keys, ok := s.teamsByBase[tn.Base]; ok && len(keys) > 0 {
		sorted := append([]string(nil), keys...)
		sort.Strings(sorted)
		return sorted
	}
	// Fall back to substring matching against known base keys, for partial
	// or loosely-spelled input (e.g. "Sao Paulo" matching "sao paulo fc").
	var matches []string
	for base, keys := range s.teamsByBase {
		if containsWord(base, tn.Base) || containsWord(tn.Base, base) {
			matches = append(matches, keys...)
		}
	}
	sort.Strings(matches)
	return matches
}

func containsWord(haystack, needle string) bool {
	if needle == "" || haystack == "" {
		return false
	}
	return len(needle) >= 3 && (haystack == needle || indexOf(haystack, needle) >= 0)
}

func indexOf(haystack, needle string) int {
	for i := 0; i+len(needle) <= len(haystack); i++ {
		if haystack[i:i+len(needle)] == needle {
			return i
		}
	}
	return -1
}

// displayName returns the canonical display name recorded for a full team
// key, falling back to the key itself.
func (s *Store) displayName(fullKey string) string {
	if d, ok := s.teamDisplay[fullKey]; ok {
		return d
	}
	return fullKey
}

func (s *Store) summary() string {
	return fmt.Sprintf("matches=%d players=%d distinct_teams=%d warnings=%d",
		len(s.Matches), len(s.Players), len(s.teamDisplay), len(s.LoadWarnings))
}
