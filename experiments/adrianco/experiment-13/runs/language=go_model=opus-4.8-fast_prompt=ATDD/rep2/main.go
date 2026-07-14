// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// exposes a knowledge graph over Brazilian soccer datasets (matches, teams,
// players, competitions) as a set of tools an LLM can call to answer natural
// language questions.
//
// Transport: newline-delimited JSON-RPC 2.0 over stdio, the standard MCP stdio
// transport. Each line read from stdin is one request; each response is written
// as one line to stdout. All logging goes to stderr so it never corrupts the
// protocol stream.
//
// Usage:
//
//	brazilian-soccer-mcp [-data DIR]
//
// DIR defaults to ./data/kaggle.
package main

import (
	"bufio"
	"flag"
	"fmt"
	"io"
	"log"
	"os"

	"brazilian-soccer-mcp/mcp"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV datasets")
	flag.Parse()

	log.SetOutput(os.Stderr)
	log.SetPrefix("[brazilian-soccer-mcp] ")

	srv, err := mcp.NewServer(*dataDir)
	if err != nil {
		log.Fatalf("failed to start: %v", err)
	}
	log.Printf("loaded data from %s; ready on stdio", *dataDir)

	if err := serve(srv, os.Stdin, os.Stdout); err != nil {
		log.Fatalf("serve: %v", err)
	}
}

// serve runs the newline-delimited JSON-RPC loop until the input closes.
func serve(srv *mcp.Server, in io.Reader, out io.Writer) error {
	reader := bufio.NewScanner(in)
	reader.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	writer := bufio.NewWriter(out)
	defer writer.Flush()

	for reader.Scan() {
		line := reader.Bytes()
		if len(line) == 0 {
			continue
		}
		resp := srv.Handle(line)
		if resp == nil {
			continue // notification, no reply
		}
		if _, err := writer.Write(resp); err != nil {
			return err
		}
		if err := writer.WriteByte('\n'); err != nil {
			return err
		}
		if err := writer.Flush(); err != nil {
			return err
		}
	}
	if err := reader.Err(); err != nil {
		return fmt.Errorf("reading stdin: %w", err)
	}
	return nil
}
