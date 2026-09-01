package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// newTestServer returns a Server backed by a fresh in-memory SQLite database.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

// do performs a request against the server and returns the recorder.
func do(t *testing.T, srv http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		switch b := body.(type) {
		case string:
			buf.WriteString(b)
		default:
			if err := json.NewEncoder(&buf).Encode(b); err != nil {
				t.Fatalf("encode body: %v", err)
			}
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
	return v
}

func createBook(t *testing.T, srv http.Handler, title, author string, year int, isbn string) Book {
	t.Helper()
	rec := do(t, srv, http.MethodPost, "/books", map[string]any{
		"title": title, "author": author, "year": year, "isbn": isbn,
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create %q: want 201, got %d: %s", title, rec.Code, rec.Body.String())
	}
	return decode[Book](t, rec)
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rec := do(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", rec.Code)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("want JSON content type, got %q", ct)
	}
	body := decode[map[string]string](t, rec)
	if body["status"] != "ok" {
		t.Errorf("want status ok, got %v", body)
	}
}

func TestCreateBook(t *testing.T) {
	srv := newTestServer(t)
	rec := do(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("want 201, got %d: %s", rec.Code, rec.Body.String())
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("want Location /books/1, got %q", loc)
	}
	b := decode[Book](t, rec)
	if b.ID != 1 || b.Title != "Dune" || b.Author != "Frank Herbert" || b.Year == nil || *b.Year != 1965 || b.ISBN != "978-0441013593" {
		t.Errorf("unexpected book: %+v", b)
	}
}

func TestCreateBook_OptionalFieldsOmitted(t *testing.T) {
	srv := newTestServer(t)
	rec := do(t, srv, http.MethodPost, "/books", map[string]any{"title": "Untitled", "author": "Anon"})
	if rec.Code != http.StatusCreated {
		t.Fatalf("want 201, got %d: %s", rec.Code, rec.Body.String())
	}
	raw := decode[map[string]any](t, rec)
	if _, has := raw["year"]; has {
		t.Errorf("year should be omitted when unset, got %v", raw)
	}
	if _, has := raw["isbn"]; has {
		t.Errorf("isbn should be omitted when unset, got %v", raw)
	}
}

func TestCreateBook_Validation(t *testing.T) {
	srv := newTestServer(t)
	cases := []struct {
		name       string
		body       any
		wantStatus int
		wantField  string
	}{
		{"missing title", map[string]any{"author": "A"}, http.StatusUnprocessableEntity, "title"},
		{"missing author", map[string]any{"title": "T"}, http.StatusUnprocessableEntity, "author"},
		{"blank title", map[string]any{"title": "   ", "author": "A"}, http.StatusUnprocessableEntity, "title"},
		{"empty body", map[string]any{}, http.StatusUnprocessableEntity, "title"},
		{"bad year", map[string]any{"title": "T", "author": "A", "year": -5}, http.StatusUnprocessableEntity, "year"},
		{"bad isbn", map[string]any{"title": "T", "author": "A", "isbn": "123"}, http.StatusUnprocessableEntity, "isbn"},
		{"wrong type", map[string]any{"title": 42, "author": "A"}, http.StatusBadRequest, ""},
		{"malformed json", `{"title": "T", `, http.StatusBadRequest, ""},
		{"unknown field", map[string]any{"title": "T", "author": "A", "publisher": "X"}, http.StatusBadRequest, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPost, "/books", tc.body)
			if rec.Code != tc.wantStatus {
				t.Fatalf("want %d, got %d: %s", tc.wantStatus, rec.Code, rec.Body.String())
			}
			resp := decode[map[string]any](t, rec)
			if _, ok := resp["error"]; !ok {
				t.Errorf("response should contain an error message: %v", resp)
			}
			if tc.wantField != "" {
				fields, _ := resp["fields"].(map[string]any)
				if _, ok := fields[tc.wantField]; !ok {
					t.Errorf("want validation error on %q, got %v", tc.wantField, resp)
				}
			}
		})
	}

	// Nothing should have been persisted by any rejected request.
	rec := do(t, srv, http.MethodGet, "/books", nil)
	if books := decode[[]Book](t, rec); len(books) != 0 {
		t.Errorf("rejected requests must not persist books, got %v", books)
	}
}

func TestListBooks(t *testing.T) {
	srv := newTestServer(t)

	rec := do(t, srv, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", rec.Code)
	}
	if strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Errorf("empty list should encode as [], got %q", rec.Body.String())
	}

	createBook(t, srv, "Dune", "Frank Herbert", 1965, "")
	createBook(t, srv, "Neuromancer", "William Gibson", 1984, "")
	createBook(t, srv, "Dune Messiah", "Frank Herbert", 1969, "")

	rec = do(t, srv, http.MethodGet, "/books", nil)
	all := decode[[]Book](t, rec)
	if len(all) != 3 {
		t.Fatalf("want 3 books, got %d", len(all))
	}
	if all[0].ID != 1 || all[1].ID != 2 || all[2].ID != 3 {
		t.Errorf("books should be ordered by id: %+v", all)
	}
}

func TestListBooks_AuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, "Dune", "Frank Herbert", 1965, "")
	createBook(t, srv, "Neuromancer", "William Gibson", 1984, "")
	createBook(t, srv, "Dune Messiah", "Frank Herbert", 1969, "")

	rec := do(t, srv, http.MethodGet, "/books?author=Frank+Herbert", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", rec.Code)
	}
	got := decode[[]Book](t, rec)
	if len(got) != 2 {
		t.Fatalf("want 2 Herbert books, got %d: %+v", len(got), got)
	}
	for _, b := range got {
		if b.Author != "Frank Herbert" {
			t.Errorf("filter leaked other author: %+v", b)
		}
	}

	// Case-insensitive match.
	rec = do(t, srv, http.MethodGet, "/books?author=william+gibson", nil)
	if got := decode[[]Book](t, rec); len(got) != 1 || got[0].Title != "Neuromancer" {
		t.Errorf("case-insensitive filter failed: %+v", got)
	}

	// No match yields an empty array, not null.
	rec = do(t, srv, http.MethodGet, "/books?author=Nobody", nil)
	if strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Errorf("want [] for unknown author, got %q", rec.Body.String())
	}
}

func TestGetBook(t *testing.T) {
	srv := newTestServer(t)
	created := createBook(t, srv, "Dune", "Frank Herbert", 1965, "9780441013593")

	rec := do(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d: %s", rec.Code, rec.Body.String())
	}
	got := decode[Book](t, rec)
	if got.ID != created.ID || got.Title != created.Title || got.ISBN != created.ISBN {
		t.Errorf("want %+v, got %+v", created, got)
	}

	rec = do(t, srv, http.MethodGet, "/books/999", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("want 404 for missing book, got %d", rec.Code)
	}

	for _, bad := range []string{"/books/abc", "/books/0", "/books/-1"} {
		rec = do(t, srv, http.MethodGet, bad, nil)
		if rec.Code != http.StatusBadRequest {
			t.Errorf("%s: want 400, got %d", bad, rec.Code)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, "Dune", "Frank Herbert", 1965, "9780441013593")

	rec := do(t, srv, http.MethodPut, "/books/1", map[string]any{
		"title": "Dune (Deluxe)", "author": "Frank Herbert", "year": 2019,
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d: %s", rec.Code, rec.Body.String())
	}
	got := decode[Book](t, rec)
	if got.ID != 1 || got.Title != "Dune (Deluxe)" || got.Year == nil || *got.Year != 2019 {
		t.Errorf("unexpected updated book: %+v", got)
	}
	// PUT is a full replacement: omitted isbn is cleared.
	if got.ISBN != "" {
		t.Errorf("PUT should replace all fields; isbn should be cleared, got %q", got.ISBN)
	}

	// Persisted.
	rec = do(t, srv, http.MethodGet, "/books/1", nil)
	if again := decode[Book](t, rec); again.Title != "Dune (Deluxe)" {
		t.Errorf("update not persisted: %+v", again)
	}

	// Validation applies to updates too.
	rec = do(t, srv, http.MethodPut, "/books/1", map[string]any{"title": "", "author": "X"})
	if rec.Code != http.StatusUnprocessableEntity {
		t.Errorf("want 422 for invalid update, got %d", rec.Code)
	}

	// Unknown ID.
	rec = do(t, srv, http.MethodPut, "/books/42", map[string]any{"title": "T", "author": "A"})
	if rec.Code != http.StatusNotFound {
		t.Errorf("want 404 for missing book, got %d", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, "Dune", "Frank Herbert", 1965, "")
	createBook(t, srv, "Neuromancer", "William Gibson", 1984, "")

	rec := do(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("want 204, got %d: %s", rec.Code, rec.Body.String())
	}
	if rec.Body.Len() != 0 {
		t.Errorf("204 must have empty body, got %q", rec.Body.String())
	}

	rec = do(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("deleted book should 404, got %d", rec.Code)
	}

	rec = do(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("second delete should 404, got %d", rec.Code)
	}

	rec = do(t, srv, http.MethodGet, "/books", nil)
	if left := decode[[]Book](t, rec); len(left) != 1 || left[0].ID != 2 {
		t.Errorf("only book 2 should remain, got %+v", left)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	srv := newTestServer(t)
	rec := do(t, srv, http.MethodPatch, "/books/1", nil)
	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("want 405, got %d", rec.Code)
	}
	rec = do(t, srv, http.MethodGet, "/nope", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("want 404, got %d", rec.Code)
	}
}

func TestStore_FileBacked(t *testing.T) {
	path := t.TempDir() + "/books.db"

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	created := createBook(t, NewServer(store), "Dune", "Frank Herbert", 1965, "")
	store.Close()

	// Reopen and confirm the row survived.
	store2, err := OpenStore(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer store2.Close()
	rec := do(t, NewServer(store2), http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("want 200 after reopen, got %d", rec.Code)
	}
	if got := decode[Book](t, rec); got.Title != created.Title {
		t.Errorf("want %+v, got %+v", created, got)
	}
}
