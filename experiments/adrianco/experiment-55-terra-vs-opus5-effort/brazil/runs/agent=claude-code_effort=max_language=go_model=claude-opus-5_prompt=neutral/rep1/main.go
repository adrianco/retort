// Command brazilian-soccer-mcp serves the Brazilian football knowledge graph
// over the Model Context Protocol.
//
// Default mode speaks MCP on stdin/stdout, which is what an LLM client such as
// Claude Desktop or Claude Code expects:
//
//	brazilian-soccer-mcp
//
// The remaining flags exist to inspect the same tools from a shell:
//
//	brazilian-soccer-mcp -list-tools
//	brazilian-soccer-mcp -tool standings -args '{"season":2019}'
//	brazilian-soccer-mcp -demo
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccerserver"
)

func main() {
	var (
		dataDir   = flag.String("data", "", "directory holding the Kaggle CSVs (default: $"+soccer.DataDirEnv+", else data/kaggle found upwards from the working directory)")
		listTools = flag.Bool("list-tools", false, "print the tool catalogue and exit")
		toolName  = flag.String("tool", "", "call one tool and print its answer, instead of serving MCP")
		toolArgs  = flag.String("args", "{}", "JSON arguments for -tool")
		demo      = flag.Bool("demo", false, "answer the built-in sample questions and exit")
		jsonOut   = flag.Bool("json", false, "with -tool, print the structured result as JSON")
		showVer   = flag.Bool("version", false, "print the version and exit")
		quiet     = flag.Bool("quiet", false, "suppress startup logging on stderr")
	)
	flag.Parse()

	if *showVer {
		fmt.Printf("%s %s\n", soccerserver.ServerName, soccerserver.ServerVersion)
		return
	}

	// Everything diagnostic goes to stderr: stdout carries the protocol.
	logger := log.New(os.Stderr, "", log.LstdFlags)
	if *quiet {
		logger.SetOutput(io.Discard)
	}

	start := time.Now()
	store, err := soccer.Load(soccer.Options{DataDir: *dataDir})
	if err != nil {
		logger.Fatalf("loading datasets: %v", err)
	}
	sum := store.Summary()
	logger.Printf("loaded %d matches, %d clubs, %d players from %s in %s",
		sum.Matches, sum.Teams, sum.Players, store.DataDir, time.Since(start).Round(time.Millisecond))

	server := soccerserver.New(store)
	server.Logf = logger.Printf

	switch {
	case *listTools:
		printTools(server)
	case *demo:
		runDemo(server)
	case *toolName != "":
		if err := runTool(server, *toolName, *toolArgs, *jsonOut); err != nil {
			logger.Fatalf("%v", err)
		}
	default:
		ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
		defer stop()
		logger.Printf("serving MCP on stdio (%d tools); press ctrl-c to stop", len(server.Tools()))
		if err := server.Serve(ctx, os.Stdin, os.Stdout); err != nil {
			logger.Fatalf("serving: %v", err)
		}
	}
}

func printTools(s *mcp.Server) {
	fmt.Printf("%s %s - %d tools\n\n", s.Name, s.Version, len(s.Tools()))
	for _, t := range s.Tools() {
		fmt.Printf("%s\n  %s\n", t.Name, firstLine(t.Description))
		if t.InputSchema != nil && len(t.InputSchema.Properties) > 0 {
			required := map[string]bool{}
			for _, r := range t.InputSchema.Required {
				required[r] = true
			}
			for _, name := range sortedKeys(t.InputSchema.Properties) {
				prop := t.InputSchema.Properties[name]
				marker := " "
				if required[name] {
					marker = "*"
				}
				fmt.Printf("   %s %-16s %-8s %s\n", marker, name, prop.Type, firstLine(prop.Description))
			}
		}
		fmt.Println()
	}
	fmt.Println("* = required")
}

func sortedKeys(m map[string]*mcp.Prop) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	for i := 1; i < len(keys); i++ {
		for j := i; j > 0 && keys[j] < keys[j-1]; j-- {
			keys[j], keys[j-1] = keys[j-1], keys[j]
		}
	}
	return keys
}

func firstLine(s string) string {
	if i := strings.IndexByte(s, '\n'); i >= 0 {
		return s[:i]
	}
	return s
}

func runTool(s *mcp.Server, name, rawArgs string, asJSON bool) error {
	var args mcp.Args
	if strings.TrimSpace(rawArgs) != "" {
		if err := json.Unmarshal([]byte(rawArgs), &args); err != nil {
			return fmt.Errorf("parsing -args: %w", err)
		}
	}
	result, err := s.CallTool(name, args)
	if err != nil {
		return err
	}
	if asJSON {
		out, err := json.MarshalIndent(result, "", "  ")
		if err != nil {
			return err
		}
		fmt.Println(string(out))
		return nil
	}
	for _, c := range result.Content {
		fmt.Println(c.Text)
	}
	if result.IsError {
		return fmt.Errorf("tool %s reported an error", name)
	}
	return nil
}

func runDemo(s *mcp.Server) {
	questions := soccerserver.SampleQuestions
	fmt.Printf("Answering %d sample questions with %s %s\n", len(questions), s.Name, s.Version)
	for i, q := range questions {
		args, _ := json.Marshal(q.Args)
		fmt.Printf("\n%s\nQ%d [%s]: %s\n  tool: %s %s\n%s\n",
			strings.Repeat("=", 78), i+1, q.Category, q.Question, q.Tool, args, strings.Repeat("-", 78))
		result, err := s.CallTool(q.Tool, q.Args)
		if err != nil {
			fmt.Printf("ERROR: %v\n", err)
			continue
		}
		for _, c := range result.Content {
			fmt.Println(strings.TrimRight(c.Text, "\n"))
		}
	}
}
