// Command brazilian-soccer-mcp serves the Brazilian soccer knowledge graph over
// the Model Context Protocol.
//
// By default it speaks MCP over stdin/stdout, which is what an MCP client such
// as Claude Desktop or Claude Code launches. Two other modes exist for
// development: -http starts the streamable HTTP transport, and -call runs a
// single tool from the command line so the server can be exercised without a
// client.
//
//	brazilian-soccer-mcp                                  # stdio MCP server
//	brazilian-soccer-mcp -http :8080                      # HTTP MCP server
//	brazilian-soccer-mcp -list-tools                      # what can it do
//	brazilian-soccer-mcp -call standings -args '{"season":2019}'
//	brazilian-soccer-mcp -demo                            # answer the sample questions
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpserver"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	var (
		dataDir   = flag.String("data", "", "directory containing the Kaggle CSVs (default: the data/kaggle directory at or above the working directory)")
		httpAddr  = flag.String("http", "", "serve MCP over streamable HTTP on this address instead of stdio, e.g. :8080")
		listTools = flag.Bool("list-tools", false, "print the tool catalogue and exit")
		call      = flag.String("call", "", "call one tool and print the result, then exit")
		args      = flag.String("args", "{}", "JSON arguments for -call")
		demo      = flag.Bool("demo", false, "answer a set of sample questions and exit")
		quiet     = flag.Bool("quiet", false, "do not log startup information to stderr")
	)
	flag.Parse()

	start := time.Now()
	srv, err := mcpserver.New(*dataDir)
	if err != nil {
		log.Fatalf("loading data: %v", err)
	}
	stats := srv.Graph().Stats()
	if !*quiet {
		log.SetFlags(0)
		log.SetPrefix("brazilian-soccer-mcp: ")
		log.Printf("loaded %d clubs, %d matches and %d players from %s in %v",
			stats.Teams, stats.Matches, stats.Players, srv.Graph().DataDir(), time.Since(start).Round(time.Millisecond))
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	switch {
	case *listTools:
		printToolCatalogue(ctx, srv)
	case *call != "":
		if err := callTool(ctx, srv, *call, *args); err != nil {
			log.Fatal(err)
		}
	case *demo:
		if err := runDemo(ctx, srv); err != nil {
			log.Fatal(err)
		}
	case *httpAddr != "":
		serveHTTP(ctx, srv, *httpAddr, *quiet)
	default:
		if err := srv.Run(ctx, &mcp.StdioTransport{}); err != nil && ctx.Err() == nil {
			log.Fatalf("serving over stdio: %v", err)
		}
	}
}

// serveHTTP runs the streamable HTTP transport, which is handy for testing with
// curl or for connecting a remote client.
func serveHTTP(ctx context.Context, srv *mcpserver.Server, addr string, quiet bool) {
	handler := mcp.NewStreamableHTTPHandler(func(*http.Request) *mcp.Server { return srv.MCP() }, nil)
	httpSrv := &http.Server{Addr: addr, Handler: handler}
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = httpSrv.Shutdown(shutdownCtx)
	}()
	if !quiet {
		log.Printf("listening for MCP over HTTP on %s", addr)
	}
	if err := httpSrv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("http server: %v", err)
	}
}

// connectLoopback wires an in-process client to the server, which is how the CLI
// modes exercise the real protocol path rather than calling Go methods directly.
func connectLoopback(ctx context.Context, srv *mcpserver.Server) (*mcp.ClientSession, error) {
	serverTransport, clientTransport := mcp.NewInMemoryTransports()
	if _, err := srv.MCP().Connect(ctx, serverTransport, nil); err != nil {
		return nil, err
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "brazilian-soccer-cli", Version: mcpserver.Version}, nil)
	return client.Connect(ctx, clientTransport, nil)
}

func printToolCatalogue(ctx context.Context, srv *mcpserver.Server) {
	session, err := connectLoopback(ctx, srv)
	if err != nil {
		log.Fatal(err)
	}
	defer session.Close()
	for tool, err := range session.Tools(ctx, nil) {
		if err != nil {
			log.Fatal(err)
		}
		fmt.Printf("%s\n    %s\n", tool.Name, tool.Description)
		if schema, err := json.Marshal(tool.InputSchema); err == nil {
			fmt.Printf("    input: %s\n", schema)
		}
	}
}

func callTool(ctx context.Context, srv *mcpserver.Server, name, rawArgs string) error {
	var arguments map[string]any
	if err := json.Unmarshal([]byte(rawArgs), &arguments); err != nil {
		return fmt.Errorf("parsing -args: %w", err)
	}
	session, err := connectLoopback(ctx, srv)
	if err != nil {
		return err
	}
	defer session.Close()
	res, err := session.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: arguments})
	if err != nil {
		return err
	}
	for _, c := range res.Content {
		if text, ok := c.(*mcp.TextContent); ok {
			fmt.Println(text.Text)
		}
	}
	if res.IsError {
		return fmt.Errorf("tool %s reported an error", name)
	}
	return nil
}

// demoQuestion pairs a natural language question with the tool call that answers
// it, so -demo doubles as executable documentation.
type demoQuestion struct {
	Question string
	Tool     string
	Args     map[string]any
}

var demoQuestions = []demoQuestion{
	{"Show me all Flamengo vs Fluminense matches", "head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Fluminense", "limit": 5}},
	{"What matches did Palmeiras play in 2023?", "search_matches", map[string]any{"team": "Palmeiras", "season": 2023, "limit": 5}},
	{"What is Corinthians' home record in the 2022 Brasileirão?", "team_stats", map[string]any{"team": "Corinthians", "competition": "Serie A", "season": 2022, "venue": "home"}},
	{"Who won the 2019 Brasileirão?", "standings", map[string]any{"season": 2019}},
	{"Which teams were relegated in 2020?", "standings", map[string]any{"season": 2020}},
	{"Show the 2018 Copa Libertadores bracket", "competition_bracket", map[string]any{"competition": "Libertadores", "season": 2018}},
	{"What is the average goals per match in the Brasileirão?", "aggregate_stats", map[string]any{"competition": "Serie A", "top": 3}},
	{"Which team has the best away record?", "team_rankings", map[string]any{"metric": "best_win_rate", "venue": "away", "competition": "Serie A", "min_matches": 100}},
	{"Who are the highest rated Brazilian players?", "search_players", map[string]any{"nationality": "Brazil", "limit": 5}},
	{"Which players play for Fluminense?", "search_players", map[string]any{"club": "Fluminense", "limit": 5}},
	{"Show me all derbies in 2023", "list_derbies", map[string]any{"season": 2023}},
	{"Where does this data come from?", "dataset_info", map[string]any{}},
}

func runDemo(ctx context.Context, srv *mcpserver.Server) error {
	session, err := connectLoopback(ctx, srv)
	if err != nil {
		return err
	}
	defer session.Close()
	for i, q := range demoQuestions {
		fmt.Printf("\n=== %d. %s\n", i+1, q.Question)
		fmt.Printf("--- %s %v\n\n", q.Tool, q.Args)
		started := time.Now()
		res, err := session.CallTool(ctx, &mcp.CallToolParams{Name: q.Tool, Arguments: q.Args})
		if err != nil {
			return fmt.Errorf("%s: %w", q.Question, err)
		}
		for _, c := range res.Content {
			if text, ok := c.(*mcp.TextContent); ok {
				fmt.Println(text.Text)
			}
		}
		fmt.Printf("\n(answered in %v)\n", time.Since(started).Round(time.Millisecond))
	}
	return nil
}
