package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"testing"
	"time"

	"bookapi/internal/api"
	"bookapi/internal/book"
	"bookapi/internal/store"
)

func lookup(env map[string]string) func(string) string {
	return func(key string) string { return env[key] }
}

func TestLoadConfig(t *testing.T) {
	tests := []struct {
		name string
		args []string
		env  map[string]string
		want config
	}{
		{name: "defaults", want: config{addr: ":8080", dbPath: "books.db"}},
		{name: "PORT sets the port", env: map[string]string{"PORT": "9090"}, want: config{addr: ":9090", dbPath: "books.db"}},
		{name: "ADDR sets the address", env: map[string]string{"ADDR": "127.0.0.1:7000"}, want: config{addr: "127.0.0.1:7000", dbPath: "books.db"}},
		{name: "ADDR wins over PORT", env: map[string]string{"ADDR": "127.0.0.1:7000", "PORT": "9090"}, want: config{addr: "127.0.0.1:7000", dbPath: "books.db"}},
		{name: "DB_PATH sets the database", env: map[string]string{"DB_PATH": "/var/lib/books.db"}, want: config{addr: ":8080", dbPath: "/var/lib/books.db"}},
		{name: "flags", args: []string{"-addr", ":1234", "-db", "x.db"}, want: config{addr: ":1234", dbPath: "x.db"}},
		{name: "double-dash flags", args: []string{"--addr=:1234", "--db=:memory:"}, want: config{addr: ":1234", dbPath: ":memory:"}},
		{
			name: "flags override the environment",
			args: []string{"-addr", ":1", "-db", "flag.db"},
			env:  map[string]string{"ADDR": ":2", "PORT": "3", "DB_PATH": "env.db"},
			want: config{addr: ":1", dbPath: "flag.db"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var out bytes.Buffer
			got, err := loadConfig(tt.args, lookup(tt.env), &out)
			if err != nil {
				t.Fatalf("loadConfig: %v\n%s", err, out.String())
			}
			if got != tt.want {
				t.Errorf("config = %+v, want %+v", got, tt.want)
			}
		})
	}
}

func TestLoadConfigRejectsBadInvocations(t *testing.T) {
	tests := []struct {
		name    string
		args    []string
		wantErr error  // nil means any error
		output  string // must appear on the output writer
	}{
		{name: "unknown flag", args: []string{"-bogus"}, output: "-bogus"},
		{name: "flag without a value", args: []string{"-db"}, output: "-db"},
		{name: "positional argument", args: []string{"extra"}, output: `unexpected argument "extra"`},
		{name: "empty address", args: []string{"-addr", ""}, output: "-addr must not be empty"},
		{name: "empty database path", args: []string{"-db="}, output: "-db must not be empty"},
		{name: "help", args: []string{"-h"}, wantErr: flag.ErrHelp, output: "-addr"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var out bytes.Buffer
			_, err := loadConfig(tt.args, lookup(nil), &out)
			if err == nil {
				t.Fatal("loadConfig succeeded, want an error")
			}
			if tt.wantErr != nil && !errors.Is(err, tt.wantErr) {
				t.Errorf("error = %v, want %v", err, tt.wantErr)
			}
			if !strings.Contains(out.String(), tt.output) {
				t.Errorf("output %q does not contain %q", out.String(), tt.output)
			}
		})
	}
}

// runningApp is a service started by startApp.
type runningApp struct {
	baseURL string
	addr    string
	cancel  context.CancelFunc // begins the shutdown
	done    <-chan error       // receives what run returns
}

// startApp runs the service on a free loopback port. Each tweak may adjust the
// app before it starts serving.
func startApp(t *testing.T, dbPath string, tweaks ...func(*app)) *runningApp {
	t.Helper()
	a, err := newApp(config{addr: "127.0.0.1:0", dbPath: dbPath}, slog.New(slog.NewTextHandler(io.Discard, nil)))
	if err != nil {
		t.Fatalf("newApp: %v", err)
	}
	for _, tweak := range tweaks {
		tweak(a)
	}
	ctx, cancel := context.WithCancel(t.Context())
	t.Cleanup(cancel)
	done := make(chan error, 1)
	go func() { done <- a.run(ctx) }()

	addr := a.ln.Addr().String()
	return &runningApp{baseURL: "http://" + addr, addr: addr, cancel: cancel, done: done}
}

// wait blocks until run has returned and checks that it shut down cleanly.
func (r *runningApp) wait(t *testing.T) {
	t.Helper()
	select {
	case err := <-r.done:
		if err != nil {
			t.Errorf("run returned %v, want nil after a clean shutdown", err)
		}
	case <-time.After(15 * time.Second):
		t.Fatal("run did not return after its context was cancelled")
	}
}

// stop begins the shutdown and waits for it to finish.
func (r *runningApp) stop(t *testing.T) {
	t.Helper()
	r.cancel()
	r.wait(t)
}

// client does not reuse connections, so that a stopped server is really
// observed as unreachable.
var client = &http.Client{
	Timeout:   5 * time.Second,
	Transport: &http.Transport{DisableKeepAlives: true},
}

func request(t *testing.T, method, url, body string) (int, []byte) {
	t.Helper()
	req, err := http.NewRequestWithContext(t.Context(), method, url, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := client.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatal(err)
	}
	return resp.StatusCode, data
}

func TestServiceEndToEnd(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "books.db")
	srv := startApp(t, dbPath)
	base := srv.baseURL

	if status, body := request(t, http.MethodGet, base+"/health", ""); status != http.StatusOK || !strings.Contains(string(body), `"ok"`) {
		t.Fatalf("GET /health = %d %s", status, body)
	}

	status, body := request(t, http.MethodPost, base+"/books",
		`{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"9780134190440"}`)
	if status != http.StatusCreated {
		t.Fatalf("POST /books = %d %s", status, body)
	}
	var created book.Book
	if err := json.Unmarshal(body, &created); err != nil || created.ID == 0 {
		t.Fatalf("POST /books returned %s (%v), want a book with an id", body, err)
	}

	if status, _ := request(t, http.MethodPost, base+"/books", `{"title":"No author"}`); status != http.StatusBadRequest {
		t.Errorf("POST without an author = %d, want 400", status)
	}

	srv.stop(t)
	if resp, err := client.Get(base + "/health"); err == nil {
		resp.Body.Close()
		t.Fatal("the server still answers after shutdown")
	}

	// A new process on the same database file sees the book stored earlier.
	srv = startApp(t, dbPath)
	defer srv.stop(t)
	status, body = request(t, http.MethodGet, srv.baseURL+"/books/"+strconv.FormatInt(created.ID, 10), "")
	if status != http.StatusOK {
		t.Fatalf("GET after restart = %d %s", status, body)
	}
	var got book.Book
	if err := json.Unmarshal(body, &got); err != nil || got != created {
		t.Errorf("after restart got %+v (%v), want %+v", got, err, created)
	}
}

func TestServesFromMemoryDatabase(t *testing.T) {
	srv := startApp(t, store.Memory)
	defer srv.stop(t)

	if status, body := request(t, http.MethodPost, srv.baseURL+"/books", `{"title":"T","author":"A"}`); status != http.StatusCreated {
		t.Fatalf("POST /books = %d %s", status, body)
	}
	status, body := request(t, http.MethodGet, srv.baseURL+"/books?author=a", "")
	if status != http.StatusOK || !strings.Contains(string(body), `"title":"T"`) {
		t.Errorf("GET /books = %d %s", status, body)
	}
}

func TestShutdownLetsInFlightRequestsFinish(t *testing.T) {
	active := make(chan struct{}, 1)
	srv := startApp(t, filepath.Join(t.TempDir(), "books.db"), func(a *app) {
		a.srv.ConnState = func(_ net.Conn, state http.ConnState) {
			if state == http.StateActive {
				select {
				case active <- struct{}{}:
				default:
				}
			}
		}
	})

	// Send a request whose body is only half there, so that it is in flight.
	conn, err := net.Dial("tcp", srv.addr)
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	conn.SetDeadline(time.Now().Add(10 * time.Second))
	const body = `{"title":"Still in flight","author":"Patient Client"}`
	head := fmt.Sprintf("POST /books HTTP/1.1\r\nHost: test\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n", len(body))
	half := len(body) / 2
	if _, err := io.WriteString(conn, head+body[:half]); err != nil {
		t.Fatal(err)
	}
	select {
	case <-active:
	case <-time.After(5 * time.Second):
		t.Fatal("the server never started on the request")
	}

	// Begin the shutdown, and wait until the service has stopped accepting
	// connections, so that the shutdown is certainly under way.
	srv.cancel()
	for deadline := time.Now().Add(5 * time.Second); ; time.Sleep(10 * time.Millisecond) {
		c, err := net.DialTimeout("tcp", srv.addr, time.Second)
		if err != nil {
			break
		}
		c.Close()
		if time.Now().After(deadline) {
			t.Fatal("the service kept accepting connections after being told to shut down")
		}
	}

	// The request that was already in flight must still be completed.
	if _, err := io.WriteString(conn, body[half:]); err != nil {
		t.Fatalf("finishing the request during shutdown: %v", err)
	}
	resp, err := http.ReadResponse(bufio.NewReader(conn), nil)
	if err != nil {
		t.Fatalf("reading the response during shutdown: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("in-flight request got status %d during shutdown, want 201", resp.StatusCode)
	}

	srv.wait(t)
}

func TestRunReturnsServerFailureAndClosesDatabase(t *testing.T) {
	a, err := newApp(config{addr: "127.0.0.1:0", dbPath: filepath.Join(t.TempDir(), "books.db")},
		slog.New(slog.NewTextHandler(io.Discard, nil)))
	if err != nil {
		t.Fatalf("newApp: %v", err)
	}
	a.ln.Close() // the server can no longer accept connections

	if err := a.run(t.Context()); err == nil {
		t.Fatal("run returned nil, want the server failure")
	}
	if err := a.store.Ping(t.Context()); err == nil {
		t.Error("the database is still open after run failed")
	}
}

func TestNewAppReportsStartupFailures(t *testing.T) {
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))

	t.Run("unusable database path", func(t *testing.T) {
		cfg := config{addr: "127.0.0.1:0", dbPath: filepath.Join(t.TempDir(), "missing", "books.db")}
		if a, err := newApp(cfg, logger); err == nil {
			a.store.Close()
			a.ln.Close()
			t.Fatal("newApp succeeded, want an error")
		}
	})

	t.Run("address already in use", func(t *testing.T) {
		busy, err := net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			t.Fatal(err)
		}
		defer busy.Close()
		cfg := config{addr: busy.Addr().String(), dbPath: filepath.Join(t.TempDir(), "books.db")}
		if a, err := newApp(cfg, logger); err == nil {
			a.store.Close()
			a.ln.Close()
			t.Fatal("newApp succeeded on an occupied address, want an error")
		}
	})
}

func TestHalfClosedClientsAreServed(t *testing.T) {
	srv := startApp(t, filepath.Join(t.TempDir(), "books.db"))
	defer srv.stop(t)

	// A client that closes its sending side after writing its request, as some
	// simple tools do, has not gone away: it is waiting for the answer. net/http
	// cancels the request context at that moment, which must not affect it.
	const body = `{"title":"Half closed","author":"Patient Client"}`
	const attempts = 50
	for i := range attempts {
		conn, err := net.Dial("tcp", srv.addr)
		if err != nil {
			t.Fatal(err)
		}
		conn.SetDeadline(time.Now().Add(10 * time.Second))
		fmt.Fprintf(conn, "POST /books HTTP/1.1\r\nHost: test\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s", len(body), body)
		if err := conn.(*net.TCPConn).CloseWrite(); err != nil {
			t.Fatal(err)
		}
		resp, err := http.ReadResponse(bufio.NewReader(conn), nil)
		if err != nil {
			t.Fatalf("attempt %d: reading the response: %v", i, err)
		}
		resp.Body.Close()
		conn.Close()
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("attempt %d: status %d, want 201", i, resp.StatusCode)
		}
	}

	// Every acknowledged write must really be stored.
	status, data := request(t, http.MethodGet, srv.baseURL+"/books", "")
	var books []book.Book
	if err := json.Unmarshal(data, &books); status != http.StatusOK || err != nil || len(books) != attempts {
		t.Errorf("GET /books = %d with %d books (%v), want %d books", status, len(books), err, attempts)
	}
}

func TestServerTimeoutsAreConfigured(t *testing.T) {
	a, err := newApp(config{addr: "127.0.0.1:0", dbPath: store.Memory}, slog.New(slog.NewTextHandler(io.Discard, nil)))
	if err != nil {
		t.Fatal(err)
	}
	defer a.ln.Close()
	defer a.store.Close()

	for name, d := range map[string]time.Duration{
		"ReadHeaderTimeout": a.srv.ReadHeaderTimeout,
		"ReadTimeout":       a.srv.ReadTimeout,
		"WriteTimeout":      a.srv.WriteTimeout,
		"IdleTimeout":       a.srv.IdleTimeout,
	} {
		if d <= 0 {
			t.Errorf("%s is not set, so slow or idle clients could hold connections open indefinitely", name)
		}
	}

	// The slowest permitted request waits api.RequestTimeout for its turn at the
	// database, and a write can then wait store.BusyTimeout for a lock. The
	// server must still have time to report the outcome, and a shutdown must be
	// able to wait for it.
	longestRequest := api.RequestTimeout + store.BusyTimeout
	if write := a.srv.WriteTimeout; write <= longestRequest {
		t.Errorf("WriteTimeout %v does not exceed the longest request, %v", write, longestRequest)
	}
	if shutdown := shutdownTimeout; shutdown <= longestRequest {
		t.Errorf("shutdownTimeout %v does not exceed the longest request, %v", shutdown, longestRequest)
	}

	// The README quotes these two numbers.
	if api.RequestTimeout != 8*time.Second || store.BusyTimeout != 5*time.Second {
		t.Errorf("api.RequestTimeout is %v and store.BusyTimeout is %v; the README says 8s and 5s, so update it",
			api.RequestTimeout, store.BusyTimeout)
	}
}

// TestMain lets the test binary stand in for the bookapi executable: when
// BOOKAPI_TEST_RUN_MAIN is set it runs main() itself, so that flag handling,
// exit codes and signal handling can be tested on a real process.
func TestMain(m *testing.M) {
	if os.Getenv("BOOKAPI_TEST_RUN_MAIN") == "1" {
		main()
		return
	}
	os.Exit(m.Run())
}

// startMain runs main() in a child process. It returns the process and the
// lines it writes to standard error, which end when the process exits.
func startMain(t *testing.T, env []string, args ...string) (*exec.Cmd, <-chan string) {
	t.Helper()
	cmd := exec.Command(os.Args[0], args...)
	cmd.Env = append(append(os.Environ(), "BOOKAPI_TEST_RUN_MAIN=1"), env...)
	stderr, err := cmd.StderrPipe()
	if err != nil {
		t.Fatal(err)
	}
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	// A watchdog, so that a server that wrongly keeps running cannot hang the tests.
	watchdog := time.AfterFunc(30*time.Second, func() { cmd.Process.Kill() })
	t.Cleanup(func() {
		watchdog.Stop()
		cmd.Process.Kill()
	})

	lines := make(chan string, 256)
	go func() {
		defer close(lines)
		for sc := bufio.NewScanner(stderr); sc.Scan(); {
			lines <- sc.Text()
		}
	}()
	return cmd, lines
}

func TestMainExitCodes(t *testing.T) {
	busy, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer busy.Close()
	dir := t.TempDir()

	tests := []struct {
		name     string
		args     []string
		wantCode int
		wantLog  string
	}{
		{"help", []string{"-h"}, 0, "Usage of bookapi"},
		{"unknown flag", []string{"-bogus"}, 2, "flag provided but not defined: -bogus"},
		{"empty address", []string{"-addr", ""}, 2, "-addr must not be empty"},
		{"missing database directory", []string{"-addr", "127.0.0.1:0", "-db", filepath.Join(dir, "missing", "books.db")}, 1, "database directory"},
		{"address already in use", []string{"-addr", busy.Addr().String(), "-db", filepath.Join(dir, "books.db")}, 1, "address already in use"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cmd, lines := startMain(t, nil, tt.args...)
			var out strings.Builder
			for line := range lines {
				out.WriteString(line + "\n")
			}
			code := 0
			if err := cmd.Wait(); err != nil {
				var exitErr *exec.ExitError
				if !errors.As(err, &exitErr) {
					t.Fatal(err)
				}
				code = exitErr.ExitCode()
			}
			if code != tt.wantCode {
				t.Errorf("exit code %d, want %d\n%s", code, tt.wantCode, out.String())
			}
			if !strings.Contains(out.String(), tt.wantLog) {
				t.Errorf("output does not contain %q:\n%s", tt.wantLog, out.String())
			}
		})
	}
}

var listeningLine = regexp.MustCompile(`msg=listening addr=(\S+)`)

// waitListening reads the child's log until it reports the address it listens
// on, appending what it reads to out.
func waitListening(t *testing.T, lines <-chan string, out *strings.Builder) string {
	t.Helper()
	for {
		select {
		case line, ok := <-lines:
			if !ok {
				t.Fatalf("the server exited before it was listening:\n%s", out.String())
			}
			out.WriteString(line + "\n")
			if m := listeningLine.FindStringSubmatch(line); m != nil {
				return m[1]
			}
		case <-time.After(20 * time.Second):
			t.Fatalf("the server did not start listening:\n%s", out.String())
		}
	}
}

func TestMainShutsDownGracefullyOnSignals(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("relies on POSIX signals")
	}
	for _, sig := range []syscall.Signal{syscall.SIGINT, syscall.SIGTERM} {
		t.Run(sig.String(), func(t *testing.T) {
			// The settings come from the environment, which exercises that plumbing too.
			dbPath := filepath.Join(t.TempDir(), "books.db")
			cmd, lines := startMain(t, []string{"ADDR=127.0.0.1:0", "DB_PATH=" + dbPath})

			var out strings.Builder
			addr := waitListening(t, lines, &out)
			if status, body := request(t, http.MethodGet, "http://"+addr+"/health", ""); status != http.StatusOK {
				t.Fatalf("GET /health = %d %s", status, body)
			}

			if err := cmd.Process.Signal(sig); err != nil {
				t.Fatal(err)
			}
			for line := range lines {
				out.WriteString(line + "\n")
			}
			if err := cmd.Wait(); err != nil {
				t.Errorf("the server exited with %v after %v, want a clean exit\n%s", err, sig, out.String())
			}
			if !strings.Contains(out.String(), "shutting down") {
				t.Errorf("the server did not log a graceful shutdown:\n%s", out.String())
			}
		})
	}
}

func TestSecondSignalEndsAStuckShutdown(t *testing.T) {
	if runtime.GOOS == "windows" {
		t.Skip("relies on POSIX signals")
	}
	cmd, lines := startMain(t, []string{"ADDR=127.0.0.1:0", "DB_PATH=" + filepath.Join(t.TempDir(), "books.db")})
	var out strings.Builder
	addr := waitListening(t, lines, &out)

	// A request whose body never arrives keeps the graceful shutdown waiting.
	// The server answers "100 Continue" when its handler starts reading that
	// body, which proves that the request really is in flight.
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	conn.SetDeadline(time.Now().Add(20 * time.Second))
	if _, err := io.WriteString(conn, "POST /books HTTP/1.1\r\nHost: test\r\nContent-Length: 100\r\nExpect: 100-continue\r\n\r\n"); err != nil {
		t.Fatal(err)
	}
	if status, err := bufio.NewReader(conn).ReadString('\n'); err != nil || !strings.HasPrefix(status, "HTTP/1.1 100") {
		t.Fatalf("expected an interim 100 Continue, got %q (%v)", status, err)
	}

	if err := cmd.Process.Signal(syscall.SIGINT); err != nil {
		t.Fatal(err)
	}
	for !strings.Contains(out.String(), "shutting down") {
		select {
		case line, ok := <-lines:
			if !ok {
				t.Fatalf("the server exited on the first interrupt although a request was in flight:\n%s", out.String())
			}
			out.WriteString(line + "\n")
		case <-time.After(10 * time.Second):
			t.Fatalf("the server did not begin shutting down:\n%s", out.String())
		}
	}

	// The shutdown is now stuck on that request. Interrupt again until the
	// process is gone; an interrupt that arrives before the default signal
	// handling has been restored is harmlessly ignored, so keep sending them.
	tick := time.NewTicker(50 * time.Millisecond)
	defer tick.Stop()
	deadline := time.After(5 * time.Second)
	for exited := false; !exited; {
		select {
		case line, ok := <-lines:
			if !ok {
				exited = true
				break
			}
			out.WriteString(line + "\n")
		case <-tick.C:
			cmd.Process.Signal(syscall.SIGINT)
		case <-deadline:
			t.Fatalf("the server was still running 5s after repeated interrupts:\n%s", out.String())
		}
	}
	var exitErr *exec.ExitError
	if err := cmd.Wait(); !errors.As(err, &exitErr) {
		t.Fatalf("Wait() = %v, want the process to have been killed by the signal\n%s", err, out.String())
	}
	if status, ok := exitErr.Sys().(syscall.WaitStatus); !ok || !status.Signaled() || status.Signal() != syscall.SIGINT {
		t.Errorf("the server ended with %v, want death by SIGINT", exitErr)
	}
}
