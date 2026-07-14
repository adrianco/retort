// Package mcpserver implements a minimal Model Context Protocol (MCP) server
// over stdio using JSON-RPC 2.0, with no external dependencies.
//
// Context:
//   - MCP clients (e.g. an LLM host) launch this process and talk to it over
//     stdin/stdout using newline-delimited JSON-RPC 2.0 messages. This file
//     defines the wire types and the read/dispatch/write loop; server.go wires
//     the protocol methods (initialize, tools/list, tools/call) to the soccer
//     query layer; tools.go declares the tool schemas and handlers.
//   - We implement the protocol directly (rather than pulling in an SDK) to keep
//     the module dependency-free and the behaviour fully transparent and
//     testable.
//   - Transport framing: this server uses line-delimited JSON (one JSON object
//     per line), which is the simplest interoperable MCP stdio framing.
package mcpserver

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"sync"
)

// JSON-RPC 2.0 message envelopes.

type request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}

type response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Result  any             `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

// Standard JSON-RPC error codes.
const (
	codeParseError     = -32700
	codeInvalidRequest = -32600
	codeMethodNotFound = -32601
	codeInvalidParams  = -32602
	codeInternalError  = -32603
)

// isNotification reports whether a request is a notification (no id => no reply).
func (r *request) isNotification() bool {
	return len(r.ID) == 0 || string(r.ID) == "null"
}

// Serve runs the read/dispatch/write loop against the given streams until EOF.
// Each line on in is a JSON-RPC request; responses are written to out. Writes
// are serialised so concurrent handlers cannot interleave output.
func (s *Server) Serve(in io.Reader, out io.Writer) error {
	scanner := bufio.NewScanner(in)
	scanner.Buffer(make([]byte, 0, 64*1024), 8*1024*1024)
	writer := bufio.NewWriter(out)
	var mu sync.Mutex

	write := func(resp response) {
		mu.Lock()
		defer mu.Unlock()
		enc := json.NewEncoder(writer)
		_ = enc.Encode(resp) // Encoder appends a newline (our framing)
		_ = writer.Flush()
	}

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(trimSpace(line)) == 0 {
			continue
		}
		var req request
		if err := json.Unmarshal(line, &req); err != nil {
			write(response{JSONRPC: "2.0", Error: &rpcError{Code: codeParseError, Message: "parse error: " + err.Error()}})
			continue
		}
		result, rpcErr := s.dispatch(&req)
		if req.isNotification() {
			continue // notifications get no response
		}
		resp := response{JSONRPC: "2.0", ID: req.ID}
		if rpcErr != nil {
			resp.Error = rpcErr
		} else {
			resp.Result = result
		}
		write(resp)
	}
	if err := scanner.Err(); err != nil {
		return fmt.Errorf("read error: %w", err)
	}
	return nil
}

func trimSpace(b []byte) []byte {
	start := 0
	for start < len(b) && (b[start] == ' ' || b[start] == '\t' || b[start] == '\r' || b[start] == '\n') {
		start++
	}
	end := len(b)
	for end > start && (b[end-1] == ' ' || b[end-1] == '\t' || b[end-1] == '\r' || b[end-1] == '\n') {
		end--
	}
	return b[start:end]
}
