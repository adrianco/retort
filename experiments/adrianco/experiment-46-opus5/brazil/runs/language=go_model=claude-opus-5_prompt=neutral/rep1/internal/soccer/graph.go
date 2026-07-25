// graph.go - assembly of the in-memory knowledge graph.
//
// Context
//
//	Load() runs the whole pipeline:
//
//	    read 6 CSVs -> observe every team spelling -> resolve club identities
//	                -> build match edges -> de-duplicate -> index
//
//	De-duplication matters because Série A 2012-2019 is present in three of the
//	five match files. Without it "Palmeiras played 38 games in 2015" becomes
//	"Palmeiras played 95 games in 2015" and every standings table is wrong.
//
//	Two rows describe the same fixture when they share competition, season, home
//	club and away club, and they come from different files. Within a league that
//	is enough - an ordered pair meets exactly once per round-robin season, so the
//	sources' disagreeing dates do not matter. Within a cup the pair can meet more
//	than once in a season, so the dates must also be within a fortnight, which
//	absorbs cross-source drift while keeping a Libertadores group meeting apart
//	from a knockout tie months later. Rows from the same file are never merged:
//	novo_campeonato_brasileiro.csv lists Botafogo as home for both 2009
//	Botafogo-Flamengo meetings, and folding those together would delete a match.
//
//	Merging is additive: the first source to describe a fixture owns the score,
//	and later sources contribute whatever the first was missing (stadium from
//	the historical file, shot and corner counts from BR-Football, round numbers
//	from the league files).
//
//	Two further guards handle outright defects in the secondary sources - see
//	the participants map and the isLeague check in LoadFS.
package soccer

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// Graph is the knowledge graph: clubs, matches, players and the indexes that
// make the MCP tools fast enough to answer inside the 2 second budget.
type Graph struct {
	clubs   map[string]*Club
	clubIDs []string

	matches   []*Match
	matchByID map[string]*Match

	byClub       map[string][]*Match
	byCompSeason map[string][]*Match
	seasons      map[Competition][]int

	players         []*Player
	playersByClubID map[string][]*Player
	playersByID     map[int]*Player

	datasets []DatasetInfo
	resolver *resolver
}

// dedupWindow is how far apart two rows describing the same knockout fixture
// may be dated and still be considered the same match. League fixtures ignore
// the window entirely - see findFixture.
const dedupWindow = 14 * 24 * time.Hour

// establishedThreshold is how many fixtures a competition season must already
// have before later, lower-precedence sources are held to its participant list.
const establishedThreshold = 20

// isLeague reports whether a competition is a round-robin league, where an
// ordered pair of clubs meets exactly once per season.
func isLeague(c Competition) bool {
	return c == SerieA || c == SerieB || c == SerieC
}

// datasetCatalog carries the provenance metadata required by the licences of
// the bundled datasets.
var datasetCatalog = map[string]DatasetInfo{
	FileBrasileirao: {
		File:        FileBrasileirao,
		Description: "Brasileirão Série A matches (2012-2022)",
		License:     "CC BY 4.0",
		Source:      "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
	},
	FileCup: {
		File:        FileCup,
		Description: "Copa do Brasil matches (2012-2021)",
		License:     "CC BY 4.0",
		Source:      "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
	},
	FileLibertadores: {
		File:        FileLibertadores,
		Description: "Copa Libertadores matches (2013-2022)",
		License:     "CC BY 4.0",
		Source:      "https://www.kaggle.com/datasets/ricardomattos05/jogos-do-campeonato-brasileiro",
	},
	FileBRFootball: {
		File:        FileBRFootball,
		Description: "Série A/B/C and Copa do Brasil with shots, corners and attacks (2014-2023)",
		License:     "CC0 Public Domain",
		Source:      "https://www.kaggle.com/datasets/cuecacuela/brazilian-football-matches",
	},
	FileHistorical: {
		File:        FileHistorical,
		Description: "Historical Brasileirão with stadiums (2003-2019)",
		License:     "CC BY 4.0",
		Source:      "https://www.kaggle.com/datasets/macedojleo/campeonato-brasileiro-2003-a-2019",
	},
	FileFIFA: {
		File:        FileFIFA,
		Description: "FIFA player database with ratings and attributes",
		License:     "Apache 2.0",
		Source:      "https://www.kaggle.com/datasets/youssefelbadry10/fifa-players-data",
	},
}

// loaders is the ordered list of match readers. Order defines precedence when
// the same fixture appears in more than one file.
var loaders = []struct {
	file string
	fn   func(fs.FS) ([]rawMatch, int, error)
}{
	{FileBrasileirao, loadBrasileirao},
	{FileHistorical, loadHistorical},
	{FileCup, loadCup},
	{FileLibertadores, loadLibertadores},
	{FileBRFootball, loadBRFootball},
}

// Load builds a graph from the CSV files in dir.
func Load(dir string) (*Graph, error) {
	return LoadFS(os.DirFS(dir))
}

// LoadFS builds a graph from any filesystem holding the six CSV files, which
// keeps the loader testable against small in-memory fixtures.
func LoadFS(fsys fs.FS) (*Graph, error) {
	g := &Graph{
		clubs:           make(map[string]*Club),
		matchByID:       make(map[string]*Match),
		byClub:          make(map[string][]*Match),
		byCompSeason:    make(map[string][]*Match),
		seasons:         make(map[Competition][]int),
		playersByClubID: make(map[string][]*Player),
		playersByID:     make(map[int]*Player),
		resolver:        newResolver(),
	}

	type sourceBatch struct {
		file string
		rows []rawMatch
		read int
	}
	var batches []sourceBatch

	// Pass 1: read every file and observe every team spelling.
	for _, l := range loaders {
		rows, read, err := l.fn(fsys)
		if err != nil {
			return nil, err
		}
		for i := range rows {
			g.resolver.observe(rows[i].Home)
			g.resolver.observe(rows[i].Away)
		}
		batches = append(batches, sourceBatch{file: l.file, rows: rows, read: read})
	}
	g.resolver.finalize()
	g.clubs = g.resolver.clubs

	// Pass 2: build and de-duplicate match edges.
	type fixtureKey struct {
		comp   Competition
		season int
		home   string
		away   string
	}
	index := make(map[fixtureKey][]*Match)

	// participants records which clubs a competition season is known to
	// involve, so that a later source cannot inject fixtures from a different
	// division. BR-Football-Dataset.csv labels 111 Série B matches from 2021 as
	// Série A; without this guard the 2021 table has 24 clubs and 491 matches.
	participants := make(map[string]map[string]bool)
	established := make(map[string]bool)
	fixtureCount := make(map[string]int)

	for _, b := range batches {
		info := datasetCatalog[b.file]
		info.Rows = b.read
		compSet := map[Competition]bool{}
		batchClubs := make(map[string]map[string]bool)

		for i := range b.rows {
			raw := &b.rows[i]
			homeID := g.resolver.resolve(raw.Home)
			awayID := g.resolver.resolve(raw.Away)
			if homeID == "" || awayID == "" || homeID == awayID {
				continue
			}
			csKey := compSeasonKey(raw.Competition, raw.Season)
			if established[csKey] && (!participants[csKey][homeID] || !participants[csKey][awayID]) {
				info.Rejected++
				continue
			}
			info.Loaded++
			compSet[raw.Competition] = true
			if batchClubs[csKey] == nil {
				batchClubs[csKey] = make(map[string]bool)
			}
			batchClubs[csKey][homeID] = true
			batchClubs[csKey][awayID] = true
			if info.SeasonMin == 0 || (raw.Season > 0 && raw.Season < info.SeasonMin) {
				info.SeasonMin = raw.Season
			}
			if raw.Season > info.SeasonMax {
				info.SeasonMax = raw.Season
			}

			key := fixtureKey{raw.Competition, raw.Season, homeID, awayID}
			if existing := findFixture(index[key], raw, b.file); existing != nil {
				mergeMatch(existing, raw, b.file)
				continue
			}
			// Once a competition season has a primary source, later sources may
			// only corroborate its league fixtures, never add new ones: an
			// ordered pair meets exactly once per round-robin season, so a
			// second unmatched row is a defect in the secondary file.
			if isLeague(raw.Competition) && established[csKey] {
				info.Loaded--
				info.Rejected++
				continue
			}
			m := g.newMatch(raw, homeID, awayID, b.file, len(index[key]))
			index[key] = append(index[key], m)
			fixtureCount[csKey]++
			g.matches = append(g.matches, m)
			g.matchByID[m.ID] = m
		}

		// Freeze this batch's participant lists so the next source is checked
		// against them.
		for csKey, clubs := range batchClubs {
			if participants[csKey] == nil {
				participants[csKey] = make(map[string]bool)
			}
			for id := range clubs {
				participants[csKey][id] = true
			}
		}
		for csKey, n := range fixtureCount {
			if n >= establishedThreshold {
				established[csKey] = true
			}
		}

		comps := make([]string, 0, len(compSet))
		for c := range compSet {
			comps = append(comps, string(c))
		}
		sort.Strings(comps)
		info.Competitions = comps
		g.datasets = append(g.datasets, info)
	}

	// Players.
	players, playerRows, err := loadPlayers(fsys)
	if err != nil {
		return nil, err
	}
	g.players = players
	pinfo := datasetCatalog[FileFIFA]
	pinfo.Rows = playerRows
	pinfo.Loaded = len(players)
	g.datasets = append(g.datasets, pinfo)

	g.buildIndexes()
	return g, nil
}

// findFixture looks for an already-built match that the raw row describes.
//
// Two rows from the *same* file are always distinct fixtures, even if they
// look identical - novo_campeonato_brasileiro.csv lists Botafogo as the home
// side for both 2009 Botafogo-Flamengo meetings, and folding those together
// would silently delete a match.
//
// Across files, an ordered pair of clubs in a round-robin league meets exactly
// once per season, so a candidate is the same fixture no matter what the two
// sources claim the date was. Cup and Libertadores ties can legitimately repeat
// within a season (a group meeting and a knockout tie months later), so those
// are only merged when the two dates are close together.
func findFixture(candidates []*Match, raw *rawMatch, source string) *Match {
	for _, m := range candidates {
		if contains(m.Sources, source) {
			continue
		}
		if isLeague(raw.Competition) {
			return m
		}
		if !m.HasDate || !raw.HasDate {
			return m
		}
		delta := m.Date.Sub(raw.Date)
		if delta < 0 {
			delta = -delta
		}
		if delta <= dedupWindow {
			return m
		}
	}
	return nil
}

func (g *Graph) newMatch(raw *rawMatch, homeID, awayID, source string, seq int) *Match {
	id := fmt.Sprintf("%s:%d:%s:%s", compSlug(raw.Competition), raw.Season, homeID, awayID)
	if seq > 0 {
		id = fmt.Sprintf("%s#%d", id, seq+1)
	}
	home, away := g.clubs[homeID], g.clubs[awayID]
	return &Match{
		ID:          id,
		Competition: raw.Competition,
		Season:      raw.Season,
		Round:       raw.Round,
		Stage:       raw.Stage,
		Date:        raw.Date,
		HasDate:     raw.HasDate,
		HasTime:     raw.HasTime,
		HomeClubID:  homeID,
		AwayClubID:  awayID,
		HomeTeam:    home.Name,
		AwayTeam:    away.Name,
		HomeGoals:   raw.HomeGoals,
		AwayGoals:   raw.AwayGoals,
		HasScore:    raw.HasScore,
		Stadium:     raw.Stadium,
		Sources:     []string{source},
		Stats:       raw.Stats,
	}
}

// mergeMatch folds a duplicate row into the match already built for it. The
// existing record wins every conflict; the new row only fills in blanks.
func mergeMatch(m *Match, raw *rawMatch, source string) {
	if !contains(m.Sources, source) {
		m.Sources = append(m.Sources, source)
	}
	if !m.HasScore && raw.HasScore {
		m.HomeGoals, m.AwayGoals, m.HasScore = raw.HomeGoals, raw.AwayGoals, true
	}
	if !m.HasDate && raw.HasDate {
		m.Date, m.HasDate, m.HasTime = raw.Date, true, raw.HasTime
	}
	if m.Round == "" {
		m.Round = raw.Round
	}
	if m.Stage == "" {
		m.Stage = raw.Stage
	}
	if m.Stadium == "" {
		m.Stadium = raw.Stadium
	}
	if m.Stats == nil {
		m.Stats = raw.Stats
	}
}

func contains(list []string, s string) bool {
	for _, v := range list {
		if v == s {
			return true
		}
	}
	return false
}

// compSlug shortens a competition name for use inside match IDs.
func compSlug(c Competition) string {
	switch c {
	case SerieA:
		return "serie-a"
	case SerieB:
		return "serie-b"
	case SerieC:
		return "serie-c"
	case CopaDoBrasil:
		return "copa-do-brasil"
	case Libertadores:
		return "libertadores"
	}
	return slugify(normalizeText(string(c)))
}

// buildIndexes sorts matches chronologically and fills the lookup tables.
func (g *Graph) buildIndexes() {
	sort.SliceStable(g.matches, func(i, j int) bool {
		a, b := g.matches[i], g.matches[j]
		if a.HasDate != b.HasDate {
			return a.HasDate
		}
		if !a.Date.Equal(b.Date) {
			return a.Date.Before(b.Date)
		}
		return a.ID < b.ID
	})

	seasonSets := make(map[Competition]map[int]bool)
	for _, m := range g.matches {
		g.byClub[m.HomeClubID] = append(g.byClub[m.HomeClubID], m)
		g.byClub[m.AwayClubID] = append(g.byClub[m.AwayClubID], m)
		key := compSeasonKey(m.Competition, m.Season)
		g.byCompSeason[key] = append(g.byCompSeason[key], m)
		if m.Season > 0 {
			if seasonSets[m.Competition] == nil {
				seasonSets[m.Competition] = make(map[int]bool)
			}
			seasonSets[m.Competition][m.Season] = true
		}
	}
	for comp, set := range seasonSets {
		list := make([]int, 0, len(set))
		for s := range set {
			list = append(list, s)
		}
		sort.Ints(list)
		g.seasons[comp] = list
	}

	for id, club := range g.clubs {
		club.Matches = len(g.byClub[id])
		g.clubIDs = append(g.clubIDs, id)
	}
	sort.Slice(g.clubIDs, func(i, j int) bool {
		a, b := g.clubs[g.clubIDs[i]], g.clubs[g.clubIDs[j]]
		if a.Matches != b.Matches {
			return a.Matches > b.Matches
		}
		return a.ID < b.ID
	})

	for _, p := range g.players {
		if p.ID != 0 {
			if _, dup := g.playersByID[p.ID]; !dup {
				g.playersByID[p.ID] = p
			}
		}
		if p.ClubID != "" {
			g.playersByClubID[p.ClubID] = append(g.playersByClubID[p.ClubID], p)
		}
	}
	for _, list := range g.playersByClubID {
		sort.Slice(list, func(i, j int) bool { return list[i].Overall > list[j].Overall })
	}
}

func compSeasonKey(c Competition, season int) string {
	return fmt.Sprintf("%s|%d", c, season)
}

// FindDataDir locates the bundled dataset directory. It honours the
// BRAZILIAN_SOCCER_DATA environment variable, then walks up from the working
// directory looking for data/kaggle, so that both `go test ./...` and a binary
// started from anywhere in the tree find the data.
func FindDataDir() (string, error) {
	if env := os.Getenv("BRAZILIAN_SOCCER_DATA"); env != "" {
		if ok, _ := dirHasDatasets(env); ok {
			return env, nil
		}
		return "", fmt.Errorf("BRAZILIAN_SOCCER_DATA=%q does not contain the expected CSV files", env)
	}
	wd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for dir := wd; ; {
		candidate := filepath.Join(dir, "data", "kaggle")
		if ok, _ := dirHasDatasets(candidate); ok {
			return candidate, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", fmt.Errorf("could not find data/kaggle above %s; set BRAZILIAN_SOCCER_DATA", wd)
}

func dirHasDatasets(dir string) (bool, error) {
	for _, f := range []string{FileBrasileirao, FileFIFA} {
		if _, err := os.Stat(filepath.Join(dir, f)); err != nil {
			return false, err
		}
	}
	return true, nil
}

// ---------------------------------------------------------------------------
// Accessors
// ---------------------------------------------------------------------------

// Clubs returns every club node, most active first.
func (g *Graph) Clubs() []*Club {
	out := make([]*Club, 0, len(g.clubIDs))
	for _, id := range g.clubIDs {
		out = append(out, g.clubs[id])
	}
	return out
}

// Club looks a club up by ID.
func (g *Graph) Club(id string) *Club { return g.clubs[id] }

// Matches returns every match edge in chronological order.
func (g *Graph) Matches() []*Match { return g.matches }

// Match looks a match up by ID.
func (g *Graph) Match(id string) *Match { return g.matchByID[id] }

// Players returns every player node.
func (g *Graph) Players() []*Player { return g.players }

// Datasets returns provenance for the loaded files.
func (g *Graph) Datasets() []DatasetInfo { return g.datasets }

// Seasons lists the seasons available for a competition.
func (g *Graph) Seasons(c Competition) []int { return g.seasons[c] }

// CompetitionsPresent lists the competitions that actually have matches.
func (g *Graph) CompetitionsPresent() []Competition {
	var out []Competition
	for _, c := range AllCompetitions {
		if len(g.seasons[c]) > 0 {
			out = append(out, c)
		}
	}
	return out
}

// ClubMatches returns every match a club took part in, chronologically.
func (g *Graph) ClubMatches(clubID string) []*Match { return g.byClub[clubID] }

// CompetitionMatches returns the matches of one competition season.
func (g *Graph) CompetitionMatches(c Competition, season int) []*Match {
	return g.byCompSeason[compSeasonKey(c, season)]
}

// PlayersAtClub returns the FIFA players linked to a graph club.
func (g *Graph) PlayersAtClub(clubID string) []*Player { return g.playersByClubID[clubID] }

// Stats summarises the size of the graph.
type Stats struct {
	Clubs        int      `json:"clubs"`
	Matches      int      `json:"matches"`
	Players      int      `json:"players"`
	Competitions int      `json:"competitions"`
	Seasons      int      `json:"seasons"`
	Edges        int      `json:"edges"`
	SeasonRange  string   `json:"season_range"`
	Sources      []string `json:"sources"`
}

// Summary reports node and edge counts for the whole graph.
func (g *Graph) Summary() Stats {
	s := Stats{Clubs: len(g.clubs), Matches: len(g.matches), Players: len(g.players)}
	minSeason, maxSeason := 0, 0
	seasonSet := map[string]bool{}
	for _, c := range g.CompetitionsPresent() {
		s.Competitions++
		for _, y := range g.seasons[c] {
			if y <= 0 {
				continue
			}
			seasonSet[fmt.Sprintf("%s|%d", c, y)] = true
			if minSeason == 0 || y < minSeason {
				minSeason = y
			}
			if y > maxSeason {
				maxSeason = y
			}
		}
	}
	s.Seasons = len(seasonSet)
	// Each match contributes home, away and competition edges; each linked
	// player contributes a plays_for edge.
	s.Edges = len(g.matches)*3 + len(g.playersLinked())
	s.SeasonRange = fmt.Sprintf("%d-%d", minSeason, maxSeason)
	for _, d := range g.datasets {
		s.Sources = append(s.Sources, d.File)
	}
	return s
}

func (g *Graph) playersLinked() []*Player {
	var out []*Player
	for _, list := range g.playersByClubID {
		out = append(out, list...)
	}
	return out
}

// LinkedFIFAClubs lists the Brazilian clubs that exist in both the match data
// and the FIFA player data, with their squad sizes. The FIFA 19 dataset only
// licenses 15 Brazilian clubs, so this is the honest answer to "which squads
// can you show me?".
func (g *Graph) LinkedFIFAClubs() []*Club {
	var out []*Club
	for id := range g.playersByClubID {
		if c := g.clubs[id]; c != nil {
			out = append(out, c)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out
}

// ParseCompetition maps user input such as "serie a", "brasileirao" or
// "libertadores" onto a canonical competition.
func ParseCompetition(s string) (Competition, bool) {
	n := normalizeText(s)
	if n == "" {
		return "", false
	}
	switch n {
	case "serie a", "seriea", "a", "brasileirao", "brasileirao serie a",
		"campeonato brasileiro", "brasileiro", "brazilian league", "league":
		return SerieA, true
	case "serie b", "serieb", "b", "brasileirao serie b", "segunda divisao":
		return SerieB, true
	case "serie c", "seriec", "c", "brasileirao serie c":
		return SerieC, true
	case "copa do brasil", "copa brasil", "brazilian cup", "cup", "copa":
		return CopaDoBrasil, true
	case "libertadores", "copa libertadores", "conmebol libertadores":
		return Libertadores, true
	}
	for _, c := range AllCompetitions {
		if normalizeText(string(c)) == n {
			return c, true
		}
	}
	// Last resort: substring match, so "libertadores 2019" still works.
	for _, c := range AllCompetitions {
		if strings.Contains(normalizeText(string(c)), n) {
			return c, true
		}
	}
	return "", false
}
