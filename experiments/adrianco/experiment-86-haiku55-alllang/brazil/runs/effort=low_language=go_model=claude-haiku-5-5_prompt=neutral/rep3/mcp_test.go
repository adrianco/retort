// BDD scenarios for the MCP protocol layer and the tool surface.

package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

// roundTrip sends newline-delimited messages to a server and returns the decoded replies.
func roundTrip(t *testing.T, srv *Server, msgs ...string) []map[string]any {
	t.Helper()
	in := strings.NewReader(strings.Join(msgs, "\n") + "\n")
	var out bytes.Buffer
	if err := srv.Serve(in, &out); err != nil {
		t.Fatalf("serve: %v", err)
	}
	var replies []map[string]any
	for _, line := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if line == "" {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal([]byte(line), &m); err != nil {
			t.Fatalf("bad reply %q: %v", line, err)
		}
		replies = append(replies, m)
	}
	return replies
}

func newTestServer(t *testing.T) *Server {
	ds := loadTestDataset(t)
	h := &Handler{DS: ds}
	return &Server{Name: "brazilian-soccer", Version: "test", Tools: Tools(), Call: h.Call}
}

func toolText(t *testing.T, reply map[string]any) string {
	t.Helper()
	result, ok := reply["result"].(map[string]any)
	if !ok {
		t.Fatalf("no result in %v", reply)
	}
	content := result["content"].([]any)
	return content[0].(map[string]any)["text"].(string)
}

func call(id int, name, args string) string {
	return fmt.Sprintf(`{"jsonrpc":"2.0","id":%d,"method":"tools/call","params":{"name":%q,"arguments":%s}}`, id, name, args)
}

func TestMCPProtocol(t *testing.T) {
	srv := newTestServer(t)

	t.Run("Given a client connects", func(t *testing.T) {
		t.Run("When it sends initialize, Then it gets the protocol version and tool capability", func(t *testing.T) {
			r := roundTrip(t, srv, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`)
			if len(r) != 1 {
				t.Fatalf("replies = %d", len(r))
			}
			res := r[0]["result"].(map[string]any)
			if res["protocolVersion"] != protocolVersion {
				t.Fatalf("protocolVersion = %v", res["protocolVersion"])
			}
			if _, ok := res["capabilities"].(map[string]any)["tools"]; !ok {
				t.Fatal("tools capability missing")
			}
		})

		t.Run("When it sends a notification, Then the server stays silent", func(t *testing.T) {
			r := roundTrip(t, srv, `{"jsonrpc":"2.0","method":"notifications/initialized"}`)
			if len(r) != 0 {
				t.Fatalf("expected no reply, got %v", r)
			}
		})

		t.Run("When it sends ping, Then it gets an empty result", func(t *testing.T) {
			r := roundTrip(t, srv, `{"jsonrpc":"2.0","id":"abc","method":"ping"}`)
			if r[0]["id"] != "abc" || r[0]["result"] == nil {
				t.Fatalf("reply = %v", r[0])
			}
		})
	})

	t.Run("Given the tool catalogue", func(t *testing.T) {
		t.Run("When it lists tools, Then all seven query tools are advertised with schemas", func(t *testing.T) {
			r := roundTrip(t, srv, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
			tools := r[0]["result"].(map[string]any)["tools"].([]any)
			names := map[string]bool{}
			for _, tl := range tools {
				m := tl.(map[string]any)
				names[m["name"].(string)] = true
				if m["inputSchema"] == nil || m["description"] == "" {
					t.Fatalf("tool missing schema or description: %v", m["name"])
				}
			}
			for _, want := range []string{"search_matches", "team_record", "head_to_head", "standings", "league_stats", "biggest_wins", "search_players"} {
				if !names[want] {
					t.Errorf("missing tool %s", want)
				}
			}
		})
	})

	t.Run("Given a malformed or unknown request", func(t *testing.T) {
		t.Run("When the JSON is invalid, Then a parse error is returned", func(t *testing.T) {
			r := roundTrip(t, srv, `{not json`)
			if r[0]["error"].(map[string]any)["code"] != float64(errParse) {
				t.Fatalf("reply = %v", r[0])
			}
		})
		t.Run("When the method is unknown, Then method-not-found is returned", func(t *testing.T) {
			r := roundTrip(t, srv, `{"jsonrpc":"2.0","id":3,"method":"nope"}`)
			if r[0]["error"].(map[string]any)["code"] != float64(errMethodNotFound) {
				t.Fatalf("reply = %v", r[0])
			}
		})
		t.Run("When a tool is called without a name, Then invalid-params is returned", func(t *testing.T) {
			r := roundTrip(t, srv, `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{}}`)
			if r[0]["error"].(map[string]any)["code"] != float64(errInvalidParams) {
				t.Fatalf("reply = %v", r[0])
			}
		})
	})

	t.Run("Given a tool call that fails", func(t *testing.T) {
		t.Run("When the tool reports an error, Then it is returned as a tool error result", func(t *testing.T) {
			r := roundTrip(t, srv, call(5, "team_record", `{}`))
			res := r[0]["result"].(map[string]any)
			if res["isError"] != true {
				t.Fatalf("expected isError, got %v", res)
			}
		})
	})

	t.Run("Given a full conversation", func(t *testing.T) {
		t.Run("When a client calls a query tool, Then it receives the formatted answer", func(t *testing.T) {
			r := roundTrip(t, srv, call(6, "team_record", `{"team":"Palmeiras","season":2023}`))
			text := toolText(t, r[0])
			if !strings.Contains(text, "Palmeiras record") || !strings.Contains(text, "Win rate:") {
				t.Fatalf("unexpected text:\n%s", text)
			}
		})
	})
}

func TestToolOutputs(t *testing.T) {
	ds := loadTestDataset(t)
	h := &Handler{DS: ds}

	t.Run("Given the Corinthians 2022 home request from the spec", func(t *testing.T) {
		t.Run("When I call team_record, Then the answer reports matches, record, goals and win rate", func(t *testing.T) {
			text, err := h.Call("team_record", map[string]any{"team": "Corinthians", "season": float64(2022), "venue": "home", "competition": "Brasileirão"})
			if err != nil {
				t.Fatal(err)
			}
			for _, want := range []string{"Matches: 15", "Wins: 10, Draws: 4, Losses: 1", "Goals For: 21", "Win rate:"} {
				if !strings.Contains(text, want) {
					t.Errorf("missing %q in:\n%s", want, text)
				}
			}
		})
	})

	t.Run("Given a Flamengo vs Fluminense request", func(t *testing.T) {
		t.Run("When I call head_to_head, Then the answer lists fixtures and the head-to-head totals", func(t *testing.T) {
			text, err := h.Call("head_to_head", map[string]any{"team": "Flamengo", "opponent": "Fluminense"})
			if err != nil {
				t.Fatal(err)
			}
			if !strings.Contains(text, "Head-to-head in dataset:") || !strings.Contains(text, "more matches in dataset") {
				t.Fatalf("unexpected output:\n%s", text)
			}
		})
	})

	t.Run("Given a 2019 standings request", func(t *testing.T) {
		t.Run("When I call standings, Then the leader is marked and ranks are numbered", func(t *testing.T) {
			text, err := h.Call("standings", map[string]any{"season": float64(2019)})
			if err != nil {
				t.Fatal(err)
			}
			if !strings.Contains(text, "1. Flamengo - 90 pts") || !strings.Contains(text, "Leader") {
				t.Fatalf("unexpected output:\n%s", text)
			}
		})
	})

	t.Run("Given a player search from the spec", func(t *testing.T) {
		t.Run("When I call search_players by club, Then matching players are listed", func(t *testing.T) {
			text, err := h.Call("search_players", map[string]any{"name": "Messi"})
			if err != nil {
				t.Fatal(err)
			}
			if !strings.Contains(text, "Messi") || !strings.Contains(text, "Overall:") {
				t.Fatalf("unexpected output:\n%s", text)
			}
		})
	})

	t.Run("Given invalid input", func(t *testing.T) {
		cases := []struct {
			name string
			args map[string]any
		}{
			{"search_matches", map[string]any{}},
			{"search_matches", map[string]any{"venue": "neutral", "team": "Santos"}},
			{"search_matches", map[string]any{"from": "03/2020", "team": "Santos"}},
			{"team_record", map[string]any{}},
			{"head_to_head", map[string]any{"team": "Santos"}},
			{"standings", map[string]any{}},
			{"league_stats", map[string]any{}},
			{"search_players", map[string]any{}},
		}
		for _, c := range cases {
			t.Run("When "+c.name+" is called with bad arguments, Then it reports an error", func(t *testing.T) {
				if _, err := h.Call(c.name, c.args); err == nil {
					t.Fatal("expected an error")
				}
			})
		}
	})

	t.Run("Given an unknown tool name", func(t *testing.T) {
		t.Run("When it is called, Then an error is returned", func(t *testing.T) {
			if _, err := h.Call("nope", nil); err == nil {
				t.Fatal("expected error")
			}
		})
	})

	t.Run("Given a tool that finds nothing", func(t *testing.T) {
		t.Run("When I search for a missing team, Then a plain no-match message is returned", func(t *testing.T) {
			text, err := h.Call("search_matches", map[string]any{"team": "Clube Imaginário"})
			if err != nil {
				t.Fatal(err)
			}
			if !strings.HasPrefix(text, "No matches") {
				t.Fatalf("unexpected output: %s", text)
			}
		})
	})
}
