package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := NewStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	switch b := body.(type) {
	case nil:
	case string:
		buf.WriteString(b)
	default:
		if err := json.NewEncoder(&buf).Encode(b); err != nil {
			t.Fatal(err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode %q: %v", rec.Body.String(), err)
	}
	return v
}

func expectStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s, "GET", "/health", nil)
	expectStatus(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec)["status"]; got != "ok" {
		t.Errorf("status field = %q", got)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}
}

func TestCRUDLifecycle(t *testing.T) {
	s := newTestServer(t)

	// Create
	rec := do(t, s, "POST", "/books", map[string]any{
		"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593",
	})
	expectStatus(t, rec, http.StatusCreated)
	created := decode[Book](t, rec)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q", loc)
	}

	// Get
	rec = do(t, s, "GET", "/books/1", nil)
	expectStatus(t, rec, http.StatusOK)
	if got := decode[Book](t, rec); got != created {
		t.Errorf("get = %+v, want %+v", got, created)
	}

	// Update
	rec = do(t, s, "PUT", "/books/1", map[string]any{
		"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969,
	})
	expectStatus(t, rec, http.StatusOK)
	rec = do(t, s, "GET", "/books/1", nil)
	if got := decode[Book](t, rec); got.Title != "Dune Messiah" || got.Year != 1969 || got.ISBN != "" {
		t.Errorf("after update = %+v", got)
	}

	// Delete
	rec = do(t, s, "DELETE", "/books/1", nil)
	expectStatus(t, rec, http.StatusNoContent)
	expectStatus(t, do(t, s, "GET", "/books/1", nil), http.StatusNotFound)
	expectStatus(t, do(t, s, "DELETE", "/books/1", nil), http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	s := newTestServer(t)

	// Empty list is [] not null.
	rec := do(t, s, "GET", "/books", nil)
	expectStatus(t, rec, http.StatusOK)
	if body := bytes.TrimSpace(rec.Body.Bytes()); string(body) != "[]" {
		t.Errorf("empty list body = %s", body)
	}

	for _, b := range []map[string]any{
		{"title": "Emma", "author": "Jane Austen"},
		{"title": "Persuasion", "author": "Jane Austen"},
		{"title": "Ulysses", "author": "James Joyce"},
	} {
		expectStatus(t, do(t, s, "POST", "/books", b), http.StatusCreated)
	}

	all := decode[[]Book](t, do(t, s, "GET", "/books", nil))
	if len(all) != 3 {
		t.Errorf("len(all) = %d, want 3", len(all))
	}

	austen := decode[[]Book](t, do(t, s, "GET", "/books?author=jane+austen", nil))
	if len(austen) != 2 {
		t.Fatalf("len(austen) = %d, want 2", len(austen))
	}
	for _, b := range austen {
		if b.Author != "Jane Austen" {
			t.Errorf("filter returned %+v", b)
		}
	}

	none := decode[[]Book](t, do(t, s, "GET", "/books?author=Nobody", nil))
	if len(none) != 0 {
		t.Errorf("len(none) = %d, want 0", len(none))
	}
}

func TestValidation(t *testing.T) {
	s := newTestServer(t)
	cases := []struct {
		name      string
		body      any
		wantField string
	}{
		{"missing title", map[string]any{"author": "A"}, "title"},
		{"blank author", map[string]any{"title": "T", "author": "   "}, "author"},
		{"negative year", map[string]any{"title": "T", "author": "A", "year": -5}, "year"},
		{"bad isbn", map[string]any{"title": "T", "author": "A", "isbn": "abc"}, "isbn"},
		{"malformed json", `{"title":`, ""},
		{"unknown field", map[string]any{"title": "T", "author": "A", "pages": 3}, ""},
		{"wrong type", map[string]any{"title": "T", "author": "A", "year": "1999"}, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, s, "POST", "/books", tc.body)
			expectStatus(t, rec, http.StatusBadRequest)
			resp := decode[struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}](t, rec)
			if resp.Error == "" {
				t.Error("missing error message")
			}
			if tc.wantField != "" && resp.Fields[tc.wantField] == "" {
				t.Errorf("expected field error for %q, got %v", tc.wantField, resp.Fields)
			}
		})
	}

	// Update validates too, and nothing was persisted by the failures above.
	expectStatus(t, do(t, s, "POST", "/books", map[string]any{"title": "T", "author": "A"}), http.StatusCreated)
	expectStatus(t, do(t, s, "PUT", "/books/1", map[string]any{"title": ""}), http.StatusBadRequest)
	if n := len(decode[[]Book](t, do(t, s, "GET", "/books", nil))); n != 1 {
		t.Errorf("book count = %d, want 1", n)
	}
}

func TestNotFoundAndBadIDs(t *testing.T) {
	s := newTestServer(t)
	valid := map[string]any{"title": "T", "author": "A"}
	expectStatus(t, do(t, s, "GET", "/books/999", nil), http.StatusNotFound)
	expectStatus(t, do(t, s, "PUT", "/books/999", valid), http.StatusNotFound)
	expectStatus(t, do(t, s, "GET", "/books/abc", nil), http.StatusBadRequest)
	expectStatus(t, do(t, s, "DELETE", "/books/0", nil), http.StatusBadRequest)
	expectStatus(t, do(t, s, "PATCH", "/books/1", valid), http.StatusMethodNotAllowed)
}

func TestPersistenceAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	store, err := NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	b := Book{Title: "Kept", Author: "Someone"}
	if err := store.Create(&b); err != nil {
		t.Fatal(err)
	}
	store.Close()

	store, err = NewStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	got, err := store.Get(b.ID)
	if err != nil || got.Title != "Kept" {
		t.Fatalf("after reopen: %+v, %v", got, err)
	}
}

func TestValidISBN(t *testing.T) {
	for s, want := range map[string]bool{
		"0-306-40615-2":     true,
		"978-3-16-148410-0": true,
		"080442957X":        true,
		"X804429570":        false,
		"12345":             false,
		"97831614841OO":     false,
	} {
		if got := validISBN(s); got != want {
			t.Errorf("validISBN(%q) = %v, want %v", s, got, want)
		}
	}
}
