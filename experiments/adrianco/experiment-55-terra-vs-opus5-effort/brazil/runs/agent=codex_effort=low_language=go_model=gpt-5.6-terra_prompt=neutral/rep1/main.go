// Brazilian Soccer MCP is a dependency-free, stdio JSON-RPC MCP server.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
)

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}
type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}
type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func main() {
	db, err := LoadDatabase(dataDir())
	if err != nil {
		fmt.Fprintln(os.Stderr, "loading data:", err)
		os.Exit(1)
	}
	s := bufio.NewScanner(os.Stdin)
	s.Buffer(make([]byte, 4096), 8*1024*1024)
	enc := json.NewEncoder(os.Stdout)
	for s.Scan() {
		var q request
		if err := json.Unmarshal(s.Bytes(), &q); err != nil {
			enc.Encode(response{JSONRPC: "2.0", Error: &rpcError{-32700, "parse error"}})
			continue
		}
		if len(q.ID) == 0 {
			continue
		}
		r := response{JSONRPC: "2.0", ID: q.ID}
		switch q.Method {
		case "initialize":
			r.Result = map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{"tools": map[string]any{}}, "serverInfo": map[string]string{"name": "brazilian-soccer", "version": "1.0.0"}}
		case "tools/list":
			r.Result = map[string]any{"tools": toolDefinitions()}
		case "tools/call":
			r.Result, r.Error = callTool(db, q.Params)
		case "ping":
			r.Result = map[string]any{}
		default:
			r.Error = &rpcError{-32601, "method not found"}
		}
		enc.Encode(r)
	}
}

func dataDir() string {
	if d := os.Getenv("SOCCER_DATA_DIR"); d != "" {
		return d
	}
	return "data/kaggle"
}
