package drivers

import (
	"fmt"
	"math"
	"strconv"
	"strings"
	"testing"
	"time"
)

// MCPDriver translates DSL steps into MCP tool calls and checks the answers.
// It is the only part of the acceptance tests that knows the system is an MCP
// server, what its tools are called, and the shape of their answers.
type MCPDriver struct {
	t     *testing.T
	start func(*testing.T) *Connection
	conn  *Connection
	last  ToolResult
	tool  string
}

var _ SystemDriver = (*MCPDriver)(nil)

func NewMCPDriver(t *testing.T, start func(*testing.T) *Connection) *MCPDriver {
	return &MCPDriver{t: t, start: start}
}

// ask calls a tool and fails the step unless the system answered.
func (d *MCPDriver) ask(tool string, args map[string]any) {
	d.t.Helper()
	if d.conn == nil {
		d.conn = d.start(d.t)
	}
	res, err := d.conn.CallTool(tool, args)
	if err != nil {
		d.t.Fatalf("asking %s: %v", tool, err)
	}
	if res.IsError {
		d.t.Fatalf("the system could not answer (%s): %s", tool, res.Text)
	}
	if strings.TrimSpace(res.Text) == "" {
		d.t.Fatalf("the system gave no readable answer to %s", tool)
	}
	if res.Structured == nil {
		d.t.Fatalf("the system gave no structured answer to %s", tool)
	}
	d.last, d.tool = res, tool
}

// ---- matches ---------------------------------------------------------------

func (d *MCPDriver) FindMatches(c map[string]string) {
	d.t.Helper()
	args := map[string]any{}
	copyText(args, c, "team", "team")
	copyText(args, c, "opponent", "opponent")
	copyText(args, c, "competition", "competition")
	copyText(args, c, "venue", "venue")
	copyText(args, c, "stage", "stage")
	copyText(args, c, "from", "date_from")
	copyText(args, c, "to", "date_to")
	copyNumber(d.t, args, c, "season", "season")
	copyNumber(d.t, args, c, "limit", "limit")
	if _, ok := args["limit"]; !ok {
		args["limit"] = 500
	}
	d.ask("find_matches", args)
}

func (d *MCPDriver) ConfirmMatchesShown(lines ...string) {
	d.t.Helper()
	d.confirmLinesIn(d.matchLines("matches"), lines...)
}

func (d *MCPDriver) ConfirmMatchCount(n int) {
	d.t.Helper()
	if got := len(d.list(d.last.Structured, "matches")); got != n {
		d.t.Fatalf("expected %d matches in the answer, there were %d:\n%s", n, got, d.last.Text)
	}
}

func (d *MCPDriver) ConfirmCompetitionsInMatches(names ...string) {
	d.t.Helper()
	seen := map[string]bool{}
	for _, m := range d.list(d.last.Structured, "matches") {
		seen[fold(str(m["competition"]))] = true
	}
	for _, n := range names {
		if !seen[fold(n)] {
			d.t.Fatalf("expected matches from %s, found competitions %v", n, keys(seen))
		}
	}
}

func (d *MCPDriver) ConfirmHeadToHeadSummary(_, _ string, expected []Expectation) {
	d.t.Helper()
	h2h, ok := d.last.Structured["head_to_head"].(map[string]any)
	if !ok {
		d.t.Fatalf("the answer has no head-to-head summary:\n%s", d.last.Text)
	}
	d.confirmTeamFacts(h2h, "team", "opponent", expected)
}

func (d *MCPDriver) ConfirmMatchStatistics(expected []Expectation) {
	d.t.Helper()
	matches := d.list(d.last.Structured, "matches")
	if len(matches) == 0 {
		d.t.Fatalf("no matches to show statistics for")
	}
	stats, ok := matches[0]["statistics"].(map[string]any)
	if !ok {
		d.t.Fatalf("the match has no statistics:\n%s", d.last.Text)
	}
	for _, e := range expected {
		want := e.Value
		got := fmt.Sprintf("%v-%v", num(stats["home_"+e.Fact]), num(stats["away_"+e.Fact]))
		if got != want {
			d.t.Fatalf("expected %s %s, got %s", e.Fact, want, got)
		}
	}
}

func (d *MCPDriver) ConfirmNoMatchesFound() {
	d.t.Helper()
	if got := d.intField(d.last.Structured, "total"); got != 0 {
		d.t.Fatalf("expected no matches, the system found %d", got)
	}
}

func (d *MCPDriver) ConfirmNoDuplicateMatches() {
	d.t.Helper()
	seen := map[string]bool{}
	for _, line := range d.matchLines("matches") {
		if seen[line] {
			d.t.Fatalf("the match %q is listed more than once", line)
		}
		seen[line] = true
	}
}

// ---- teams -----------------------------------------------------------------

func (d *MCPDriver) TeamRecord(team string, c map[string]string) {
	d.t.Helper()
	args := map[string]any{"team": team}
	copyText(args, c, "competition", "competition")
	copyText(args, c, "venue", "venue")
	copyNumber(d.t, args, c, "season", "season")
	d.ask("team_record", args)
}

func (d *MCPDriver) TeamOverview(team string) {
	d.t.Helper()
	d.ask("team_overview", map[string]any{"team": team})
}

func (d *MCPDriver) HeadToHead(teamA, teamB string, c map[string]string) {
	d.t.Helper()
	args := map[string]any{"team_a": teamA, "team_b": teamB}
	copyText(args, c, "competition", "competition")
	copyNumber(d.t, args, c, "season", "season")
	d.ask("head_to_head", args)
}

func (d *MCPDriver) RankTeams(c map[string]string) {
	d.t.Helper()
	metrics := map[string]string{
		"goals scored": "goals_for", "goals conceded": "goals_against", "win rate": "win_rate",
		"points": "points", "wins": "wins", "goal difference": "goal_difference",
	}
	metric, ok := metrics[strings.ToLower(c["by"])]
	if !ok {
		d.t.Fatalf("cannot rank teams by %q", c["by"])
	}
	args := map[string]any{"metric": metric}
	copyText(args, c, "competition", "competition")
	copyText(args, c, "venue", "venue")
	copyNumber(d.t, args, c, "season", "season")
	copyNumber(d.t, args, c, "minimum matches", "min_matches")
	d.ask("rank_teams", args)
}

func (d *MCPDriver) CompetitionsPlayed(team string) {
	d.t.Helper()
	d.ask("team_competitions", map[string]any{"team": team})
}

func (d *MCPDriver) ConfirmRecord(expected []Expectation) {
	d.t.Helper()
	record := d.last.Structured
	if r, ok := record["record"].(map[string]any); ok {
		record = r
	}
	d.confirmFacts(record, expected)
}

func (d *MCPDriver) ConfirmHeadToHead(expected []Expectation) {
	d.t.Helper()
	d.confirmTeamFacts(d.last.Structured, "team_a", "team_b", expected)
}

func (d *MCPDriver) ConfirmRankedFirst(team string, expected []Expectation) {
	d.t.Helper()
	ranking := d.list(d.last.Structured, "ranking")
	if len(ranking) == 0 {
		d.t.Fatalf("the ranking is empty:\n%s", d.last.Text)
	}
	if !sameName(str(ranking[0]["team"]), team) {
		d.t.Fatalf("expected %s to be ranked first, but it was %s:\n%s", team, str(ranking[0]["team"]), d.last.Text)
	}
	d.confirmFacts(ranking[0], expected)
}

func (d *MCPDriver) ConfirmCompetitionsPlayed(names ...string) {
	d.t.Helper()
	var got []string
	for _, c := range d.list(d.last.Structured, "competitions") {
		got = append(got, str(c["competition"]))
	}
	if len(got) != len(names) {
		d.t.Fatalf("expected competitions %v, got %v", names, got)
	}
	for _, n := range names {
		if !containsName(got, n) {
			d.t.Fatalf("expected competitions %v, got %v", names, got)
		}
	}
}

func (d *MCPDriver) ConfirmSquad(expected []Expectation) {
	d.t.Helper()
	squad, ok := d.last.Structured["squad"].(map[string]any)
	if !ok {
		d.t.Fatalf("the answer says nothing about the squad:\n%s", d.last.Text)
	}
	d.confirmFacts(squad, expected)
}

// ---- players ---------------------------------------------------------------

func (d *MCPDriver) FindPlayers(c map[string]string) {
	d.t.Helper()
	args := map[string]any{}
	copyText(args, c, "name", "name")
	copyText(args, c, "nationality", "nationality")
	copyText(args, c, "club", "club")
	copyText(args, c, "position", "position")
	copyNumber(d.t, args, c, "minimum rating", "min_overall")
	copyNumber(d.t, args, c, "limit", "limit")
	d.ask("search_players", args)
}

func (d *MCPDriver) BrazilianPlayersAtBrazilianClubs() {
	d.t.Helper()
	d.ask("players_by_club", map[string]any{"nationality": "Brazil", "brazilian_clubs_only": true})
}

func (d *MCPDriver) playerNames(field string) []string {
	var names []string
	for _, p := range d.list(d.last.Structured, field) {
		names = append(names, str(p["name"]))
	}
	return names
}

func (d *MCPDriver) ConfirmPlayersListed(names ...string) {
	d.t.Helper()
	got := d.playerNames("players")
	for _, n := range names {
		if !containsName(got, n) {
			d.t.Fatalf("expected %s among the players, got %v", n, got)
		}
	}
}

func (d *MCPDriver) ConfirmPlayersNotListed(names ...string) {
	d.t.Helper()
	got := d.playerNames("players")
	for _, n := range names {
		if containsName(got, n) {
			d.t.Fatalf("did not expect %s among the players %v", n, got)
		}
	}
}

func (d *MCPDriver) ConfirmPlayersInOrder(names ...string) {
	d.t.Helper()
	got := d.playerNames("players")
	if len(got) < len(names) {
		d.t.Fatalf("expected at least %v, got %v", names, got)
	}
	for i, n := range names {
		if !sameName(got[i], n) {
			d.t.Fatalf("expected players in the order %v, got %v", names, got)
		}
	}
}

func (d *MCPDriver) ConfirmPlayerDetails(name string, expected []Expectation) {
	d.t.Helper()
	for _, p := range d.list(d.last.Structured, "players") {
		if sameName(str(p["name"]), name) {
			d.confirmFacts(p, expected)
			return
		}
	}
	d.t.Fatalf("%s is not among the players", name)
}

func (d *MCPDriver) ConfirmPlayersSuggested(names ...string) {
	d.t.Helper()
	got := d.playerNames("suggestions")
	for _, n := range names {
		if !containsName(got, n) {
			d.t.Fatalf("expected %s to be suggested, suggestions were %v:\n%s", n, got, d.last.Text)
		}
	}
}

func (d *MCPDriver) clubSummary(club string) map[string]any {
	for _, c := range d.list(d.last.Structured, "clubs") {
		if sameName(str(c["club"]), club) {
			return c
		}
	}
	return nil
}

func (d *MCPDriver) ConfirmClubSummary(club string, expected []Expectation) {
	d.t.Helper()
	c := d.clubSummary(club)
	if c == nil {
		d.t.Fatalf("%s is not in the club summary:\n%s", club, d.last.Text)
	}
	d.confirmFacts(c, expected)
}

func (d *MCPDriver) ConfirmClubNotSummarised(club string) {
	d.t.Helper()
	if d.clubSummary(club) != nil {
		d.t.Fatalf("did not expect %s in the club summary", club)
	}
}

// ---- competitions ----------------------------------------------------------

func (d *MCPDriver) Standings(c map[string]string) {
	d.t.Helper()
	args := map[string]any{}
	copyText(args, c, "competition", "competition")
	copyNumber(d.t, args, c, "season", "season")
	d.ask("standings", args)
}

func (d *MCPDriver) Bracket(c map[string]string) {
	d.t.Helper()
	args := map[string]any{}
	copyText(args, c, "competition", "competition")
	copyNumber(d.t, args, c, "season", "season")
	d.ask("knockout_bracket", args)
}

func (d *MCPDriver) ConfirmChampion(team string, expected []Expectation) {
	d.t.Helper()
	if !sameName(str(d.last.Structured["champion"]), team) {
		d.t.Fatalf("expected %s to be champion, got %v:\n%s", team, d.last.Structured["champion"], d.last.Text)
	}
	table := d.list(d.last.Structured, "table")
	d.confirmFacts(table[0], expected)
}

func (d *MCPDriver) ConfirmFinishingOrder(teams ...string) {
	d.t.Helper()
	var got []string
	for _, row := range d.list(d.last.Structured, "table") {
		got = append(got, str(row["team"]))
	}
	if len(got) < len(teams) {
		d.t.Fatalf("expected the table to start %v, got %v", teams, got)
	}
	for i, team := range teams {
		if !sameName(got[i], team) {
			d.t.Fatalf("expected the table to start %v, got %v", teams, got)
		}
	}
}

func (d *MCPDriver) ConfirmRelegated(teams ...string) {
	d.t.Helper()
	got := strs(d.last.Structured["relegated"])
	if len(got) != len(teams) {
		d.t.Fatalf("expected %v to be relegated, got %v", teams, got)
	}
	for _, team := range teams {
		if !containsName(got, team) {
			d.t.Fatalf("expected %v to be relegated, got %v", teams, got)
		}
	}
}

func (d *MCPDriver) ConfirmTeamsInTable(n int) {
	d.t.Helper()
	if got := len(d.list(d.last.Structured, "table")); got != n {
		d.t.Fatalf("expected %d teams in the table, got %d", n, got)
	}
}

func (d *MCPDriver) stage(name string) map[string]any {
	for _, s := range d.list(d.last.Structured, "stages") {
		if fold(str(s["stage"])) == fold(name) {
			return s
		}
	}
	return nil
}

func (d *MCPDriver) ConfirmTie(stage string, expected []Expectation) {
	d.t.Helper()
	s := d.stage(stage)
	if s == nil {
		d.t.Fatalf("the bracket has no %s:\n%s", stage, d.last.Text)
	}
	var winner, aggregate string
	for _, e := range expected {
		switch e.Fact {
		case "winner":
			winner = e.Value
		case "aggregate":
			aggregate = e.Value
		}
	}
	var described []string
	for _, tie := range d.list(s, "ties") {
		a, b := str(tie["team_a"]), str(tie["team_b"])
		ga, gb := num(tie["team_a_goals"]), num(tie["team_b_goals"])
		forward := fmt.Sprintf("%s %v-%v %s", a, ga, gb, b)
		reverse := fmt.Sprintf("%s %v-%v %s", b, gb, ga, a)
		described = append(described, forward+" (winner "+str(tie["winner"])+")")
		if aggregate != "" && fold(aggregate) != fold(forward) && fold(aggregate) != fold(reverse) {
			continue
		}
		if winner != "" && !sameName(str(tie["winner"]), winner) {
			continue
		}
		return
	}
	d.t.Fatalf("expected a %s tie won by %q with aggregate %q, ties were %v", stage, winner, aggregate, described)
}

func (d *MCPDriver) ConfirmNoStage(stage string) {
	d.t.Helper()
	if d.stage(stage) != nil {
		d.t.Fatalf("did not expect the %s in the knockout bracket", stage)
	}
}

// ---- statistics ------------------------------------------------------------

func (d *MCPDriver) CompetitionStatistics(c map[string]string) {
	d.t.Helper()
	args := map[string]any{}
	copyText(args, c, "competition", "competition")
	copyNumber(d.t, args, c, "season", "season")
	d.ask("competition_stats", args)
}

func (d *MCPDriver) BiggestWins(c map[string]string) {
	d.t.Helper()
	args := map[string]any{"limit": 10}
	copyText(args, c, "competition", "competition")
	copyText(args, c, "team", "team")
	copyNumber(d.t, args, c, "season", "season")
	d.ask("biggest_wins", args)
}

func (d *MCPDriver) CompareSeasons(c map[string]string, seasons ...string) {
	d.t.Helper()
	var list []any
	for _, s := range seasons {
		n, err := strconv.Atoi(s)
		if err != nil {
			d.t.Fatalf("%q is not a season", s)
		}
		list = append(list, n)
	}
	args := map[string]any{"seasons": list}
	copyText(args, c, "competition", "competition")
	d.ask("compare_seasons", args)
}

func (d *MCPDriver) Derbies(c map[string]string) {
	d.t.Helper()
	args := map[string]any{}
	copyText(args, c, "competition", "competition")
	copyNumber(d.t, args, c, "season", "season")
	d.ask("derbies", args)
}

func (d *MCPDriver) ConfirmStatistics(expected []Expectation) {
	d.t.Helper()
	d.confirmFacts(d.last.Structured, expected)
}

func (d *MCPDriver) ConfirmWinsInOrder(lines ...string) {
	d.t.Helper()
	got := d.matchLines("matches")
	if len(got) < len(lines) {
		d.t.Fatalf("expected at least %d wins, got %v", len(lines), got)
	}
	for i, l := range lines {
		if !strings.Contains(fold(got[i]), fold(l)) {
			d.t.Fatalf("expected the biggest wins to be %v, got %v", lines, got)
		}
	}
}

func (d *MCPDriver) ConfirmSeason(season string, expected []Expectation) {
	d.t.Helper()
	for _, s := range d.list(d.last.Structured, "seasons") {
		if fmt.Sprint(num(s["season"])) == season {
			d.confirmFacts(s, expected)
			return
		}
	}
	d.t.Fatalf("the comparison does not include %s:\n%s", season, d.last.Text)
}

func (d *MCPDriver) ConfirmDerbies(names ...string) {
	d.t.Helper()
	var got []string
	for _, m := range d.list(d.last.Structured, "derbies") {
		got = append(got, str(m["derby"]))
	}
	for _, n := range names {
		if !containsName(got, n) {
			d.t.Fatalf("expected a %s, derbies found were %v", n, got)
		}
	}
}

func (d *MCPDriver) ConfirmDerbyCount(n int) {
	d.t.Helper()
	if got := d.intField(d.last.Structured, "total"); got != n {
		d.t.Fatalf("expected %d derbies, found %d:\n%s", n, got, d.last.Text)
	}
}

// ---- datasets and experience -----------------------------------------------

func (d *MCPDriver) ListDatasets() {
	d.t.Helper()
	d.ask("list_datasets", map[string]any{})
}

func (d *MCPDriver) ConfirmDatasetLoaded(dataset string, expected []Expectation) {
	d.t.Helper()
	file := datasetFile(dataset)
	for _, ds := range d.list(d.last.Structured, "datasets") {
		if str(ds["file"]) == file {
			if ds["loaded"] != true {
				d.t.Fatalf("the %s were not loaded: %v", dataset, ds["error"])
			}
			d.confirmFacts(ds, expected)
			return
		}
	}
	d.t.Fatalf("the system does not know about the %s", dataset)
}

func (d *MCPDriver) ConfirmAnsweredWithin(limit time.Duration) {
	d.t.Helper()
	if d.last.Duration > limit {
		d.t.Fatalf("%s took %v to answer; expected under %v", d.tool, d.last.Duration, limit)
	}
}

// ---- helpers ---------------------------------------------------------------

func (d *MCPDriver) matchLines(field string) []string {
	var lines []string
	for _, m := range d.list(d.last.Structured, field) {
		lines = append(lines, fmt.Sprintf("%s: %s %v-%v %s", str(m["date"]), str(m["home"]), num(m["home_goals"]), num(m["away_goals"]), str(m["away"])))
	}
	return lines
}

func (d *MCPDriver) confirmLinesIn(got []string, want ...string) {
	d.t.Helper()
	for _, w := range want {
		found := false
		for _, g := range got {
			if strings.Contains(fold(g), fold(w)) {
				found = true
				break
			}
		}
		if !found {
			d.t.Fatalf("expected to see %q, the answer was:\n%s", w, d.last.Text)
		}
	}
}

// confirmTeamFacts checks facts such as "Flamengo wins: 2" against an answer
// that describes two teams under the given fields.
func (d *MCPDriver) confirmTeamFacts(obj map[string]any, fieldA, fieldB string, expected []Expectation) {
	d.t.Helper()
	teamA, teamB := str(obj[fieldA]), str(obj[fieldB])
	var plain []Expectation
	for _, e := range expected {
		resolved := false
		for _, suffix := range []string{"wins", "goals"} {
			if team, ok := strings.CutSuffix(e.Fact, " "+suffix); ok {
				switch {
				case sameName(team, teamA):
					plain = append(plain, Expectation{Fact: fieldA + "_" + suffix, Value: e.Value})
				case sameName(team, teamB):
					plain = append(plain, Expectation{Fact: fieldB + "_" + suffix, Value: e.Value})
				default:
					d.t.Fatalf("the answer compares %s and %s, not %s", teamA, teamB, team)
				}
				resolved = true
			}
		}
		if !resolved {
			plain = append(plain, e)
		}
	}
	d.confirmFacts(obj, plain)
}

var factFields = map[string]string{
	"average rating": "average_overall",
	"rating":         "overall",
}

// confirmFacts compares each expected fact with the matching answer field.
// Numbers match to the precision the test case states them with.
func (d *MCPDriver) confirmFacts(obj map[string]any, expected []Expectation) {
	d.t.Helper()
	for _, e := range expected {
		field, ok := factFields[e.Fact]
		if !ok {
			field = strings.ReplaceAll(e.Fact, " ", "_")
		}
		got, present := obj[field]
		if !present {
			d.t.Fatalf("the answer does not mention %s:\n%s", e.Fact, d.last.Text)
		}
		if !matchesValue(got, e.Value) {
			d.t.Fatalf("expected %s to be %s, but it was %v:\n%s", e.Fact, e.Value, num(got), d.last.Text)
		}
	}
}

func matchesValue(got any, want string) bool {
	if f, ok := got.(float64); ok {
		w, err := strconv.ParseFloat(want, 64)
		if err != nil {
			return false
		}
		decimals := 0
		if i := strings.Index(want, "."); i >= 0 {
			decimals = len(want) - i - 1
		}
		return math.Abs(f-w) <= 0.5*math.Pow(10, -float64(decimals))+1e-9
	}
	return sameName(fmt.Sprint(got), want)
}

func (d *MCPDriver) list(obj map[string]any, field string) []map[string]any {
	d.t.Helper()
	raw, ok := obj[field].([]any)
	if !ok {
		if obj[field] == nil {
			return nil
		}
		d.t.Fatalf("expected a list of %s in the answer", field)
	}
	out := make([]map[string]any, 0, len(raw))
	for _, r := range raw {
		if m, ok := r.(map[string]any); ok {
			out = append(out, m)
		}
	}
	return out
}

func (d *MCPDriver) intField(obj map[string]any, field string) int {
	d.t.Helper()
	f, ok := obj[field].(float64)
	if !ok {
		d.t.Fatalf("the answer does not say how many %s:\n%s", field, d.last.Text)
	}
	return int(f)
}

func copyText(args map[string]any, c map[string]string, from, to string) {
	if v, ok := c[from]; ok {
		args[to] = v
	}
}

func copyNumber(t *testing.T, args map[string]any, c map[string]string, from, to string) {
	t.Helper()
	if v, ok := c[from]; ok {
		n, err := strconv.Atoi(v)
		if err != nil {
			t.Fatalf("%s should be a number, got %q", from, v)
		}
		args[to] = n
	}
}

func str(v any) string {
	if v == nil {
		return ""
	}
	return fmt.Sprint(v)
}

func num(v any) any {
	if f, ok := v.(float64); ok && f == math.Trunc(f) {
		return int(f)
	}
	return v
}

func strs(v any) []string {
	raw, _ := v.([]any)
	out := make([]string, 0, len(raw))
	for _, r := range raw {
		out = append(out, str(r))
	}
	return out
}

func keys(m map[string]bool) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}

func containsName(list []string, name string) bool {
	for _, l := range list {
		if sameName(l, name) {
			return true
		}
	}
	return false
}

func sameName(a, b string) bool { return fold(a) == fold(b) }

// fold makes names comparable regardless of case and accents.
func fold(s string) string {
	return accents.Replace(strings.ToLower(strings.TrimSpace(s)))
}

var accents = strings.NewReplacer(
	"á", "a", "à", "a", "â", "a", "ã", "a", "ä", "a",
	"é", "e", "è", "e", "ê", "e", "ë", "e",
	"í", "i", "ì", "i", "î", "i", "ï", "i",
	"ó", "o", "ò", "o", "ô", "o", "õ", "o", "ö", "o",
	"ú", "u", "ù", "u", "û", "u", "ü", "u",
	"ç", "c", "ñ", "n",
)
