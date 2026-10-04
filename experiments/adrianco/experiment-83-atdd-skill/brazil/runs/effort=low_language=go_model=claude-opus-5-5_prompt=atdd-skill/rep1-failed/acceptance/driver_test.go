package acceptance

// Protocol driver: the only layer that knows the system is an MCP server
// speaking JSON-RPC over stdio. It launches the real server binary.

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"testing"
	"time"
)

var (
	buildOnce sync.Once
	binPath   string
	buildErr  error
)

func serverBinary(t *testing.T) string {
	buildOnce.Do(func() {
		dir, _ := os.MkdirTemp("", "brsoccer")
		binPath = filepath.Join(dir, "brsoccer-mcp")
		out, err := exec.Command("go", "build", "-o", binPath, "../cmd/brsoccer-mcp").CombinedOutput()
		if err != nil {
			buildErr = fmt.Errorf("building server: %v\n%s", err, out)
		}
	})
	if buildErr != nil {
		t.Fatal(buildErr)
	}
	return binPath
}

type MCPDriver struct {
	t      *testing.T
	in     io.WriteCloser
	out    *bufio.Reader
	nextID int
	last   string
}

func NewMCPDriver(t *testing.T) *MCPDriver {
	t.Helper()
	cmd := exec.Command(serverBinary(t), "-data", "../data/kaggle")
	in, _ := cmd.StdinPipe()
	out, _ := cmd.StdoutPipe()
	cmd.Stderr = os.Stderr
	if err := cmd.Start(); err != nil {
		t.Fatalf("starting server: %v", err)
	}
	t.Cleanup(func() { in.Close(); cmd.Wait() })
	d := &MCPDriver{t: t, in: in, out: bufio.NewReaderSize(out, 1<<20)}
	d.rpc("initialize", map[string]any{"protocolVersion": "2024-11-05", "capabilities": map[string]any{},
		"clientInfo": map[string]any{"name": "acceptance", "version": "1"}})
	d.notify("notifications/initialized")
	return d
}

func (d *MCPDriver) notify(method string) {
	b, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "method": method})
	d.in.Write(append(b, '\n'))
}

func (d *MCPDriver) rpc(method string, params any) json.RawMessage {
	d.t.Helper()
	d.nextID++
	b, _ := json.Marshal(map[string]any{"jsonrpc": "2.0", "id": d.nextID, "method": method, "params": params})
	if _, err := d.in.Write(append(b, '\n')); err != nil {
		d.t.Fatalf("sending %s: %v", method, err)
	}
	line, err := d.out.ReadBytes('\n')
	if err != nil {
		d.t.Fatalf("no response to %s: %v", method, err)
	}
	var resp struct {
		Result json.RawMessage           `json:"result"`
		Error  *struct{ Message string } `json:"error"`
	}
	if err := json.Unmarshal(line, &resp); err != nil {
		d.t.Fatalf("bad response %q: %v", line, err)
	}
	if resp.Error != nil {
		d.t.Fatalf("%s failed: %s", method, resp.Error.Message)
	}
	return resp.Result
}

func (d *MCPDriver) Ask(tool string, args map[string]any) {
	d.t.Helper()
	raw := d.rpc("tools/call", map[string]any{"name": tool, "arguments": args})
	var res struct {
		Content []struct{ Text string } `json:"content"`
		IsError bool                    `json:"isError"`
	}
	json.Unmarshal(raw, &res)
	if res.IsError || len(res.Content) == 0 {
		d.t.Fatalf("question %s %v was not answered: %s", tool, args, raw)
	}
	d.last = res.Content[0].Text
}

func (d *MCPDriver) ShouldContain(texts ...string) {
	d.t.Helper()
	for _, s := range texts {
		if !strings.Contains(d.last, s) {
			d.t.Fatalf("expected answer to mention %q, got:\n%s", s, d.last)
		}
	}
}

var matchLine = regexp.MustCompile(`(?m)^- (\d{4})-\d\d-\d\d: .*\((.*)\)$`)

func (d *MCPDriver) matchLines() [][]string {
	d.t.Helper()
	ms := matchLine.FindAllStringSubmatch(d.last, -1)
	if len(ms) == 0 {
		d.t.Fatalf("expected matches, got:\n%s", d.last)
	}
	return ms
}

func (d *MCPDriver) ShouldListMatchesOnlyIn(year int) {
	d.t.Helper()
	for _, m := range d.matchLines() {
		if m[1] != strconv.Itoa(year) {
			d.t.Fatalf("match outside %d: %s", year, m[0])
		}
	}
}

func (d *MCPDriver) ShouldListMatchesOnlyFrom(c string) {
	d.t.Helper()
	for _, m := range d.matchLines() {
		if !strings.HasPrefix(m[2], c) {
			d.t.Fatalf("match not from %s: %s", c, m[0])
		}
	}
}

func (d *MCPDriver) MatchCount() int {
	d.t.Helper()
	m := regexp.MustCompile(`Found (\d+) matches`).FindStringSubmatch(d.last)
	if m == nil {
		d.t.Fatalf("no match count in:\n%s", d.last)
	}
	n, _ := strconv.Atoi(m[1])
	return n
}

func (d *MCPDriver) ShouldHaveMatchCount(n int) {
	d.t.Helper()
	if got := d.MatchCount(); got != n {
		d.t.Fatalf("expected %d matches, got %d", n, got)
	}
}

func (d *MCPDriver) ShouldHavePlayed(n int) {
	d.t.Helper()
	d.ShouldContain(fmt.Sprintf("Matches: %d\n", n))
}

func (d *MCPDriver) ShouldRankFirst(name string) {
	d.t.Helper()
	if !regexp.MustCompile(`(?m)^1\. ` + regexp.QuoteMeta(name) + ` `).MatchString(d.last) {
		d.t.Fatalf("expected %s ranked first, got:\n%s", name, d.last)
	}
}

func (d *MCPDriver) ShouldHaveChampion(team string, points int) {
	d.t.Helper()
	want := fmt.Sprintf("1. %s - %d pts", team, points)
	if !strings.Contains(d.last, want) || !strings.Contains(d.last, "Champion") {
		d.t.Fatalf("expected %q as champion, got:\n%s", want, d.last)
	}
}

func (d *MCPDriver) ShouldTakeLessThan(limit time.Duration, question func()) {
	d.t.Helper()
	start := time.Now()
	question()
	if el := time.Since(start); el > limit {
		d.t.Fatalf("answer took %v, limit %v", el, limit)
	}
}

func (d *MCPDriver) ShouldMarkRelegated(teams ...string) {
	d.t.Helper()
	var got []string
	for _, m := range regexp.MustCompile(`(?m)^\d+\. (.+?) - \d+ pts.*- Relegated$`).FindAllStringSubmatch(d.last, -1) {
		got = append(got, m[1])
	}
	if strings.Join(got, ",") != strings.Join(teams, ",") {
		d.t.Fatalf("expected relegated %v, got %v:\n%s", teams, got, d.last)
	}
}
