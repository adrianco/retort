// Package mcpserver exposes the Brazilian soccer knowledge graph over the Model
// Context Protocol using the official Go SDK.
//
// server.go wires the server together: it registers the fifteen tools defined in
// tools.go, five read-only resources that let a client browse the data without
// calling a tool, and three prompt templates for common analyses. The graph is
// loaded once and shared by every request; it is immutable after loading, so no
// locking is needed.
package mcpserver

import (
	"context"
	"fmt"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Version is reported to clients during initialization.
const Version = "1.0.0"

// Server couples an MCP server with the knowledge graph it queries.
type Server struct {
	graph *soccer.Graph
	mcp   *mcp.Server
}

// instructions tell the connected model what this server is for and how to get
// good answers out of it.
const instructions = `This server answers natural language questions about Brazilian soccer from six
Kaggle datasets: Brasileirão Série A (2003-2023), Série B and C (2014-2023),
Copa do Brasil (2012-2023), Copa Libertadores (2013-2022) and a FIFA player
database of 18,207 players.

Guidance:
  - Club names may be given in any form found in the data: "Palmeiras",
    "Palmeiras-SP", "Palmeiras - SP", nicknames such as "Timão" or "Galo", and
    accents are optional. Use list_teams when a name is ambiguous.
  - Statistics are computed over a de-duplicated view of the matches: Série A
    2014-2019 appears in three source files and is counted once.
  - Standings, champions and relegation are calculated from match results, not
    read from a table, and every result reports whether the underlying season is
    complete.
  - The datasets contain no goalscorer, lineup or referee information. Do not
    guess: aggregate_stats and competition_summary report per-team scoring
    instead, and say so.
  - Start with dataset_info if you need to know exactly what is covered.`

// New loads the graph from dataDir and builds a configured MCP server.
func New(dataDir string) (*Server, error) {
	graph, err := soccer.Load(dataDir)
	if err != nil {
		return nil, err
	}
	return NewWithGraph(graph), nil
}

// NewWithGraph builds a server around an already loaded graph, which is what the
// tests use to avoid reloading the CSVs for every case.
func NewWithGraph(graph *soccer.Graph) *Server {
	s := &Server{graph: graph}
	s.mcp = mcp.NewServer(
		&mcp.Implementation{
			Name:    "brazilian-soccer",
			Title:   "Brazilian Soccer Knowledge Graph",
			Version: Version,
		},
		&mcp.ServerOptions{Instructions: instructions},
	)
	s.registerTools()
	s.registerResources()
	s.registerPrompts()
	return s
}

// MCP returns the underlying protocol server.
func (s *Server) MCP() *mcp.Server { return s.mcp }

// Graph returns the knowledge graph the server queries.
func (s *Server) Graph() *soccer.Graph { return s.graph }

// Run serves the protocol over the given transport until the client goes away.
func (s *Server) Run(ctx context.Context, t mcp.Transport) error { return s.mcp.Run(ctx, t) }

// textResult wraps a rendered report as the unstructured half of a tool result.
// The SDK fills in the structured half from the typed return value.
func textResult(text string) *mcp.CallToolResult {
	return &mcp.CallToolResult{Content: []mcp.Content{&mcp.TextContent{Text: text}}}
}

// registerResources publishes browsable, read-only views of the graph.
func (s *Server) registerResources() {
	add := func(uri, name, description, mime string, body func() string) {
		s.mcp.AddResource(
			&mcp.Resource{URI: uri, Name: name, Description: description, MIMEType: mime},
			func(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
				return &mcp.ReadResourceResult{Contents: []*mcp.ResourceContents{{
					URI: uri, MIMEType: mime, Text: body(),
				}}}, nil
			})
	}

	add("soccer://datasets", "Datasets",
		"Provenance, licences, row counts and known gaps for the six source files.",
		"text/markdown", func() string {
			return soccer.FormatDatasetInfo(s.graph.DatasetInfo())
		})

	add("soccer://teams", "Team directory",
		"Every club in the knowledge graph with its canonical id, name variants and match count.",
		"text/markdown", func() string {
			entries := s.graph.ListTeams("", 0)
			return soccer.FormatTeamList(entries, len(entries))
		})

	add("soccer://competitions", "Competition coverage",
		"Seasons available per competition and the champion computed for each.",
		"text/markdown", func() string {
			var b strings.Builder
			for _, c := range soccer.AllCompetitions {
				seasons := s.graph.Seasons(c)
				fmt.Fprintf(&b, "## %s\n\n", c)
				if len(seasons) == 0 {
					b.WriteString("No data.\n\n")
					continue
				}
				fmt.Fprintf(&b, "Seasons %d-%d (%d seasons)\n\n", seasons[0], seasons[len(seasons)-1], len(seasons))
				b.WriteString(soccer.FormatChampions(s.graph.Champions(c, 0, 0)))
				b.WriteString("\n\n")
			}
			return b.String()
		})

	add("soccer://sample-questions", "Sample questions",
		"Worked examples showing which tool answers which kind of question.",
		"text/markdown", func() string { return sampleQuestionsDoc })

	add("soccer://tools", "Tool reference",
		"One line description of every tool this server exposes.",
		"text/markdown", func() string {
			var b strings.Builder
			b.WriteString("# Tools\n\n")
			for _, t := range toolCatalog {
				fmt.Fprintf(&b, "- **%s**: %s\n", t.name, t.summary)
			}
			return b.String()
		})
}

// registerPrompts publishes reusable analysis templates.
func (s *Server) registerPrompts() {
	s.mcp.AddPrompt(&mcp.Prompt{
		Name:        "club_report",
		Description: "Produce a full report on one club: record, competitions, titles, rivalries and squad.",
		Arguments: []*mcp.PromptArgument{
			{Name: "club", Description: "Club name, e.g. Palmeiras or Atlético-MG", Required: true},
		},
	}, func(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		club := req.Params.Arguments["club"]
		return &mcp.GetPromptResult{
			Description: "Club report for " + club,
			Messages: []*mcp.PromptMessage{{
				Role: "user",
				Content: &mcp.TextContent{Text: fmt.Sprintf(
					"Write a report on %s using the brazilian-soccer tools. Call team_profile for the overview, "+
						"team_stats for the win/draw/loss record, list_derbies for the rivalries and search_players "+
						"for the squad. Quote concrete numbers and say explicitly which seasons the data covers.", club)},
			}},
		}, nil
	})

	s.mcp.AddPrompt(&mcp.Prompt{
		Name:        "season_review",
		Description: "Review one season of a competition: table, champion, relegation and statistics.",
		Arguments: []*mcp.PromptArgument{
			{Name: "competition", Description: "Brasileirão Série A, Série B, Série C, Copa do Brasil or Copa Libertadores", Required: true},
			{Name: "season", Description: "Four digit year, e.g. 2019", Required: true},
		},
	}, func(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		comp := req.Params.Arguments["competition"]
		season := req.Params.Arguments["season"]
		return &mcp.GetPromptResult{
			Description: fmt.Sprintf("Season review: %s %s", comp, season),
			Messages: []*mcp.PromptMessage{{
				Role: "user",
				Content: &mcp.TextContent{Text: fmt.Sprintf(
					"Review the %s %s season. Use competition_summary for the headline numbers, standings (or "+
						"competition_bracket for a cup) for the classification, and aggregate_stats for goals and "+
						"home advantage. Note whether the season is complete in the data before naming a champion.",
					season, comp)},
			}},
		}, nil
	})

	s.mcp.AddPrompt(&mcp.Prompt{
		Name:        "compare_clubs",
		Description: "Compare two clubs head-to-head and by overall record.",
		Arguments: []*mcp.PromptArgument{
			{Name: "team_a", Description: "First club", Required: true},
			{Name: "team_b", Description: "Second club", Required: true},
		},
	}, func(ctx context.Context, req *mcp.GetPromptRequest) (*mcp.GetPromptResult, error) {
		a, b := req.Params.Arguments["team_a"], req.Params.Arguments["team_b"]
		return &mcp.GetPromptResult{
			Description: fmt.Sprintf("Compare %s and %s", a, b),
			Messages: []*mcp.PromptMessage{{
				Role: "user",
				Content: &mcp.TextContent{Text: fmt.Sprintf(
					"Compare %s and %s. Call head_to_head for the direct record and team_stats for each club, then "+
						"say who has the better overall record and how the head-to-head splits home and away.", a, b)},
			}},
		}, nil
	})
}

// sampleQuestionsDoc is served as a resource and doubles as documentation of
// which tool answers which question.
const sampleQuestionsDoc = `# Sample questions

| Question | Tool | Arguments |
|---|---|---|
| Show me all Flamengo vs Fluminense matches | head_to_head | team_a=Flamengo, team_b=Fluminense |
| What matches did Palmeiras play in 2023? | search_matches | team=Palmeiras, season=2023 |
| Find all Copa do Brasil finals | search_matches | competition=Copa do Brasil, stage=final |
| When did Flamengo last play Corinthians? | head_to_head | team_a=Flamengo, team_b=Corinthians, limit=1 |
| What is Corinthians' home record in 2022? | team_stats | team=Corinthians, season=2022, venue=home |
| Which team scored the most goals in Série A 2023? | team_rankings | metric=most_goals_scored, competition=Série A, season=2023 |
| Compare Palmeiras and Santos head-to-head | head_to_head | team_a=Palmeiras, team_b=Santos |
| Who won the 2019 Brasileirão? | champions | competition=Série A, season_from=2019, season_to=2019 |
| Which teams were relegated in 2020? | standings | competition=Série A, season=2020 |
| Show the 2018 Copa Libertadores bracket | competition_bracket | competition=Libertadores, season=2018 |
| What is the average goals per match in the Brasileirão? | aggregate_stats | competition=Série A |
| Which team has the best away record? | team_rankings | metric=best_win_rate, venue=away |
| Show me the biggest wins in the dataset | aggregate_stats | top=10 |
| Find all Brazilian players | search_players | nationality=Brazil, group_by_club=true |
| Who are the highest rated players at Fluminense? | search_players | club=Fluminense |
| Show me all forwards from Santos | search_players | club=Santos, position=forward |
| Who is Gabriel Barbosa? | player_profile | name=Gabriel Barbosa |
| Which players play for Grêmio? | team_profile | team=Grêmio |
| Show me all derbies in 2023 | list_derbies | season=2023 |
| What competitions has Palmeiras played in? | team_profile | team=Palmeiras |
| Compare the 2018 and 2019 seasons | competition_summary | competition=Série A, seasons=[2018,2019] |
| Where does this data come from? | dataset_info | |
`
