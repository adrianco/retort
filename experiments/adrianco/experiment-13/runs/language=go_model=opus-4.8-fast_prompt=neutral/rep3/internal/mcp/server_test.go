package mcp

import (
	"bufio"
	"context"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// testServer builds a server over a tiny synthetic dataset.
func testServer(t *testing.T) *Server {
	t.Helper()
	dir := t.TempDir()
	write := func(name, content string) {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	write("novo_campeonato_brasileiro.csv", `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2019.01,01/05/2019,2019,1,Flamengo,Vasco,3,0,RJ,RJ,Mandante,Maracanã,
2019.02,02/05/2019,2019,1,Palmeiras,Santos,1,1,SP,SP,Empate,Allianz,
`)
	write("fifa_data.csv", `ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight,Preferred Foot
1,Neymar Jr,27,Brazil,92,93,Paris Saint-Germain,LW,10,5'9,150lbs,Right
2,Bruno,28,Brazil,75,76,Santos,GK,1,6'3,180lbs,Right
`)

	db, err := soccer.Load(dir)
	if err != nil {
		t.Fatal(err)
	}
	return NewServer(db, "test", "0.0.1")
}

func TestInitialize(t *testing.T) {
	s := testServer(t)
	res, rerr := s.Dispatch("initialize", nil)
	if rerr != nil {
		t.Fatalf("initialize error: %v", rerr)
	}
	m := res.(map[string]interface{})
	if m["protocolVersion"] != protocolVersion {
		t.Errorf("protocolVersion = %v, want %v", m["protocolVersion"], protocolVersion)
	}
	if _, ok := m["capabilities"]; !ok {
		t.Error("missing capabilities")
	}
}

func TestToolsList(t *testing.T) {
	s := testServer(t)
	res, rerr := s.Dispatch("tools/list", nil)
	if rerr != nil {
		t.Fatalf("tools/list error: %v", rerr)
	}
	tools := res.(map[string]interface{})["tools"].([]Tool)
	if len(tools) != 7 {
		t.Errorf("tools = %d, want 7", len(tools))
	}
	for _, tool := range tools {
		if tool.Name == "" || tool.Description == "" || tool.InputSchema == nil {
			t.Errorf("tool %q incompletely defined", tool.Name)
		}
	}
}

func TestUnknownMethod(t *testing.T) {
	s := testServer(t)
	_, rerr := s.Dispatch("does/not/exist", nil)
	if rerr == nil || rerr.Code != codeMethodNotFound {
		t.Errorf("expected method-not-found, got %v", rerr)
	}
}

func TestToolCallStandings(t *testing.T) {
	s := testServer(t)
	out, err := s.CallTool("standings", map[string]interface{}{"season": float64(2019)})
	if err != nil {
		t.Fatalf("standings: %v", err)
	}
	if !strings.Contains(out, "Flamengo") || !strings.Contains(out, "Champion") {
		t.Errorf("standings output missing expected content:\n%s", out)
	}
}

func TestToolCallPlayerSearch(t *testing.T) {
	s := testServer(t)
	out, err := s.CallTool("search_players", map[string]interface{}{"nationality": "Brazil"})
	if err != nil {
		t.Fatalf("search_players: %v", err)
	}
	if !strings.Contains(out, "Neymar Jr") {
		t.Errorf("expected Neymar in output:\n%s", out)
	}
}

func TestToolCallMissingRequiredArg(t *testing.T) {
	s := testServer(t)
	// head_to_head requires both teams; omitting one is a tool-level error.
	_, err := s.CallTool("head_to_head", map[string]interface{}{"team_a": "Flamengo"})
	if err == nil {
		t.Error("expected error for missing team_b")
	}
}

// TestStdioRoundTrip drives the server through its real newline-delimited
// JSON-RPC transport, the way an MCP client would.
func TestStdioRoundTrip(t *testing.T) {
	s := testServer(t)

	inR, inW := io.Pipe()
	outR, outW := io.Pipe()

	go func() {
		_ = s.Serve(context.Background(), inR, outW)
		outW.Close()
	}()

	requests := []string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"head_to_head","arguments":{"team_a":"Flamengo","team_b":"Vasco"}}}`,
	}
	go func() {
		for _, r := range requests {
			io.WriteString(inW, r+"\n")
		}
		inW.Close()
	}()

	scanner := bufio.NewScanner(outR)
	scanner.Buffer(make([]byte, 0, 64*1024), 1<<20)

	var responses []response
	for scanner.Scan() {
		var resp response
		if err := json.Unmarshal(scanner.Bytes(), &resp); err != nil {
			t.Fatalf("bad response line %q: %v", scanner.Text(), err)
		}
		responses = append(responses, resp)
	}

	// The notification must NOT produce a response: 2 requests with IDs -> 2 responses.
	if len(responses) != 2 {
		t.Fatalf("got %d responses, want 2 (notification must be silent)", len(responses))
	}

	// Second response is the head_to_head tool result.
	rb, _ := json.Marshal(responses[1].Result)
	if !strings.Contains(string(rb), "Flamengo") || !strings.Contains(string(rb), "head-to-head") {
		t.Errorf("unexpected tool result: %s", rb)
	}
}

func TestParseError(t *testing.T) {
	// A malformed line should yield a parse error response, not a crash.
	s := testServer(t)
	var buf strings.Builder
	s.out = &buf
	s.handleLine([]byte(`{not json`))
	if !strings.Contains(buf.String(), "parse error") {
		t.Errorf("expected parse error, got %q", buf.String())
	}
}
