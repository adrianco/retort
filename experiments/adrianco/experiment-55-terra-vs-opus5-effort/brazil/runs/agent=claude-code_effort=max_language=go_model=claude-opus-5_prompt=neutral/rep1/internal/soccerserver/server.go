// server.go assembles the MCP server: 20 tools, five resources, five prompt
// templates and argument completion, all backed by one loaded soccer.Store.
package soccerserver

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// ServerName and ServerVersion identify this implementation to clients.
const (
	ServerName    = "brazilian-soccer"
	ServerVersion = "1.0.0"
)

// New builds an MCP server over an already loaded store.
func New(store *soccer.Store) *mcp.Server {
	a := &api{store: store}
	s := mcp.NewServer(ServerName, ServerVersion)
	s.Title = "Brazilian Soccer Knowledge Graph"
	s.Instructions = a.instructions()

	for _, tool := range []*mcp.Tool{
		a.listDatasetsTool(),
		a.listCompetitionsTool(),
		a.listTeamsTool(),
		a.teamProfileTool(),
		a.searchMatchesTool(),
		a.matchDetailsTool(),
		a.headToHeadTool(),
		a.teamStatsTool(),
		a.standingsTool(),
		a.seasonSummaryTool(),
		a.compareSeasonsTool(),
		a.leagueStatisticsTool(),
		a.biggestWinsTool(),
		a.bestRecordsTool(),
		a.findDerbiesTool(),
		a.searchPlayersTool(),
		a.playerProfileTool(),
		a.clubSquadsTool(),
		a.graphNeighborsTool(),
		a.graphPathTool(),
	} {
		s.AddTool(tool)
	}

	a.addResources(s)
	a.addPrompts(s)
	s.SetCompletion(a.complete)
	return s
}

// instructions is the server-level guidance handed to the model at
// initialisation: what the data covers and, just as importantly, what it does
// not.
func (a *api) instructions() string {
	sum := a.store.Summary()
	first, last := a.store.DateRange()
	var b strings.Builder
	fmt.Fprintf(&b, "Knowledge graph of Brazilian football built from six Kaggle CSVs: %d matches (%s to %s), %d clubs and %d FIFA player records, linked into %d graph nodes.\n\n",
		sum.Matches, first.Format("2006-01-02"), last.Format("2006-01-02"), sum.Teams, sum.Players, sum.GraphNodes)
	b.WriteString("Coverage:\n")
	for _, c := range a.store.CompetitionsWithData() {
		seasons := a.store.Seasons(c.ID)
		fmt.Fprintf(&b, "- %s: %d-%d (%d matches)\n", c.Name, seasons[0], seasons[len(seasons)-1], sum.PerComp[c.ID])
	}
	b.WriteString(`
How to use it:
- Club names are normalised, so "Flamengo", "Flamengo-RJ" and "Clube de Regatas do Flamengo" all resolve to the same club; ambiguous names such as "América" or "Botafogo-PB" are reported back with the candidates.
- Standings, records and averages are computed from the match results, not stored, so they only describe the seasons present here.
- Prefer head_to_head for two clubs, standings or season_summary for a season, team_stats for one club's record and league_statistics for averages.
- Call list_datasets when you need to know what can be answered before promising an answer.

Limitations to be honest about:
- There are no goalscorer, assist, lineup, card or attendance columns anywhere in the data, so individual scoring questions cannot be answered.
- The player file is a single FIFA 19 snapshot. Its Brazilian league squads use placeholder names, and Flamengo, Palmeiras, Corinthians, São Paulo and Vasco have no squad in it at all.
- Copa do Brasil rounds are labelled from the fixture ladder, and the 2022-2023 finals are inferred from the schedule; they are marked as inferred.
`)
	return b.String()
}

// ---------------------------------------------------------------------------
// Resources
// ---------------------------------------------------------------------------

func (a *api) addResources(s *mcp.Server) {
	s.AddResource(&mcp.Resource{
		URI:         "soccer://datasets",
		Name:        "datasets",
		Title:       "Dataset coverage",
		Description: "Which CSVs are loaded, their licences and what they cover.",
		MIMEType:    "text/plain",
		Reader: func() (string, error) {
			res, err := a.listDatasets(mcp.Args{})
			if err != nil {
				return "", err
			}
			return res.Content[0].Text, nil
		},
	})
	s.AddResource(&mcp.Resource{
		URI:         "soccer://teams",
		Name:        "teams",
		Title:       "Club catalogue",
		Description: "Every canonical club with its id, state, spellings and match count.",
		MIMEType:    "application/json",
		Reader: func() (string, error) {
			teams := a.store.Teams.Teams()
			return toJSON(teams)
		},
	})
	s.AddResource(&mcp.Resource{
		URI:         "soccer://competitions",
		Name:        "competitions",
		Title:       "Competitions and seasons",
		Description: "Competitions with the seasons and match counts available.",
		MIMEType:    "application/json",
		Reader: func() (string, error) {
			var out []map[string]any
			for _, c := range a.store.CompetitionsWithData() {
				out = append(out, map[string]any{
					"id": c.ID, "name": c.Name, "kind": c.Kind,
					"seasons": a.store.Seasons(c.ID),
					"matches": len(a.store.CompetitionMatches(c.ID)),
				})
			}
			return toJSON(out)
		},
	})
	s.AddResource(&mcp.Resource{
		URI:         "soccer://graph/schema",
		Name:        "graph_schema",
		Title:       "Knowledge graph schema",
		Description: "Node and edge types, with counts.",
		MIMEType:    "text/plain",
		Reader: func() (string, error) {
			var b strings.Builder
			b.WriteString(graphSchemaText + "\n\nNodes:\n")
			writeCounts(&b, a.store.Graph.CountsByType())
			b.WriteString("\nEdges:\n")
			writeCounts(&b, a.store.Graph.EdgeCountsByType())
			return b.String(), nil
		},
	})
	s.AddResource(&mcp.Resource{
		URI:         "soccer://sample-questions",
		Name:        "sample_questions",
		Title:       "Sample questions",
		Description: "Questions this server can answer, with the tool call that answers each.",
		MIMEType:    "text/plain",
		Reader: func() (string, error) {
			var b strings.Builder
			b.WriteString("Questions this knowledge graph can answer:\n\n")
			for i, q := range SampleQuestions {
				args, _ := json.Marshal(q.Args)
				fmt.Fprintf(&b, "%2d. %s\n    -> %s %s\n", i+1, q.Question, q.Tool, args)
			}
			return b.String(), nil
		},
	})
}

func writeCounts(b *strings.Builder, counts map[string]int) {
	keys := make([]string, 0, len(counts))
	for k := range counts {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		fmt.Fprintf(b, "- %-14s %d\n", k, counts[k])
	}
}

func toJSON(v any) (string, error) {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return "", err
	}
	return string(b), nil
}

// ---------------------------------------------------------------------------
// Prompts
// ---------------------------------------------------------------------------

func (a *api) addPrompts(s *mcp.Server) {
	s.AddPrompt(&mcp.Prompt{
		Name:        "club_dossier",
		Title:       "Club dossier",
		Description: "Research one club: record, competitions, derbies and squad.",
		Arguments: []mcp.PromptArgument{
			{Name: "team", Description: "Club name, e.g. Flamengo", Required: true},
		},
		Render: func(args map[string]string) (string, string, error) {
			team := args["team"]
			return fmt.Sprintf("Dossier for %s", team), fmt.Sprintf(
				"Build a dossier on %s using the Brazilian soccer knowledge graph.\n\n"+
					"1. Call team_profile with team=%q for the identity, record and squad.\n"+
					"2. Call team_stats for the home/away split, and best_records to place the club against its rivals.\n"+
					"3. Call find_derbies with team=%q for the derby history.\n"+
					"Report only what the tools return, and say explicitly which seasons the data covers.",
				team, team, team), nil
		},
	})
	s.AddPrompt(&mcp.Prompt{
		Name:        "season_review",
		Title:       "Season review",
		Description: "Review one competition season: table, champion, relegation and statistics.",
		Arguments: []mcp.PromptArgument{
			{Name: "competition", Description: "brasileirao, serie-b, serie-c, copa-do-brasil or libertadores"},
			{Name: "season", Description: "Season year, e.g. 2019", Required: true},
		},
		Render: func(args map[string]string) (string, string, error) {
			comp := args["competition"]
			if comp == "" {
				comp = soccer.CompBrasileirao
			}
			return fmt.Sprintf("Review of %s %s", comp, args["season"]), fmt.Sprintf(
				"Review the %s %s season.\n\n"+
					"1. Call season_summary with competition=%q and season=%s.\n"+
					"2. For a league, quote the top four and the relegated clubs from the standings; for a cup, walk the bracket to the final.\n"+
					"3. Add the headline statistics (goals per match, home advantage) and the biggest wins.\n"+
					"Do not invent goalscorers: the data has none.",
				comp, args["season"], comp, args["season"]), nil
		},
	})
	s.AddPrompt(&mcp.Prompt{
		Name:        "derby_briefing",
		Title:       "Derby briefing",
		Description: "Brief on a rivalry between two clubs.",
		Arguments: []mcp.PromptArgument{
			{Name: "team_a", Description: "First club", Required: true},
			{Name: "team_b", Description: "Second club", Required: true},
		},
		Render: func(args map[string]string) (string, string, error) {
			return fmt.Sprintf("%s vs %s", args["team_a"], args["team_b"]), fmt.Sprintf(
				"Brief me on %s versus %s.\n\n"+
					"1. Call head_to_head with team_a=%q and team_b=%q.\n"+
					"2. Call search_matches for the five most recent meetings and quote the scores.\n"+
					"3. Mention the derby name if the tools report one, and the biggest win for each side.",
				args["team_a"], args["team_b"], args["team_a"], args["team_b"]), nil
		},
	})
	s.AddPrompt(&mcp.Prompt{
		Name:        "answer_question",
		Title:       "Answer a football question",
		Description: "Route a natural language question to the right tools.",
		Arguments: []mcp.PromptArgument{
			{Name: "question", Description: "The question to answer", Required: true},
		},
		Render: func(args map[string]string) (string, string, error) {
			return "Answer a Brazilian football question", fmt.Sprintf(
				"Answer this question from the Brazilian soccer knowledge graph: %q\n\n"+
					"Pick the tools by shape of question:\n"+
					"- two clubs -> head_to_head; one club's results -> search_matches or team_stats\n"+
					"- a season -> standings or season_summary; several seasons -> compare_seasons\n"+
					"- rankings -> best_records; averages -> league_statistics; extremes -> biggest_wins\n"+
					"- people -> search_players or player_profile; squads -> club_squads\n"+
					"- relationships -> graph_neighbors or graph_path\n"+
					"If a tool reports that the data does not cover something, say so instead of guessing.",
				args["question"]), nil
		},
	})
	s.AddPrompt(&mcp.Prompt{
		Name:        "sample_questions",
		Title:       "Sample questions",
		Description: "List questions this server can answer.",
		Render: func(map[string]string) (string, string, error) {
			var b strings.Builder
			b.WriteString("Here are questions the Brazilian soccer knowledge graph can answer:\n\n")
			for i, q := range SampleQuestions {
				fmt.Fprintf(&b, "%2d. %s\n", i+1, q.Question)
			}
			b.WriteString("\nPick one and answer it with the matching tool.")
			return "Sample questions", b.String(), nil
		},
	})
}

// complete supplies argument completions for prompts (club names, competitions
// and seasons).
func (a *api) complete(ref, argument, value string) []string {
	folded := soccer.Fold(value)
	switch argument {
	case "team", "team_a", "team_b":
		var out []string
		for _, t := range a.store.Teams.Teams() {
			if folded == "" || strings.HasPrefix(soccer.Fold(t.Name), folded) {
				out = append(out, t.Name)
			}
		}
		return out
	case "competition":
		var out []string
		for _, c := range a.store.CompetitionsWithData() {
			if folded == "" || strings.HasPrefix(soccer.Fold(c.ID), folded) || strings.HasPrefix(soccer.Fold(c.Short), folded) {
				out = append(out, c.ID)
			}
		}
		return out
	case "season":
		var out []string
		seen := map[int]bool{}
		for _, c := range a.store.CompetitionsWithData() {
			for _, season := range a.store.Seasons(c.ID) {
				if seen[season] {
					continue
				}
				seen[season] = true
				s := fmt.Sprint(season)
				if value == "" || strings.HasPrefix(s, value) {
					out = append(out, s)
				}
			}
		}
		sort.Strings(out)
		return out
	}
	return nil
}
