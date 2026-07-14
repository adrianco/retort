// Brazilian Soccer MCP Server.
//
// Loads the bundled Kaggle datasets (Brasileirão, Copa do Brasil, Copa
// Libertadores match data plus the FIFA player database) into an in-memory
// knowledge graph and exposes them over the Model Context Protocol so an LLM
// can answer natural-language questions about Brazilian soccer.
//
// Transport: newline-delimited JSON-RPC 2.0 over stdin/stdout. Diagnostics go
// to stderr so they never corrupt the protocol stream.
package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"io"
	"log"
	"os"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV files")
	flag.Parse()

	log.SetOutput(os.Stderr)
	log.SetFlags(0)
	log.SetPrefix("[brazilian-soccer-mcp] ")

	resolved := resolveDataDir(*dataDir)
	db, err := BuildDB(resolved)
	if err != nil {
		log.Fatalf("failed to load datasets from %q: %v", resolved, err)
	}
	log.Printf("loaded %d matches (%d raw rows) and %d players from %q",
		len(db.Matches), len(db.AllMatches), len(db.Players), resolved)

	if err := serve(db, os.Stdin, os.Stdout); err != nil && err != io.EOF {
		log.Fatalf("server error: %v", err)
	}
}

// serve runs the MCP request loop, reading newline-delimited JSON-RPC messages
// from in and writing responses to out.
func serve(db *DB, in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 1024*1024), 16*1024*1024)
	writer := bufio.NewWriter(out)
	defer writer.Flush()

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var req rpcRequest
		if err := json.Unmarshal(line, &req); err != nil {
			log.Printf("dropping unparseable message: %v", err)
			writeResponse(writer, &rpcResponse{
				JSONRPC: "2.0",
				ID:      json.RawMessage("null"),
				Error:   &rpcError{Code: -32700, Message: "parse error"},
			})
			continue
		}
		resp := handleRequest(db, &req)
		if resp == nil {
			continue // notification: no response expected
		}
		writeResponse(writer, resp)
	}
	return scanner.Err()
}

// writeResponse marshals resp as a single line of JSON and flushes it.
func writeResponse(w *bufio.Writer, resp *rpcResponse) {
	data, err := json.Marshal(resp)
	if err != nil {
		log.Printf("failed to marshal response: %v", err)
		return
	}
	w.Write(data)
	w.WriteByte('\n')
	if err := w.Flush(); err != nil {
		log.Printf("failed to flush response: %v", err)
	}
}
