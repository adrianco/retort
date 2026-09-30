package api_test

import (
	"bufio"
	"bytes"
	"context"
	"database/sql"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"bookapi/internal/api"
	"bookapi/internal/book"
	"bookapi/internal/store"
)

func TestHealth(t *testing.T) {
	h := newHandler(t)
	rec := send(t, h, http.MethodGet, "/health", "")
	wantStatus(t, rec, http.StatusOK)
	wantJSON(t, rec)
	if got := decode[map[string]string](t, rec); got["status"] != "ok" {
		t.Errorf("body = %v, want status ok", got)
	}
}

func TestHealthSupportsHEAD(t *testing.T) {
	h := newHandler(t)
	rec := send(t, h, http.MethodHead, "/health", "")
	wantStatus(t, rec, http.StatusOK)
}

func TestHealthReportsUnavailableDatabase(t *testing.T) {
	var logs bytes.Buffer
	h := api.New(failingStore{err: errors.New("database is closed")}, slog.New(slog.NewTextHandler(&logs, nil)))

	rec := send(t, h, http.MethodGet, "/health", "")
	wantStatus(t, rec, http.StatusServiceUnavailable)
	wantJSON(t, rec)
	if got := decode[map[string]string](t, rec); got["status"] != "unavailable" {
		t.Errorf("body = %v, want status unavailable", got)
	}
	if strings.Contains(rec.Body.String(), "database is closed") {
		t.Errorf("health response leaks the failure detail: %s", rec.Body)
	}
	if !strings.Contains(logs.String(), "database is closed") {
		t.Errorf("health failure was not logged:\n%s", logs.String())
	}
}

func TestHealthNoticesWhenTheBooksTableDisappears(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	s, err := store.Open(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { s.Close() })
	h := api.New(s, discardLogger())
	wantStatus(t, send(t, h, http.MethodGet, "/health", ""), http.StatusOK)

	other, err := sql.Open("sqlite", path)
	if err != nil {
		t.Fatal(err)
	}
	defer other.Close()
	if _, err := other.ExecContext(t.Context(), "DROP TABLE books"); err != nil {
		t.Fatal(err)
	}

	// The service can no longer serve books, so it must not claim to be healthy.
	wantStatus(t, send(t, h, http.MethodGet, "/health", ""), http.StatusServiceUnavailable)
	wantError(t, send(t, h, http.MethodGet, "/books", ""), http.StatusInternalServerError, "internal server error")
}

func TestUnknownRoutesReturnJSON404(t *testing.T) {
	h := newHandler(t)
	for _, target := range []string{"/", "/nope", "/book", "/books/", "/books/1/extra", "/health/deep", "/api/books"} {
		t.Run(target, func(t *testing.T) {
			wantError(t, send(t, h, http.MethodGet, target, ""), http.StatusNotFound, "not found")
		})
	}
}

func TestUnsupportedMethodsReturnJSON405WithAllowHeader(t *testing.T) {
	h := newHandler(t)
	tests := []struct {
		method, target, allow string
	}{
		{http.MethodPut, "/books", "GET, HEAD, POST"},
		{http.MethodDelete, "/books", "GET, HEAD, POST"},
		{http.MethodPatch, "/books", "GET, HEAD, POST"},
		{http.MethodPost, "/books/1", "GET, HEAD, PUT, DELETE"},
		{http.MethodPatch, "/books/1", "GET, HEAD, PUT, DELETE"},
		{http.MethodPost, "/books/not-a-number", "GET, HEAD, PUT, DELETE"},
		{http.MethodPost, "/health", "GET, HEAD"},
		{http.MethodDelete, "/health", "GET, HEAD"},
	}
	for _, tt := range tests {
		t.Run(tt.method+" "+tt.target, func(t *testing.T) {
			rec := send(t, h, tt.method, tt.target, "")
			wantError(t, rec, http.StatusMethodNotAllowed, "method not allowed")
			if got := rec.Header().Get("Allow"); got != tt.allow {
				t.Errorf("Allow = %q, want %q", got, tt.allow)
			}
		})
	}
}

func TestStoreFailuresAreLoggedButNotShownToClients(t *testing.T) {
	var logs bytes.Buffer
	failure := errors.New("disk I/O error at /var/lib/private/books.db")
	h := api.New(failingStore{err: failure}, slog.New(slog.NewTextHandler(&logs, nil)))

	const body = `{"title":"T","author":"A"}`
	tests := []struct {
		name, method, target, body string
	}{
		{"create", http.MethodPost, "/books", body},
		{"list", http.MethodGet, "/books", ""},
		{"get", http.MethodGet, "/books/1", ""},
		{"update", http.MethodPut, "/books/1", body},
		{"delete", http.MethodDelete, "/books/1", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := send(t, h, tt.method, tt.target, tt.body)
			got := wantError(t, rec, http.StatusInternalServerError, "internal server error")
			if got.Error != "internal server error" || strings.Contains(rec.Body.String(), "private") {
				t.Errorf("body %s leaks internals", rec.Body)
			}
		})
	}
	if !strings.Contains(logs.String(), "disk I/O error at /var/lib/private/books.db") {
		t.Errorf("the underlying failure was not logged:\n%s", logs.String())
	}
}

// A write from a client that has hung up, or that closed its sending side
// after writing its request (net/http cancels the request context in both
// cases), is still carried out, and the response says so truthfully.
func TestWritesCompleteEvenIfTheClientHasGone(t *testing.T) {
	var logs bytes.Buffer
	h := api.New(openStore(t), slog.New(slog.NewTextHandler(&logs, nil)))

	ctx, cancel := context.WithCancel(t.Context())
	cancel()
	gone := func(method, target, body string) *httptest.ResponseRecorder {
		req := httptest.NewRequest(method, target, strings.NewReader(body)).WithContext(ctx)
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		return rec
	}

	rec := gone(http.MethodPost, "/books", `{"title":"Written anyway","author":"A"}`)
	wantStatus(t, rec, http.StatusCreated)
	created := decode[book.Book](t, rec)
	if got := decode[book.Book](t, send(t, h, http.MethodGet, bookPath(created), "")); got != created {
		t.Fatalf("the create was acknowledged but stored %+v, want %+v", got, created)
	}

	wantStatus(t, gone(http.MethodPut, bookPath(created), `{"title":"Renamed anyway","author":"A"}`), http.StatusOK)
	if got := decode[book.Book](t, send(t, h, http.MethodGet, bookPath(created), "")); got.Title != "Renamed anyway" {
		t.Errorf("the update was acknowledged but the title is %q", got.Title)
	}

	wantStatus(t, gone(http.MethodDelete, bookPath(created), ""), http.StatusNoContent)
	wantError(t, send(t, h, http.MethodGet, bookPath(created), ""), http.StatusNotFound, "book not found")

	if strings.Contains(logs.String(), "level=ERROR") {
		t.Errorf("writes from a departed client were logged as errors:\n%s", logs.String())
	}
}

// Reads, by contrast, are abandoned once the client is gone, so that departed
// clients cannot keep the database busy. That is not a server fault.
func TestReadsAreAbandonedWhenTheClientHasGone(t *testing.T) {
	var logs bytes.Buffer
	h := api.New(openStore(t), slog.New(slog.NewTextHandler(&logs, nil)))
	created := createBook(t, h, dune)

	ctx, cancel := context.WithCancel(t.Context())
	cancel()
	for _, target := range []string{"/books", "/books?author=Frank+Herbert", bookPath(created), "/health"} {
		t.Run(target, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, target, nil).WithContext(ctx)
			rec := httptest.NewRecorder()
			h.ServeHTTP(rec, req)
			wantStatus(t, rec, 499)
			wantJSON(t, rec)
		})
	}

	out := logs.String()
	if strings.Contains(out, "level=ERROR") {
		t.Errorf("reads by a departed client were logged as errors:\n%s", out)
	}
	if !strings.Contains(out, "status=499") {
		t.Errorf("the access log does not record the abandoned reads:\n%s", out)
	}
}

// callContext describes the context of one store call at the moment it was
// made. (Looking later would show it cancelled by the handler's own clean-up.)
type callContext struct {
	called      bool
	errAtCall   error
	at          time.Time
	deadline    time.Time
	hasDeadline bool
}

func noteContext(ctx context.Context) callContext {
	deadline, ok := ctx.Deadline()
	return callContext{called: true, errAtCall: ctx.Err(), at: time.Now(), deadline: deadline, hasDeadline: ok}
}

// contextRecorder is a BookStore that records the context of its last List (a
// read) and Create (a write). It is safe to inspect from another goroutine.
type contextRecorder struct {
	failingStore
	mu          sync.Mutex
	read, write callContext
}

func (c *contextRecorder) List(ctx context.Context, _ string) ([]book.Book, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.read = noteContext(ctx)
	return nil, nil
}

func (c *contextRecorder) Create(ctx context.Context, in book.Input) (book.Book, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.write = noteContext(ctx)
	return book.Book{ID: 1, Input: in}, nil
}

func (c *contextRecorder) noted() (read, write callContext) {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.read, c.write
}

func TestOnlyReadsFollowTheClientAndBothAreBounded(t *testing.T) {
	store := &contextRecorder{}
	h := api.New(store, discardLogger())

	ctx, cancel := context.WithCancel(t.Context())
	cancel() // the client's context is done...
	for _, r := range []struct{ method, target, body string }{
		{http.MethodGet, "/books", ""},
		{http.MethodPost, "/books", `{"title":"T","author":"A"}`},
	} {
		req := httptest.NewRequest(r.method, r.target, strings.NewReader(r.body)).WithContext(ctx)
		h.ServeHTTP(httptest.NewRecorder(), req)
	}

	read, write := store.noted()
	if !read.called || !write.called {
		t.Fatalf("the store was not called for both requests: read %v, write %v", read.called, write.called)
	}
	if !errors.Is(read.errAtCall, context.Canceled) {
		t.Errorf("a read ran with a live context (%v) although its client had gone", read.errAtCall)
	}
	if write.errAtCall != nil { // ...but a write must not be abandoned midway
		t.Errorf("a write ran with a dead context (%v) and could be abandoned midway", write.errAtCall)
	}
	for name, c := range map[string]callContext{"read": read, "write": write} {
		if !c.hasDeadline {
			t.Errorf("a %s has no deadline, so a stuck database could hold it indefinitely", name)
			continue
		}
		if window := c.deadline.Sub(c.at); window <= 0 || window > api.RequestTimeout {
			t.Errorf("a %s was given %v, want within (0, %v]", name, window, api.RequestTimeout)
		}
	}
}

// The time a client takes to upload its request must not eat into the time the
// database is allowed to take: the write's deadline starts at the store call.
func TestWriteDeadlineStartsAfterTheBodyHasArrived(t *testing.T) {
	store := &contextRecorder{}
	srv := httptest.NewServer(api.New(store, discardLogger()))
	defer srv.Close()

	conn, err := net.Dial("tcp", srv.Listener.Addr().String())
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	conn.SetDeadline(time.Now().Add(20 * time.Second))
	const body = `{"title":"Slow upload","author":"A"}`
	head := fmt.Sprintf("POST /books HTTP/1.1\r\nHost: test\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n", len(body))
	if _, err := io.WriteString(conn, head+body[:10]); err != nil {
		t.Fatal(err)
	}
	time.Sleep(time.Second) // a slow client
	if _, err := io.WriteString(conn, body[10:]); err != nil {
		t.Fatal(err)
	}
	resp, err := http.ReadResponse(bufio.NewReader(conn), nil)
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("status %d, want 201", resp.StatusCode)
	}

	_, write := store.noted()
	if window := write.deadline.Sub(write.at); window < api.RequestTimeout-500*time.Millisecond {
		t.Errorf("the write was given only %v to complete after a 1s upload, want about %v", window, api.RequestTimeout)
	}
}

func TestSlowDatabaseAnswers503(t *testing.T) {
	var logs bytes.Buffer
	slow := fmt.Errorf("list books: %w", context.DeadlineExceeded)
	h := api.New(failingStore{err: slow}, slog.New(slog.NewTextHandler(&logs, nil)))

	const body = `{"title":"T","author":"A"}`
	for _, r := range []struct{ method, target, body string }{
		{http.MethodPost, "/books", body},
		{http.MethodGet, "/books", ""},
		{http.MethodGet, "/books/1", ""},
		{http.MethodPut, "/books/1", body},
		{http.MethodDelete, "/books/1", ""},
	} {
		t.Run(r.method+" "+r.target, func(t *testing.T) {
			wantError(t, send(t, h, r.method, r.target, r.body), http.StatusServiceUnavailable, "database is busy")
		})
	}
	out := logs.String()
	if !strings.Contains(out, `level=WARN msg="store call timed out"`) {
		t.Errorf("the timeout was not logged as a warning:\n%s", out)
	}
	if strings.Contains(out, `msg="store failure"`) {
		t.Errorf("a timeout was reported as a store failure:\n%s", out)
	}
}

func TestPanickingHandlerBecomesJSON500(t *testing.T) {
	var logs bytes.Buffer
	h := api.New(failingStore{panicValue: "kaboom"}, slog.New(slog.NewTextHandler(&logs, nil)))

	rec := send(t, h, http.MethodGet, "/books", "")
	wantError(t, rec, http.StatusInternalServerError, "internal server error")
	if out := logs.String(); !strings.Contains(out, "panic serving request") || !strings.Contains(out, "kaboom") {
		t.Errorf("panic was not logged with its value:\n%s", out)
	}

	// The service keeps working after a panic.
	wantStatus(t, send(t, h, http.MethodGet, "/nope", ""), http.StatusNotFound)
}

func TestAbortHandlerPanicIsPropagated(t *testing.T) {
	h := api.New(failingStore{panicValue: http.ErrAbortHandler}, discardLogger())
	defer func() {
		if got := recover(); got != http.ErrAbortHandler {
			t.Errorf("recovered %v, want http.ErrAbortHandler to pass through to net/http", got)
		}
	}()
	send(t, h, http.MethodGet, "/books", "")
	t.Error("the request completed, want the abort panic to propagate")
}

func TestRequestsAreLogged(t *testing.T) {
	var logs bytes.Buffer
	h := api.New(openStore(t), slog.New(slog.NewTextHandler(&logs, nil)))

	send(t, h, http.MethodGet, "/health", "")
	send(t, h, http.MethodGet, "/books/999", "")
	send(t, h, http.MethodPost, "/books", `{"title":"T","author":"A"}`)

	out := logs.String()
	for _, want := range []string{
		"level=INFO msg=request method=GET path=/health status=200",
		"level=INFO msg=request method=GET path=/books/999 status=404",
		"level=INFO msg=request method=POST path=/books status=201",
		"duration=",
	} {
		if !strings.Contains(out, want) {
			t.Errorf("log does not contain %q:\n%s", want, out)
		}
	}
}

func TestServerErrorsAreLoggedAtErrorLevel(t *testing.T) {
	var logs bytes.Buffer
	h := api.New(failingStore{err: errors.New("boom")}, slog.New(slog.NewTextHandler(&logs, nil)))

	send(t, h, http.MethodGet, "/books", "")

	if want := "level=ERROR msg=request method=GET path=/books status=500"; !strings.Contains(logs.String(), want) {
		t.Errorf("log does not contain %q:\n%s", want, logs.String())
	}
}

// brokenWriter is a ResponseWriter whose body writes fail, like a connection
// the client has already closed.
type brokenWriter struct{ http.ResponseWriter }

func (brokenWriter) Write([]byte) (int, error) { return 0, errors.New("broken pipe") }

func TestResponseWriteFailuresAreLogged(t *testing.T) {
	var logs bytes.Buffer
	h := api.New(openStore(t), slog.New(slog.NewTextHandler(&logs, nil)))

	h.ServeHTTP(brokenWriter{httptest.NewRecorder()}, httptest.NewRequest(http.MethodGet, "/health", nil))

	// A failed write almost always means the client left, so it is a warning.
	out := logs.String()
	if !strings.Contains(out, "level=WARN msg=\"write response\"") || !strings.Contains(out, "broken pipe") {
		t.Errorf("write failure was not logged as a warning:\n%s", out)
	}
	if strings.Contains(out, "level=ERROR msg=\"write response\"") {
		t.Errorf("write failure was logged as an error:\n%s", out)
	}
}

func TestNilLoggerFallsBackToDefault(t *testing.T) {
	h := api.New(openStore(t), nil)
	wantStatus(t, send(t, h, http.MethodGet, "/health", ""), http.StatusOK)
}
