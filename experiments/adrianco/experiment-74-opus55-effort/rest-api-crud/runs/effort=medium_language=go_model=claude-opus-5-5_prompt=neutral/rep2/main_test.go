package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	ts := httptest.NewServer((&Server{store: store}).Routes())
	t.Cleanup(func() {
		ts.Close()
		store.Close()
	})
	return ts
}

func do(t *testing.T, ts *httptest.Server, method, path, body string) *http.Response {
	t.Helper()
	req, err := http.NewRequest(method, ts.URL+path, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
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
	ts := newTestServer(t)
	resp := do(t, ts, "GET", "/health", "")
	expectStatus(t, resp, http.StatusOK)
	if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("content-type = %q", ct)
	}
	if got := decode[map[string]string](t, resp); got["status"] != "ok" {
		t.Errorf("status = %q", got["status"])
	}
}

func TestBookCRUDLifecycle(t *testing.T) {
	ts := newTestServer(t)

	resp := do(t, ts, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`)
	expectStatus(t, resp, http.StatusCreated)
	created := decode[Book](t, resp)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := resp.Header.Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q", loc)
	}

	resp = do(t, ts, "GET", "/books/1", "")
	expectStatus(t, resp, http.StatusOK)
	if got := decode[Book](t, resp); got != created {
		t.Errorf("get = %+v, want %+v", got, created)
	}

	resp = do(t, ts, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	expectStatus(t, resp, http.StatusOK)
	if got := decode[Book](t, resp); got.Title != "Dune Messiah" || got.Year != 1969 || got.ISBN != "" {
		t.Errorf("updated = %+v", got)
	}

	resp = do(t, ts, "GET", "/books/1", "")
	if got := decode[Book](t, resp); got.Title != "Dune Messiah" {
		t.Errorf("update not persisted: %+v", got)
	}

	expectStatus(t, do(t, ts, "DELETE", "/books/1", ""), http.StatusNoContent)
	expectStatus(t, do(t, ts, "GET", "/books/1", ""), http.StatusNotFound)
	expectStatus(t, do(t, ts, "DELETE", "/books/1", ""), http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	resp := do(t, ts, "GET", "/books", "")
	expectStatus(t, resp, http.StatusOK)
	if got := decode[[]Book](t, resp); got == nil || len(got) != 0 {
		t.Fatalf("empty list should be [], got %v", got)
	}

	for _, b := range []string{
		`{"title":"Emma","author":"Jane Austen"}`,
		`{"title":"Persuasion","author":"Jane Austen"}`,
		`{"title":"Ulysses","author":"James Joyce"}`,
	} {
		expectStatus(t, do(t, ts, "POST", "/books", b), http.StatusCreated)
	}

	resp = do(t, ts, "GET", "/books", "")
	if got := decode[[]Book](t, resp); len(got) != 3 {
		t.Errorf("all books: got %d, want 3", len(got))
	}

	resp = do(t, ts, "GET", "/books?author=jane%20austen", "")
	expectStatus(t, resp, http.StatusOK)
	got := decode[[]Book](t, resp)
	if len(got) != 2 {
		t.Fatalf("filtered: got %d, want 2", len(got))
	}
	for _, b := range got {
		if b.Author != "Jane Austen" {
			t.Errorf("unexpected author %q", b.Author)
		}
	}

	resp = do(t, ts, "GET", "/books?author=Nobody", "")
	if got := decode[[]Book](t, resp); len(got) != 0 {
		t.Errorf("unknown author: got %d", len(got))
	}
}

func TestValidation(t *testing.T) {
	ts := newTestServer(t)

	cases := []struct {
		name, body string
		status     int
		field      string
	}{
		{"missing title", `{"author":"A"}`, http.StatusUnprocessableEntity, "title"},
		{"missing author", `{"title":"T"}`, http.StatusUnprocessableEntity, "author"},
		{"blank title", `{"title":"   ","author":"A"}`, http.StatusUnprocessableEntity, "title"},
		{"bad isbn", `{"title":"T","author":"A","isbn":"abc"}`, http.StatusUnprocessableEntity, "isbn"},
		{"negative year", `{"title":"T","author":"A","year":-5}`, http.StatusUnprocessableEntity, "year"},
		{"malformed json", `{"title":`, http.StatusBadRequest, ""},
		{"unknown field", `{"title":"T","author":"A","pages":3}`, http.StatusBadRequest, ""},
		{"wrong type", `{"title":"T","author":"A","year":"1999"}`, http.StatusBadRequest, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp := do(t, ts, "POST", "/books", tc.body)
			expectStatus(t, resp, tc.status)
			body := decode[struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}](t, resp)
			if body.Error == "" {
				t.Error("missing error message")
			}
			if tc.field != "" && body.Fields[tc.field] == "" {
				t.Errorf("expected field error for %q, got %v", tc.field, body.Fields)
			}
		})
	}

	// Validation also applies to updates.
	expectStatus(t, do(t, ts, "POST", "/books", `{"title":"T","author":"A"}`), http.StatusCreated)
	expectStatus(t, do(t, ts, "PUT", "/books/1", `{"title":""}`), http.StatusUnprocessableEntity)
}

func TestNotFoundAndBadIDs(t *testing.T) {
	ts := newTestServer(t)
	expectStatus(t, do(t, ts, "GET", "/books/999", ""), http.StatusNotFound)
	expectStatus(t, do(t, ts, "PUT", "/books/999", `{"title":"T","author":"A"}`), http.StatusNotFound)
	expectStatus(t, do(t, ts, "GET", "/books/abc", ""), http.StatusBadRequest)
	expectStatus(t, do(t, ts, "DELETE", "/books/0", ""), http.StatusBadRequest)
	expectStatus(t, do(t, ts, "PATCH", "/books/1", ""), http.StatusMethodNotAllowed)
}

func TestPersistenceAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	s1, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	b := &Book{Title: "Beloved", Author: "Toni Morrison", Year: 1987}
	if err := s1.Create(b); err != nil {
		t.Fatal(err)
	}
	s1.Close()

	s2, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	got, err := s2.Get(b.ID)
	if err != nil || *got != *b {
		t.Fatalf("after reopen got %+v, %v", got, err)
	}
}

func TestValidISBN(t *testing.T) {
	for s, want := range map[string]bool{
		"0-306-40615-2":     true,
		"978-0-306-40615-7": true,
		"080442957X":        true,
		"12345":             false,
		"97803064061X7":     false,
		"":                  false,
	} {
		if got := validISBN(s); got != want {
			t.Errorf("validISBN(%q) = %v, want %v", s, got, want)
		}
	}
}
