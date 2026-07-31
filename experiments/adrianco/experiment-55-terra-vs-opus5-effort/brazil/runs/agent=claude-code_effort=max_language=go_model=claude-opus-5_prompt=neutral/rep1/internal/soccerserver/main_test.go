package soccerserver

import (
	"strings"
	"sync"
	"testing"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// The datasets are loaded once and shared by every test in the package.
var (
	once        sync.Once
	sharedStore *soccer.Store
	sharedSrv   *mcp.Server
	sharedErr   error
)

func testServer(t testing.TB) *mcp.Server {
	t.Helper()
	once.Do(func() {
		sharedStore, sharedErr = soccer.Load(soccer.Options{})
		if sharedErr == nil {
			sharedSrv = New(sharedStore)
		}
	})
	if sharedErr != nil {
		t.Fatalf("loading datasets: %v", sharedErr)
	}
	return sharedSrv
}

func testStore(t testing.TB) *soccer.Store {
	t.Helper()
	testServer(t)
	return sharedStore
}

// answer calls a tool and returns its text, failing the test if the call
// errors or the tool reports a problem.
func answer(t testing.TB, tool string, args map[string]any) string {
	t.Helper()
	result, err := testServer(t).CallTool(tool, args)
	if err != nil {
		t.Fatalf("%s: %v", tool, err)
	}
	if result.IsError {
		t.Fatalf("%s reported an error: %s", tool, text(result))
	}
	if len(result.Content) == 0 || strings.TrimSpace(result.Content[0].Text) == "" {
		t.Fatalf("%s returned no text", tool)
	}
	return result.Content[0].Text
}

// failure calls a tool that is expected to refuse, and returns its message.
func failure(t testing.TB, tool string, args map[string]any) string {
	t.Helper()
	result, err := testServer(t).CallTool(tool, args)
	if err != nil {
		t.Fatalf("%s: %v", tool, err)
	}
	if !result.IsError {
		t.Fatalf("%s was expected to fail, but answered: %s", tool, text(result))
	}
	return text(result)
}

func text(r *mcp.ToolResult) string {
	var b strings.Builder
	for _, c := range r.Content {
		b.WriteString(c.Text)
	}
	return b.String()
}

// structured returns the structuredContent of a successful call.
func structured(t testing.TB, tool string, args map[string]any) map[string]any {
	t.Helper()
	result, err := testServer(t).CallTool(tool, args)
	if err != nil {
		t.Fatalf("%s: %v", tool, err)
	}
	if result.IsError {
		t.Fatalf("%s reported an error: %s", tool, text(result))
	}
	data, ok := result.StructuredContent.(map[string]any)
	if !ok {
		t.Fatalf("%s returned %T as structured content", tool, result.StructuredContent)
	}
	return data
}

func containsAll(t testing.TB, got string, wants ...string) {
	t.Helper()
	for _, want := range wants {
		if !strings.Contains(got, want) {
			t.Errorf("answer does not contain %q:\n%s", want, got)
		}
	}
}
