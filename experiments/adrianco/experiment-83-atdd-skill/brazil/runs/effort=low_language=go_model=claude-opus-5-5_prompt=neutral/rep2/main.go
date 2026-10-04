// Command brsoccer is an MCP (stdio) server answering questions about
// Brazilian soccer from the bundled Kaggle datasets.
//
// Usage:
//
//	brsoccer [-data data/kaggle]                 # run MCP server on stdin/stdout
//	brsoccer -call search_players '{"nationality":"Brazil"}'  # one-off tool call
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
)

func main() {
	dir := flag.String("data", envOr("BRSOCCER_DATA", "data/kaggle"), "directory containing the CSV datasets")
	call := flag.String("call", "", "call a single tool (arguments as JSON in first positional arg) and exit")
	flag.Parse()
	log.SetOutput(os.Stderr)

	db, err := LoadDB(*dir)
	if err != nil {
		log.Fatalf("loading data: %v", err)
	}
	if *call != "" {
		a := args{}
		if flag.NArg() > 0 {
			if err := json.Unmarshal([]byte(flag.Arg(0)), &a); err != nil {
				log.Fatalf("bad arguments: %v", err)
			}
		}
		out, err := db.CallTool(*call, a)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Println(out)
		return
	}
	if err := db.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}

func envOr(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}
