// main.go — entry point for the Brazilian soccer MCP server.
//
// Usage:
//
//	brsoccer [-data DIR]                       serve MCP over stdio (default)
//	brsoccer [-data DIR] tools                 list tools
//	brsoccer [-data DIR] call TOOL '{"k":"v"}'  run one tool and print the text
//
// The data directory defaults to $BRSOCCER_DATA, then ./data/kaggle, then
// data/kaggle next to the executable.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

func defaultDataDir() string {
	if d := os.Getenv("BRSOCCER_DATA"); d != "" {
		return d
	}
	if _, err := os.Stat(filepath.Join("data", "kaggle", SrcFIFA)); err == nil {
		return filepath.Join("data", "kaggle")
	}
	if exe, err := os.Executable(); err == nil {
		d := filepath.Join(filepath.Dir(exe), "data", "kaggle")
		if _, err := os.Stat(d); err == nil {
			return d
		}
	}
	return filepath.Join("data", "kaggle")
}

func main() {
	dataDir := flag.String("data", defaultDataDir(), "directory containing the Kaggle CSV files")
	quiet := flag.Bool("quiet", false, "do not log to stderr")
	flag.Parse()

	start := time.Now()
	store, err := LoadStore(*dataDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "load data:", err)
		os.Exit(1)
	}
	if !*quiet {
		fmt.Fprintf(os.Stderr, "%s: loaded %d matches, %d teams, %d players from %s in %s\n",
			serverName, len(store.Matches), len(store.Teams.Teams()), len(store.Players), *dataDir, time.Since(start).Round(time.Millisecond))
	}

	switch flag.Arg(0) {
	case "", "serve":
		srv := NewServer(store)
		if !*quiet {
			srv.Log = os.Stderr
		}
		if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
			fmt.Fprintln(os.Stderr, "serve:", err)
			os.Exit(1)
		}
	case "tools":
		for _, t := range Tools() {
			fmt.Printf("%-18s %s\n", t.Name, t.Description)
		}
	case "call":
		if flag.NArg() < 2 {
			fmt.Fprintln(os.Stderr, "usage: brsoccer call TOOL [JSON-ARGS]")
			os.Exit(2)
		}
		args := Args{}
		if flag.NArg() >= 3 {
			if err := json.Unmarshal([]byte(flag.Arg(2)), &args); err != nil {
				fmt.Fprintln(os.Stderr, "bad JSON arguments:", err)
				os.Exit(2)
			}
		}
		text, err := CallTool(store, flag.Arg(1), args)
		if err != nil {
			fmt.Fprintln(os.Stderr, "error:", err)
			os.Exit(1)
		}
		fmt.Print(text)
	default:
		fmt.Fprintf(os.Stderr, "unknown command %q (use serve, tools or call)\n", flag.Arg(0))
		os.Exit(2)
	}
}
