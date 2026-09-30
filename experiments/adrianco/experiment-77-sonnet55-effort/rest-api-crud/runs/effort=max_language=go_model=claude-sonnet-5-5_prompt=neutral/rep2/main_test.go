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
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"slices"
	"strings"
	"sync"
	"syscall"
	"testing"
	"time"
)

// TestMain lets the tests run this binary as the real program: with
// BOOKAPI_RUN_MAIN=1 it executes main() instead of the tests, so exit codes and
// signal handling can be checked in a child process.
func TestMain(m *testing.M) {
	if os.Getenv("BOOKAPI_RUN_MAIN") == "1" {
		main()
		os.Exit(0)
	}
	os.Exit(m.Run())
}

func TestLoadConfig(t *testing.T) {
	tests := []struct {
		name    string
		args    []string
		env     map[string]string
		want    config
		wantErr string // substring of the reported problem; empty means success
	}{
		{name: "defaults", want: config{addr: ":8080", dbPath: "books.db"}},
		{name: "PORT sets the port", env: map[string]string{"PORT": "9000"}, want: config{addr: ":9000", dbPath: "books.db"}},
		{name: "DB_PATH sets the database", env: map[string]string{"DB_PATH": "/data/b.db"}, want: config{addr: ":8080", dbPath: "/data/b.db"}},
		{
			name: "flags",
			args: []string{"-addr", "127.0.0.1:1234", "-db", "flag.db"},
			want: config{addr: "127.0.0.1:1234", dbPath: "flag.db"},
		},
		{
			name: "flags take precedence over the environment",
			args: []string{"-addr", ":1", "-db", "flag.db"},
			env:  map[string]string{"PORT": "9000", "DB_PATH": "env.db"},
			want: config{addr: ":1", dbPath: "flag.db"},
		},
		{name: "unknown flag", args: []string{"-nope"}, wantErr: "flag provided but not defined"},
		{name: "positional argument", args: []string{"extra"}, wantErr: `unexpected argument "extra"`},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var stderr bytes.Buffer
			getenv := func(k string) string { return tt.env[k] }

			got, err := loadConfig(tt.args, getenv, &stderr)
			if tt.wantErr != "" {
				if err == nil {
					t.Fatalf("loadConfig(%v) succeeded, want an error", tt.args)
				}
				if !strings.Contains(stderr.String(), tt.wantErr) {
					t.Errorf("stderr = %q, want it to mention %q", stderr.String(), tt.wantErr)
				}
				return
			}
			if err != nil {
				t.Fatalf("loadConfig: %v", err)
			}
			if got != tt.want {
				t.Errorf("config = %+v, want %+v", got, tt.want)
			}
		})
	}
}

func TestLoadConfigHelpListsTheFlags(t *testing.T) {
	var stderr bytes.Buffer
	_, err := loadConfig([]string{"-h"}, func(string) string { return "" }, &stderr)
	if !errors.Is(err, flag.ErrHelp) {
		t.Fatalf("error = %v, want flag.ErrHelp", err)
	}
	for _, want := range []string{"-addr", "-db", "PORT", "DB_PATH"} {
		if !strings.Contains(stderr.String(), want) {
			t.Errorf("usage does not mention %q:\n%s", want, stderr.String())
		}
	}
}

// startServer runs the real server on an ephemeral port. stop shuts it down
// gracefully and returns run's result; it is safe to call more than once.
func startServer(t *testing.T, dbPath string) (baseURL string, stop func() error) {
	t.Helper()
	ctx, cancel := context.WithCancel(context.Background())
	ready := make(chan net.Addr, 1)
	done := make(chan error, 1)
	go func() {
		cfg := config{addr: "127.0.0.1:0", dbPath: dbPath}
		done <- run(ctx, cfg, slog.New(slog.DiscardHandler), func(a net.Addr) { ready <- a })
	}()

	select {
	case addr := <-ready:
		baseURL = "http://" + addr.String()
	case err := <-done:
		cancel()
		t.Fatalf("server exited before it was ready: %v", err)
	case <-time.After(10 * time.Second):
		cancel()
		t.Fatal("server did not become ready")
	}

	stop = sync.OnceValue(func() error {
		cancel()
		select {
		case err := <-done:
			return err
		case <-time.After(15 * time.Second):
			return errors.New("server did not shut down in time")
		}
	})
	t.Cleanup(func() { stop() })
	return baseURL, stop
}

// call sends a real HTTP request and returns the status, headers and body.
func call(t *testing.T, method, url, body string) (int, http.Header, string) {
	t.Helper()
	var reader io.Reader
	if body != "" {
		reader = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, url, reader)
	if err != nil {
		t.Fatal(err)
	}
	client := &http.Client{Timeout: 5 * time.Second, Transport: &http.Transport{DisableKeepAlives: true}}
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("%s %s: reading body: %v", method, url, err)
	}
	return resp.StatusCode, resp.Header, string(data)
}

func expectStatus(t *testing.T, got, want int, body string) {
	t.Helper()
	if got != want {
		t.Fatalf("status = %d, want %d; body: %s", got, want, body)
	}
}

func TestServerEndToEnd(t *testing.T) {
	baseURL, stop := startServer(t, filepath.Join(t.TempDir(), "books.db"))

	status, _, body := call(t, http.MethodGet, baseURL+"/health", "")
	expectStatus(t, status, http.StatusOK, body)
	if strings.TrimSpace(body) != `{"status":"ok"}` {
		t.Errorf("health body = %q", body)
	}

	status, header, body := call(t, http.MethodPost, baseURL+"/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`)
	expectStatus(t, status, http.StatusCreated, body)
	if loc := header.Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	status, _, body = call(t, http.MethodGet, baseURL+"/books?author=frank+herbert", "")
	expectStatus(t, status, http.StatusOK, body)
	var listed []map[string]any
	if err := json.Unmarshal([]byte(body), &listed); err != nil || len(listed) != 1 || listed[0]["title"] != "Dune" {
		t.Errorf("filtered list = %s (%v), want exactly Dune", body, err)
	}

	status, _, body = call(t, http.MethodPut, baseURL+"/books/1", `{"title":"Dune Messiah","author":"Frank Herbert"}`)
	expectStatus(t, status, http.StatusOK, body)

	status, _, body = call(t, http.MethodGet, baseURL+"/books/1", "")
	expectStatus(t, status, http.StatusOK, body)
	if !strings.Contains(body, `"title":"Dune Messiah"`) {
		t.Errorf("book after update = %s", body)
	}

	status, _, body = call(t, http.MethodDelete, baseURL+"/books/1", "")
	expectStatus(t, status, http.StatusNoContent, body)
	status, _, body = call(t, http.MethodGet, baseURL+"/books/1", "")
	expectStatus(t, status, http.StatusNotFound, body)

	if err := stop(); err != nil {
		t.Fatalf("graceful shutdown: %v", err)
	}
	client := &http.Client{Timeout: 2 * time.Second, Transport: &http.Transport{DisableKeepAlives: true}}
	if resp, err := client.Get(baseURL + "/health"); err == nil {
		resp.Body.Close()
		t.Error("server still accepts connections after shutdown")
	}
}

func TestDataSurvivesRestart(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "books.db")

	baseURL, stop := startServer(t, dbPath)
	status, _, body := call(t, http.MethodPost, baseURL+"/books", `{"title":"Durable","author":"Disk","year":2024,"isbn":"42"}`)
	expectStatus(t, status, http.StatusCreated, body)
	if err := stop(); err != nil {
		t.Fatalf("shutdown: %v", err)
	}

	baseURL, _ = startServer(t, dbPath)
	status, _, got := call(t, http.MethodGet, baseURL+"/books/1", "")
	expectStatus(t, status, http.StatusOK, got)
	if strings.TrimSpace(got) != strings.TrimSpace(body) {
		t.Errorf("after restart GET /books/1 = %s, want %s", got, body)
	}
}

func TestRunFailsFastOnUnusableConfig(t *testing.T) {
	busy, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer busy.Close()

	tests := []struct {
		name string
		cfg  config
	}{
		{"database directory does not exist", config{addr: "127.0.0.1:0", dbPath: filepath.Join(t.TempDir(), "missing", "books.db")}},
		{"database path is empty", config{addr: "127.0.0.1:0", dbPath: ""}},
		{"port already in use", config{addr: busy.Addr().String(), dbPath: filepath.Join(t.TempDir(), "books.db")}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// The timeout only guards against run wrongly serving forever.
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			if err := run(ctx, tt.cfg, slog.New(slog.DiscardHandler), nil); err == nil {
				t.Error("run succeeded, want an error")
			}
		})
	}
}

// syncBuffer is a bytes.Buffer that can be read while a child process writes to it.
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

// startMain runs main() in a child process with the given arguments.
func startMain(t *testing.T, args ...string) (*exec.Cmd, *syncBuffer) {
	t.Helper()
	cmd := exec.Command(os.Args[0], args...)
	// Keep the developer's own PORT/DB_PATH out of the child so the run is hermetic.
	env := slices.DeleteFunc(os.Environ(), func(kv string) bool {
		return strings.HasPrefix(kv, "PORT=") || strings.HasPrefix(kv, "DB_PATH=")
	})
	cmd.Env = append(env, "BOOKAPI_RUN_MAIN=1")
	stderr := &syncBuffer{}
	cmd.Stderr = stderr
	if err := cmd.Start(); err != nil {
		t.Fatalf("starting child process: %v", err)
	}
	t.Cleanup(func() { cmd.Process.Kill() }) // a no-op once the child has exited
	return cmd, stderr
}

// exitCode waits for the child to exit and returns its exit code.
func exitCode(t *testing.T, cmd *exec.Cmd) int {
	t.Helper()
	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()

	select {
	case err := <-done:
		var exitErr *exec.ExitError
		switch {
		case err == nil:
			return 0
		case errors.As(err, &exitErr):
			return exitErr.ExitCode()
		default:
			t.Fatalf("waiting for child process: %v", err)
		}
	case <-time.After(15 * time.Second):
		cmd.Process.Kill()
		t.Fatal("child process did not exit in time")
	}
	return -1
}

var listeningAddr = regexp.MustCompile(`msg=listening addr=(\S+)`)

// waitListening returns the address the child reports it is serving on.
func waitListening(t *testing.T, stderr *syncBuffer) string {
	t.Helper()
	for deadline := time.Now().Add(10 * time.Second); time.Now().Before(deadline); time.Sleep(20 * time.Millisecond) {
		if m := listeningAddr.FindStringSubmatch(stderr.String()); m != nil {
			return m[1]
		}
	}
	t.Fatalf("server never reported its address; stderr:\n%s", stderr.String())
	return ""
}

func TestMainExitCodes(t *testing.T) {
	busy, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer busy.Close()

	tests := []struct {
		name       string
		args       []string
		wantCode   int
		wantStderr string
	}{
		{"help", []string{"-h"}, 0, "-addr"},
		{"unknown flag", []string{"-bogus"}, 2, "flag provided but not defined"},
		{
			"port already in use",
			[]string{"-addr", busy.Addr().String(), "-db", filepath.Join(t.TempDir(), "books.db")},
			1, "server failed",
		},
		{
			"unusable database",
			[]string{"-addr", "127.0.0.1:0", "-db", filepath.Join(t.TempDir(), "missing", "books.db")},
			1, "server failed",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cmd, stderr := startMain(t, tt.args...)
			if code := exitCode(t, cmd); code != tt.wantCode {
				t.Errorf("exit code = %d, want %d; stderr:\n%s", code, tt.wantCode, stderr.String())
			}
			if !strings.Contains(stderr.String(), tt.wantStderr) {
				t.Errorf("stderr does not contain %q:\n%s", tt.wantStderr, stderr.String())
			}
		})
	}
}

func TestMainShutsDownGracefullyOnSignal(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("POSIX signals cannot be sent to a process on Windows")
	}
	for _, sig := range []os.Signal{syscall.SIGTERM, os.Interrupt} {
		t.Run(sig.String(), func(t *testing.T) {
			cmd, stderr := startMain(t, "-addr", "127.0.0.1:0", "-db", filepath.Join(t.TempDir(), "books.db"))
			addr := waitListening(t, stderr)

			status, _, body := call(t, http.MethodGet, "http://"+addr+"/health", "")
			expectStatus(t, status, http.StatusOK, body)

			if err := cmd.Process.Signal(sig); err != nil {
				t.Fatalf("sending %v: %v", sig, err)
			}
			if code := exitCode(t, cmd); code != 0 {
				t.Errorf("exit code = %d, want 0 after a graceful shutdown; stderr:\n%s", code, stderr.String())
			}
			if !strings.Contains(stderr.String(), "shutting down") {
				t.Errorf("stderr does not show a graceful shutdown:\n%s", stderr.String())
			}
		})
	}
}
