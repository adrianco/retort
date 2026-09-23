package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
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

func do(t *testing.T, ts *httptest.Server, method, path string, body any) (*http.Response, []byte) {
	t.Helper()
	var r *bytes.Reader
	switch b := body.(type) {
	case nil:
		r = bytes.NewReader(nil)
	case string:
		r = bytes.NewReader([]byte(b))
	default:
		data, err := json.Marshal(b)
		if err != nil {
			t.Fatal(err)
		}
		r = bytes.NewReader(data)
	}
	req, err := http.NewRequest(method, ts.URL+path, r)
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var buf bytes.Buffer
	buf.ReadFrom(resp.Body)
	return resp, buf.Bytes()
}

func expectStatus(t *testing.T, resp *http.Response, body []byte, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("status = %d, want %d; body: %s", resp.StatusCode, want, body)
	}
}

func createBook(t *testing.T, ts *httptest.Server, in map[string]any) Book {
	t.Helper()
	resp, body := do(t, ts, http.MethodPost, "/books", in)
	expectStatus(t, resp, body, http.StatusCreated)
	var b Book
	if err := json.Unmarshal(body, &b); err != nil {
		t.Fatal(err)
	}
	return b
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, ts, http.MethodGet, "/health", nil)
	expectStatus(t, resp, body, http.StatusOK)
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

	b := createBook(t, ts, map[string]any{
		"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593",
	})
	if b.ID == 0 || b.Title != "Dune" || b.Author != "Frank Herbert" || b.Year != 1965 || b.ISBN != "978-0441013593" {
		t.Fatalf("unexpected created book: %+v", b)
	}
	path := "/books/" + itoa(b.ID)

	resp, body := do(t, ts, http.MethodGet, path, nil)
	expectStatus(t, resp, body, http.StatusOK)
	var got Book
	json.Unmarshal(body, &got)
	if got != b {
		t.Fatalf("GET = %+v, want %+v", got, b)
	}

	resp, body = do(t, ts, http.MethodPut, path, map[string]any{
		"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969,
	})
	expectStatus(t, resp, body, http.StatusOK)

	resp, body = do(t, ts, http.MethodGet, path, nil)
	expectStatus(t, resp, body, http.StatusOK)
	got = Book{}
	json.Unmarshal(body, &got)
	if got.Title != "Dune Messiah" || got.Year != 1969 || got.ISBN != "" {
		t.Fatalf("after update = %+v", got)
	}

	resp, body = do(t, ts, http.MethodDelete, path, nil)
	expectStatus(t, resp, body, http.StatusNoContent)

	resp, body = do(t, ts, http.MethodGet, path, nil)
	expectStatus(t, resp, body, http.StatusNotFound)

	resp, body = do(t, ts, http.MethodDelete, path, nil)
	expectStatus(t, resp, body, http.StatusNotFound)
}

func TestListWithAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	resp, body := do(t, ts, http.MethodGet, "/books", nil)
	expectStatus(t, resp, body, http.StatusOK)
	if string(bytes.TrimSpace(body)) != "[]" {
		t.Fatalf("empty list = %s, want []", body)
	}

	createBook(t, ts, map[string]any{"title": "Emma", "author": "Jane Austen"})
	createBook(t, ts, map[string]any{"title": "Persuasion", "author": "Jane Austen"})
	createBook(t, ts, map[string]any{"title": "Ulysses", "author": "James Joyce"})

	var books []Book
	resp, body = do(t, ts, http.MethodGet, "/books", nil)
	expectStatus(t, resp, body, http.StatusOK)
	json.Unmarshal(body, &books)
	if len(books) != 3 {
		t.Fatalf("got %d books, want 3", len(books))
	}

	resp, body = do(t, ts, http.MethodGet, "/books?author=jane%20austen", nil)
	expectStatus(t, resp, body, http.StatusOK)
	books = nil
	json.Unmarshal(body, &books)
	if len(books) != 2 {
		t.Fatalf("filtered: got %d books, want 2: %s", len(books), body)
	}
	for _, b := range books {
		if b.Author != "Jane Austen" {
			t.Errorf("unexpected author %q", b.Author)
		}
	}
}

func TestValidation(t *testing.T) {
	ts := newTestServer(t)
	existing := createBook(t, ts, map[string]any{"title": "Emma", "author": "Jane Austen"})

	cases := []struct {
		name   string
		method string
		path   string
		body   any
		status int
		field  string
	}{
		{"missing title", "POST", "/books", map[string]any{"author": "A"}, 422, "title"},
		{"missing author", "POST", "/books", map[string]any{"title": "T"}, 422, "author"},
		{"blank title", "POST", "/books", map[string]any{"title": "   ", "author": "A"}, 422, "title"},
		{"bad isbn", "POST", "/books", map[string]any{"title": "T", "author": "A", "isbn": "abc"}, 422, "isbn"},
		{"negative year", "POST", "/books", map[string]any{"title": "T", "author": "A", "year": -5}, 422, "year"},
		{"malformed json", "POST", "/books", `{"title":`, 400, ""},
		{"unknown field", "POST", "/books", `{"title":"T","author":"A","pages":3}`, 400, ""},
		{"wrong type", "POST", "/books", `{"title":"T","author":"A","year":"1999"}`, 400, ""},
		{"update missing author", "PUT", "/books/" + itoa(existing.ID), map[string]any{"title": "T"}, 422, "author"},
		{"update not found", "PUT", "/books/9999", map[string]any{"title": "T", "author": "A"}, 404, ""},
		{"invalid id", "GET", "/books/abc", nil, 400, ""},
		{"zero id", "DELETE", "/books/0", nil, 400, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, body := do(t, ts, tc.method, tc.path, tc.body)
			expectStatus(t, resp, body, tc.status)
			var e errorResponse
			if err := json.Unmarshal(body, &e); err != nil || e.Error == "" {
				t.Fatalf("expected JSON error body, got %s", body)
			}
			if tc.field != "" && e.Fields[tc.field] == "" {
				t.Errorf("expected field error for %q, got %+v", tc.field, e.Fields)
			}
		})
	}

	// Failed update must not modify the stored record.
	resp, body := do(t, ts, http.MethodGet, "/books/"+itoa(existing.ID), nil)
	expectStatus(t, resp, body, http.StatusOK)
	var got Book
	json.Unmarshal(body, &got)
	if got != existing {
		t.Errorf("book changed after rejected update: %+v", got)
	}
}

func TestPersistenceAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	s1, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	b := Book{Title: "Beloved", Author: "Toni Morrison", Year: 1987}
	if err := s1.Create(&b); err != nil {
		t.Fatal(err)
	}
	s1.Close()

	s2, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	got, err := s2.Get(b.ID)
	if err != nil || got != b {
		t.Fatalf("after reopen: %+v, %v", got, err)
	}
}

func TestValidISBN(t *testing.T) {
	for s, want := range map[string]bool{
		"0306406152":        true,
		"0-306-40615-X":     true,
		"978-0-306-40615-7": true,
		"12345":             false,
		"978030640615X":     false,
		"abcdefghij":        false,
	} {
		if got := validISBN(s); got != want {
			t.Errorf("validISBN(%q) = %v, want %v", s, got, want)
		}
	}
}

func itoa(n int64) string { return strconv.FormatInt(n, 10) }
