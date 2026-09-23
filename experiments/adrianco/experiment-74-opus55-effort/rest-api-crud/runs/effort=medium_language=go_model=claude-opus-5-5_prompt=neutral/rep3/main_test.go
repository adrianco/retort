package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	srv := httptest.NewServer(NewServer(store))
	t.Cleanup(func() {
		srv.Close()
		store.Close()
	})
	return srv
}

func do(t *testing.T, srv *httptest.Server, method, path string, body any) *http.Response {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if s, ok := body.(string); ok {
			buf.WriteString(s)
		} else if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatal(err)
		}
	}
	req, err := http.NewRequest(method, srv.URL+path, &buf)
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { resp.Body.Close() })
	return resp
}

func decode[T any](t *testing.T, resp *http.Response) T {
	t.Helper()
	var v T
	if err := json.NewDecoder(resp.Body).Decode(&v); err != nil {
		t.Fatalf("decode: %v", err)
	}
	return v
}

func expectStatus(t *testing.T, resp *http.Response, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("%s %s: status = %d, want %d", resp.Request.Method, resp.Request.URL.Path, resp.StatusCode, want)
	}
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	resp := do(t, srv, "GET", "/health", nil)
	expectStatus(t, resp, http.StatusOK)
	if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}
	if got := decode[map[string]string](t, resp); got["status"] != "ok" {
		t.Errorf("health body = %v", got)
	}
}

func TestBookCRUDLifecycle(t *testing.T) {
	srv := newTestServer(t)

	// Create
	resp := do(t, srv, "POST", "/books", bookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441013593"})
	expectStatus(t, resp, http.StatusCreated)
	created := decode[Book](t, resp)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := resp.Header.Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q", loc)
	}

	// Get
	resp = do(t, srv, "GET", "/books/1", nil)
	expectStatus(t, resp, http.StatusOK)
	if got := decode[Book](t, resp); got != created {
		t.Errorf("get = %+v, want %+v", got, created)
	}

	// Update
	resp = do(t, srv, "PUT", "/books/1", bookInput{Title: "Dune (Revised)", Author: "Frank Herbert", Year: 1966})
	expectStatus(t, resp, http.StatusOK)
	resp = do(t, srv, "GET", "/books/1", nil)
	if got := decode[Book](t, resp); got.Title != "Dune (Revised)" || got.Year != 1966 || got.ISBN != "" {
		t.Errorf("after update = %+v", got)
	}

	// Delete
	resp = do(t, srv, "DELETE", "/books/1", nil)
	expectStatus(t, resp, http.StatusNoContent)
	expectStatus(t, do(t, srv, "GET", "/books/1", nil), http.StatusNotFound)
	expectStatus(t, do(t, srv, "DELETE", "/books/1", nil), http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	// Empty list is [] not null.
	resp := do(t, srv, "GET", "/books", nil)
	expectStatus(t, resp, http.StatusOK)
	if got := decode[[]Book](t, resp); got == nil || len(got) != 0 {
		t.Fatalf("empty list = %#v", got)
	}

	for _, b := range []bookInput{
		{Title: "Emma", Author: "Jane Austen"},
		{Title: "Persuasion", Author: "Jane Austen"},
		{Title: "Ulysses", Author: "James Joyce"},
	} {
		expectStatus(t, do(t, srv, "POST", "/books", b), http.StatusCreated)
	}

	all := decode[[]Book](t, do(t, srv, "GET", "/books", nil))
	if len(all) != 3 {
		t.Errorf("list all: got %d books", len(all))
	}

	austen := decode[[]Book](t, do(t, srv, "GET", "/books?author=jane%20austen", nil))
	if len(austen) != 2 {
		t.Fatalf("author filter: got %d books, want 2", len(austen))
	}
	for _, b := range austen {
		if b.Author != "Jane Austen" {
			t.Errorf("filter returned %+v", b)
		}
	}

	none := decode[[]Book](t, do(t, srv, "GET", "/books?author=Nobody", nil))
	if len(none) != 0 {
		t.Errorf("unknown author returned %d books", len(none))
	}
}

func TestValidation(t *testing.T) {
	srv := newTestServer(t)

	cases := []struct {
		name   string
		method string
		path   string
		body   any
		status int
		field  string
	}{
		{"missing title", "POST", "/books", bookInput{Author: "A"}, http.StatusUnprocessableEntity, "title"},
		{"missing author", "POST", "/books", bookInput{Title: "T"}, http.StatusUnprocessableEntity, "author"},
		{"blank title", "POST", "/books", bookInput{Title: "   ", Author: "A"}, http.StatusUnprocessableEntity, "title"},
		{"negative year", "POST", "/books", bookInput{Title: "T", Author: "A", Year: -5}, http.StatusUnprocessableEntity, "year"},
		{"bad isbn", "POST", "/books", bookInput{Title: "T", Author: "A", ISBN: "abc"}, http.StatusUnprocessableEntity, "isbn"},
		{"malformed json", "POST", "/books", `{"title":`, http.StatusBadRequest, ""},
		{"unknown field", "POST", "/books", `{"title":"T","author":"A","pages":3}`, http.StatusBadRequest, ""},
		{"wrong type", "POST", "/books", `{"title":"T","author":"A","year":"1999"}`, http.StatusBadRequest, ""},
		{"non-numeric id", "GET", "/books/abc", nil, http.StatusBadRequest, ""},
		{"update missing author", "PUT", "/books/1", bookInput{Title: "T"}, http.StatusUnprocessableEntity, "author"},
		{"update nonexistent", "PUT", "/books/999", bookInput{Title: "T", Author: "A"}, http.StatusNotFound, ""},
		{"get nonexistent", "GET", "/books/999", nil, http.StatusNotFound, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp := do(t, srv, tc.method, tc.path, tc.body)
			expectStatus(t, resp, tc.status)
			body := decode[map[string]any](t, resp)
			if body["error"] == nil {
				t.Errorf("missing error message: %v", body)
			}
			if tc.field != "" {
				fields, _ := body["fields"].(map[string]any)
				if _, ok := fields[tc.field]; !ok {
					t.Errorf("expected field error for %q, got %v", tc.field, body)
				}
			}
		})
	}

	// Nothing invalid should have been persisted.
	if got := decode[[]Book](t, do(t, srv, "GET", "/books", nil)); len(got) != 0 {
		t.Errorf("invalid requests persisted %d books", len(got))
	}
}

func TestValidISBN(t *testing.T) {
	for s, want := range map[string]bool{
		"0441013597":     true,
		"044101359X":     true,
		"978-0441013593": true,
		"978 0441013593": true,
		"12345":          false,
		"97804410135X3":  false,
		"abcdefghij":     false,
	} {
		if got := validISBN(s); got != want {
			t.Errorf("validISBN(%q) = %v, want %v", s, got, want)
		}
	}
}

func TestPersistenceAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	s1, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := s1.Create(Book{Title: "Kept", Author: "Someone"}); err != nil {
		t.Fatal(err)
	}
	s1.Close()

	s2, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	b, err := s2.Get(1)
	if err != nil || b.Title != "Kept" {
		t.Fatalf("after reopen: %+v, %v", b, err)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	srv := newTestServer(t)
	resp := do(t, srv, "PATCH", "/books/1", nil)
	expectStatus(t, resp, http.StatusMethodNotAllowed)
	if body := decode[map[string]any](t, resp); body["error"] == nil {
		t.Errorf("missing error message: %v", body)
	}
}

func TestUnknownRoute(t *testing.T) {
	srv := newTestServer(t)
	resp := do(t, srv, "GET", "/nope", nil)
	expectStatus(t, resp, http.StatusNotFound)
	if body := decode[map[string]any](t, resp); body["error"] != "not found" {
		t.Errorf("unexpected body: %v", body)
	}
}
