package driver

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"slices"
	"strconv"
	"strings"
	"testing"
	"time"
)

// ServerBinary is the built soccer knowledge server; the acceptance test
// run sets it before any spec starts.
var ServerBinary string

// ProvidedDataDir is where the provided Kaggle datasets live.
func ProvidedDataDir() string {
	if dir := os.Getenv("SOCCER_DATA_DIR"); dir != "" {
		return dir
	}
	_, here, _, _ := runtime.Caller(0)
	return filepath.Join(filepath.Dir(here), "..", "..", "data", "kaggle")
}

// mcpDriver reaches the server the way an LLM host does: it starts the
// server process and calls its MCP tools.
type mcpDriver struct {
	t         testing.TB
	synthetic bool
	dataDir   string
	matches   []MatchFixture
	players   []PlayerFixture
	client    *mcpClient
	stale     bool
	last      answer
	tools     []string
}

type answer struct {
	tool       string
	text       string
	isError    bool
	structured json.RawMessage
	took       time.Duration
}

// NewSyntheticDriver gives a server that knows only what the spec records.
func NewSyntheticDriver(t testing.TB) SoccerDriver {
	d := &mcpDriver{t: t, synthetic: true, dataDir: t.TempDir(), stale: true}
	t.Cleanup(d.stop)
	return d
}

// NewProvidedDataDriver gives a server holding the provided datasets.
func NewProvidedDataDriver(t testing.TB) SoccerDriver {
	d := &mcpDriver{t: t, dataDir: ProvidedDataDir(), stale: true}
	t.Cleanup(d.stop)
	return d
}

func (d *mcpDriver) UseTest(t testing.TB) { d.t = t }

func (d *mcpDriver) stop() {
	if d.client != nil {
		d.client.close()
		d.client = nil
	}
}

func (d *mcpDriver) RecordMatch(m MatchFixture) {
	d.matches = append(d.matches, m)
	d.stale = true
}

func (d *mcpDriver) RecordPlayer(p PlayerFixture) {
	d.players = append(d.players, p)
	d.stale = true
}

// ensureServer (re)starts the server so that it holds every recorded fact.
func (d *mcpDriver) ensureServer() {
	d.t.Helper()
	if !d.stale && d.client != nil {
		return
	}
	d.stop()
	if ServerBinary == "" {
		d.t.Fatalf("the soccer knowledge server has not been built")
	}
	if d.synthetic {
		if err := writeDataFiles(d.dataDir, d.matches, d.players); err != nil {
			d.t.Fatalf("could not prepare the match and player data: %v", err)
		}
	}
	client, err := startMCPClient(ServerBinary, "-data", d.dataDir)
	if err != nil {
		d.t.Fatalf("could not start the soccer knowledge server: %v", err)
	}
	d.client = client
	d.stale = false
}

// ask calls one of the server's tools and keeps its answer for the
// confirmations that follow.
func (d *mcpDriver) ask(tool string, args map[string]any) {
	d.t.Helper()
	d.ensureServer()
	started := time.Now()
	raw, err := d.client.request("tools/call", map[string]any{"name": tool, "arguments": args})
	took := time.Since(started)
	if err != nil {
		d.t.Fatalf("asking %s: %v", tool, err)
	}
	var result struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		StructuredContent json.RawMessage `json:"structuredContent"`
		IsError           bool            `json:"isError"`
	}
	if err := json.Unmarshal(raw, &result); err != nil {
		d.t.Fatalf("answer from %s was not a tool result: %v", tool, err)
	}
	var text strings.Builder
	for _, c := range result.Content {
		if c.Type == "text" {
			text.WriteString(c.Text)
		}
	}
	d.last = answer{tool: tool, text: text.String(), isError: result.IsError, structured: result.StructuredContent, took: took}
}

// read decodes the last answer, failing the spec if there was none or the
// server could not answer.
func (d *mcpDriver) read(into any) {
	d.t.Helper()
	if d.last.tool == "" {
		d.t.Fatalf("no question has been asked yet")
	}
	if d.last.isError {
		d.t.Fatalf("the server could not answer: %s", d.last.text)
	}
	if err := json.Unmarshal(d.last.structured, into); err != nil {
		d.t.Fatalf("could not read the answer to %s: %v\n%s", d.last.tool, err, d.last.text)
	}
}

// criteria translates the spec's named values into tool arguments.
func criteria(c map[string]string, rename map[string]string) map[string]any {
	args := map[string]any{}
	for k, v := range c {
		name := strings.ReplaceAll(k, " ", "_")
		if r, ok := rename[k]; ok {
			name = r
		}
		if n, err := strconv.Atoi(v); err == nil && name == "season" {
			args[name] = n
			continue
		}
		args[name] = v
	}
	return args
}

// ---------------------------------------------------------------- matches

type matchJSON struct {
	Date        string `json:"date"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Round       int    `json:"round"`
	Stage       string `json:"stage"`
	Home        string `json:"home"`
	Away        string `json:"away"`
	HomeGoals   int    `json:"home_goals"`
	AwayGoals   int    `json:"away_goals"`
	Stats       *struct {
		HomeCorners *int `json:"home_corners"`
		AwayCorners *int `json:"away_corners"`
		HomeShots   *int `json:"home_shots"`
		AwayShots   *int `json:"away_shots"`
	} `json:"stats"`
}

func (m matchJSON) describe() string {
	return fmt.Sprintf("%s %d-%d %s on %s", m.Home, m.HomeGoals, m.AwayGoals, m.Away, m.Date)
}

type headToHeadJSON struct {
	TeamA      string `json:"team_a"`
	TeamB      string `json:"team_b"`
	Meetings   int    `json:"meetings"`
	TeamAWins  int    `json:"team_a_wins"`
	TeamBWins  int    `json:"team_b_wins"`
	Draws      int    `json:"draws"`
	TeamAGoals int    `json:"team_a_goals"`
	TeamBGoals int    `json:"team_b_goals"`
}

type matchListJSON struct {
	Total      int             `json:"total"`
	Matches    []matchJSON     `json:"matches"`
	HeadToHead *headToHeadJSON `json:"head_to_head"`
}

func (d *mcpDriver) SearchMatches(c map[string]string) {
	d.t.Helper()
	args := criteria(c, map[string]string{"from": "date_from", "to": "date_to"})
	args["limit"] = 500
	d.ask("search_matches", args)
}

func (d *mcpDriver) FindLastMeeting(team, opponent string) {
	d.t.Helper()
	d.ask("last_meeting", map[string]any{"team": team, "opponent": opponent})
}

func (d *mcpDriver) SearchDerbies(c map[string]string) {
	d.t.Helper()
	args := criteria(c, nil)
	args["limit"] = 500
	d.ask("find_derbies", args)
}

var matchDescription = regexp.MustCompile(`^(.+?) (\d+)-(\d+) (.+?)(?: on (\d{4}-\d{2}-\d{2}))?$`)

type describedMatch struct {
	home, away           string
	homeGoals, awayGoals int
	date                 string
}

func (d *mcpDriver) parseDescription(desc string) describedMatch {
	d.t.Helper()
	m := matchDescription.FindStringSubmatch(desc)
	if m == nil {
		d.t.Fatalf("match %q should be described like \"Home 2-1 Away on 2023-09-03\"", desc)
	}
	hg, _ := strconv.Atoi(m[2])
	ag, _ := strconv.Atoi(m[3])
	return describedMatch{home: m[1], away: m[4], homeGoals: hg, awayGoals: ag, date: m[5]}
}

func (dm describedMatch) is(m matchJSON) bool {
	return sameName(dm.home, m.Home) && sameName(dm.away, m.Away) &&
		dm.homeGoals == m.HomeGoals && dm.awayGoals == m.AwayGoals &&
		(dm.date == "" || dm.date == m.Date)
}

func describeAll(ms []matchJSON) string {
	var lines []string
	for _, m := range ms {
		lines = append(lines, "  "+m.describe())
	}
	return strings.Join(lines, "\n")
}

func (d *mcpDriver) ConfirmMatchesFound(descriptions []string) {
	d.t.Helper()
	var list matchListJSON
	d.read(&list)
	for _, desc := range descriptions {
		want := d.parseDescription(desc)
		if !slices.ContainsFunc(list.Matches, want.is) {
			d.t.Errorf("expected to find %s, but found:\n%s", desc, describeAll(list.Matches))
		}
	}
}

func (d *mcpDriver) ConfirmMatchCount(count int, exactly bool) {
	d.t.Helper()
	var list matchListJSON
	d.read(&list)
	if exactly && list.Total != count {
		d.t.Errorf("expected %d matches, found %d:\n%s", count, list.Total, describeAll(list.Matches))
	}
	if !exactly && list.Total < count {
		d.t.Errorf("expected at least %d matches, found %d", count, list.Total)
	}
}

func (d *mcpDriver) headToHead() headToHeadJSON {
	d.t.Helper()
	var list matchListJSON
	d.read(&list)
	if list.HeadToHead != nil {
		return *list.HeadToHead
	}
	var h headToHeadJSON
	d.read(&h)
	if h.TeamA == "" {
		d.t.Fatalf("the answer gave no head-to-head summary:\n%s", d.last.text)
	}
	return h
}

func (d *mcpDriver) ConfirmHeadToHead(expected map[string]string) {
	d.t.Helper()
	h := d.headToHead()
	actual := map[string]int{"meetings": h.Meetings, "draws": h.Draws}
	for key := range expected {
		team, figure, ok := strings.Cut(key, " ")
		if !ok {
			continue
		}
		switch {
		case sameName(team, h.TeamA) && figure == "wins":
			actual[key] = h.TeamAWins
		case sameName(team, h.TeamB) && figure == "wins":
			actual[key] = h.TeamBWins
		case sameName(team, h.TeamA) && figure == "goals":
			actual[key] = h.TeamAGoals
		case sameName(team, h.TeamB) && figure == "goals":
			actual[key] = h.TeamBGoals
		}
	}
	d.confirmFigures("head-to-head", expected, func(key string) (string, bool) {
		v, ok := actual[key]
		return strconv.Itoa(v), ok
	})
}

func (d *mcpDriver) ConfirmHeadToHeadMeetingsAtLeast(count int) {
	d.t.Helper()
	if h := d.headToHead(); h.Meetings < count {
		d.t.Errorf("expected at least %d meetings, found %d", count, h.Meetings)
	}
}

func (d *mcpDriver) ConfirmMatchStatistics(expected map[string]string) {
	d.t.Helper()
	var list matchListJSON
	d.read(&list)
	if len(list.Matches) == 0 || list.Matches[0].Stats == nil {
		d.t.Fatalf("no match statistics were given:\n%s", d.last.text)
	}
	s := list.Matches[0].Stats
	pair := func(h, a *int) (string, bool) {
		if h == nil || a == nil {
			return "", false
		}
		return fmt.Sprintf("%d-%d", *h, *a), true
	}
	d.confirmFigures("match statistics", expected, func(key string) (string, bool) {
		switch key {
		case "corners":
			return pair(s.HomeCorners, s.AwayCorners)
		case "shots":
			return pair(s.HomeShots, s.AwayShots)
		}
		return "", false
	})
}

// ------------------------------------------------------------------ teams

type recordJSON struct {
	Team          string       `json:"team"`
	Competition   string       `json:"competition"`
	Matches       int          `json:"matches"`
	Wins          int          `json:"wins"`
	Draws         int          `json:"draws"`
	Losses        int          `json:"losses"`
	GoalsFor      int          `json:"goals_for"`
	GoalsAgainst  int          `json:"goals_against"`
	Points        int          `json:"points"`
	WinRate       float64      `json:"win_rate"`
	ByCompetition []recordJSON `json:"by_competition"`
}

func (r recordJSON) figure(key string) (string, bool) {
	switch key {
	case "matches":
		return strconv.Itoa(r.Matches), true
	case "wins":
		return strconv.Itoa(r.Wins), true
	case "draws":
		return strconv.Itoa(r.Draws), true
	case "losses":
		return strconv.Itoa(r.Losses), true
	case "goals for":
		return strconv.Itoa(r.GoalsFor), true
	case "goals against":
		return strconv.Itoa(r.GoalsAgainst), true
	case "points":
		return strconv.Itoa(r.Points), true
	case "win rate":
		return fmt.Sprintf("%.1f%%", r.WinRate), true
	}
	return "", false
}

type clubProfileJSON struct {
	Team      string       `json:"team"`
	SquadSize int          `json:"squad_size"`
	Squad     []playerJSON `json:"squad"`
	Record    *recordJSON  `json:"record"`
}

func (d *mcpDriver) TeamRecord(c map[string]string) {
	d.t.Helper()
	d.ask("team_record", criteria(c, nil))
}

func (d *mcpDriver) record() recordJSON {
	d.t.Helper()
	var profile clubProfileJSON
	d.read(&profile)
	if profile.Record != nil {
		return *profile.Record
	}
	var r recordJSON
	d.read(&r)
	return r
}

func (d *mcpDriver) ConfirmTeamRecord(expected map[string]string) {
	d.t.Helper()
	d.confirmFigures("record", expected, d.record().figure)
}

func (d *mcpDriver) ConfirmCompetitionRecord(expected map[string]string) {
	d.t.Helper()
	r := d.record()
	competition := expected["competition"]
	for _, part := range r.ByCompetition {
		if containsName(part.Competition, competition) {
			delete(expected, "competition")
			d.confirmFigures(part.Competition+" record", expected, part.figure)
			return
		}
	}
	d.t.Errorf("no record was given for %s:\n%s", competition, d.last.text)
}

func (d *mcpDriver) CompareHeadToHead(team, opponent string) {
	d.t.Helper()
	d.ask("head_to_head", map[string]any{"team_a": team, "team_b": opponent})
}

func (d *mcpDriver) CompetitionsPlayedBy(team string) {
	d.t.Helper()
	d.ask("team_competitions", map[string]any{"team": team})
}

func (d *mcpDriver) ConfirmPlayedIn(competitions []string) {
	d.t.Helper()
	var answer struct {
		Competitions []struct {
			Competition string `json:"competition"`
			Matches     int    `json:"matches"`
		} `json:"competitions"`
	}
	d.read(&answer)
	for _, want := range competitions {
		found := slices.ContainsFunc(answer.Competitions, func(c struct {
			Competition string `json:"competition"`
			Matches     int    `json:"matches"`
		}) bool {
			return sameName(c.Competition, want) && c.Matches > 0
		})
		if !found {
			d.t.Errorf("expected %s among the competitions played:\n%s", want, d.last.text)
		}
	}
}

var rankingMetrics = map[string]string{
	"goals scored": "goals_for", "goals conceded": "goals_against", "win rate": "win_rate",
	"points": "points", "wins": "wins", "goal difference": "goal_difference",
}

func (d *mcpDriver) RankTeams(c map[string]string) {
	d.t.Helper()
	args := criteria(c, nil)
	delete(args, "by")
	if by, ok := c["by"]; ok {
		metric, known := rankingMetrics[by]
		if !known {
			d.t.Fatalf("teams cannot be ranked by %q", by)
		}
		args["metric"] = metric
	}
	d.ask("rank_teams", args)
}

func (d *mcpDriver) ConfirmRankedFirst(expected map[string]string) {
	d.t.Helper()
	var answer struct {
		Ranking []struct {
			Team         string `json:"team"`
			DisplayValue string `json:"display_value"`
		} `json:"ranking"`
	}
	d.read(&answer)
	if len(answer.Ranking) == 0 {
		d.t.Fatalf("no team was ranked:\n%s", d.last.text)
	}
	leader := answer.Ranking[0]
	if team, ok := expected["team"]; ok && !sameName(team, leader.Team) {
		d.t.Errorf("expected %s to be ranked first, but it was %s:\n%s", team, leader.Team, d.last.text)
	}
	if value, ok := expected["value"]; ok && value != leader.DisplayValue {
		d.t.Errorf("expected the leader's figure to be %s, but it was %s", value, leader.DisplayValue)
	}
}

func (d *mcpDriver) FindTeam(name string) {
	d.t.Helper()
	d.ask("find_team", map[string]any{"name": name})
}

func (d *mcpDriver) ConfirmKnownAs(names []string) {
	d.t.Helper()
	var answer struct {
		Teams []struct {
			Name     string   `json:"name"`
			Variants []string `json:"variants"`
		} `json:"teams"`
	}
	d.read(&answer)
	if len(answer.Teams) == 0 {
		d.t.Fatalf("no team was identified:\n%s", d.last.text)
	}
	for _, name := range names {
		if !slices.Contains(answer.Teams[0].Variants, name) {
			d.t.Errorf("expected %s to be known as %q, but its names were %q", answer.Teams[0].Name, name, answer.Teams[0].Variants)
		}
	}
}

func (d *mcpDriver) ProfileClub(team string) {
	d.t.Helper()
	d.ask("club_profile", map[string]any{"team": team})
}

func (d *mcpDriver) ConfirmSquadIncludes(players []string) {
	d.t.Helper()
	var profile clubProfileJSON
	d.read(&profile)
	for _, name := range players {
		if !slices.ContainsFunc(profile.Squad, func(p playerJSON) bool { return sameName(p.Name, name) }) {
			d.t.Errorf("expected %s in the squad of %s:\n%s", name, profile.Team, d.last.text)
		}
	}
}

func (d *mcpDriver) ConfirmSquadSizeAtLeast(count int) {
	d.t.Helper()
	var profile clubProfileJSON
	d.read(&profile)
	if profile.SquadSize < count {
		d.t.Errorf("expected a squad of at least %d, found %d", count, profile.SquadSize)
	}
}

// ---------------------------------------------------------------- players

type playerJSON struct {
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	Overall     int    `json:"overall"`
	Age         int    `json:"age"`
}

type playerListJSON struct {
	Total   int          `json:"total"`
	Players []playerJSON `json:"players"`
}

func (d *mcpDriver) SearchPlayers(c map[string]string) {
	d.t.Helper()
	args := criteria(c, nil)
	args["limit"] = 100
	d.ask("search_players", args)
}

func (d *mcpDriver) LookUpPlayer(name string) {
	d.t.Helper()
	d.ask("get_player", map[string]any{"name": name})
}

func (d *mcpDriver) ConfirmPlayerProfile(expected map[string]string) {
	d.t.Helper()
	var answer struct {
		Player *playerJSON `json:"player"`
	}
	d.read(&answer)
	if answer.Player == nil {
		d.t.Fatalf("no player was described:\n%s", d.last.text)
	}
	p := answer.Player
	d.confirmFigures("player", expected, func(key string) (string, bool) {
		switch key {
		case "name":
			return p.Name, true
		case "club":
			return p.Club, true
		case "overall":
			return strconv.Itoa(p.Overall), true
		case "position":
			return p.Position, true
		case "nationality":
			return p.Nationality, true
		}
		return "", false
	})
}

func playerNames(ps []playerJSON) []string {
	var names []string
	for _, p := range ps {
		names = append(names, p.Name)
	}
	return names
}

func (d *mcpDriver) ConfirmPlayersInOrder(names []string) {
	d.t.Helper()
	var list playerListJSON
	d.read(&list)
	found := playerNames(list.Players)
	if len(found) < len(names) {
		d.t.Fatalf("expected the list to start %q, but it was %q", names, found)
	}
	for i, name := range names {
		if !sameName(name, found[i]) {
			d.t.Errorf("expected the list to start %q, but it was %q", names, found[:len(names)])
			return
		}
	}
}

func (d *mcpDriver) ConfirmPlayersFound(names []string) {
	d.t.Helper()
	var list playerListJSON
	d.read(&list)
	for _, name := range names {
		if !slices.ContainsFunc(list.Players, func(p playerJSON) bool { return sameName(p.Name, name) }) {
			d.t.Errorf("expected to find %s, but found %q", name, playerNames(list.Players))
		}
	}
}

func (d *mcpDriver) ConfirmPlayerCount(count int, exactly bool) {
	d.t.Helper()
	var list playerListJSON
	d.read(&list)
	if exactly && list.Total != count {
		d.t.Errorf("expected %d players, found %d: %q", count, list.Total, playerNames(list.Players))
	}
	if !exactly && list.Total < count {
		d.t.Errorf("expected at least %d players, found %d", count, list.Total)
	}
}

func (d *mcpDriver) ConfirmPlayerTotal(count int) {
	d.t.Helper()
	d.ConfirmPlayerCount(count, true)
}

type clubSummaryJSON struct {
	Clubs []struct {
		Club           string  `json:"club"`
		Players        int     `json:"players"`
		AverageOverall float64 `json:"average_overall"`
	} `json:"clubs"`
}

func (d *mcpDriver) SummariseBrazilianPlayersAtBrazilianClubs() {
	d.t.Helper()
	d.ask("brazilian_players_by_club", map[string]any{})
}

func (d *mcpDriver) ConfirmClubSummary(expected map[string]string) {
	d.t.Helper()
	var summary clubSummaryJSON
	d.read(&summary)
	for _, c := range summary.Clubs {
		if sameName(c.Club, expected["club"]) {
			d.confirmFigures(c.Club, expected, func(key string) (string, bool) {
				switch key {
				case "club":
					return c.Club, true
				case "players":
					return strconv.Itoa(c.Players), true
				case "average rating":
					return fmt.Sprintf("%.1f", c.AverageOverall), true
				}
				return "", false
			})
			return
		}
	}
	d.t.Errorf("expected %s in the summary:\n%s", expected["club"], d.last.text)
}

func (d *mcpDriver) ConfirmClubNotInSummary(club string) {
	d.t.Helper()
	var summary clubSummaryJSON
	d.read(&summary)
	for _, c := range summary.Clubs {
		if sameName(c.Club, club) {
			d.t.Errorf("did not expect %s in the summary:\n%s", club, d.last.text)
		}
	}
}

// ----------------------------------------------------------- competitions

type standingsJSON struct {
	Champion  string   `json:"champion"`
	Relegated []string `json:"relegated"`
	Table     []struct {
		Position       int    `json:"position"`
		Team           string `json:"team"`
		Wins           int    `json:"wins"`
		Draws          int    `json:"draws"`
		Losses         int    `json:"losses"`
		GoalDifference int    `json:"goal_difference"`
		Points         int    `json:"points"`
	} `json:"table"`
}

func (d *mcpDriver) Standings(c map[string]string) {
	d.t.Helper()
	d.ask("standings", criteria(c, nil))
}

func (d *mcpDriver) ConfirmStanding(expected map[string]string) {
	d.t.Helper()
	var s standingsJSON
	d.read(&s)
	for _, row := range s.Table {
		if strconv.Itoa(row.Position) != expected["position"] {
			continue
		}
		d.confirmFigures(fmt.Sprintf("position %d", row.Position), expected, func(key string) (string, bool) {
			switch key {
			case "position":
				return strconv.Itoa(row.Position), true
			case "team":
				return row.Team, true
			case "points":
				return strconv.Itoa(row.Points), true
			case "wins":
				return strconv.Itoa(row.Wins), true
			case "draws":
				return strconv.Itoa(row.Draws), true
			case "losses":
				return strconv.Itoa(row.Losses), true
			case "goal difference":
				return strconv.Itoa(row.GoalDifference), true
			}
			return "", false
		})
		return
	}
	d.t.Errorf("the table has no position %s:\n%s", expected["position"], d.last.text)
}

func (d *mcpDriver) ConfirmChampionNamed(team string) {
	d.t.Helper()
	var s standingsJSON
	d.read(&s)
	switch {
	case team == "" && s.Champion != "":
		d.t.Errorf("expected no champion to be named, but %s was:\n%s", s.Champion, d.last.text)
	case !sameName(s.Champion, team):
		d.t.Errorf("expected %s to be named champion, but the champion was %q", team, s.Champion)
	}
}

func (d *mcpDriver) ConfirmRelegated(teams []string) {
	d.t.Helper()
	var s standingsJSON
	d.read(&s)
	for _, team := range teams {
		if !slices.ContainsFunc(s.Relegated, func(r string) bool { return sameName(r, team) }) {
			d.t.Errorf("expected %s to be relegated; relegated teams were %q", team, s.Relegated)
		}
	}
}

type bracketJSON struct {
	Stages []struct {
		Stage string `json:"stage"`
		Ties  []struct {
			TeamA     string `json:"team_a"`
			TeamB     string `json:"team_b"`
			Aggregate string `json:"aggregate"`
			Winner    string `json:"winner"`
		} `json:"ties"`
	} `json:"stages"`
}

func (d *mcpDriver) Bracket(c map[string]string) {
	d.t.Helper()
	d.ask("knockout_bracket", criteria(c, nil))
}

func (d *mcpDriver) ConfirmTie(expected map[string]string) {
	d.t.Helper()
	var b bracketJSON
	d.read(&b)
	teamA, teamB, _ := strings.Cut(expected["teams"], " v ")
	for _, stage := range b.Stages {
		if !sameName(stage.Stage, expected["stage"]) {
			continue
		}
		for _, tie := range stage.Ties {
			if sameName(tie.TeamA, teamA) && sameName(tie.TeamB, teamB) {
				d.confirmFigures(stage.Stage+" tie", expected, func(key string) (string, bool) {
					switch key {
					case "stage":
						return stage.Stage, true
					case "teams":
						return tie.TeamA + " v " + tie.TeamB, true
					case "aggregate":
						return tie.Aggregate, true
					case "winner":
						return tie.Winner, true
					}
					return "", false
				})
				return
			}
		}
	}
	d.t.Errorf("expected a %s tie %s:\n%s", expected["stage"], expected["teams"], d.last.text)
}

func (d *mcpDriver) ConfirmNoStage(stage string) {
	d.t.Helper()
	var b bracketJSON
	d.read(&b)
	for _, s := range b.Stages {
		if sameName(s.Stage, stage) {
			d.t.Errorf("did not expect the %s in the bracket", stage)
		}
	}
}

// ------------------------------------------------------------- statistics

type summaryJSON struct {
	Season         int      `json:"season"`
	Matches        int      `json:"matches"`
	AverageGoals   float64  `json:"average_goals"`
	HomeWinRate    float64  `json:"home_win_rate"`
	DrawRate       float64  `json:"draw_rate"`
	AwayWinRate    float64  `json:"away_win_rate"`
	AverageCorners *float64 `json:"average_corners"`
	Champion       string   `json:"champion"`
}

func (s summaryJSON) figure(key string) (string, bool) {
	switch key {
	case "season":
		return strconv.Itoa(s.Season), true
	case "matches":
		return strconv.Itoa(s.Matches), true
	case "average goals":
		return fmt.Sprintf("%.2f", s.AverageGoals), true
	case "home win rate":
		return fmt.Sprintf("%.1f%%", s.HomeWinRate), true
	case "draw rate":
		return fmt.Sprintf("%.1f%%", s.DrawRate), true
	case "away win rate":
		return fmt.Sprintf("%.1f%%", s.AwayWinRate), true
	case "average corners":
		if s.AverageCorners == nil {
			return "not recorded", true
		}
		return fmt.Sprintf("%.2f", *s.AverageCorners), true
	case "champion":
		return s.Champion, true
	}
	return "", false
}

func (d *mcpDriver) SummariseCompetition(c map[string]string) {
	d.t.Helper()
	d.ask("competition_stats", criteria(c, nil))
}

func (d *mcpDriver) ConfirmSummary(expected map[string]string) {
	d.t.Helper()
	var s summaryJSON
	d.read(&s)
	d.confirmFigures("summary", expected, s.figure)
}

func (d *mcpDriver) ConfirmAverageGoalsBetween(low, high float64) {
	d.t.Helper()
	var s summaryJSON
	d.read(&s)
	if s.AverageGoals < low || s.AverageGoals > high {
		d.t.Errorf("expected average goals between %.2f and %.2f, got %.2f", low, high, s.AverageGoals)
	}
}

func (d *mcpDriver) BiggestWins(c map[string]string) {
	d.t.Helper()
	d.ask("biggest_wins", criteria(c, nil))
}

func (d *mcpDriver) ConfirmBiggestWinsInOrder(results []string) {
	d.t.Helper()
	var list matchListJSON
	d.read(&list)
	if len(list.Matches) < len(results) {
		d.t.Fatalf("expected at least %d results:\n%s", len(results), describeAll(list.Matches))
	}
	for i, r := range results {
		if !d.parseDescription(r).is(list.Matches[i]) {
			d.t.Errorf("expected result %d to be %s:\n%s", i+1, r, describeAll(list.Matches))
			return
		}
	}
}

func (d *mcpDriver) ConfirmBiggestWinMarginAtLeast(goals int) {
	d.t.Helper()
	var list matchListJSON
	d.read(&list)
	if len(list.Matches) == 0 {
		d.t.Fatalf("no results were listed")
	}
	m := list.Matches[0]
	if margin := max(m.HomeGoals-m.AwayGoals, m.AwayGoals-m.HomeGoals); margin < goals {
		d.t.Errorf("expected the biggest win to be by at least %d goals, it was %s", goals, m.describe())
	}
}

func (d *mcpDriver) CompareSeasons(seasons []string) {
	d.t.Helper()
	d.ask("compare_seasons", map[string]any{"seasons": strings.Join(seasons, ",")})
}

func (d *mcpDriver) ConfirmSeasonComparison(expected map[string]string) {
	d.t.Helper()
	var answer struct {
		Seasons []summaryJSON `json:"seasons"`
	}
	d.read(&answer)
	for _, s := range answer.Seasons {
		if strconv.Itoa(s.Season) == expected["season"] {
			d.confirmFigures("season "+expected["season"], expected, s.figure)
			return
		}
	}
	d.t.Errorf("season %s was not compared:\n%s", expected["season"], d.last.text)
}

// --------------------------------------------------- datasets & assistant

func (d *mcpDriver) DescribeDatasets() {
	d.t.Helper()
	d.ask("dataset_overview", map[string]any{})
}

func (d *mcpDriver) ConfirmDatasetsLoaded(datasets []string) {
	d.t.Helper()
	var answer struct {
		Datasets []struct {
			Name    string `json:"name"`
			Records int    `json:"records"`
		} `json:"datasets"`
	}
	d.read(&answer)
	for _, want := range datasets {
		loaded := false
		for _, ds := range answer.Datasets {
			if sameName(ds.Name, want) && ds.Records > 0 {
				loaded = true
			}
		}
		if !loaded {
			d.t.Errorf("expected the %s dataset to be loaded:\n%s", want, d.last.text)
		}
	}
}

var capabilityTools = map[string]string{
	"match search": "search_matches", "head-to-head": "head_to_head", "team record": "team_record",
	"team rankings": "rank_teams", "standings": "standings", "knockout bracket": "knockout_bracket",
	"player search": "search_players", "player profile": "get_player",
	"competition statistics": "competition_stats", "biggest wins": "biggest_wins",
	"season comparison": "compare_seasons", "derbies": "find_derbies", "club profile": "club_profile",
	"dataset overview": "dataset_overview",
}

func (d *mcpDriver) DiscoverCapabilities() {
	d.t.Helper()
	d.ensureServer()
	raw, err := d.client.request("tools/list", map[string]any{})
	if err != nil {
		d.t.Fatalf("could not discover the server's capabilities: %v", err)
	}
	var list struct {
		Tools []struct {
			Name        string         `json:"name"`
			Description string         `json:"description"`
			InputSchema map[string]any `json:"inputSchema"`
		} `json:"tools"`
	}
	if err := json.Unmarshal(raw, &list); err != nil {
		d.t.Fatalf("the capability list could not be read: %v", err)
	}
	d.tools = nil
	for _, tool := range list.Tools {
		if tool.Description == "" || tool.InputSchema == nil {
			d.t.Errorf("capability %s is not described well enough for an assistant to use", tool.Name)
		}
		d.tools = append(d.tools, tool.Name)
	}
}

func (d *mcpDriver) ConfirmCapabilities(kinds []string) {
	d.t.Helper()
	for _, kind := range kinds {
		tool, known := capabilityTools[kind]
		if !known {
			d.t.Fatalf("the driver does not know how the server offers %q", kind)
		}
		if !slices.Contains(d.tools, tool) {
			d.t.Errorf("the assistant was not offered %s; it was offered %q", kind, d.tools)
		}
	}
}

func (d *mcpDriver) ConfirmAnswerContains(line string) {
	d.t.Helper()
	if !strings.Contains(d.last.text, line) {
		d.t.Errorf("expected the answer to read %q, but it was:\n%s", line, d.last.text)
	}
}

func (d *mcpDriver) ConfirmAnsweredWithin(limit time.Duration) {
	d.t.Helper()
	if d.last.tool == "" {
		d.t.Fatalf("no question has been asked yet")
	}
	if d.last.isError {
		d.t.Fatalf("the server could not answer: %s", d.last.text)
	}
	if d.last.took > limit {
		d.t.Errorf("expected an answer within %s, it took %s", limit, d.last.took)
	}
}

func (d *mcpDriver) ConfirmToldUnknown(name string) {
	d.t.Helper()
	if !d.last.isError || !containsName(d.last.text, name) {
		d.t.Errorf("expected to be told that %q is not known, but the answer was:\n%s", name, d.last.text)
	}
}

// ---------------------------------------------------------------- helpers

// confirmFigures compares each expected figure with the one in the answer.
func (d *mcpDriver) confirmFigures(what string, expected map[string]string, actual func(string) (string, bool)) {
	d.t.Helper()
	keys := make([]string, 0, len(expected))
	for k := range expected {
		keys = append(keys, k)
	}
	slices.Sort(keys)
	for _, key := range keys {
		got, ok := actual(key)
		if !ok {
			d.t.Fatalf("the driver does not know how to check %q in a %s", key, what)
		}
		if !sameName(got, expected[key]) {
			d.t.Errorf("expected %s %s to be %s, but it was %s\n%s", what, key, expected[key], got, d.last.text)
		}
	}
}

var accents = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a", "é", "e", "ê", "e", "è", "e", "ë", "e",
	"í", "i", "î", "i", "ì", "i", "ï", "i", "ó", "o", "ô", "o", "õ", "o", "ò", "o", "ö", "o",
	"ú", "u", "û", "u", "ù", "u", "ü", "u", "ç", "c", "ñ", "n")

// fold ignores case and accents, which differ between data sources.
func fold(s string) string {
	return accents.Replace(strings.ToLower(strings.TrimSpace(s)))
}

func sameName(a, b string) bool { return fold(a) == fold(b) }

func contains(s, part string) bool { return strings.Contains(s, part) }

func containsName(s, part string) bool { return strings.Contains(fold(s), fold(part)) }
