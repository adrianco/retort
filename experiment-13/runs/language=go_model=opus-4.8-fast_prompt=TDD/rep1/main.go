// Package main — Brazilian Soccer MCP Server.
//
// main.go: Program entry point and the stdio transport loop. It loads the
// datasets once into memory, then serves the Model Context Protocol over
// newline-delimited JSON-RPC on stdin/stdout — the transport MCP clients (e.g.
// an LLM host) use to launch and talk to a local server. The data directory is
// configurable via the first CLI argument or the BR_SOCCER_DATA env var,
// defaulting to ./data/kaggle.
package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"os"
)

// defaultDataDir is where the bundled Kaggle CSVs live.
const defaultDataDir = "data/kaggle"

func main() {
	dir := resolveDataDir()
	ds, err := LoadDataset(dir)
	if err != nil {
		log.Fatalf("failed to load datasets from %q: %v", dir, err)
	}
	// Diagnostics go to stderr so they don't corrupt the JSON-RPC stream.
	fmt.Fprintf(os.Stderr, "brazilian-soccer-mcp: loaded %d matches and %d players from %s\n",
		len(ds.Matches), len(ds.Players), dir)

	srv := NewServer(ds)
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("serve error: %v", err)
	}
}

// resolveDataDir picks the data directory from CLI arg, env var, or default.
func resolveDataDir() string {
	if len(os.Args) > 1 && os.Args[1] != "" {
		return os.Args[1]
	}
	if env := os.Getenv("BR_SOCCER_DATA"); env != "" {
		return env
	}
	return defaultDataDir
}

// Serve runs the JSON-RPC loop, reading newline-delimited request objects from
// r and writing newline-delimited responses to w until EOF. Notifications and
// blank lines produce no output. A large scanner buffer accommodates big
// requests; per-line parse failures are reported as JSON-RPC errors rather than
// terminating the loop.
func (s *Server) Serve(r io.Reader, w io.Writer) error {
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
	out := bufio.NewWriter(w)
	defer out.Flush()

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(trimSpace(line)) == 0 {
			continue
		}
		resp, ok := s.Dispatch(line)
		if !ok {
			continue
		}
		if _, err := out.Write(resp); err != nil {
			return err
		}
		if err := out.WriteByte('\n'); err != nil {
			return err
		}
		if err := out.Flush(); err != nil {
			return err
		}
	}
	return scanner.Err()
}

// trimSpace reports the input with leading/trailing ASCII whitespace removed,
// used to detect blank lines without allocating a string.
func trimSpace(b []byte) []byte {
	start, end := 0, len(b)
	for start < end && isSpace(b[start]) {
		start++
	}
	for end > start && isSpace(b[end-1]) {
		end--
	}
	return b[start:end]
}

func isSpace(c byte) bool {
	return c == ' ' || c == '\t' || c == '\r' || c == '\n'
}
