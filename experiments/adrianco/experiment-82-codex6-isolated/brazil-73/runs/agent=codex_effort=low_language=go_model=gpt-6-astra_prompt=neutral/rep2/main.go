package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	dir := flag.String("data", "data/kaggle", "Directory containing all six CSV datasets")
	flag.Parse()
	s, e := Load(*dir)
	if e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "Loaded %d unique matches and %d players\n", len(s.Matches), len(s.Players))
	if e = Serve(os.Stdin, os.Stdout, s); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
