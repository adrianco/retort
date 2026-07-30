package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"testing"
	"time"
)

// syncBuffer collects log output written from the server goroutine.
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

var listenAddrRE = regexp.MustCompile(`addr=(127\.0\.0\.1:\d+)`)

// waitForListenAddr reads the address the server actually bound out of its own
// startup log, which is how the test learns the port chosen by :0.
func waitForListenAddr(t *testing.T, logs *syncBuffer) string {
	t.Helper()
	deadline := time.Now().Add(10 * time.Second)
	for time.Now().Before(deadline) {
		if m := listenAddrRE.FindStringSubmatch(logs.String()); m != nil {
			return m[1]
		}
		time.Sleep(5 * time.Millisecond)
	}
	t.Fatalf("server never logged a listen address; log so far:\n%s", logs.String())
	return ""
}

// TestRunServesAndShutsDownCleanly exercises the real entry point: flag
// parsing, database creation, serving traffic, and graceful shutdown on
// context cancellation.
func TestRunServesAndShutsDownCleanly(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "books.db")
	logs := &syncBuffer{}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	done := make(chan error, 1)
	go func() {
		done <- run(ctx, []string{"-addr", "127.0.0.1:0", "-db", dbPath}, logs)
	}()

	base := "http://" + waitForListenAddr(t, logs)

	res, err := http.Get(base + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	var health healthResponse
	if err := json.NewDecoder(res.Body).Decode(&health); err != nil {
		t.Fatalf("decoding health response: %v", err)
	}
	res.Body.Close()
	if res.StatusCode != http.StatusOK || health.Status != "ok" {
		t.Errorf("health = %d %+v, want 200 {ok up}", res.StatusCode, health)
	}

	res, err = http.Post(base+"/books", "application/json",
		strings.NewReader(`{"title":"Dune","author":"Frank Herbert","year":1965}`))
	if err != nil {
		t.Fatalf("POST /books: %v", err)
	}
	var created Book
	if err := json.NewDecoder(res.Body).Decode(&created); err != nil {
		t.Fatalf("decoding created book: %v", err)
	}
	res.Body.Close()
	if res.StatusCode != http.StatusCreated {
		t.Fatalf("POST /books status = %d, want 201", res.StatusCode)
	}
	if created.ID <= 0 {
		t.Errorf("created book has id %d, want a positive id", created.ID)
	}

	cancel()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("run() = %v, want nil after a clean shutdown", err)
		}
	case <-time.After(shutdownTimeout + 5*time.Second):
		t.Fatal("run() did not return after its context was cancelled")
	}

	if _, err := os.Stat(dbPath); err != nil {
		t.Errorf("database file was not created at %s: %v", dbPath, err)
	}
	if !strings.Contains(logs.String(), "stopped") {
		t.Errorf("shutdown was not logged; log:\n%s", logs.String())
	}
}

func TestRunReportsStartupFailures(t *testing.T) {
	tests := []struct {
		name    string
		args    []string
		wantErr string
	}{
		{
			name:    "unknown log level",
			args:    []string{"-log-level", "chatty", "-db", filepath.Join(t.TempDir(), "books.db")},
			wantErr: "unknown log level",
		},
		{
			name:    "database path in a directory that does not exist",
			args:    []string{"-db", filepath.Join(t.TempDir(), "missing", "books.db")},
			wantErr: "sqlite database",
		},
		{
			name:    "address already in a bad shape",
			args:    []string{"-addr", "127.0.0.1:not-a-port", "-db", filepath.Join(t.TempDir(), "books.db")},
			wantErr: "listen on",
		},
		{
			name:    "unknown flag",
			args:    []string{"-nonsense"},
			wantErr: "flag provided but not defined",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := run(context.Background(), tt.args, io.Discard)
			if err == nil {
				t.Fatalf("run(%v) = nil, want an error mentioning %q", tt.args, tt.wantErr)
			}
			if !strings.Contains(err.Error(), tt.wantErr) {
				t.Errorf("run(%v) = %q, want it to mention %q", tt.args, err, tt.wantErr)
			}
		})
	}
}

func TestParseLevel(t *testing.T) {
	for input, want := range map[string]slog.Level{
		"debug":   slog.LevelDebug,
		"INFO":    slog.LevelInfo,
		"":        slog.LevelInfo,
		" warn ":  slog.LevelWarn,
		"warning": slog.LevelWarn,
		"error":   slog.LevelError,
	} {
		got, err := parseLevel(input)
		if err != nil {
			t.Errorf("parseLevel(%q) returned %v", input, err)
			continue
		}
		if got != want {
			t.Errorf("parseLevel(%q) = %v, want %v", input, got, want)
		}
	}

	if _, err := parseLevel("loud"); err == nil {
		t.Error(`parseLevel("loud") = nil error, want a failure`)
	}
}

func TestEnvOr(t *testing.T) {
	const key = "BOOKAPI_TEST_ENV_OR"

	if got := envOr(key, "fallback"); got != "fallback" {
		t.Errorf("envOr with the variable unset = %q, want %q", got, "fallback")
	}

	t.Setenv(key, "")
	if got := envOr(key, "fallback"); got != "fallback" {
		t.Errorf("envOr with the variable empty = %q, want %q", got, "fallback")
	}

	t.Setenv(key, "from-env")
	if got := envOr(key, "fallback"); got != "from-env" {
		t.Errorf("envOr with the variable set = %q, want %q", got, "from-env")
	}
}
