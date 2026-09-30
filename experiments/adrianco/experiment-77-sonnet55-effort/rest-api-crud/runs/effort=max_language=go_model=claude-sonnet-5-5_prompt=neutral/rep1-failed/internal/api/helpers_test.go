package api_test

import (
	"context"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"bookapi/internal/book"
	"bookapi/internal/store"
)

// Invisible characters are built from their code points so that they can be
// seen in this source file.
var (
	zeroWidthSpace  = string(rune(0x200B))
	wordJoiner      = string(rune(0x2060))
	byteOrderMark   = string(rune(0xFEFF)) // also the zero-width no-break space
	zeroWidthJoiner = string(rune(0x200D))
	noBreakSpace    = string(rune(0x00A0))
)

// bookJSON encodes a title and author as a request body, so that unusual
// characters never have to be typed into the tests as JSON escapes.
func bookJSON(title, author string) string {
	b, err := json.Marshal(map[string]string{"title": title, "author": author})
	if err != nil {
		panic(err)
	}
	return string(b)
}

func discardLogger() *slog.Logger {
	return slog.New(slog.NewTextHandler(io.Discard, nil))
}

// openStore returns a real SQLite store in a temporary directory.
func openStore(t testing.TB) *store.Store {
	t.Helper()
	s, err := store.Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("store.Open: %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

// send performs a request against h. A non-empty body is sent as JSON.
func send(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	var rd io.Reader
	if body != "" {
		rd = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, target, rd)
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("response body is not the expected JSON: %v\nbody: %s", err, rec.Body)
	}
	return v
}

// errorResponse mirrors the JSON error body.
type errorResponse struct {
	Error   string            `json:"error"`
	Details []book.FieldError `json:"details"`
}

func wantStatus(t *testing.T, rec *httptest.ResponseRecorder, status int) {
	t.Helper()
	if rec.Code != status {
		t.Fatalf("status = %d, want %d\nbody: %s", rec.Code, status, rec.Body)
	}
}

func wantJSON(t *testing.T, rec *httptest.ResponseRecorder) {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	if got := rec.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Errorf("X-Content-Type-Options = %q, want nosniff", got)
	}
}

// wantError checks for a JSON error response with the given status whose
// message contains the given text, and returns the decoded body.
func wantError(t *testing.T, rec *httptest.ResponseRecorder, status int, contains string) errorResponse {
	t.Helper()
	wantStatus(t, rec, status)
	wantJSON(t, rec)
	got := decode[errorResponse](t, rec)
	if !strings.Contains(got.Error, contains) {
		t.Errorf("error = %q, want it to contain %q", got.Error, contains)
	}
	return got
}

// createBook posts body and returns the book the API reports as created.
func createBook(t *testing.T, h http.Handler, body string) book.Book {
	t.Helper()
	rec := send(t, h, http.MethodPost, "/books", body)
	wantStatus(t, rec, http.StatusCreated)
	return decode[book.Book](t, rec)
}

func bookPath(b book.Book) string {
	return "/books/" + strconv.FormatInt(b.ID, 10)
}

func titles(books []book.Book) []string {
	out := make([]string, len(books))
	for i, b := range books {
		out[i] = b.Title
	}
	return out
}

// failingStore is a BookStore whose every method fails with err, or panics
// with panicValue when that is set.
type failingStore struct {
	err        error
	panicValue any
}

func (s failingStore) fail() error {
	if s.panicValue != nil {
		panic(s.panicValue)
	}
	return s.err
}

func (s failingStore) Create(context.Context, book.Input) (book.Book, error) {
	return book.Book{}, s.fail()
}

func (s failingStore) Get(context.Context, int64) (book.Book, error) {
	return book.Book{}, s.fail()
}

func (s failingStore) List(context.Context, string) ([]book.Book, error) {
	return nil, s.fail()
}

func (s failingStore) Update(context.Context, int64, book.Input) (book.Book, error) {
	return book.Book{}, s.fail()
}

func (s failingStore) Delete(context.Context, int64) error { return s.fail() }

func (s failingStore) Ping(context.Context) error { return s.fail() }
