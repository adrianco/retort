package main

import (
	"fmt"
	"os"
)

func main() {
	s, err := LoadStore(dataDir())
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := Serve(os.Stdin, os.Stdout, s); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
