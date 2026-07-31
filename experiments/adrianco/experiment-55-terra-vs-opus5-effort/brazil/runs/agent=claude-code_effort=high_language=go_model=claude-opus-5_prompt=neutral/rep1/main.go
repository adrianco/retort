// Command brazilian-soccer-mcp serves a knowledge graph of Brazilian soccer
// over the Model Context Protocol.
//
// By default it speaks MCP over stdio, which is how MCP clients (Claude
// Desktop, Claude Code, ...) launch a server:
//
//	brazilian-soccer-mcp
//
// Two other modes help with development and demonstration:
//
//	brazilian-soccer-mcp -demo    # answer the catalogue of sample questions
//	brazilian-soccer-mcp -ask search_matches -args '{"team":"Flamengo"}'
//
// The six Kaggle CSV datasets are embedded in the binary; -data points the
// loader at a directory on disk instead.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpsrv"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func main() {
	var (
		dataDir = flag.String("data", "", "directory holding the Kaggle CSV files (default: the copies embedded in this binary)")
		demo    = flag.Bool("demo", false, "answer the catalogue of sample questions and exit")
		ask     = flag.String("ask", "", "call a single tool by name and exit")
		args    = flag.String("args", "{}", "JSON arguments for -ask")
		version = flag.Bool("version", false, "print the version and exit")
	)
	flag.Parse()

	if *version {
		fmt.Println("brazilian-soccer-mcp", mcpsrv.Version)
		return
	}

	// MCP servers own stdout for protocol traffic, so all logging goes to stderr.
	log.SetOutput(os.Stderr)
	log.SetFlags(0)

	fsys, err := dataFS(*dataDir)
	if err != nil {
		log.Fatalf("locating datasets: %v", err)
	}
	graph, err := soccer.Load(fsys)
	if err != nil {
		log.Fatalf("loading datasets: %v", err)
	}
	log.Printf("loaded %d teams, %d matches and %d players in %dms",
		len(graph.Teams), len(graph.Matches), len(graph.Players), graph.Stats.LoadMillis)

	srv := mcpsrv.New(graph)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	switch {
	case *demo:
		if err := runDemo(ctx, srv, os.Stdout); err != nil {
			log.Fatalf("demo: %v", err)
		}
	case *ask != "":
		if err := runAsk(ctx, srv, *ask, *args, os.Stdout); err != nil {
			log.Fatalf("ask: %v", err)
		}
	default:
		if err := srv.MCP.Run(ctx, &mcp.StdioTransport{}); err != nil {
			log.Fatalf("serving: %v", err)
		}
	}
}

// dataFS returns the filesystem the CSV files are read from.
func dataFS(dir string) (fs.FS, error) {
	if dir != "" {
		if _, err := os.Stat(dir); err != nil {
			return nil, err
		}
		return os.DirFS(dir), nil
	}
	return embeddedDataFS()
}

// connectClient wires an in-process MCP client to the server, so the CLI modes
// exercise exactly the same code path (schema validation included) that a real
// client would.
func connectClient(ctx context.Context, srv *mcpsrv.Server) (*mcp.ClientSession, error) {
	serverT, clientT := mcp.NewInMemoryTransports()
	if _, err := srv.MCP.Connect(ctx, serverT, nil); err != nil {
		return nil, err
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "brazilian-soccer-cli", Version: mcpsrv.Version}, nil)
	return client.Connect(ctx, clientT, nil)
}

func runDemo(ctx context.Context, srv *mcpsrv.Server, out io.Writer) error {
	cs, err := connectClient(ctx, srv)
	if err != nil {
		return err
	}
	defer cs.Close()

	questions := mcpsrv.SampleQuestions()
	for i, q := range questions {
		fmt.Fprintf(out, "\n%s\nQ%d. %s\n%s\n", strings.Repeat("=", 78), i+1, q.Question, strings.Repeat("=", 78))
		fmt.Fprintf(out, "[tool: %s %s]\n\n", q.Tool, mustJSON(q.Args))
		res, err := cs.CallTool(ctx, &mcp.CallToolParams{Name: q.Tool, Arguments: q.Args})
		if err != nil {
			return fmt.Errorf("question %d (%s): %w", i+1, q.Tool, err)
		}
		fmt.Fprintln(out, toolText(res))
	}
	fmt.Fprintf(out, "\n%d sample questions answered.\n", len(questions))
	return nil
}

func runAsk(ctx context.Context, srv *mcpsrv.Server, tool, args string, out io.Writer) error {
	var parsed map[string]any
	if err := json.Unmarshal([]byte(args), &parsed); err != nil {
		return fmt.Errorf("parsing -args: %w", err)
	}
	cs, err := connectClient(ctx, srv)
	if err != nil {
		return err
	}
	defer cs.Close()

	res, err := cs.CallTool(ctx, &mcp.CallToolParams{Name: tool, Arguments: parsed})
	if err != nil {
		return err
	}
	fmt.Fprintln(out, toolText(res))
	return nil
}

// toolText extracts the human-readable block from a tool result.
func toolText(res *mcp.CallToolResult) string {
	var b strings.Builder
	for _, c := range res.Content {
		if tc, ok := c.(*mcp.TextContent); ok {
			b.WriteString(tc.Text)
			b.WriteString("\n")
		}
	}
	if res.IsError {
		return "ERROR: " + strings.TrimSpace(b.String())
	}
	return strings.TrimRight(b.String(), "\n")
}

func mustJSON(v any) string {
	b, err := json.Marshal(v)
	if err != nil {
		return "{}"
	}
	return string(b)
}
