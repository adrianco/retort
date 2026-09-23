package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// newTestServer returns an API server backed by a fresh SQLite database in a
// temporary directory, so every test runs against the real storage layer.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := OpenSQLiteStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	s := NewServer(store)
	s.now = func() time.Time { return time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC) }
	return s
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var req *http.Request
	if body == "" {
		req = httptest.NewRequest(method, path, nil)
	} else {
		req = httptest.NewRequest(method, path, strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("Content-Type = %q, want application/json", ct)
	}
	var v T
	if err := json.NewDecoder(rec.Body).Decode(&v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
	return v
}

func mustCreate(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: status %d, body %s", rec.Code, rec.Body)
	}
	return decode[Book](t, rec)
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	got := decode[map[string]string](t, rec)
	if got["status"] != "ok" {
		t.Errorf("status field = %q, want ok", got["status"])
	}
}

func TestHealthReportsDatabaseDown(t *testing.T) {
	s := newTestServer(t)
	s.store.Close()
	rec := do(t, s, http.MethodGet, "/health", "")
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("status = %d, want 503", rec.Code)
	}
}

func TestBookCRUDLifecycle(t *testing.T) {
	s := newTestServer(t)

	// Create
	created := mustCreate(t, s, `{"title":"The Go Programming Language","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}`)
	if created.ID <= 0 {
		t.Fatalf("expected positive id, got %d", created.ID)
	}
	if created.Title != "The Go Programming Language" || created.Author != "Alan Donovan" ||
		created.Year == nil || *created.Year != 2015 || created.ISBN != "978-0134190440" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	// Read
	rec := do(t, s, http.MethodGet, "/books/1", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("get: status %d", rec.Code)
	}
	if got := decode[Book](t, rec); got.Title != created.Title {
		t.Errorf("get: title = %q, want %q", got.Title, created.Title)
	}

	// Update
	rec = do(t, s, http.MethodPut, "/books/1", `{"title":"The Go Programming Language (2nd ed.)","author":"Alan Donovan","year":2016}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("update: status %d, body %s", rec.Code, rec.Body)
	}
	updated := decode[Book](t, rec)
	if updated.ID != created.ID || updated.Title != "The Go Programming Language (2nd ed.)" || *updated.Year != 2016 || updated.ISBN != "" {
		t.Errorf("update: unexpected book %+v", updated)
	}
	// Persisted?
	if got := decode[Book](t, do(t, s, http.MethodGet, "/books/1", "")); got.Title != updated.Title {
		t.Errorf("update not persisted: %+v", got)
	}

	// Delete
	rec = do(t, s, http.MethodDelete, "/books/1", "")
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: status %d", rec.Code)
	}
	if rec := do(t, s, http.MethodGet, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("get after delete: status %d, want 404", rec.Code)
	}
	if rec := do(t, s, http.MethodDelete, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("second delete: status %d, want 404", rec.Code)
	}
}

func TestCreateSetsLocationHeader(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("status %d", rec.Code)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}
	b := decode[Book](t, rec)
	if b.Year != nil || b.ISBN != "" {
		t.Errorf("optional fields should be empty, got %+v", b)
	}
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	s := newTestServer(t)

	// Empty list must be a JSON array, not null.
	rec := do(t, s, http.MethodGet, "/books", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status %d", rec.Code)
	}
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %s, want []", body)
	}

	mustCreate(t, s, `{"title":"Dune","author":"Frank Herbert"}`)
	mustCreate(t, s, `{"title":"Children of Dune","author":"Frank Herbert"}`)
	mustCreate(t, s, `{"title":"Neuromancer","author":"William Gibson"}`)
	mustCreate(t, s, `{"title":"Odd","author":"100%_Real"}`)

	tests := []struct {
		query  string
		titles []string
	}{
		{"/books", []string{"Dune", "Children of Dune", "Neuromancer", "Odd"}},
		{"/books?author=Frank+Herbert", []string{"Dune", "Children of Dune"}},
		{"/books?author=frank%20herbert", []string{"Dune", "Children of Dune"}}, // case-insensitive
		{"/books?author=Gibson", []string{"Neuromancer"}},                       // partial match
		{"/books?author=Tolkien", []string{}},
		{"/books?author=%25", []string{"Odd"}}, // "%" is matched literally, not as a wildcard
		{"/books?author=_", []string{"Odd"}},   // "_" too
		{"/books?author=", []string{"Dune", "Children of Dune", "Neuromancer", "Odd"}},
	}
	for _, tc := range tests {
		t.Run(tc.query, func(t *testing.T) {
			rec := do(t, s, http.MethodGet, tc.query, "")
			if rec.Code != http.StatusOK {
				t.Fatalf("status %d", rec.Code)
			}
			books := decode[[]Book](t, rec)
			if len(books) != len(tc.titles) {
				t.Fatalf("got %d books %+v, want %v", len(books), books, tc.titles)
			}
			for i, b := range books {
				if b.Title != tc.titles[i] {
					t.Errorf("book %d title = %q, want %q", i, b.Title, tc.titles[i])
				}
			}
		})
	}
}

func TestCreateValidation(t *testing.T) {
	s := newTestServer(t)
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string
	}{
		{"missing title", `{"author":"A"}`, 400, []string{"title"}},
		{"missing author", `{"title":"T"}`, 400, []string{"author"}},
		{"missing both", `{}`, 400, []string{"title", "author"}},
		{"whitespace only", `{"title":"   ","author":"\t"}`, 400, []string{"title", "author"}},
		{"negative year", `{"title":"T","author":"A","year":-5}`, 400, []string{"year"}},
		{"future year", `{"title":"T","author":"A","year":3000}`, 400, []string{"year"}},
		{"bad isbn", `{"title":"T","author":"A","isbn":"abc"}`, 400, []string{"isbn"}},
		{"isbn wrong length", `{"title":"T","author":"A","isbn":"12345"}`, 400, []string{"isbn"}},
		{"title too long", `{"title":"` + strings.Repeat("x", maxTitleLength+1) + `","author":"A"}`, 400, []string{"title"}},
		{"malformed json", `{"title":`, 400, nil},
		{"wrong type", `{"title":123,"author":"A"}`, 400, nil},
		{"trailing data", `{"title":"T","author":"A"}{}`, 400, nil},
		{"empty body", ``, 400, nil},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(tc.body))
			rec := httptest.NewRecorder()
			s.ServeHTTP(rec, req)
			if rec.Code != tc.wantStatus {
				t.Fatalf("status = %d, want %d (body %s)", rec.Code, tc.wantStatus, rec.Body)
			}
			resp := decode[struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}](t, rec)
			if resp.Error == "" {
				t.Error("expected non-empty error message")
			}
			for _, f := range tc.wantFields {
				if _, ok := resp.Fields[f]; !ok {
					t.Errorf("expected field error for %q, got %v", f, resp.Fields)
				}
			}
			if len(tc.wantFields) > 0 && len(resp.Fields) != len(tc.wantFields) {
				t.Errorf("fields = %v, want exactly %v", resp.Fields, tc.wantFields)
			}
		})
	}

	// Nothing invalid should have been stored.
	if books := decode[[]Book](t, do(t, s, http.MethodGet, "/books", "")); len(books) != 0 {
		t.Errorf("invalid requests created %d books", len(books))
	}
}

func TestCreateTrimsWhitespace(t *testing.T) {
	s := newTestServer(t)
	b := mustCreate(t, s, `{"title":"  Dune  ","author":" Frank Herbert ","isbn":" 0-441-17271-7 "}`)
	if b.Title != "Dune" || b.Author != "Frank Herbert" || b.ISBN != "0-441-17271-7" {
		t.Errorf("fields not trimmed: %+v", b)
	}
}

func TestCreateRejectsOversizedBody(t *testing.T) {
	s := newTestServer(t)
	body := `{"title":"` + strings.Repeat("x", maxBodyBytes) + `","author":"A"}`
	rec := do(t, s, http.MethodPost, "/books", body)
	if rec.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("status = %d, want 413", rec.Code)
	}
}

func TestUpdateErrors(t *testing.T) {
	s := newTestServer(t)
	mustCreate(t, s, `{"title":"Dune","author":"Frank Herbert"}`)

	if rec := do(t, s, http.MethodPut, "/books/999", `{"title":"T","author":"A"}`); rec.Code != http.StatusNotFound {
		t.Errorf("update missing: status %d, want 404", rec.Code)
	}
	if rec := do(t, s, http.MethodPut, "/books/1", `{"title":""}`); rec.Code != http.StatusBadRequest {
		t.Errorf("update invalid: status %d, want 400", rec.Code)
	}
	// Failed update must leave the record untouched.
	if got := decode[Book](t, do(t, s, http.MethodGet, "/books/1", "")); got.Title != "Dune" {
		t.Errorf("book modified by failed update: %+v", got)
	}
}

func TestInvalidIDs(t *testing.T) {
	s := newTestServer(t)
	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
		for _, id := range []string{"abc", "0", "-1", "1.5", "99999999999999999999"} {
			body := ""
			if method == http.MethodPut {
				body = `{"title":"T","author":"A"}`
			}
			rec := do(t, s, method, "/books/"+id, body)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("%s /books/%s: status %d, want 400", method, id, rec.Code)
			}
		}
	}
	if rec := do(t, s, http.MethodGet, "/books/42", ""); rec.Code != http.StatusNotFound {
		t.Errorf("GET unknown id: status %d, want 404", rec.Code)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	s := newTestServer(t)
	if rec := do(t, s, http.MethodPatch, "/books/1", `{}`); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("PATCH: status %d, want 405", rec.Code)
	}
}

func TestPersistenceAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	store, err := OpenSQLiteStore(path)
	if err != nil {
		t.Fatal(err)
	}
	mustCreate(t, NewServer(store), `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	store.Close()

	store, err = OpenSQLiteStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	b, err := store.Get(context.Background(), 1)
	if err != nil {
		t.Fatalf("get after reopen: %v", err)
	}
	if b.Title != "Dune" || b.Year == nil || *b.Year != 1965 {
		t.Errorf("unexpected book after reopen: %+v", b)
	}
}

func TestStoreNotFound(t *testing.T) {
	store, err := OpenSQLiteStore(filepath.Join(t.TempDir(), "s.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	ctx := context.Background()
	if _, err := store.Get(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := store.Update(ctx, Book{ID: 1, Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := store.Delete(ctx, 1); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestConcurrentCreates(t *testing.T) {
	s := newTestServer(t)
	const n = 50
	errs := make(chan error, n)
	for i := 0; i < n; i++ {
		go func() {
			req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(`{"title":"T","author":"A"}`))
			rec := httptest.NewRecorder()
			s.ServeHTTP(rec, req)
			if rec.Code != http.StatusCreated {
				errs <- errors.New(rec.Body.String())
				return
			}
			errs <- nil
		}()
	}
	for i := 0; i < n; i++ {
		if err := <-errs; err != nil {
			t.Errorf("concurrent create failed: %v", err)
		}
	}
	if books := decode[[]Book](t, do(t, s, http.MethodGet, "/books", "")); len(books) != n {
		t.Errorf("got %d books, want %d", len(books), n)
	}
}

func TestValidISBN(t *testing.T) {
	valid := []string{"0441172717", "0-441-17271-7", "978-0134190440", "9780134190440", "080442957X", "080442957x", "978 0 13 419044 0"}
	invalid := []string{"", "123", "X441172717", "97801341904X0", "978013419044", "isbn0441172717", "04411727177"}
	for _, s := range valid {
		if !validISBN(s) {
			t.Errorf("validISBN(%q) = false, want true", s)
		}
	}
	for _, s := range invalid {
		if validISBN(s) {
			t.Errorf("validISBN(%q) = true, want false", s)
		}
	}
}
