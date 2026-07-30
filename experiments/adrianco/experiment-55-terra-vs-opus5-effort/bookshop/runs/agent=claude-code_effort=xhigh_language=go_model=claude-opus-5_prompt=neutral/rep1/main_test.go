package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

// TestRunServesThenShutsDownCleanly starts the real binary's entry point on an
// ephemeral port, serves a request, and checks that cancelling the context
// stops it without an error — the path a SIGTERM takes in production.
func TestRunServesThenShutsDownCleanly(t *testing.T) {
	t.Parallel()

	logs := &syncBuffer{}
	ctx, cancel := context.WithCancel(t.Context())
	defer cancel()

	done := make(chan error, 1)
	go func() {
		done <- run(ctx, []string{
			"-addr", "127.0.0.1:0",
			"-db", filepath.Join(t.TempDir(), "books.db"),
		}, logs)
	}()

	addr := waitForListenAddr(t, logs)

	resp, err := http.Get("http://" + addr + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		t.Errorf("GET /health = %d, want 200; body: %s", resp.StatusCode, body)
	}

	cancel()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("run returned %v, want a clean shutdown", err)
		}
	case <-time.After(shutdownGrace + 5*time.Second):
		t.Fatal("run did not return after its context was cancelled")
	}

	if !strings.Contains(logs.String(), "stopped cleanly") {
		t.Errorf("shutdown was not logged; logs:\n%s", logs.String())
	}
}

func TestRunRejectsBadConfiguration(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name string
		args []string
	}{
		{name: "unknown flag", args: []string{"-nope"}},
		{name: "bad log level", args: []string{"-log-level", "chatty"}},
		{name: "undirectory database path", args: []string{"-db", filepath.Join(t.TempDir(), "missing", "books.db")}},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			// A free-form port is never reached: each case must fail first.
			args := append([]string{"-addr", "127.0.0.1:0"}, tc.args...)
			if err := run(t.Context(), args, io.Discard); err == nil {
				t.Errorf("run(%v) = nil, want an error", args)
			}
		})
	}
}

// Not parallel: t.Setenv mutates process-wide state.
func TestEnvOr(t *testing.T) {
	if got := envOr("BOOKAPI_TEST_UNSET_VAR", "fallback"); got != "fallback" {
		t.Errorf("envOr with no variable set = %q, want %q", got, "fallback")
	}

	t.Setenv("BOOKAPI_TEST_VAR", "from-env")
	if got := envOr("BOOKAPI_TEST_VAR", "fallback"); got != "from-env" {
		t.Errorf("envOr = %q, want the environment value", got)
	}

	// An empty variable is treated as unset, so `BOOKAPI_DB= bookapi` still
	// gets a usable default instead of trying to open "".
	t.Setenv("BOOKAPI_TEST_VAR", "")
	if got := envOr("BOOKAPI_TEST_VAR", "fallback"); got != "fallback" {
		t.Errorf("envOr with an empty variable = %q, want %q", got, "fallback")
	}
}

func TestParseLevel(t *testing.T) {
	t.Parallel()

	for name, want := range map[string]slog.Level{
		"debug": slog.LevelDebug,
		"info":  slog.LevelInfo,
		"WARN":  slog.LevelWarn,
		"error": slog.LevelError,
	} {
		got, err := parseLevel(name)
		if err != nil {
			t.Errorf("parseLevel(%q): %v", name, err)
			continue
		}
		if got != want {
			t.Errorf("parseLevel(%q) = %v, want %v", name, got, want)
		}
	}

	if _, err := parseLevel("verbose"); err == nil {
		t.Error("parseLevel(\"verbose\") = nil error, want a rejection")
	}
}

// waitForListenAddr blocks until run logs the address it bound to, and returns
// it. Reading the address from the log avoids racing to guess a free port.
func waitForListenAddr(t *testing.T, logs *syncBuffer) string {
	t.Helper()

	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		for line := range strings.SplitSeq(logs.String(), "\n") {
			var entry struct {
				Msg  string `json:"msg"`
				Addr string `json:"addr"`
			}
			if json.Unmarshal([]byte(line), &entry) == nil && entry.Msg == "listening" {
				return entry.Addr
			}
		}
		time.Sleep(10 * time.Millisecond)
	}

	t.Fatalf("server never logged a listen address; logs:\n%s", logs.String())
	return ""
}

// syncBuffer collects log output written by the server goroutine while the
// test goroutine reads it.
type syncBuffer struct {
	mu  sync.Mutex
	buf bytes.Buffer
}

func (b *syncBuffer) Write(p []byte) (int, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.Write(p)
}

func (b *syncBuffer) String() string {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.String()
}
