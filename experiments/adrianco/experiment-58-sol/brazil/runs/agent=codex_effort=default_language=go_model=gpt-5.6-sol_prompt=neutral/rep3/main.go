package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
)

func main() {
	if err := run(os.Args[1:], os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}

// run contains the documented command's complete startup path so tests can
// exercise dataset loading and stdio MCP serving without a second executable.
func run(args []string, stdin io.Reader, stdout io.Writer) error {
	flags := flag.NewFlagSet("brazilian-soccer-mcp", flag.ContinueOnError)
	flags.SetOutput(io.Discard)
	dataDir := flags.String("data", defaultDataDir(), "directory containing the six Kaggle CSV files")
	showVersion := flags.Bool("version", false, "print version and exit")
	if err := flags.Parse(args); err != nil {
		return err
	}
	if *showVersion {
		_, err := fmt.Fprintln(stdout, serverVersion)
		return err
	}
	db, err := LoadDatabase(*dataDir)
	if err != nil {
		return fmt.Errorf("load soccer datasets: %w", err)
	}
	if err := NewMCPServer(db).Serve(stdin, stdout); err != nil {
		return fmt.Errorf("serve MCP: %w", err)
	}
	return nil
}

func defaultDataDir() string {
	if value := os.Getenv("BRAZILIAN_SOCCER_DATA"); value != "" {
		return value
	}
	if executable, err := os.Executable(); err == nil {
		candidate := filepath.Join(filepath.Dir(executable), "data", "kaggle")
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
	}
	return filepath.Join("data", "kaggle")
}
