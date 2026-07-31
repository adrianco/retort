// Package soccer implements the Brazilian soccer knowledge graph that backs the
// MCP server: it loads the Kaggle CSV datasets shipped in data/kaggle, reconciles
// the different team-naming conventions used by each file into a single set of
// team entities, and answers match / team / player / competition / statistics
// queries over the result.
//
// model.go defines the entity types stored in the graph (Competition, Team,
// Match, Player) plus the small helpers used throughout the query layer. Nothing
// in this file touches the filesystem; loading lives in loader.go and indexing in
// graph.go.
package soccer

import (
	"fmt"
	"strings"
	"time"
)

// Competition is the canonical name of a tournament. The raw datasets spell
// competitions in several ways ("Serie A", "Brasileirão", one file per cup);
// every match is mapped onto exactly one of these values.
type Competition string

// The competitions covered by the provided datasets.
const (
	SerieA       Competition = "Brasileirão Série A"
	SerieB       Competition = "Brasileirão Série B"
	SerieC       Competition = "Brasileirão Série C"
	CopaDoBrasil Competition = "Copa do Brasil"
	Libertadores Competition = "Copa Libertadores"
)

// AllCompetitions lists every competition in the knowledge graph, in the order
// used for display.
var AllCompetitions = []Competition{SerieA, SerieB, SerieC, CopaDoBrasil, Libertadores}

// IsLeague reports whether the competition is a round-robin league, i.e. one for
// which a standings table can be computed. Cups are knockout tournaments and are
// summarised by stage instead.
func (c Competition) IsLeague() bool {
	switch c {
	case SerieA, SerieB, SerieC:
		return true
	}
	return false
}

// Short returns a compact label ("Série A", "Copa do Brasil") for use in
// one-line match renderings.
func (c Competition) Short() string {
	switch c {
	case SerieA:
		return "Série A"
	case SerieB:
		return "Série B"
	case SerieC:
		return "Série C"
	default:
		return string(c)
	}
}

// competitionAliases maps normalised user input to a competition. Keys are
// produced by foldKey (lower case, accents removed, punctuation collapsed).
var competitionAliases = map[string]Competition{
	"serie a":                        SerieA,
	"seriea":                         SerieA,
	"a":                              SerieA,
	"brasileirao":                    SerieA,
	"brasileirao serie a":            SerieA,
	"campeonato brasileiro":          SerieA,
	"campeonato brasileiro serie a":  SerieA,
	"brazilian league":               SerieA,
	"brazilian championship":         SerieA,
	"serie b":                        SerieB,
	"serieb":                         SerieB,
	"b":                              SerieB,
	"brasileirao serie b":            SerieB,
	"segunda divisao":                SerieB,
	"serie c":                        SerieC,
	"seriec":                         SerieC,
	"c":                              SerieC,
	"brasileirao serie c":            SerieC,
	"copa do brasil":                 CopaDoBrasil,
	"copa brasil":                    CopaDoBrasil,
	"brazilian cup":                  CopaDoBrasil,
	"cup":                            CopaDoBrasil,
	"copa":                           CopaDoBrasil,
	"libertadores":                   Libertadores,
	"copa libertadores":              Libertadores,
	"conmebol libertadores":          Libertadores,
	"copa libertadores da america":   Libertadores,
	"copa libertadores de america":   Libertadores,
	"libertadores da america":        Libertadores,
	"taca libertadores":              Libertadores,
	"copa conmebol libertadores":     Libertadores,
	"south american champions cup":   Libertadores,
	"campeonato brasileiro serie b":  SerieB,
	"campeonato brasileiro serie c":  SerieC,
	"brasileiro":                     SerieA,
	"brazilian serie a":              SerieA,
	"brazilian serie b":              SerieB,
	"brazilian serie c":              SerieC,
	"brasileirao a":                  SerieA,
	"brasileirao b":                  SerieB,
	"brasileirao c":                  SerieC,
	"brazilian first division":       SerieA,
	"first division":                 SerieA,
	"brazilian second division":      SerieB,
	"brazilian national cup":         CopaDoBrasil,
	"copa do brasil de futebol":      CopaDoBrasil,
	"campeonato brasileiro de serie": SerieA,
}

// ParseCompetition resolves free-form user input ("brasileirao", "Série A",
// "libertadores") to a Competition. An empty input means "all competitions" and
// yields ok == false with no error.
func ParseCompetition(s string) (Competition, error) {
	key := foldKey(s)
	if key == "" {
		return "", nil
	}
	if c, ok := competitionAliases[key]; ok {
		return c, nil
	}
	for _, c := range AllCompetitions {
		if foldKey(string(c)) == key || foldKey(c.Short()) == key {
			return c, nil
		}
	}
	// Fall back to a prefix match so that "libert" or "copa do bra" still work.
	var hits []Competition
	for _, c := range AllCompetitions {
		if strings.Contains(foldKey(string(c)), key) {
			hits = append(hits, c)
		}
	}
	if len(hits) == 1 {
		return hits[0], nil
	}
	return "", fmt.Errorf("unknown competition %q (known: %s)", s, joinCompetitions(AllCompetitions))
}

func joinCompetitions(cs []Competition) string {
	parts := make([]string, len(cs))
	for i, c := range cs {
		parts[i] = string(c)
	}
	return strings.Join(parts, ", ")
}

// Team is a club as seen across every dataset. One Team aggregates all of the
// spellings found in the CSV files ("Palmeiras-SP", "Palmeiras", "Palmeiras - SP").
type Team struct {
	// ID is the stable canonical identifier, e.g. "flamengo-rj" or "santos-sp".
	ID string `json:"id"`
	// Name is the display name without a state suffix, e.g. "Atlético".
	Name string `json:"name"`
	// Display is the name shown to users; it carries the state suffix when the
	// bare name would be ambiguous (e.g. "Atlético-MG" vs "Atlético-PR").
	Display string `json:"display"`
	// State is the two-letter Brazilian state (UF) the club belongs to, if known.
	State string `json:"state,omitempty"`
	// Country is a three-letter code for non-Brazilian clubs (Libertadores
	// opponents), empty for Brazilian clubs.
	Country string `json:"country,omitempty"`
	// Aliases are the distinct raw spellings encountered in the datasets.
	Aliases []string `json:"aliases,omitempty"`
	// Nicknames are curated popular names ("Mengão", "Timão").
	Nicknames []string `json:"nicknames,omitempty"`

	base     string // canonical folded base shared with same-named clubs
	matchIdx []int  // indexes into Graph.matches, ordered by date
}

// StateName returns the full name of the club's state, e.g. "Minas Gerais".
func (t *Team) StateName() string { return stateNames[t.State] }

// CountryName returns the full country name for a foreign club.
func (t *Team) CountryName() string {
	if t.Country == "" {
		return "Brazil"
	}
	if n, ok := foreignCountries[t.Country]; ok {
		return n
	}
	return t.Country
}

// IsBrazilian reports whether the club is Brazilian (i.e. has no foreign country
// code attached).
func (t *Team) IsBrazilian() bool { return t.Country == "" }

// MatchStats holds the extended per-match statistics that only the
// BR-Football-Dataset provides. It is attached to a match when available,
// including when it has to be carried over from a duplicate row in another file.
type MatchStats struct {
	HomeCorners  int    `json:"home_corners"`
	AwayCorners  int    `json:"away_corners"`
	TotalCorners int    `json:"total_corners"`
	HomeAttacks  int    `json:"home_attacks"`
	AwayAttacks  int    `json:"away_attacks"`
	HomeShots    int    `json:"home_shots"`
	AwayShots    int    `json:"away_shots"`
	KickOff      string `json:"kick_off,omitempty"`
}

// Match is a single fixture. Matches are stored once per source file; the graph
// then elects one "primary" row per real-world fixture (see graph.go) so that
// overlapping datasets do not double count.
type Match struct {
	ID          string      `json:"id"`
	Source      string      `json:"source"`
	Competition Competition `json:"competition"`
	Season      int         `json:"season"`
	Round       int         `json:"round,omitempty"`
	Stage       string      `json:"stage,omitempty"`
	Date        time.Time   `json:"-"`
	HasDate     bool        `json:"-"`
	HomeID      string      `json:"home_id"`
	AwayID      string      `json:"away_id"`
	HomeRaw     string      `json:"-"`
	AwayRaw     string      `json:"-"`
	HomeGoals   int         `json:"home_goals"`
	AwayGoals   int         `json:"away_goals"`
	Venue       string      `json:"venue,omitempty"`
	Stats       *MatchStats `json:"stats,omitempty"`

	primary bool     // elected representative of its duplicate group
	dupes   []string // source keys of rows describing the same fixture
	home    *Team
	away    *Team
}

// DateString renders the match date as YYYY-MM-DD, or "unknown" when the source
// row had no usable date.
func (m *Match) DateString() string {
	if !m.HasDate {
		return "unknown"
	}
	return m.Date.Format("2006-01-02")
}

// TotalGoals returns the combined score.
func (m *Match) TotalGoals() int { return m.HomeGoals + m.AwayGoals }

// GoalDifference returns the absolute winning margin.
func (m *Match) GoalDifference() int {
	d := m.HomeGoals - m.AwayGoals
	if d < 0 {
		return -d
	}
	return d
}

// WinnerID returns the team ID of the winner, or "" for a draw.
func (m *Match) WinnerID() string {
	switch {
	case m.HomeGoals > m.AwayGoals:
		return m.HomeID
	case m.AwayGoals > m.HomeGoals:
		return m.AwayID
	default:
		return ""
	}
}

// Involves reports whether the given team ID played in the match.
func (m *Match) Involves(teamID string) bool {
	return m.HomeID == teamID || m.AwayID == teamID
}

// OpponentOf returns the other team's ID, or "" if teamID did not play.
func (m *Match) OpponentOf(teamID string) string {
	switch teamID {
	case m.HomeID:
		return m.AwayID
	case m.AwayID:
		return m.HomeID
	}
	return ""
}

// SourceList returns every dataset that contains this fixture: the file the
// primary row came from, followed by the files that duplicated it.
func (m *Match) SourceList() []string {
	out := make([]string, 0, 1+len(m.dupes))
	out = append(out, m.Source)
	out = append(out, m.dupes...)
	return out
}

// StageLabel is a human readable description of where in the competition the
// match was played ("Round 22", "group stage", "final").
func (m *Match) StageLabel() string {
	if m.Stage != "" {
		return m.Stage
	}
	if m.Round > 0 {
		return fmt.Sprintf("Round %d", m.Round)
	}
	return ""
}

// Player is a row of the FIFA player database.
type Player struct {
	ID          int            `json:"id"`
	Name        string         `json:"name"`
	Age         int            `json:"age"`
	Nationality string         `json:"nationality"`
	Overall     int            `json:"overall"`
	Potential   int            `json:"potential"`
	Club        string         `json:"club,omitempty"`
	ClubTeamID  string         `json:"club_team_id,omitempty"`
	Position    string         `json:"position,omitempty"`
	Jersey      int            `json:"jersey_number,omitempty"`
	Height      string         `json:"height,omitempty"`
	Weight      string         `json:"weight,omitempty"`
	Foot        string         `json:"preferred_foot,omitempty"`
	WorkRate    string         `json:"work_rate,omitempty"`
	Value       string         `json:"value,omitempty"`
	ValueEUR    int64          `json:"value_eur,omitempty"`
	Wage        string         `json:"wage,omitempty"`
	WageEUR     int64          `json:"wage_eur,omitempty"`
	Joined      string         `json:"joined,omitempty"`
	ContractTo  string         `json:"contract_valid_until,omitempty"`
	Skills      map[string]int `json:"skills,omitempty"`

	nameKey string // fold(name), for search
}

// PositionGroup buckets a FIFA position code into goalkeeper / defender /
// midfielder / forward, so that queries such as "forwards from São Paulo" work.
func (p *Player) PositionGroup() string { return positionGroup(p.Position) }

func positionGroup(pos string) string {
	switch strings.ToUpper(strings.TrimSpace(pos)) {
	case "GK":
		return "goalkeeper"
	case "CB", "LCB", "RCB", "LB", "RB", "LWB", "RWB":
		return "defender"
	case "CDM", "LDM", "RDM", "CM", "LCM", "RCM", "LM", "RM", "CAM", "LAM", "RAM":
		return "midfielder"
	case "ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW":
		return "forward"
	}
	return ""
}

// positionGroupAliases maps user words to a position group.
var positionGroupAliases = map[string]string{
	"gk": "goalkeeper", "goalkeeper": "goalkeeper", "goalkeepers": "goalkeeper",
	"keeper": "goalkeeper", "goalie": "goalkeeper", "goleiro": "goalkeeper",
	"def": "defender", "defender": "defender", "defenders": "defender",
	"defence": "defender", "defense": "defender", "zagueiro": "defender",
	"mid": "midfielder", "midfield": "midfielder", "midfielder": "midfielder",
	"midfielders": "midfielder", "meia": "midfielder",
	"fw": "forward", "forward": "forward", "forwards": "forward",
	"attacker": "forward", "attackers": "forward", "striker": "forward",
	"strikers": "forward", "atacante": "forward",
}

// SourceInfo records what a single CSV contributed, including provenance so the
// server can answer "where does this data come from?".
type SourceInfo struct {
	Key         string   `json:"key"`
	File        string   `json:"file"`
	Description string   `json:"description"`
	URL         string   `json:"url"`
	License     string   `json:"license"`
	Kind        string   `json:"kind"` // "matches" or "players"
	Rows        int      `json:"rows"`
	Skipped     int      `json:"skipped_rows"`
	SkipReasons []string `json:"skip_reasons,omitempty"`
	Competition []string `json:"competitions,omitempty"`
	SeasonMin   int      `json:"season_min,omitempty"`
	SeasonMax   int      `json:"season_max,omitempty"`
}
