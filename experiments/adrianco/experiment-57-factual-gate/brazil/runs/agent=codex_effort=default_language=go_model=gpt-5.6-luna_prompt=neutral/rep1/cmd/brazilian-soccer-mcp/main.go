package main

import (
	soccer "brazilian-soccer-mcp"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
)

func main() {
	dir := flag.String("data", "", "directory containing the CSV files")
	flag.Parse()
	d := *dir
	if d == "" {
		d = os.Getenv("SOCCER_DATA_DIR")
	}
	if d == "" {
		d = filepath.Join("data", "kaggle")
	}
	s, e := soccer.Load(d)
	if e != nil {
		log.Fatal(e)
	}
	if e = soccer.NewServer(s).Serve(os.Stdin, os.Stdout); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
