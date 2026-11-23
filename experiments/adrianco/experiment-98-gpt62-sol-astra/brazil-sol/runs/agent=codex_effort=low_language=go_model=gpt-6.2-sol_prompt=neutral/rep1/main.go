package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
)

const protocolVersion = "2025-06-18"

type Request struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params"`
}

type RPCError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type Response struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  *object         `json:"result,omitempty"`
	Error   *RPCError       `json:"error,omitempty"`
}

func serve(store *Store, input io.Reader, output io.Writer) error {
	tools := soccerTools()
	byName := make(map[string]Tool, len(tools))
	for _, tool := range tools {
		byName[tool.Name] = tool
	}

	scanner := bufio.NewScanner(input)
	scanner.Buffer(make([]byte, 4096), 1024*1024)
	writer := json.NewEncoder(output)
	for scanner.Scan() {
		line := bytes.TrimSpace(scanner.Bytes())
		if len(line) == 0 {
			continue
		}
		response := Response{JSONRPC: "2.0"}
		var request Request
		switch {
		case !json.Valid(line):
			response.Error = &RPCError{-32700, "Parse error"}
		case json.Unmarshal(line, &request) != nil || request.JSONRPC != "2.0" || request.Method == "" || !validID(request.ID):
			response.Error = &RPCError{-32600, "Invalid request"}
		case len(request.ID) == 0:
			// MCP notifications have no request ID and receive no response.
			continue
		default:
			response.ID = request.ID
			result, err := dispatch(store, tools, byName, request)
			response.Error = err
			if err == nil {
				response.Result = &result
			}
		}
		if err := writer.Encode(response); err != nil {
			return err
		}
	}
	return scanner.Err()
}

func validID(id json.RawMessage) bool {
	if len(id) == 0 || id[0] == '"' {
		return true
	}
	if id[0] == '-' {
		id = id[1:]
	}
	for _, digit := range id {
		if digit < '0' || digit > '9' {
			return false
		}
	}
	return len(id) != 0
}

func dispatch(store *Store, tools []Tool, byName map[string]Tool, request Request) (object, *RPCError) {
	switch request.Method {
	case "initialize":
		var params struct {
			ProtocolVersion string `json:"protocolVersion"`
		}
		if json.Unmarshal(request.Params, &params) != nil || params.ProtocolVersion == "" {
			return nil, &RPCError{-32602, "initialize requires protocolVersion"}
		}
		version := protocolVersion
		switch params.ProtocolVersion {
		case "2024-11-05", "2025-03-26", "2025-06-18":
			version = params.ProtocolVersion
		}
		return object{
			"protocolVersion": version,
			"capabilities":    object{"tools": object{"listChanged": false}},
			"serverInfo":      object{"name": "brazilian-soccer", "version": "1.0.0"},
			"instructions":    "Translate soccer questions into tool calls. Results reflect only the supplied datasets. Use season for competition editions and date bounds for calendar dates. An empty roster or search result means there is no match in that snapshot.",
		}, nil
	case "ping":
		return object{}, nil
	case "tools/list":
		return object{"tools": tools}, nil
	case "tools/call":
		var params struct {
			Name      string          `json:"name"`
			Arguments json.RawMessage `json:"arguments"`
		}
		if json.Unmarshal(request.Params, &params) != nil || params.Name == "" {
			return nil, &RPCError{-32602, "tools/call requires a tool name"}
		}
		tool, ok := byName[params.Name]
		if !ok {
			return nil, &RPCError{-32602, fmt.Sprintf("Unknown tool %q", params.Name)}
		}
		result, err := tool.run(store, params.Arguments)
		if err != nil {
			return object{"isError": true, "content": []object{{"type": "text", "text": err.Error()}}}, nil
		}
		body, err := json.Marshal(result)
		if err != nil {
			return nil, &RPCError{-32603, "Could not encode tool result"}
		}
		return object{"content": []object{{"type": "text", "text": string(body)}}}, nil
	default:
		return nil, &RPCError{-32601, "Method not found"}
	}
}

func main() {
	dir := flag.String("data-dir", "data/kaggle", "directory containing the six Kaggle CSV files")
	flag.Parse()
	store, err := loadStore(*dir)
	if err != nil {
		log.Fatal(err)
	}
	if err := serve(store, os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}
