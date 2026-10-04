// Command brsoccer is an MCP (Model Context Protocol) stdio server that
// answers questions about Brazilian soccer from the bundled Kaggle datasets.
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
	tool := flag.String("tool", "", "run a single tool and print the result (CLI mode)")
	args := flag.String("args", "{}", "JSON arguments for -tool")
	flag.Parse()
	log.SetOutput(os.Stderr)
	db, err := LoadDB(*dir)
	if err != nil {
		log.Fatalf("loading data: %v", err)
	}
	s := &Server{DB: db}
	if *tool != "" {
		var a Args
		if err := json.Unmarshal([]byte(*args), &a); err != nil {
			log.Fatalf("bad -args: %v", err)
		}
		out, err := s.Call(*tool, a)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Print(out)
		return
	}
	if err := s.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}

func envOr(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}
