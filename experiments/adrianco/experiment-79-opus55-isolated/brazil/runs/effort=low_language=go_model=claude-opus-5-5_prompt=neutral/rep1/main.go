// Command brsoccer-mcp is an MCP server answering questions about Brazilian
// soccer from the bundled Kaggle datasets.
//
// Usage:
//
//	brsoccer-mcp [-data DIR]                      serve MCP over stdio
//	brsoccer-mcp [-data DIR] -call TOOL -args JSON  run one tool and print the result
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
)

// findDataDir locates the CSV directory: flag, $BRSOCCER_DATA_DIR, then
// data/kaggle relative to the working directory or the executable.
func findDataDir(flagDir string) (string, error) {
	candidates := []string{flagDir, os.Getenv("BRSOCCER_DATA_DIR"), filepath.Join("data", "kaggle")}
	if exe, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(exe), "data", "kaggle"))
	}
	for _, c := range candidates {
		if c == "" {
			continue
		}
		if _, err := os.Stat(filepath.Join(c, FileBrasileirao)); err == nil {
			return c, nil
		}
		if c == flagDir {
			return "", fmt.Errorf("data directory %q does not contain %s", c, FileBrasileirao)
		}
	}
	return "", fmt.Errorf("data directory not found; pass -data or set BRSOCCER_DATA_DIR")
}

func main() {
	dataDir := flag.String("data", "", "directory containing the Kaggle CSV files (default data/kaggle)")
	call := flag.String("call", "", "run a single tool and exit instead of serving MCP")
	argsJSON := flag.String("args", "{}", "JSON object with tool arguments, used with -call")
	flag.Parse()
	log.SetOutput(os.Stderr) // stdout is reserved for the protocol

	dir, err := findDataDir(*dataDir)
	if err != nil {
		log.Fatal(err)
	}
	store, err := LoadStore(dir)
	if err != nil {
		log.Fatalf("loading data: %v", err)
	}
	srv := NewServer(store)

	if *call != "" {
		var a Args
		if err := json.Unmarshal([]byte(*argsJSON), &a); err != nil {
			log.Fatalf("invalid -args: %v", err)
		}
		out, err := srv.CallTool(*call, a)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Println(out)
		return
	}

	log.Printf("%s %s: %d matches, %d teams, %d players loaded from %s",
		serverName, serverVersion, len(store.Matches), len(store.Reg.Teams), len(store.Players), dir)
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}
