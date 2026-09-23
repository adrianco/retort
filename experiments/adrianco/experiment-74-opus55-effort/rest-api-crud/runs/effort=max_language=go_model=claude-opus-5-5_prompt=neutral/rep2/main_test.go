package main

import (
	"context"
	"io"
	"log/slog"
	"net"
	"net/http"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestParseConfig(t *testing.T) {
	env := map[string]string{"PORT": "9000", "DB_PATH": "/data/books.db"}
	tests := []struct {
		name string
		args []string
		env  map[string]string
		want config
	}{
		{"defaults", nil, nil, config{addr: ":8080", dbPath: "books.db"}},
		{"environment", nil, env, config{addr: ":9000", dbPath: "/data/books.db"}},
		{
			"flags override environment", []string{"-addr", "127.0.0.1:7000", "-db", ":memory:"}, env,
			config{addr: "127.0.0.1:7000", dbPath: ":memory:"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := parseConfig(tt.args, func(key string) string { return tt.env[key] })
			if err != nil {
				t.Fatalf("parseConfig: %v", err)
			}
			if got != tt.want {
				t.Errorf("parseConfig() = %+v, want %+v", got, tt.want)
			}
		})
	}
}

// TestRun starts the real server, uses the API over HTTP, and checks that
// cancelling the context shuts the server down cleanly.
func TestRun(t *testing.T) {
	addr := freeAddr(t)
	cfg := config{addr: addr, dbPath: filepath.Join(t.TempDir(), "books.db")}
	ctx, cancel := context.WithCancel(t.Context())
	defer cancel()
	done := make(chan error, 1)
	go func() { done <- run(ctx, cfg, slog.New(slog.DiscardHandler)) }()

	base := "http://" + addr
	client := &http.Client{Timeout: 5 * time.Second}
	waitUntilHealthy(t, client, base, done)

	resp, err := client.Post(base+"/books", "application/json", strings.NewReader(orwellJSON))
	if err != nil {
		t.Fatalf("POST /books: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("POST /books: status %d, want %d", resp.StatusCode, http.StatusCreated)
	}

	location := resp.Header.Get("Location")
	resp, err = client.Get(base + location)
	if err != nil {
		t.Fatalf("GET %s: %v", location, err)
	}
	body, err := io.ReadAll(resp.Body)
	resp.Body.Close()
	if err != nil {
		t.Fatalf("GET %s: reading body: %v", location, err)
	}
	if resp.StatusCode != http.StatusOK || !strings.Contains(string(body), `"title":"Nineteen Eighty-Four"`) {
		t.Fatalf("GET %s: status %d, body %s", location, resp.StatusCode, body)
	}

	cancel()
	select {
	case err := <-done:
		if err != nil {
			t.Errorf("run() = %v, want nil after a graceful shutdown", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("run did not return after its context was cancelled")
	}
}

func TestRunFailsWhenAddressIsTaken(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	defer ln.Close()

	cfg := config{addr: ln.Addr().String(), dbPath: ":memory:"}
	if err := run(t.Context(), cfg, slog.New(slog.DiscardHandler)); err == nil {
		t.Error("run() = nil, want an error for an address that is already in use")
	}
}

// freeAddr returns a loopback address whose port was free when checked.
func freeAddr(t *testing.T) string {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("finding a free port: %v", err)
	}
	defer ln.Close()
	return ln.Addr().String()
}

// waitUntilHealthy polls GET /health until it succeeds, failing the test if
// run exits first or the server doesn't come up in time.
func waitUntilHealthy(t *testing.T, client *http.Client, base string, done <-chan error) {
	t.Helper()
	deadline := time.Now().Add(5 * time.Second)
	for {
		select {
		case err := <-done:
			t.Fatalf("run exited early: %v", err)
		default:
		}
		if resp, err := client.Get(base + "/health"); err == nil {
			resp.Body.Close()
			if resp.StatusCode == http.StatusOK {
				return
			}
		}
		if time.Now().After(deadline) {
			t.Fatalf("server at %s did not become healthy", base)
		}
		time.Sleep(10 * time.Millisecond)
	}
}
