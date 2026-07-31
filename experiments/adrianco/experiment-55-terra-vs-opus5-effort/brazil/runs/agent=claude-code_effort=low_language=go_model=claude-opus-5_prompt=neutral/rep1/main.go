// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// exposes a knowledge graph over the Brazilian football datasets in
// data/kaggle as tools an LLM can call.
//
// Usage:
//
//	brazilian-soccer-mcp                 # serve MCP over stdio
//	brazilian-soccer-mcp -data ./data/kaggle
//	brazilian-soccer-mcp -list           # print the tool catalogue and exit
//	brazilian-soccer-mcp -call search_matches -args '{"team":"Flamengo"}'
//
// The -call form runs a single tool from the command line, which makes the
// server easy to exercise without an MCP client.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/soccer"
	"github.com/adriancockcroft/brazilian-soccer-mcp/tools"
)

// Version is the reported server version.
const Version = "1.0.0"

func main() {
	dataDir := flag.String("data", defaultDataDir(), "directory containing the Kaggle CSV files")
	list := flag.Bool("list", false, "print the tool catalogue and exit")
	call := flag.String("call", "", "run a single tool by name and exit")
	argsJSON := flag.String("args", "{}", "JSON arguments for -call")
	flag.Parse()

	start := time.Now()
	store, err := soccer.Load(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load data: %v\n", err)
		os.Exit(1)
	}
	// Diagnostics go to stderr: stdout is the MCP transport.
	fmt.Fprintf(os.Stderr, "loaded %d matches and %d players from %s in %s\n",
		len(store.Matches), len(store.Players), *dataDir, time.Since(start).Round(time.Millisecond))
	for _, w := range store.LoadErrors() {
		fmt.Fprintf(os.Stderr, "warning: %s\n", w)
	}

	srv := mcp.NewServer("brazilian-soccer", Version, tools.Instructions)
	tools.Register(srv, store)

	switch {
	case *list:
		for _, t := range srv.Tools() {
			fmt.Printf("%-20s %s\n", t.Name, t.Description)
		}
	case *call != "":
		if err := runTool(srv, *call, *argsJSON); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	default:
		if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
			fmt.Fprintf(os.Stderr, "server error: %v\n", err)
			os.Exit(1)
		}
	}
}

// runTool invokes one tool through the JSON-RPC layer and prints its text
// result, so the CLI path exercises exactly the same code as a real client.
func runTool(srv *mcp.Server, name, argsJSON string) error {
	var args map[string]any
	if err := json.Unmarshal([]byte(argsJSON), &args); err != nil {
		return fmt.Errorf("invalid -args JSON: %w", err)
	}
	req, _ := json.Marshal(map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "tools/call",
		"params": map[string]any{"name": name, "arguments": args},
	})
	resp, _ := srv.HandleMessage(req)
	if resp.Error != nil {
		return fmt.Errorf("%s: %s", name, resp.Error.Message)
	}
	res, ok := resp.Result.(*mcp.CallToolResult)
	if !ok {
		return fmt.Errorf("unexpected result type %T", resp.Result)
	}
	for _, c := range res.Content {
		fmt.Println(c.Text)
	}
	if res.IsError {
		os.Exit(1)
	}
	return nil
}

// defaultDataDir looks for the datasets next to the working directory, falling
// back to the path relative to the executable.
func defaultDataDir() string {
	for _, c := range []string{"data/kaggle", "../data/kaggle", "../../data/kaggle"} {
		if fi, err := os.Stat(c); err == nil && fi.IsDir() {
			return c
		}
	}
	return "data/kaggle"
}
