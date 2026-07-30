package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
)

func main() {
	dataDir := flag.String("data-dir", "data/kaggle", "directory containing the Kaggle CSV files")
	flag.Parse()
	db, err := LoadDatabase(*dataDir)
	if err != nil {
		log.Fatal(err)
	}
	server := NewServer(db)
	scanner := bufio.NewScanner(os.Stdin)
	// Large tool arguments are valid MCP messages.
	scanner.Buffer(make([]byte, 4096), 4*1024*1024)
	enc := json.NewEncoder(os.Stdout)
	for scanner.Scan() {
		var request rpcRequest
		if err := json.Unmarshal(scanner.Bytes(), &request); err != nil {
			_ = enc.Encode(rpcResponse{JSONRPC: "2.0", Error: &rpcError{Code: -32700, Message: "parse error"}})
			continue
		}
		response := server.Handle(context.Background(), request)
		if err := enc.Encode(response); err != nil {
			log.Printf("write response: %v", err)
			return
		}
	}
	if err := scanner.Err(); err != nil {
		fmt.Fprintln(os.Stderr, err)
	}
}
