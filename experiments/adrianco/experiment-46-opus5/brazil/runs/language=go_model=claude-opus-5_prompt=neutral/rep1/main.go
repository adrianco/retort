// Command brazilian-soccer-mcp serves the Brazilian football knowledge graph
// over the Model Context Protocol.
//
// Context
//
//	This is the process entry point. It loads the six bundled Kaggle CSV files
//	into memory once, then speaks MCP over stdio - the transport every MCP host
//	(Claude Desktop, Claude Code, any SDK client) uses for local servers.
//
//	Usage:
//	    brazilian-soccer-mcp                      # stdio MCP server
//	    brazilian-soccer-mcp -data ./data/kaggle  # explicit dataset directory
//	    brazilian-soccer-mcp -check               # load, report, exit (health check)
//	    brazilian-soccer-mcp -tool head_to_head \
//	        -args '{"team_a":"Flamengo","team_b":"Fluminense"}'
//	    brazilian-soccer-mcp -list-tools          # names and descriptions
//
//	The -tool form runs a real MCP round trip over an in-memory transport, so
//	what it prints is exactly what a connected model would see.
//
//	Diagnostics go to stderr because stdout carries the JSON-RPC stream and any
//	stray byte written there corrupts the protocol.
package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpserver"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/jsonrpc"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	var opts options
	flag.StringVar(&opts.dataDir, "data", "", "directory holding the Kaggle CSV files (default: $BRAZILIAN_SOCCER_DATA, else the data/kaggle directory found above the working directory)")
	flag.BoolVar(&opts.check, "check", false, "load the datasets, print a summary and exit")
	flag.BoolVar(&opts.listTools, "list-tools", false, "list the MCP tools and exit")
	flag.StringVar(&opts.tool, "tool", "", "call one MCP tool from the command line and print its response")
	flag.StringVar(&opts.args, "args", "{}", "JSON arguments for -tool")
	flag.BoolVar(&opts.quiet, "quiet", false, "suppress start-up diagnostics on stderr")
	flag.Parse()

	if err := run(opts); err != nil {
		fmt.Fprintf(os.Stderr, "brazilian-soccer-mcp: %v\n", err)
		os.Exit(1)
	}
}

type options struct {
	dataDir   string
	check     bool
	listTools bool
	tool      string
	args      string
	quiet     bool
}

func run(opts options) error {
	dataDir, check, quiet := opts.dataDir, opts.check, opts.quiet
	if dataDir == "" {
		found, err := soccer.FindDataDir()
		if err != nil {
			return err
		}
		dataDir = found
	}

	start := time.Now()
	graph, err := soccer.Load(dataDir)
	if err != nil {
		return fmt.Errorf("loading datasets from %s: %w", dataDir, err)
	}
	summary := graph.Summary()
	if !quiet {
		fmt.Fprintf(os.Stderr, "loaded %d clubs, %d matches and %d players from %s in %s\n",
			summary.Clubs, summary.Matches, summary.Players, dataDir, time.Since(start).Round(time.Millisecond))
	}

	if check {
		printCheck(graph)
		return nil
	}

	srv := mcpserver.New(graph)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if opts.listTools {
		return listTools(ctx, srv)
	}
	if opts.tool != "" {
		return callTool(ctx, srv, opts.tool, opts.args)
	}

	if !quiet {
		fmt.Fprintln(os.Stderr, "serving MCP over stdio")
	}
	if err := srv.Run(ctx, &mcp.StdioTransport{}); !isCleanShutdown(err) {
		return err
	}
	return nil
}

// codeServerClosing is the JSON-RPC error code the SDK reports when the peer
// hangs up. The SDK keeps the sentinel in an internal package, so the code is
// the only stable way to recognise it from outside.
const codeServerClosing = -32004

// isCleanShutdown reports whether the server stopped for an expected reason: the
// host closed the pipe, or the process was interrupted. Both are normal ends to
// an MCP session and must not become a non-zero exit status, or every host that
// disconnects tidily makes this server look like it crashed.
func isCleanShutdown(err error) bool {
	if err == nil {
		return true
	}
	if errors.Is(err, io.EOF) ||
		errors.Is(err, io.ErrClosedPipe) ||
		errors.Is(err, context.Canceled) ||
		errors.Is(err, os.ErrClosed) {
		return true
	}
	var wire *jsonrpc.Error
	return errors.As(err, &wire) && wire.Code == codeServerClosing
}

// connect wires an in-memory MCP client to the server so the command line
// paths exercise the same code as a remote host.
func connect(ctx context.Context, srv *mcpserver.Server) (*mcp.ClientSession, error) {
	serverTransport, clientTransport := mcp.NewInMemoryTransports()
	if _, err := srv.MCP().Connect(ctx, serverTransport, nil); err != nil {
		return nil, err
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "brazilian-soccer-cli", Version: mcpserver.Version}, nil)
	return client.Connect(ctx, clientTransport, nil)
}

func listTools(ctx context.Context, srv *mcpserver.Server) error {
	session, err := connect(ctx, srv)
	if err != nil {
		return err
	}
	defer session.Close()

	res, err := session.ListTools(ctx, nil)
	if err != nil {
		return err
	}
	for _, t := range res.Tools {
		fmt.Printf("%-24s %s\n", t.Name, t.Description)
	}
	fmt.Printf("\n%d tools\n", len(res.Tools))
	return nil
}

func callTool(ctx context.Context, srv *mcpserver.Server, name, rawArgs string) error {
	var args map[string]any
	if err := json.Unmarshal([]byte(rawArgs), &args); err != nil {
		return fmt.Errorf("parsing -args as JSON: %w", err)
	}
	session, err := connect(ctx, srv)
	if err != nil {
		return err
	}
	defer session.Close()

	res, err := session.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		return err
	}
	for _, c := range res.Content {
		if tc, ok := c.(*mcp.TextContent); ok {
			fmt.Println(tc.Text)
		}
	}
	if res.IsError {
		return fmt.Errorf("tool %s reported an error", name)
	}
	return nil
}

// printCheck writes a human readable health report to stdout.
func printCheck(g *soccer.Graph) {
	s := g.Summary()
	fmt.Printf("Brazilian Soccer MCP - dataset check\n\n")
	fmt.Printf("Clubs:   %d\nMatches: %d\nPlayers: %d\nEdges:   %d\n\n", s.Clubs, s.Matches, s.Players, s.Edges)
	fmt.Println("Datasets:")
	for _, d := range g.Datasets() {
		fmt.Printf("  %-34s %6d rows -> %6d loaded", d.File, d.Rows, d.Loaded)
		if d.Rejected > 0 {
			fmt.Printf(" (%d rejected)", d.Rejected)
		}
		fmt.Printf("  %s\n", d.License)
	}
	fmt.Println("\nCompetitions:")
	for _, c := range g.CompetitionsPresent() {
		seasons := g.Seasons(c)
		fmt.Printf("  %-24s %d seasons %d-%d\n", c, len(seasons), seasons[0], seasons[len(seasons)-1])
	}
}
