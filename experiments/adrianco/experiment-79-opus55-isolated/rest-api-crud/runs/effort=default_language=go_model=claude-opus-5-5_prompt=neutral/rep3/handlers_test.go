package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

// newTestAPI returns a handler backed by a fresh in-memory database.
func newTestAPI(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store).Routes()
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decode[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
	return v
}

func mustCreate(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: status = %d, body = %s", rec.Code, rec.Body.String())
	}
	return decode[Book](t, rec)
}

func TestHealth(t *testing.T) {
	h := newTestAPI(t)
	rec := do(t, h, http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := decode[map[string]string](t, rec); got["status"] != "ok" {
		t.Errorf("body = %v, want status ok", got)
	}
}

func TestCreateBook(t *testing.T) {
	h := newTestAPI(t)
	rec := do(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201; body = %s", rec.Code, rec.Body.String())
	}
	got := decode[Book](t, rec)
	want := Book{ID: got.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	if got != want || got.ID <= 0 {
		t.Errorf("book = %+v, want %+v with positive ID", got, want)
	}
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}
}

func TestCreateBookValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string
	}{
		{"missing title", `{"author":"Frank Herbert"}`, 400, []string{"title"}},
		{"missing author", `{"title":"Dune"}`, 400, []string{"author"}},
		{"missing both", `{}`, 400, []string{"title", "author"}},
		{"blank title", `{"title":"   ","author":"Frank Herbert"}`, 400, []string{"title"}},
		{"negative year", `{"title":"Dune","author":"Frank Herbert","year":-1}`, 400, []string{"year"}},
		{"wrong type", `{"title":"Dune","author":"Frank Herbert","year":"1965"}`, 400, nil},
		{"malformed json", `{"title":`, 400, nil},
		{"empty body", ``, 400, nil},
		{"trailing data", `{"title":"Dune","author":"Frank Herbert"}{}`, 400, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newTestAPI(t)
			rec := do(t, h, http.MethodPost, "/books", tt.body)
			if rec.Code != tt.wantStatus {
				t.Fatalf("status = %d, want %d; body = %s", rec.Code, tt.wantStatus, rec.Body.String())
			}
			resp := decode[errorResponse](t, rec)
			if resp.Error == "" {
				t.Error("error message is empty")
			}
			if len(resp.Details) != len(tt.wantFields) {
				t.Errorf("details = %v, want fields %v", resp.Details, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if resp.Details[f] == "" {
					t.Errorf("details missing field %q: %v", f, resp.Details)
				}
			}
			// Nothing should have been stored.
			if books := decode[[]Book](t, do(t, h, http.MethodGet, "/books", "")); len(books) != 0 {
				t.Errorf("books stored after invalid create: %+v", books)
			}
		})
	}
}

func TestGetBook(t *testing.T) {
	h := newTestAPI(t)
	created := mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)

	rec := do(t, h, http.MethodGet, "/books/1", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := decode[Book](t, rec); got != created {
		t.Errorf("book = %+v, want %+v", got, created)
	}

	if rec := do(t, h, http.MethodGet, "/books/999", ""); rec.Code != http.StatusNotFound {
		t.Errorf("missing book: status = %d, want 404", rec.Code)
	} else if decode[errorResponse](t, rec).Error == "" {
		t.Error("missing book: empty error message")
	}
	for _, id := range []string{"abc", "0", "-1", "1.5"} {
		if rec := do(t, h, http.MethodGet, "/books/"+id, ""); rec.Code != http.StatusBadRequest {
			t.Errorf("id %q: status = %d, want 400", id, rec.Code)
		}
	}
}

func TestListBooks(t *testing.T) {
	h := newTestAPI(t)

	// An empty collection is an empty JSON array, not null.
	rec := do(t, h, http.MethodGet, "/books", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %q, want []", body)
	}

	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	mustCreate(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	mustCreate(t, h, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)

	titles := func(path string) []string {
		t.Helper()
		rec := do(t, h, http.MethodGet, path, "")
		if rec.Code != http.StatusOK {
			t.Fatalf("GET %s: status = %d, want 200", path, rec.Code)
		}
		var out []string
		for _, b := range decode[[]Book](t, rec) {
			out = append(out, b.Title)
		}
		return out
	}

	tests := []struct {
		path string
		want string
	}{
		{"/books", "Dune,Emma,Dune Messiah"},
		{"/books?author=Frank+Herbert", "Dune,Dune Messiah"},
		{"/books?author=frank%20herbert", "Dune,Dune Messiah"},
		{"/books?author=Jane+Austen", "Emma"},
		{"/books?author=Nobody", ""},
		{"/books?author=Frank", ""},
		{"/books?author=", "Dune,Emma,Dune Messiah"},
	}
	for _, tt := range tests {
		if got := strings.Join(titles(tt.path), ","); got != tt.want {
			t.Errorf("GET %s: titles = %q, want %q", tt.path, got, tt.want)
		}
	}
}

func TestListAuthorFilterIsNotInjectable(t *testing.T) {
	h := newTestAPI(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)

	rec := do(t, h, http.MethodGet, "/books?author=x%27+OR+%271%27%3D%271", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if books := decode[[]Book](t, rec); len(books) != 0 {
		t.Errorf("books = %+v, want none", books)
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestAPI(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)

	rec := do(t, h, http.MethodPut, "/books/1", `{"title":"Dune (Revised)","author":"F. Herbert","year":1966}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200; body = %s", rec.Code, rec.Body.String())
	}
	// PUT replaces the whole record, so the omitted isbn is cleared.
	want := Book{ID: 1, Title: "Dune (Revised)", Author: "F. Herbert", Year: 1966}
	if got := decode[Book](t, rec); got != want {
		t.Errorf("response = %+v, want %+v", got, want)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("stored = %+v, want %+v", got, want)
	}

	if rec := do(t, h, http.MethodPut, "/books/1", `{"title":"","author":"F. Herbert"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("invalid update: status = %d, want 400", rec.Code)
	}
	if got := decode[Book](t, do(t, h, http.MethodGet, "/books/1", "")); got != want {
		t.Errorf("after invalid update: stored = %+v, want %+v", got, want)
	}
	if rec := do(t, h, http.MethodPut, "/books/999", `{"title":"X","author":"Y"}`); rec.Code != http.StatusNotFound {
		t.Errorf("missing book: status = %d, want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodPut, "/books/abc", `{"title":"X","author":"Y"}`); rec.Code != http.StatusBadRequest {
		t.Errorf("bad id: status = %d, want 400", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestAPI(t)
	mustCreate(t, h, `{"title":"Dune","author":"Frank Herbert"}`)
	mustCreate(t, h, `{"title":"Emma","author":"Jane Austen"}`)

	rec := do(t, h, http.MethodDelete, "/books/1", "")
	if rec.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want 204", rec.Code)
	}
	if rec.Body.Len() != 0 {
		t.Errorf("body = %q, want empty", rec.Body.String())
	}
	if rec := do(t, h, http.MethodGet, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("get after delete: status = %d, want 404", rec.Code)
	}
	if rec := do(t, h, http.MethodDelete, "/books/1", ""); rec.Code != http.StatusNotFound {
		t.Errorf("second delete: status = %d, want 404", rec.Code)
	}
	books := decode[[]Book](t, do(t, h, http.MethodGet, "/books", ""))
	if len(books) != 1 || books[0].Title != "Emma" {
		t.Errorf("remaining books = %+v, want only Emma", books)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	h := newTestAPI(t)
	if rec := do(t, h, http.MethodPatch, "/books/1", `{}`); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("PATCH /books/1: status = %d, want 405", rec.Code)
	}
	if rec := do(t, h, http.MethodDelete, "/books", ""); rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("DELETE /books: status = %d, want 405", rec.Code)
	}
}

func TestDataPersistsAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	created := mustCreate(t, NewServer(store).Routes(), `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	store, err = NewStore(path)
	if err != nil {
		t.Fatalf("reopen NewStore: %v", err)
	}
	defer store.Close()
	rec := do(t, NewServer(store).Routes(), http.MethodGet, "/books/1", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	if got := decode[Book](t, rec); got != created {
		t.Errorf("book = %+v, want %+v", got, created)
	}
}
