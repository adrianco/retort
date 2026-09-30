package api_test

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"bookapi/internal/api"
	"bookapi/internal/book"
	"bookapi/internal/sqlite"
)

var discard = slog.New(slog.NewTextHandler(io.Discard, nil))

func ptr[T any](v T) *T { return &v }

// bookJSON and errorJSON describe the wire format independently of the
// implementation's own types, so the tests pin the JSON contract itself.
type bookJSON struct {
	ID     int64   `json:"id"`
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Year   *int    `json:"year"`
	ISBN   *string `json:"isbn"`
}

type errorJSON struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details"`
}

// newHandler returns the API wired to a real SQLite database in a temp dir.
func newHandler(t testing.TB) http.Handler {
	t.Helper()
	store, err := sqlite.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return api.New(store, discard)
}

// do sends one request straight to the handler. A non-empty body is sent as JSON.
func do(t testing.TB, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	var reader io.Reader
	if body != "" {
		reader = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, target, reader)
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// expect fails the test unless the response has the given status and, for
// anything but 204, a JSON content type.
func expect(t testing.TB, rec *httptest.ResponseRecorder, status int) {
	t.Helper()
	if rec.Code != status {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, status, rec.Body)
	}
	if status != http.StatusNoContent {
		if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
			t.Errorf("Content-Type = %q, want application/json", ct)
		}
	}
}

func decode[T any](t testing.TB, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("response is not valid JSON for %T: %v\nbody: %s", v, err, rec.Body)
	}
	return v
}

// create posts a book that is expected to be accepted.
func create(t testing.TB, h http.Handler, body string) bookJSON {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	expect(t, rec, http.StatusCreated)
	return decode[bookJSON](t, rec)
}

func titles(books []bookJSON) []string {
	out := make([]string, len(books))
	for i, b := range books {
		out[i] = b.Title
	}
	return out
}

// failingStore fails every operation with err.
type failingStore struct{ err error }

func (f failingStore) Create(context.Context, book.Input) (book.Book, error) {
	return book.Book{}, f.err
}
func (f failingStore) Get(context.Context, int64) (book.Book, error) { return book.Book{}, f.err }
func (f failingStore) List(context.Context, string) ([]book.Book, error) {
	return nil, f.err
}
func (f failingStore) Update(context.Context, int64, book.Input) (book.Book, error) {
	return book.Book{}, f.err
}
func (f failingStore) Delete(context.Context, int64) error { return f.err }
func (f failingStore) Ping(context.Context) error          { return f.err }

// panickingStore is healthy except that Get panics.
type panickingStore struct{ failingStore }

func (panickingStore) Get(context.Context, int64) (book.Book, error) { panic("kaboom") }
