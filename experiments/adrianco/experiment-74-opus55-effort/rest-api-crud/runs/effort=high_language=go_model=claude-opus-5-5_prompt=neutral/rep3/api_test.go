package main

import (
	"bytes"
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
	ts := httptest.NewServer(NewServer(store))
	t.Cleanup(func() {
		ts.Close()
		store.Close()
	})
	return ts
}

func do(t *testing.T, ts *httptest.Server, method, path, body string) (*http.Response, []byte) {
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
	defer resp.Body.Close()
	var buf bytes.Buffer
	buf.ReadFrom(resp.Body)
	return resp, buf.Bytes()
}

func mustStatus(t *testing.T, resp *http.Response, body []byte, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("%s %s: status = %d, want %d; body: %s",
			resp.Request.Method, resp.Request.URL.Path, resp.StatusCode, want, body)
	}
}

func createBook(t *testing.T, ts *httptest.Server, body string) Book {
	t.Helper()
	resp, raw := do(t, ts, http.MethodPost, "/books", body)
	mustStatus(t, resp, raw, http.StatusCreated)
	var b Book
	if err := json.Unmarshal(raw, &b); err != nil {
		t.Fatalf("decode: %v", err)
	}
	return b
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, ts, http.MethodGet, "/health", "")
	mustStatus(t, resp, body, http.StatusOK)
	if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}
	var got map[string]string
	json.Unmarshal(body, &got)
	if got["status"] != "ok" {
		t.Errorf("status = %q, want ok", got["status"])
	}
}

func TestCRUDLifecycle(t *testing.T) {
	ts := newTestServer(t)

	created := createBook(t, ts, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441013593"}`)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}

	// Get
	resp, body := do(t, ts, http.MethodGet, "/books/1", "")
	mustStatus(t, resp, body, http.StatusOK)
	var got Book
	json.Unmarshal(body, &got)
	if got != created {
		t.Fatalf("get = %+v, want %+v", got, created)
	}

	// Update
	resp, body = do(t, ts, http.MethodPut, "/books/1",
		`{"title":"Dune (Deluxe)","author":"Frank Herbert","year":2019,"isbn":"0441013597"}`)
	mustStatus(t, resp, body, http.StatusOK)
	json.Unmarshal(body, &got)
	if got.Title != "Dune (Deluxe)" || got.Year != 2019 || got.ID != 1 {
		t.Fatalf("updated = %+v", got)
	}
	resp, body = do(t, ts, http.MethodGet, "/books/1", "")
	json.Unmarshal(body, &got)
	if got.Title != "Dune (Deluxe)" {
		t.Fatalf("update not persisted: %+v", got)
	}

	// Delete
	resp, body = do(t, ts, http.MethodDelete, "/books/1", "")
	mustStatus(t, resp, body, http.StatusNoContent)
	resp, body = do(t, ts, http.MethodGet, "/books/1", "")
	mustStatus(t, resp, body, http.StatusNotFound)
	resp, body = do(t, ts, http.MethodDelete, "/books/1", "")
	mustStatus(t, resp, body, http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	// Empty collection returns an empty JSON array, not null.
	resp, body := do(t, ts, http.MethodGet, "/books", "")
	mustStatus(t, resp, body, http.StatusOK)
	if strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("empty list body = %s, want []", body)
	}

	createBook(t, ts, `{"title":"Emma","author":"Jane Austen"}`)
	createBook(t, ts, `{"title":"Persuasion","author":"Jane Austen"}`)
	createBook(t, ts, `{"title":"Ulysses","author":"James Joyce"}`)

	var books []Book
	resp, body = do(t, ts, http.MethodGet, "/books", "")
	mustStatus(t, resp, body, http.StatusOK)
	json.Unmarshal(body, &books)
	if len(books) != 3 {
		t.Fatalf("len = %d, want 3", len(books))
	}

	resp, body = do(t, ts, http.MethodGet, "/books?author=jane+austen", "")
	mustStatus(t, resp, body, http.StatusOK)
	books = nil
	json.Unmarshal(body, &books)
	if len(books) != 2 {
		t.Fatalf("filtered len = %d, want 2: %s", len(books), body)
	}
	for _, b := range books {
		if b.Author != "Jane Austen" {
			t.Errorf("unexpected author %q", b.Author)
		}
	}

	resp, body = do(t, ts, http.MethodGet, "/books?author=Nobody", "")
	mustStatus(t, resp, body, http.StatusOK)
	if strings.TrimSpace(string(body)) != "[]" {
		t.Fatalf("no-match body = %s, want []", body)
	}
}

func TestValidation(t *testing.T) {
	ts := newTestServer(t)
	createBook(t, ts, `{"title":"Existing","author":"Someone"}`)

	cases := []struct {
		name, method, path, body string
		wantField                string
	}{
		{"missing title", http.MethodPost, "/books", `{"author":"A"}`, "title"},
		{"missing author", http.MethodPost, "/books", `{"title":"T"}`, "author"},
		{"blank title", http.MethodPost, "/books", `{"title":"   ","author":"A"}`, "title"},
		{"negative year", http.MethodPost, "/books", `{"title":"T","author":"A","year":-5}`, "year"},
		{"bad isbn", http.MethodPost, "/books", `{"title":"T","author":"A","isbn":"abc"}`, "isbn"},
		{"update missing author", http.MethodPut, "/books/1", `{"title":"T"}`, "author"},
		{"malformed json", http.MethodPost, "/books", `{"title":`, ""},
		{"unknown field", http.MethodPost, "/books", `{"title":"T","author":"A","pages":3}`, ""},
		{"wrong type", http.MethodPost, "/books", `{"title":"T","author":"A","year":"1999"}`, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body := do(t, ts, tc.method, tc.path, tc.body)
			mustStatus(t, resp, body, http.StatusBadRequest)
			var er errorResponse
			if err := json.Unmarshal(body, &er); err != nil || er.Error == "" {
				t.Fatalf("expected JSON error body, got %s", body)
			}
			if tc.wantField != "" && er.Fields[tc.wantField] == "" {
				t.Errorf("expected field error for %q, got %+v", tc.wantField, er.Fields)
			}
		})
	}

	// Failed update must not modify the stored book.
	resp, body := do(t, ts, http.MethodGet, "/books/1", "")
	mustStatus(t, resp, body, http.StatusOK)
	var b Book
	json.Unmarshal(body, &b)
	if b.Title != "Existing" {
		t.Errorf("book modified by invalid update: %+v", b)
	}
}

func TestNotFoundAndBadIDs(t *testing.T) {
	ts := newTestServer(t)
	valid := `{"title":"T","author":"A"}`

	cases := []struct {
		method, path, body string
		want               int
	}{
		{http.MethodGet, "/books/999", "", http.StatusNotFound},
		{http.MethodPut, "/books/999", valid, http.StatusNotFound},
		{http.MethodDelete, "/books/999", "", http.StatusNotFound},
		{http.MethodGet, "/books/abc", "", http.StatusBadRequest},
		{http.MethodGet, "/books/0", "", http.StatusBadRequest},
		{http.MethodPut, "/books/-1", valid, http.StatusBadRequest},
		{http.MethodPatch, "/books/1", valid, http.StatusMethodNotAllowed},
	}
	for _, tc := range cases {
		resp, body := do(t, ts, tc.method, tc.path, tc.body)
		mustStatus(t, resp, body, tc.want)
	}
}

func TestCreateSetsLocationHeader(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, ts, http.MethodPost, "/books", `{"title":"T","author":"A"}`)
	mustStatus(t, resp, body, http.StatusCreated)
	if loc := resp.Header.Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}
}

func TestPersistenceAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	s1, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := s1.Create(t.Context(), Book{Title: "Kept", Author: "A"}); err != nil {
		t.Fatal(err)
	}
	s1.Close()

	s2, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	b, err := s2.Get(t.Context(), 1)
	if err != nil || b.Title != "Kept" {
		t.Fatalf("after reopen: %+v, %v", b, err)
	}
}

func TestValidISBN(t *testing.T) {
	for s, want := range map[string]bool{
		"0441013597":        true,
		"044101359X":        true,
		"978-0-441-01359-3": true,
		"9780441013593":     true,
		"12345":             false,
		"X441013597":        false,
		"97804410135AB":     false,
	} {
		if got := validISBN(s); got != want {
			t.Errorf("validISBN(%q) = %v, want %v", s, got, want)
		}
	}
}
