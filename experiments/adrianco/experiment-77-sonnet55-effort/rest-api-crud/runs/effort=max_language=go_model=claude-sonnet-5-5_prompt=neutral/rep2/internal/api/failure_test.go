package api_test

import (
	"bytes"
	"context"
	"errors"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"testing/iotest"

	"bookapi/internal/api"
	"bookapi/internal/book"
)

// brokenStore fails every operation, like a database that has gone away.
type brokenStore struct{ err error }

func (s brokenStore) Create(context.Context, book.Input) (book.Book, error) {
	return book.Book{}, s.err
}
func (s brokenStore) Get(context.Context, int64) (book.Book, error)     { return book.Book{}, s.err }
func (s brokenStore) List(context.Context, string) ([]book.Book, error) { return nil, s.err }
func (s brokenStore) Update(context.Context, int64, book.Input) (book.Book, error) {
	return book.Book{}, s.err
}
func (s brokenStore) Delete(context.Context, int64) error { return s.err }
func (s brokenStore) Ping(context.Context) error          { return s.err }

// panickyStore panics in List and is otherwise healthy. The embedded nil
// interface means any other method would fail the test loudly.
type panickyStore struct{ api.BookStore }

func (panickyStore) List(context.Context, string) ([]book.Book, error) { panic("kaboom") }
func (panickyStore) Ping(context.Context) error                        { return nil }

func TestStoreFailuresBecomeGeneric500s(t *testing.T) {
	t.Parallel()
	const secret = "disk I/O error: /var/secret/path/books.db"

	var logs bytes.Buffer
	h := api.New(brokenStore{err: errors.New(secret)}, slog.New(slog.NewTextHandler(&logs, nil)))

	tests := []struct {
		method, path, body string
	}{
		{http.MethodPost, "/books", `{"title":"T","author":"A"}`},
		{http.MethodGet, "/books", ""},
		{http.MethodGet, "/books/1", ""},
		{http.MethodPut, "/books/1", `{"title":"T","author":"A"}`},
		{http.MethodDelete, "/books/1", ""},
	}
	for _, tt := range tests {
		rec := send(t, h, tt.method, tt.path, tt.body)
		wantStatus(t, rec, http.StatusInternalServerError)

		if got := decode[errorResponse](t, rec); got.Error != "internal server error" {
			t.Errorf("%s %s: error = %q, want a generic message", tt.method, tt.path, got.Error)
		}
		if strings.Contains(rec.Body.String(), "secret") {
			t.Errorf("%s %s leaked the internal error to the client: %s", tt.method, tt.path, rec.Body.String())
		}
	}

	// The cause is not lost: operators can find it in the log.
	if !strings.Contains(logs.String(), secret) {
		t.Errorf("internal error was not logged; log output:\n%s", logs.String())
	}
}

func TestHealthReportsUnavailableWhenDatabaseFails(t *testing.T) {
	t.Parallel()
	h := api.New(brokenStore{err: errors.New("database is closed")}, discardLogger)

	rec := send(t, h, http.MethodGet, "/health", "")
	wantStatus(t, rec, http.StatusServiceUnavailable)
	if got := decode[map[string]string](t, rec); got["status"] != "unavailable" {
		t.Errorf("body = %v, want status unavailable", got)
	}
}

func TestPanicBecomes500AndServerKeepsServing(t *testing.T) {
	t.Parallel()
	var logs bytes.Buffer
	h := api.New(panickyStore{}, slog.New(slog.NewTextHandler(&logs, nil)))

	rec := send(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusInternalServerError)
	if got := decode[errorResponse](t, rec); got.Error != "internal server error" {
		t.Errorf("error = %q, want a generic message", got.Error)
	}
	if !strings.Contains(logs.String(), "kaboom") {
		t.Errorf("panic was not logged; log output:\n%s", logs.String())
	}

	// The handler is still usable after the panic.
	wantStatus(t, send(t, h, http.MethodGet, "/health", ""), http.StatusOK)
}

func TestRequestsAreLogged(t *testing.T) {
	t.Parallel()
	var logs bytes.Buffer
	st := newStore(t)
	h := api.New(st, slog.New(slog.NewTextHandler(&logs, nil)))

	send(t, h, http.MethodGet, "/health", "")
	send(t, h, http.MethodGet, "/books/999", "")
	send(t, h, http.MethodPost, "/books", `{"title":"T","author":"A"}`)

	for _, want := range []string{
		"method=GET path=/health status=200",
		"method=GET path=/books/999 status=404",
		"method=POST path=/books status=201",
	} {
		if !strings.Contains(logs.String(), want) {
			t.Errorf("log is missing %q; log output:\n%s", want, logs.String())
		}
	}
}

func TestUnreadableRequestBodyIsABadRequest(t *testing.T) {
	t.Parallel()
	h := newAPI(t)

	r := httptest.NewRequest(http.MethodPost, "/books", iotest.ErrReader(errors.New("connection reset by peer")))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, r)

	wantStatus(t, rec, http.StatusBadRequest)
	if got := decode[errorResponse](t, rec); got.Error != "invalid request body" {
		t.Errorf("error = %q, want %q", got.Error, "invalid request body")
	}
}

func TestNilLoggerFallsBackToDefault(t *testing.T) {
	t.Parallel()
	h := api.New(newStore(t), nil)
	wantStatus(t, send(t, h, http.MethodGet, "/health", ""), http.StatusOK)
}
