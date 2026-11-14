// Brazilian Soccer MCP server.
//
// Usage:
//
//	brsoccer [-data DIR]                     serve MCP over stdio
//	brsoccer [-data DIR] -call TOOL -args '{"team":"Flamengo"}'   one-off query
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"time"
)

func main() {
	dataDir := flag.String("data", "", "directory with the Kaggle CSV files (default: $BRSOCCER_DATA_DIR or ./data/kaggle)")
	call := flag.String("call", "", "run one tool and print its result instead of serving MCP")
	argsJSON := flag.String("args", "{}", "JSON arguments for -call")
	flag.Parse()
	log.SetOutput(os.Stderr) // stdout is reserved for the protocol
	log.SetPrefix("brsoccer: ")

	dir, err := FindDataDir(*dataDir)
	if err != nil {
		log.Fatal(err)
	}
	start := time.Now()
	db, err := LoadDB(dir)
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("loaded %d matches, %d teams, %d players from %s in %v", len(db.Matches), len(db.Teams), len(db.Players), dir, time.Since(start).Round(time.Millisecond))

	if *call != "" {
		var args Args
		if err := json.Unmarshal([]byte(*argsJSON), &args); err != nil {
			log.Fatalf("invalid -args: %v", err)
		}
		out, err := CallTool(db, *call, args)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Print(out)
		return
	}
	if err := NewServer(db).Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}
