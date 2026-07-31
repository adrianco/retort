// main_test.go covers the command line entry points: the demo question list
// must stay in step with the tool surface, and the -call and -demo paths must
// work end to end over a real MCP session.
package main

import (
	"context"
	"strings"
	"testing"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpserver"
)

func newServer(t *testing.T) *mcpserver.Server {
	t.Helper()
	srv, err := mcpserver.New("")
	if err != nil {
		t.Fatalf("loading the datasets: %v", err)
	}
	return srv
}

func TestDemoQuestionsAllAnswer(t *testing.T) {
	if len(demoQuestions) < 10 {
		t.Fatalf("only %d demo questions", len(demoQuestions))
	}
	srv := newServer(t)
	ctx := context.Background()
	session, err := connectLoopback(ctx, srv)
	if err != nil {
		t.Fatal(err)
	}
	defer session.Close()

	available := map[string]bool{}
	for tool, err := range session.Tools(ctx, nil) {
		if err != nil {
			t.Fatal(err)
		}
		available[tool.Name] = true
	}
	for _, q := range demoQuestions {
		if !available[q.Tool] {
			t.Errorf("demo question %q calls unknown tool %q", q.Question, q.Tool)
		}
	}
	if err := runDemo(ctx, srv); err != nil {
		t.Errorf("running the demo: %v", err)
	}
}

func TestCallToolCLI(t *testing.T) {
	srv := newServer(t)
	ctx := context.Background()
	if err := callTool(ctx, srv, "standings", `{"season":2019}`); err != nil {
		t.Errorf("calling standings: %v", err)
	}
	// A tool error must be surfaced to the shell as a non-nil error.
	err := callTool(ctx, srv, "team_stats", `{"team":"Manchester United"}`)
	if err == nil {
		t.Error("expected an error for a club that is not in the data")
	}
	// Malformed JSON must be reported clearly.
	err = callTool(ctx, srv, "standings", `{season:2019}`)
	if err == nil || !strings.Contains(err.Error(), "parsing -args") {
		t.Errorf("expected a JSON parse error, got %v", err)
	}
}
