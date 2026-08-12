package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func TestMCPProtocol(t *testing.T) {
	s := &Server{Store: &Store{}}
	in := `{"jsonrpc":"2.0","id":1,"method":"initialize"}` + "\n" + `{"jsonrpc":"2.0","id":2,"method":"tools/list"}` + "\n"
	var out bytes.Buffer
	if e := run(s, strings.NewReader(in), &out); e != nil {
		t.Fatal(e)
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 2 {
		t.Fatalf("responses: %s", out.String())
	}
	var v map[string]any
	if json.Unmarshal([]byte(lines[1]), &v) != nil || v["result"] == nil {
		t.Fatal("invalid response")
	}
}
