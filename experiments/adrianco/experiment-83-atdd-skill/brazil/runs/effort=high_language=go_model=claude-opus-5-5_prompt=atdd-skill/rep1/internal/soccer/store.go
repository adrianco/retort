package soccer

import (
	"sort"
	"strings"
	"time"
)

// Match is one played match, possibly recorded by several datasets.
type Match struct {
	Date        time.Time
	Competition Competition
	Season      int
	Round       int
	Stage       string
	HomeKey     string
	AwayKey     string
	HomeGoals   int
	AwayGoals   int
	Arena       string
	Stats       *MatchStats
	Sources     []string
}

// MatchStats are the extended statistics some datasets record.
type MatchStats struct {
	HomeCorners, AwayCorners *int
	HomeShots, AwayShots     *int
	HomeAttacks, AwayAttacks *int
}

// Involves reports whether the team played in the match.
func (m *Match) Involves(key string) bool { return m.HomeKey == key || m.AwayKey == key }

// GoalsFor returns the goals scored and conceded by the team.
func (m *Match) GoalsFor(key string) (scored, conceded int) {
	if m.HomeKey == key {
		return m.HomeGoals, m.AwayGoals
	}
	return m.AwayGoals, m.HomeGoals
}

func (m *Match) Opponent(key string) string {
	if m.HomeKey == key {
		return m.AwayKey
	}
	return m.HomeKey
}

func (m *Match) Margin() int {
	if m.HomeGoals > m.AwayGoals {
		return m.HomeGoals - m.AwayGoals
	}
	return m.AwayGoals - m.HomeGoals
}

// Player is one player in the FIFA player database.
type Player struct {
	ID            int
	Name          string
	Age           int
	Nationality   string
	Overall       int
	Potential     int
	Club          string
	ClubKey       string
	Position      string
	Jersey        int
	Height        string
	Weight        string
	Value         string
	Wage          string
	PreferredFoot string
	Joined        string
	ContractUntil string
	Skills        []Skill
}

// Skill is one named attribute rating.
type Skill struct {
	Name   string `json:"name"`
	Rating int    `json:"rating"`
}

// Team is everything known about a team's identity.
type Team struct {
	Key      string
	Display  string
	Known    bool
	Variants map[string]int
}

// Dataset describes one loaded data file.
type Dataset struct {
	Name       string `json:"name"`
	File       string `json:"file"`
	Records    int    `json:"records"`
	NewMatches int    `json:"new_matches,omitempty"`
	Merged     int    `json:"merged_with_other_sources,omitempty"`
	Skipped    int    `json:"skipped_rows,omitempty"`
	Seasons    string `json:"seasons,omitempty"`
	Error      string `json:"error,omitempty"`
}

// Store holds all the soccer knowledge, loaded once at start-up.
type Store struct {
	Matches  []*Match
	Players  []*Player
	Teams    map[string]*Team
	Datasets []Dataset

	byPairing map[string][]*Match
	domestic  map[string]bool
}

func newStore() *Store {
	return &Store{Teams: map[string]*Team{}, byPairing: map[string][]*Match{}, domestic: map[string]bool{}}
}

// team registers a spelling of a team name and returns its key.
func (s *Store) team(raw string) string {
	n := NormalizeTeam(raw)
	t, ok := s.Teams[n.Key]
	if !ok {
		t = &Team{Key: n.Key, Display: n.Display, Known: n.Known, Variants: map[string]int{}}
		s.Teams[n.Key] = t
	}
	t.Variants[strings.TrimSpace(raw)]++
	return n.Key
}

// Display is the name to show for a team key.
func (s *Store) Display(key string) string {
	if t, ok := s.Teams[key]; ok {
		return t.Display
	}
	return key
}

const sameMatchWindow = 3 * 24 * time.Hour

// addMatch records a match unless another dataset already recorded it,
// in which case the two records are merged. Datasets disagree by a day
// or so on dates near midnight, so matches between the same teams in
// the same competition within a few days are the same match.
func (s *Store) addMatch(m *Match, source string) (merged bool) {
	key := string(m.Competition) + "|" + m.HomeKey + "|" + m.AwayKey
	for _, existing := range s.byPairing[key] {
		diff := existing.Date.Sub(m.Date)
		if diff < 0 {
			diff = -diff
		}
		if diff <= sameMatchWindow {
			existing.merge(m, source)
			return true
		}
	}
	m.Sources = []string{source}
	s.byPairing[key] = append(s.byPairing[key], m)
	s.Matches = append(s.Matches, m)
	if m.Competition.IsDomestic() {
		s.domestic[m.HomeKey] = true
		s.domestic[m.AwayKey] = true
	}
	return false
}

func (m *Match) merge(other *Match, source string) {
	m.Sources = append(m.Sources, source)
	if m.Stats == nil {
		m.Stats = other.Stats
	}
	if m.Round == 0 {
		m.Round = other.Round
	}
	if m.Stage == "" {
		m.Stage = other.Stage
	}
	if m.Arena == "" {
		m.Arena = other.Arena
	}
}

// IsBrazilianClub reports whether the team plays in Brazilian domestic competitions.
func (s *Store) IsBrazilianClub(key string) bool { return s.domestic[key] }

func (s *Store) finish() {
	sort.SliceStable(s.Matches, func(i, j int) bool { return s.Matches[i].Date.Before(s.Matches[j].Date) })
	s.inferCupStages()
	for _, t := range s.Teams {
		if !t.Known {
			t.Display = bestDisplay(t)
		}
	}
	sort.SliceStable(s.Players, func(i, j int) bool { return playerBefore(s.Players[i], s.Players[j]) })
}

// bestDisplay picks the most common spelling, preferring accented ones.
func bestDisplay(t *Team) string {
	best, bestScore := t.Display, -1
	for raw, count := range t.Variants {
		d := NormalizeTeam(raw).Display
		score := count
		if d != accentFolder.Replace(d) {
			score += 1_000_000
		}
		if score > bestScore || (score == bestScore && d < best) {
			best, bestScore = d, score
		}
	}
	return best
}

// inferCupStages names the knockout stages of the Copa do Brasil, whose
// dataset numbers its rounds rather than naming them. When the last
// round of a season is a single tie, it is the final, and the rounds
// before it are the semi-finals, quarter-finals and round of 16.
func (s *Store) inferCupStages() {
	bySeason := map[int][]*Match{}
	for _, m := range s.Matches {
		if m.Competition == CopaDoBrasil {
			bySeason[m.Season] = append(bySeason[m.Season], m)
		}
	}
	names := []string{"final", "semifinals", "quarterfinals", "round of 16"}
	for _, matches := range bySeason {
		maxRound := 0
		for _, m := range matches {
			maxRound = max(maxRound, m.Round)
		}
		if maxRound == 0 {
			// No round numbers: the last tie of the season is the final.
			last := matches[len(matches)-1]
			for _, m := range matches {
				if samePairing(m, last) && last.Date.Sub(m.Date) < 21*24*time.Hour {
					m.Stage = "final"
				}
			}
			continue
		}
		pairings := map[string]bool{}
		for _, m := range matches {
			if m.Round == maxRound {
				pairings[pairingKey(m)] = true
			}
		}
		if len(pairings) != 1 {
			continue
		}
		for _, m := range matches {
			if step := maxRound - m.Round; m.Round > 0 && step < len(names) && m.Stage == "" {
				m.Stage = names[step]
			}
		}
	}
}

func pairingKey(m *Match) string {
	if m.HomeKey < m.AwayKey {
		return m.HomeKey + "|" + m.AwayKey
	}
	return m.AwayKey + "|" + m.HomeKey
}

func samePairing(a, b *Match) bool { return pairingKey(a) == pairingKey(b) }
