package api

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"bookapi/internal/store"
)

// newTestServer boots the real handler on top of a real SQLite database.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	st, err := store.Open(filepath.Join(t.TempDir(), "api.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { st.Close() })

	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	ts := httptest.NewServer(New(st, logger).Handler())
	t.Cleanup(ts.Close)
	return ts
}

func do(t *testing.T, method, url string, body any) (*http.Response, []byte) {
	t.Helper()
	var rdr io.Reader
	switch b := body.(type) {
	case nil:
	case string:
		rdr = strings.NewReader(b)
	default:
		buf, err := json.Marshal(b)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}
		rdr = bytes.NewReader(buf)
	}
	req, err := http.NewRequest(method, url, rdr)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if rdr != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	defer resp.Body.Close()
	data, _ := io.ReadAll(resp.Body)
	return resp, data
}

func decode[T any](t *testing.T, data []byte) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(data, &v); err != nil {
		t.Fatalf("unmarshal %q: %v", data, err)
	}
	return v
}

func wantStatus(t *testing.T, resp *http.Response, body []byte, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("%s %s: want status %d, got %d; body=%s",
			resp.Request.Method, resp.Request.URL.Path, want, resp.StatusCode, body)
	}
	if ct := resp.Header.Get("Content-Type"); want != http.StatusNoContent && !strings.HasPrefix(ct, "application/json") {
		t.Errorf("want JSON content type, got %q", ct)
	}
}

func createBook(t *testing.T, base string, in map[string]any) store.Book {
	t.Helper()
	resp, body := do(t, http.MethodPost, base+"/books", in)
	wantStatus(t, resp, body, http.StatusCreated)
	return decode[store.Book](t, body)
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, http.MethodGet, ts.URL+"/health", nil)
	wantStatus(t, resp, body, http.StatusOK)
	got := decode[map[string]string](t, body)
	if got["status"] != "ok" || got["database"] != "ok" {
		t.Errorf("unexpected health body: %v", got)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	ts := newTestServer(t)

	resp, body := do(t, http.MethodPost, ts.URL+"/books", map[string]any{
		"title": "  The Left Hand of Darkness ", "author": "Ursula K. Le Guin", "year": 1969, "isbn": "978-0-441-47812-5",
	})
	wantStatus(t, resp, body, http.StatusCreated)
	created := decode[store.Book](t, body)
	if created.ID == 0 {
		t.Fatal("expected assigned id")
	}
	if created.Title != "The Left Hand of Darkness" {
		t.Errorf("title should be trimmed, got %q", created.Title)
	}
	if loc := resp.Header.Get("Location"); loc != fmt.Sprintf("/books/%d", created.ID) {
		t.Errorf("Location header = %q", loc)
	}

	resp, body = do(t, http.MethodGet, fmt.Sprintf("%s/books/%d", ts.URL, created.ID), nil)
	wantStatus(t, resp, body, http.StatusOK)
	got := decode[store.Book](t, body)
	if got.ID != created.ID || got.Author != "Ursula K. Le Guin" || got.Year == nil || *got.Year != 1969 || got.ISBN != "978-0-441-47812-5" {
		t.Errorf("GET returned %+v", got)
	}
}

func TestCreateValidation(t *testing.T) {
	ts := newTestServer(t)

	cases := []struct {
		name       string
		body       any
		wantStatus int
		wantField  string
	}{
		{"missing title", map[string]any{"author": "A"}, http.StatusUnprocessableEntity, "title"},
		{"missing author", map[string]any{"title": "T"}, http.StatusUnprocessableEntity, "author"},
		{"whitespace title", map[string]any{"title": "   ", "author": "A"}, http.StatusUnprocessableEntity, "title"},
		{"bad year", map[string]any{"title": "T", "author": "A", "year": 99999}, http.StatusUnprocessableEntity, "year"},
		{"bad isbn", map[string]any{"title": "T", "author": "A", "isbn": "not-an-isbn"}, http.StatusUnprocessableEntity, "isbn"},
		{"wrong type", map[string]any{"title": "T", "author": "A", "year": "1999"}, http.StatusBadRequest, ""},
		{"unknown field", map[string]any{"title": "T", "author": "A", "publisher": "P"}, http.StatusBadRequest, ""},
		{"malformed json", `{"title": "T", `, http.StatusBadRequest, ""},
		{"empty body", "", http.StatusBadRequest, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body := do(t, http.MethodPost, ts.URL+"/books", tc.body)
			wantStatus(t, resp, body, tc.wantStatus)
			er := decode[errorResponse](t, body)
			if er.Error == "" {
				t.Error("expected error message")
			}
			if tc.wantField != "" {
				if _, ok := er.Fields[tc.wantField]; !ok {
					t.Errorf("expected field error for %q, got %v", tc.wantField, er.Fields)
				}
			}
		})
	}

	// Nothing should have been persisted.
	resp, body := do(t, http.MethodGet, ts.URL+"/books", nil)
	wantStatus(t, resp, body, http.StatusOK)
	if books := decode[[]store.Book](t, body); len(books) != 0 {
		t.Errorf("expected no books persisted, got %+v", books)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	// Empty collection returns [] not null.
	resp, body := do(t, http.MethodGet, ts.URL+"/books", nil)
	wantStatus(t, resp, body, http.StatusOK)
	if strings.TrimSpace(string(body)) != "[]" {
		t.Errorf("empty list should be [], got %s", body)
	}

	createBook(t, ts.URL, map[string]any{"title": "Foundation", "author": "Isaac Asimov", "year": 1951})
	createBook(t, ts.URL, map[string]any{"title": "I, Robot", "author": "Isaac Asimov", "year": 1950})
	createBook(t, ts.URL, map[string]any{"title": "Hyperion", "author": "Dan Simmons", "year": 1989})

	resp, body = do(t, http.MethodGet, ts.URL+"/books", nil)
	wantStatus(t, resp, body, http.StatusOK)
	if all := decode[[]store.Book](t, body); len(all) != 3 {
		t.Errorf("want 3 books, got %d", len(all))
	}

	resp, body = do(t, http.MethodGet, ts.URL+"/books?author=Isaac+Asimov", nil)
	wantStatus(t, resp, body, http.StatusOK)
	filtered := decode[[]store.Book](t, body)
	if len(filtered) != 2 {
		t.Fatalf("want 2 Asimov books, got %d: %+v", len(filtered), filtered)
	}
	for _, b := range filtered {
		if b.Author != "Isaac Asimov" {
			t.Errorf("unexpected book in filter: %+v", b)
		}
	}

	resp, body = do(t, http.MethodGet, ts.URL+"/books?author=Nobody", nil)
	wantStatus(t, resp, body, http.StatusOK)
	if none := decode[[]store.Book](t, body); len(none) != 0 {
		t.Errorf("want empty result, got %+v", none)
	}
}

func TestUpdateBook(t *testing.T) {
	ts := newTestServer(t)
	b := createBook(t, ts.URL, map[string]any{"title": "Old", "author": "Someone", "year": 2000, "isbn": "1234567890"})
	url := fmt.Sprintf("%s/books/%d", ts.URL, b.ID)

	resp, body := do(t, http.MethodPut, url, map[string]any{"title": "New", "author": "Someone Else"})
	wantStatus(t, resp, body, http.StatusOK)
	updated := decode[store.Book](t, body)
	if updated.ID != b.ID || updated.Title != "New" || updated.Author != "Someone Else" {
		t.Errorf("PUT returned %+v", updated)
	}
	if updated.Year != nil || updated.ISBN != "" {
		t.Errorf("PUT should fully replace the resource, got year=%v isbn=%q", updated.Year, updated.ISBN)
	}

	resp, body = do(t, http.MethodGet, url, nil)
	wantStatus(t, resp, body, http.StatusOK)
	if got := decode[store.Book](t, body); got.Title != "New" {
		t.Errorf("update not persisted: %+v", got)
	}

	// Validation applies to PUT as well.
	resp, body = do(t, http.MethodPut, url, map[string]any{"title": "", "author": "X"})
	wantStatus(t, resp, body, http.StatusUnprocessableEntity)

	// Unknown id.
	resp, body = do(t, http.MethodPut, ts.URL+"/books/4242", map[string]any{"title": "T", "author": "A"})
	wantStatus(t, resp, body, http.StatusNotFound)
}

func TestDeleteBook(t *testing.T) {
	ts := newTestServer(t)
	b := createBook(t, ts.URL, map[string]any{"title": "Ephemeral", "author": "Gone Soon"})
	url := fmt.Sprintf("%s/books/%d", ts.URL, b.ID)

	resp, body := do(t, http.MethodDelete, url, nil)
	wantStatus(t, resp, body, http.StatusNoContent)
	if len(body) != 0 {
		t.Errorf("204 should have empty body, got %s", body)
	}

	resp, body = do(t, http.MethodGet, url, nil)
	wantStatus(t, resp, body, http.StatusNotFound)

	resp, body = do(t, http.MethodDelete, url, nil)
	wantStatus(t, resp, body, http.StatusNotFound)
}

func TestInvalidIDsAndRoutes(t *testing.T) {
	ts := newTestServer(t)

	for _, id := range []string{"abc", "0", "-1", "1.5"} {
		resp, body := do(t, http.MethodGet, ts.URL+"/books/"+id, nil)
		wantStatus(t, resp, body, http.StatusBadRequest)
	}

	resp, body := do(t, http.MethodGet, ts.URL+"/books/99999", nil)
	wantStatus(t, resp, body, http.StatusNotFound)

	// Method not allowed on a known path.
	resp, _ = do(t, http.MethodPatch, ts.URL+"/books/1", map[string]any{"title": "x"})
	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("PATCH: want 405, got %d", resp.StatusCode)
	}
}

func TestDuplicateISBNConflict(t *testing.T) {
	ts := newTestServer(t)
	createBook(t, ts.URL, map[string]any{"title": "First", "author": "A", "isbn": "9780000000002"})

	resp, body := do(t, http.MethodPost, ts.URL+"/books", map[string]any{"title": "Second", "author": "B", "isbn": "9780000000002"})
	wantStatus(t, resp, body, http.StatusConflict)
}

// failingStore exercises the 500 / unhealthy paths without a real DB failure.
type failingStore struct{ Store }

func (failingStore) Ping(context.Context) error { return errors.New("db down") }
func (failingStore) List(context.Context, string) ([]store.Book, error) {
	return nil, errors.New("boom")
}

func TestStoreFailures(t *testing.T) {
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	ts := httptest.NewServer(New(failingStore{}, logger).Handler())
	defer ts.Close()

	resp, body := do(t, http.MethodGet, ts.URL+"/health", nil)
	wantStatus(t, resp, body, http.StatusServiceUnavailable)

	resp, body = do(t, http.MethodGet, ts.URL+"/books", nil)
	wantStatus(t, resp, body, http.StatusInternalServerError)
	if er := decode[errorResponse](t, body); er.Error != "internal server error" {
		t.Errorf("internal errors must not leak details, got %q", er.Error)
	}
}
