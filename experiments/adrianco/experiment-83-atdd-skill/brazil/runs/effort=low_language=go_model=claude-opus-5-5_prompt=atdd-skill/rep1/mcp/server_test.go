package mcp

import (
	"bytes"
	"strings"
	"testing"

	"brsoccer/soccer"
)

func TestServerListsAndCallsTools(t *testing.T) {
	db, err := soccer.Load("../data/kaggle")
	if err != nil {
		t.Fatal(err)
	}
	in := strings.NewReader(`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_players","arguments":{"name":"Neymar"}}}
`)
	var out bytes.Buffer
	if err := New(db).Serve(in, &out); err != nil {
		t.Fatal(err)
	}
	s := out.String()
	for _, want := range []string{`"serverInfo"`, `"search_players"`, "Neymar"} {
		if !strings.Contains(s, want) {
			t.Errorf("missing %s in %.500s", want, s)
		}
	}
}
