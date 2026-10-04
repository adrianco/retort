package soccer

import (
	"encoding/csv"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Dataset describes one of the provided source files.
type Dataset struct {
	Name        string `json:"name"`
	File        string `json:"file"`
	Description string `json:"description"`
	Records     int    `json:"records"`
	Loaded      bool   `json:"loaded"`
	Error       string `json:"error,omitempty"`
}

// The provided datasets, in order of preference when two of them describe
// the same match.
var datasetCatalogue = []Dataset{
	{Name: "Brasileirão results", File: "Brasileirao_Matches.csv", Description: "Brasileirão Série A matches 2012-2022"},
	{Name: "Copa do Brasil results", File: "Brazilian_Cup_Matches.csv", Description: "Copa do Brasil matches 2012-2021"},
	{Name: "Libertadores results", File: "Libertadores_Matches.csv", Description: "Copa Libertadores matches 2013-2022"},
	{Name: "historical Brasileirão", File: "novo_campeonato_brasileiro.csv", Description: "Brasileirão Série A matches 2003-2019 with stadiums"},
	{Name: "extended statistics", File: "BR-Football-Dataset.csv", Description: "Série A/B/C and Copa do Brasil matches 2014-2023 with corners, attacks and shots"},
	{Name: "FIFA player ratings", File: "fifa_data.csv", Description: "FIFA 19 player ratings and attributes"},
}

// Match is one match, merged from every dataset that records it.
type Match struct {
	Date        time.Time
	Competition string
	Season      int
	Round       int
	Stage       string
	Home, Away  TeamID
	HomeGoals   int
	AwayGoals   int
	ScoreKnown  bool
	Arena       string
	Stats       *MatchStats
	Sources     []string
}

// MatchStats are the extended statistics some datasets record.
type MatchStats struct {
	HomeCorners int `json:"home_corners"`
	AwayCorners int `json:"away_corners"`
	HomeShots   int `json:"home_shots"`
	AwayShots   int `json:"away_shots"`
	HomeAttacks int `json:"home_attacks"`
	AwayAttacks int `json:"away_attacks"`
}

// Player is one player from the FIFA ratings.
type Player struct {
	ID            int            `json:"id"`
	Name          string         `json:"name"`
	Age           int            `json:"age"`
	Nationality   string         `json:"nationality"`
	Overall       int            `json:"overall"`
	Potential     int            `json:"potential"`
	Club          string         `json:"club"`
	Position      string         `json:"position"`
	JerseyNumber  string         `json:"jersey_number,omitempty"`
	Height        string         `json:"height,omitempty"`
	Weight        string         `json:"weight,omitempty"`
	PreferredFoot string         `json:"preferred_foot,omitempty"`
	Value         string         `json:"value,omitempty"`
	Wage          string         `json:"wage,omitempty"`
	Skills        map[string]int `json:"skills,omitempty"`
}

var skillColumns = []string{"Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling",
	"Curve", "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions",
	"Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions",
	"Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle",
	"GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes"}

// Store holds everything the system knows.
type Store struct {
	Teams     *Teams
	Matches   []*Match // matches with a known result, oldest first
	Players   []*Player
	Datasets  []Dataset
	Unplayed  int // fixtures with no result in any dataset
	serieA    map[TeamID]bool
	byTeam    map[TeamID][]*Match
	clubTeams map[string]TeamID
}

type rawMatch struct {
	source      int
	competition string
	season      int
	date        time.Time
	round       int
	stage       string
	home, away  TeamName
	homeGoals   int
	awayGoals   int
	known       bool
	arena       string
	stats       *MatchStats
}

// Load reads every provided dataset from dir. A missing or unreadable file
// is reported in Datasets rather than stopping the system.
func Load(dir string) *Store {
	s := &Store{Teams: NewTeams()}
	var raws []rawMatch
	for i, ds := range datasetCatalogue {
		rows, err := readCSV(filepath.Join(dir, ds.File))
		if err != nil {
			ds.Error = err.Error()
		} else {
			ds.Loaded = true
			ds.Records = len(rows)
			if ds.File == "fifa_data.csv" {
				s.Players = parsePlayers(rows)
			} else {
				raws = append(raws, parseMatches(i, ds.File, rows)...)
			}
		}
		s.Datasets = append(s.Datasets, ds)
	}
	for _, r := range raws {
		s.Teams.Observe(r.home)
		s.Teams.Observe(r.away)
	}
	s.Teams.Settle()
	s.merge(raws)
	s.index()
	return s
}

type row map[string]string

func readCSV(path string) ([]row, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r := csv.NewReader(f)
	r.FieldsPerRecord = -1
	r.LazyQuotes = true
	header, err := r.Read()
	if err != nil {
		return nil, fmt.Errorf("reading header: %w", err)
	}
	for i := range header {
		header[i] = strings.TrimSpace(strings.TrimPrefix(header[i], "\ufeff"))
	}
	var rows []row
	for {
		rec, err := r.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		m := make(row, len(header))
		for i, h := range header {
			if i < len(rec) {
				m[h] = strings.TrimSpace(rec[i])
			}
		}
		rows = append(rows, m)
	}
	return rows, nil
}

func parseMatches(source int, file string, rows []row) []rawMatch {
	var out []rawMatch
	for _, r := range rows {
		var m rawMatch
		m.source = source
		switch file {
		case "Brasileirao_Matches.csv":
			m.competition = SerieA
			m.date, _ = ParseDate(r["datetime"])
			m.home, m.away = ParseTeamName(withState(r["home_team"], r["home_team_state"])), ParseTeamName(withState(r["away_team"], r["away_team_state"]))
			m.homeGoals, m.awayGoals, m.known = goals(r["home_goal"], r["away_goal"])
			m.season = atoi(r["season"])
			m.round = atoi(r["round"])
		case "Brazilian_Cup_Matches.csv":
			m.competition = CopaDoBrasil
			m.date, _ = ParseDate(r["datetime"])
			m.home, m.away = ParseTeamName(r["home_team"]), ParseTeamName(r["away_team"])
			m.homeGoals, m.awayGoals, m.known = goals(r["home_goal"], r["away_goal"])
			m.season = atoi(r["season"])
			m.round = atoi(r["round"])
		case "Libertadores_Matches.csv":
			m.competition = Libertadores
			m.date, _ = ParseDate(r["datetime"])
			m.home, m.away = ParseTeamName(r["home_team"]), ParseTeamName(r["away_team"])
			m.homeGoals, m.awayGoals, m.known = goals(r["home_goal"], r["away_goal"])
			m.season = atoi(r["season"])
			m.stage = strings.ToLower(r["stage"])
		case "novo_campeonato_brasileiro.csv":
			m.competition = SerieA
			m.date, _ = ParseDate(r["Data"])
			// The archive's state columns are unreliable (Vitória is recorded
			// as ES), so clubs are identified by name alone.
			m.home, m.away = ParseTeamName(r["Equipe_mandante"]), ParseTeamName(r["Equipe_visitante"])
			m.homeGoals, m.awayGoals, m.known = goals(r["Gols_mandante"], r["Gols_visitante"])
			m.season = atoi(r["Ano"])
			m.round = atoi(r["Rodada"])
			m.arena = r["Arena"]
		case "BR-Football-Dataset.csv":
			m.competition = ParseCompetition(r["tournament"])
			m.date, _ = ParseDate(r["date"])
			m.home, m.away = ParseTeamName(r["home"]), ParseTeamName(r["away"])
			m.homeGoals, m.awayGoals, m.known = goals(r["home_goal"], r["away_goal"])
			m.season = m.date.Year()
			if r["home_corner"] != "" || r["home_shots"] != "" {
				m.stats = &MatchStats{
					HomeCorners: atoi(r["home_corner"]), AwayCorners: atoi(r["away_corner"]),
					HomeShots: atoi(r["home_shots"]), AwayShots: atoi(r["away_shots"]),
					HomeAttacks: atoi(r["home_attack"]), AwayAttacks: atoi(r["away_attack"]),
				}
			}
		}
		if m.date.IsZero() || m.competition == "" || m.home.Base == "" || m.away.Base == "" {
			continue
		}
		if m.season == 0 {
			m.season = m.date.Year()
		}
		out = append(out, m)
	}
	return out
}

// withState adds the state column to a name that lacks the suffix, so
// "Flamengo" + "RJ" reads like "Flamengo-RJ".
func withState(name, state string) string {
	state = strings.ToUpper(strings.TrimSpace(state))
	if !brazilianStates[state] {
		return name
	}
	if ParseTeamName(name).Qualifier != "" {
		return name
	}
	return name + "-" + state
}

func goals(h, a string) (int, int, bool) {
	hg, err1 := strconv.ParseFloat(strings.TrimSpace(h), 64)
	ag, err2 := strconv.ParseFloat(strings.TrimSpace(a), 64)
	if err1 != nil || err2 != nil || hg < 0 || ag < 0 {
		return 0, 0, false
	}
	return int(hg), int(ag), true
}

func atoi(s string) int {
	f, err := strconv.ParseFloat(strings.TrimSpace(s), 64)
	if err != nil || math.IsNaN(f) {
		return 0
	}
	return int(f)
}

// merge combines records of the same match from different datasets: same
// competition, same home and away clubs, dates within three days. The
// preferred dataset's facts win; gaps are filled from the others.
func (s *Store) merge(raws []rawMatch) {
	sort.SliceStable(raws, func(i, j int) bool { return raws[i].source < raws[j].source })
	buckets := map[string][]*Match{}
	var all []*Match
	for _, r := range raws {
		home, away := s.Teams.Register(r.home), s.Teams.Register(r.away)
		key := r.competition + "|" + string(home) + "|" + string(away)
		srcName := datasetCatalogue[r.source].Name
		var target *Match
		for _, m := range buckets[key] {
			if sameFixture(m, r) {
				target = m
				break
			}
		}
		if target == nil {
			target = &Match{Date: r.date, Competition: r.competition, Season: r.season, Round: r.round, Stage: r.stage,
				Home: home, Away: away, HomeGoals: r.homeGoals, AwayGoals: r.awayGoals, ScoreKnown: r.known,
				Arena: r.arena, Stats: r.stats}
			buckets[key] = append(buckets[key], target)
			all = append(all, target)
		} else {
			if !target.ScoreKnown && r.known {
				target.HomeGoals, target.AwayGoals, target.ScoreKnown = r.homeGoals, r.awayGoals, true
			}
			if target.Arena == "" {
				target.Arena = r.arena
			}
			if target.Stats == nil {
				target.Stats = r.stats
			}
			if target.Round == 0 {
				target.Round = r.round
			}
			if target.Stage == "" {
				target.Stage = r.stage
			}
		}
		if !hasSource(target, srcName) {
			target.Sources = append(target.Sources, srcName)
		}
	}
	all = dropStrangers(all)
	labelCupStages(all)
	for _, m := range all {
		if m.ScoreKnown {
			s.Matches = append(s.Matches, m)
		} else {
			s.Unplayed++
		}
	}
	sort.SliceStable(s.Matches, func(i, j int) bool { return s.Matches[i].Date.Before(s.Matches[j].Date) })
}

// sameFixture decides whether a record describes an already known match.
// Records within three days of each other are the same match; and because
// the Série A is a double round-robin, a home/away pairing happens only once
// in a Série A season (though one dataset may itself list a pairing twice,
// so that rule only links records from different datasets).
func sameFixture(m *Match, r rawMatch) bool {
	if absDays(m.Date.Sub(r.date)) <= 3 {
		return true
	}
	return m.Competition == SerieA && m.Season == r.season && !hasSource(m, datasetCatalogue[r.source].Name)
}

// dropStrangers removes Série A matches known only from the extended
// statistics when another dataset covers that season and neither club
// appears in it there: such rows are mislabelled regional matches.
func dropStrangers(all []*Match) []*Match {
	const extended = "extended statistics"
	primary := map[int]map[TeamID]bool{}
	for _, m := range all {
		if m.Competition == SerieA && !(len(m.Sources) == 1 && m.Sources[0] == extended) {
			if primary[m.Season] == nil {
				primary[m.Season] = map[TeamID]bool{}
			}
			primary[m.Season][m.Home], primary[m.Season][m.Away] = true, true
		}
	}
	kept := all[:0]
	for _, m := range all {
		teams := primary[m.Season]
		if m.Competition == SerieA && teams != nil && !teams[m.Home] && !teams[m.Away] {
			continue
		}
		kept = append(kept, m)
	}
	return kept
}

func hasSource(m *Match, src string) bool {
	for _, s := range m.Sources {
		if s == src {
			return true
		}
	}
	return false
}

func absDays(d time.Duration) float64 {
	return math.Abs(d.Hours() / 24)
}

// labelCupStages names Copa do Brasil rounds. The last round of a season is
// the final only when it is a single tie; earlier rounds count back from it.
func labelCupStages(all []*Match) {
	type season struct {
		maxRound int
		inMax    int
	}
	seasons := map[int]*season{}
	for _, m := range all {
		if m.Competition != CopaDoBrasil || m.Round == 0 {
			continue
		}
		s := seasons[m.Season]
		if s == nil {
			s = &season{}
			seasons[m.Season] = s
		}
		if m.Round > s.maxRound {
			s.maxRound, s.inMax = m.Round, 0
		}
		if m.Round == s.maxRound {
			s.inMax++
		}
	}
	names := []string{"final", "semifinals", "quarterfinals", "round of 16"}
	for _, m := range all {
		if m.Competition != CopaDoBrasil || m.Round == 0 {
			continue
		}
		s := seasons[m.Season]
		m.Stage = fmt.Sprintf("round %d", m.Round)
		if s.inMax <= 2 {
			if back := s.maxRound - m.Round; back < len(names) {
				m.Stage = names[back]
			}
		}
	}
}

func parsePlayers(rows []row) []*Player {
	players := make([]*Player, 0, len(rows))
	for _, r := range rows {
		if r["Name"] == "" {
			continue
		}
		p := &Player{
			ID: atoi(r["ID"]), Name: r["Name"], Age: atoi(r["Age"]), Nationality: r["Nationality"],
			Overall: atoi(r["Overall"]), Potential: atoi(r["Potential"]), Club: r["Club"], Position: r["Position"],
			JerseyNumber: trimFloat(r["Jersey Number"]), Height: r["Height"], Weight: r["Weight"],
			PreferredFoot: r["Preferred Foot"], Value: r["Value"], Wage: r["Wage"], Skills: map[string]int{},
		}
		for _, c := range skillColumns {
			if v := r[c]; v != "" {
				p.Skills[c] = atoi(v)
			}
		}
		players = append(players, p)
	}
	return players
}

func trimFloat(s string) string {
	return strings.TrimSuffix(s, ".0")
}

func (s *Store) index() {
	s.byTeam = map[TeamID][]*Match{}
	s.serieA = map[TeamID]bool{}
	for _, m := range s.Matches {
		s.byTeam[m.Home] = append(s.byTeam[m.Home], m)
		s.byTeam[m.Away] = append(s.byTeam[m.Away], m)
		if m.Competition == SerieA {
			s.serieA[m.Home], s.serieA[m.Away] = true, true
		}
	}
	s.clubTeams = map[string]TeamID{}
	for _, p := range s.Players {
		if _, seen := s.clubTeams[p.Club]; seen || p.Club == "" {
			continue
		}
		if id, ok := s.Teams.ResolveExact(p.Club); ok {
			s.clubTeams[p.Club] = id
		} else {
			s.clubTeams[p.Club] = ""
		}
	}
}

// ClubTeam links a FIFA club name to the club in the match data, if any.
func (s *Store) ClubTeam(club string) (TeamID, bool) {
	id := s.clubTeams[club]
	return id, id != ""
}

// IsBrazilianTopFlightClub reports whether a club has played in the
// Brasileirão Série A in the match data.
func (s *Store) IsBrazilianTopFlightClub(id TeamID) bool { return s.serieA[id] }
