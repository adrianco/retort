package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"testing"
	"time"
)

func noEnv(string) string { return "" }

func envOf(vars map[string]string) func(string) string {
	return func(key string) string { return vars[key] }
}

func TestParseConfig(t *testing.T) {
	tests := []struct {
		name string
		args []string
		env  map[string]string
		want config
	}{
		{"defaults", nil, nil, config{addr: ":8080", dbPath: "books.db"}},
		{"PORT sets the listen port", nil, map[string]string{"PORT": "9090"}, config{addr: ":9090", dbPath: "books.db"}},
		{"DB_PATH sets the database", nil, map[string]string{"DB_PATH": "/tmp/x.db"}, config{addr: ":8080", dbPath: "/tmp/x.db"}},
		{"flags", []string{"-addr", "127.0.0.1:7000", "-db", "data.db"}, nil, config{addr: "127.0.0.1:7000", dbPath: "data.db"}},
		{"flags beat the environment", []string{"-addr", ":1234", "-db", "f.db"},
			map[string]string{"PORT": "9090", "DB_PATH": "e.db"}, config{addr: ":1234", dbPath: "f.db"}},
		{"a flag can override just one setting", []string{"-db", "f.db"},
			map[string]string{"PORT": "9090"}, config{addr: ":9090", dbPath: "f.db"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := parseConfig(tt.args, envOf(tt.env), io.Discard)
			if err != nil {
				t.Fatalf("parseConfig: %v", err)
			}
			if got != tt.want {
				t.Errorf("config = %+v, want %+v", got, tt.want)
			}
		})
	}
}

func TestParseConfigErrors(t *testing.T) {
	for name, args := range map[string][]string{
		"unknown flag":       {"-nope"},
		"missing flag value": {"-addr"},
		"stray argument":     {"extra"},
	} {
		t.Run(name, func(t *testing.T) {
			var out bytes.Buffer
			if _, err := parseConfig(args, noEnv, &out); err == nil {
				t.Error("parseConfig succeeded, want an error")
			}
		})
	}

	var out bytes.Buffer
	if _, err := parseConfig([]string{"-h"}, noEnv, &out); !errors.Is(err, flag.ErrHelp) {
		t.Errorf("-h error = %v, want flag.ErrHelp", err)
	}
	if !strings.Contains(out.String(), "-addr") || !strings.Contains(out.String(), "-db") {
		t.Errorf("usage does not document the flags:\n%s", out.String())
	}
}

// syncBuffer lets the test read what the server goroutine logs.
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

var listeningAddr = regexp.MustCompile(`addr=(\S+)`)

// startApp runs the whole application on a random loopback port. It returns the
// base URL and an idempotent stop function that shuts the app down and reports
// what run returned. The test is skipped if the sandbox forbids listening.
func startApp(t *testing.T, dbPath string) (baseURL string, stop func() error) {
	t.Helper()

	logs := &syncBuffer{}
	ctx, cancel := context.WithCancel(context.Background())

	// run's result is stored before finished is closed, so any number of
	// callers can wait for it, including the cleanup after a failed start.
	var result error
	finished := make(chan struct{})
	go func() {
		defer close(finished)
		result = run(ctx, []string{"-addr", "127.0.0.1:0", "-db", dbPath}, noEnv, slog.New(slog.NewTextHandler(logs, nil)))
	}()

	// Bounded, so a shutdown bug fails this test quickly instead of hanging it
	// until go test's own timeout.
	stop = func() error {
		cancel()
		select {
		case <-finished:
			return result
		case <-time.After(15 * time.Second):
			t.Errorf("run did not return within 15s of being cancelled")
			return errors.New("run did not stop")
		}
	}
	t.Cleanup(func() { stop() })

	deadline := time.After(10 * time.Second)
	for {
		if m := listeningAddr.FindStringSubmatch(logs.String()); m != nil {
			return "http://" + m[1], stop
		}
		select {
		case <-finished:
			var opErr *net.OpError
			if errors.As(result, &opErr) && opErr.Op == "listen" {
				t.Skipf("cannot listen on the loopback interface here: %v", result)
			}
			t.Fatalf("run exited before it was listening: %v\nlogs: %s", result, logs)
		case <-deadline:
			t.Fatalf("timed out waiting for the server to listen\nlogs: %s", logs)
		case <-time.After(5 * time.Millisecond):
		}
	}
}

func TestRunServesTheAPIAndKeepsDataAcrossRestarts(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "books.db")
	client := &http.Client{Timeout: 5 * time.Second}

	base, stop := startApp(t, dbPath)

	resp, err := client.Get(base + "/health")
	if err != nil {
		t.Fatal(err)
	}
	var health map[string]string
	json.NewDecoder(resp.Body).Decode(&health)
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK || health["status"] != "ok" {
		t.Errorf("GET /health = %d %v, want 200 status ok", resp.StatusCode, health)
	}

	resp, err = client.Head(base + "/health")
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("HEAD /health = %d, want 200", resp.StatusCode)
	}

	resp, err = client.Post(base+"/books", "application/json",
		strings.NewReader(`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`))
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	location := resp.Header.Get("Location")
	if resp.StatusCode != http.StatusCreated || location == "" {
		t.Fatalf("POST /books = %d with Location %q, want 201 and a Location", resp.StatusCode, location)
	}

	// Shutting down is clean and really stops the server.
	if err := stop(); err != nil {
		t.Fatalf("run returned %v after shutdown, want nil", err)
	}
	if resp, err := client.Get(base + "/health"); err == nil {
		resp.Body.Close()
		t.Error("the server still answers after shutdown")
	}

	// A new process on the same database file sees the book stored by the first.
	base, _ = startApp(t, dbPath)
	resp, err = client.Get(base + location)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var got struct {
		Title string `json:"title"`
		Year  int    `json:"year"`
	}
	json.NewDecoder(resp.Body).Decode(&got)
	if resp.StatusCode != http.StatusOK || got.Title != "Dune" || got.Year != 1965 {
		t.Errorf("after restart GET %s = %d %+v, want the stored book", location, resp.StatusCode, got)
	}
}

func TestRunReportsStartupFailures(t *testing.T) {
	occupied, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Skipf("cannot listen on the loopback interface here: %v", err)
	}
	defer occupied.Close()

	// If a startup failure were missed, run would start serving; the deadline
	// stops it so the test fails promptly instead of hanging.
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	quiet := slog.New(slog.NewTextHandler(io.Discard, nil))

	freshDB := filepath.Join(t.TempDir(), "books.db")
	err = run(ctx, []string{"-addr", occupied.Addr().String(), "-db", freshDB}, noEnv, quiet)
	if err == nil || !strings.Contains(err.Error(), "listen on") {
		t.Errorf("run with the port in use returned %v, want a \"listen on\" error", err)
	}
	if _, err := os.Stat(freshDB); !errors.Is(err, os.ErrNotExist) {
		t.Errorf("a failed listen left a database file behind (stat error: %v)", err)
	}

	// An unusable database path is reported, and the port claimed just before
	// is handed back.
	free, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Skipf("cannot listen on the loopback interface here: %v", err)
	}
	addr := free.Addr().String()
	free.Close()

	missingDir := filepath.Join(t.TempDir(), "no-such-dir", "books.db")
	err = run(ctx, []string{"-addr", addr, "-db", missingDir}, noEnv, quiet)
	if err == nil || !strings.Contains(err.Error(), missingDir) {
		t.Errorf("run with an unusable database path returned %v, want an error naming %q", err, missingDir)
	}
	again, err := net.Listen("tcp", addr)
	if err != nil {
		t.Errorf("the port was not released after the database failed to open: %v", err)
	} else {
		again.Close()
	}
}

func TestServeReturnsListenerFailures(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Skipf("cannot listen on the loopback interface here: %v", err)
	}
	ln.Close() // serving on a closed listener fails immediately

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second) // fail, don't hang, if it did not
	defer cancel()
	err = serve(ctx, ln, http.NotFoundHandler(), slog.New(slog.NewTextHandler(io.Discard, nil)))
	if err == nil {
		t.Error("serve on a closed listener returned nil, want the failure")
	}
}

// Shutdown must let a request that is already being served finish, as the
// README promises, instead of cutting it off.
func TestServeLetsInFlightRequestsFinish(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Skipf("cannot listen on the loopback interface here: %v", err)
	}
	quiet := slog.New(slog.NewTextHandler(io.Discard, nil))

	started := make(chan struct{})
	release := make(chan struct{})
	slow := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		close(started)
		<-release
		io.WriteString(w, "finished")
	})

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	served := make(chan error, 1)
	go func() { served <- serve(ctx, ln, slow, quiet) }()

	type reply struct {
		body string
		err  error
	}
	replies := make(chan reply, 1)
	go func() {
		client := &http.Client{Timeout: 10 * time.Second}
		resp, err := client.Get("http://" + ln.Addr().String())
		if err != nil {
			replies <- reply{err: err}
			return
		}
		defer resp.Body.Close()
		body, err := io.ReadAll(resp.Body)
		replies <- reply{string(body), err}
	}()

	select {
	case <-started:
	case <-time.After(5 * time.Second):
		t.Fatal("the request never reached the handler")
	}

	cancel() // ask the server to shut down while the request is in flight
	select {
	case err := <-served:
		t.Fatalf("serve returned (%v) while a request was still in flight", err)
	case <-time.After(200 * time.Millisecond):
	}

	close(release)
	if r := <-replies; r.err != nil || r.body != "finished" {
		t.Errorf("in-flight request got %q, %v, want it to complete normally", r.body, r.err)
	}
	select {
	case err := <-served:
		if err != nil {
			t.Errorf("serve returned %v after draining, want nil", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("serve did not return after the in-flight request finished")
	}
}
