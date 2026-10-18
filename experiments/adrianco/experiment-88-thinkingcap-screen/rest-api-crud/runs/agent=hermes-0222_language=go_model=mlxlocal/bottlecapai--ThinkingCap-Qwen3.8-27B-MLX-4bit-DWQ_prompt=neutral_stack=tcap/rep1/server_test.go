package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

// newTestServer starts a server backed by a fresh throwaway database.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "books.db")
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	if err := initDB(db); err != nil {
		t.Fatalf("init db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	srv := httptest.NewServer(NewHandler(db))
	t.Cleanup(srv.Close)
	return srv
}

// doJSON performs a request with an optional JSON body and returns the
// response, the raw response body, and the body parsed as a Book (zero
// value when the body is not a single book object).
func doJSON(t *testing.T, method, url string, body any) (*http.Response, []byte, Book) {
	t.Helper()
	var reader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		reader = strings.NewReader(string(data))
	}
	req, err := http.NewRequest(method, url, reader)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	var out Book
	if len(raw) > 0 {
		_ = json.Unmarshal(raw, &out) // may be an error object; ignore
	}
	return resp, raw, out
}

func checkStatus(t *testing.T, resp *http.Response, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("status = %d, want %d", resp.StatusCode, want)
	}
}

func TestRootInfo(t *testing.T) {
	srv := newTestServer(t)
	resp, raw, _ := doJSON(t, http.MethodGet, srv.URL+"/", nil)
	checkStatus(t, resp, http.StatusOK)
	if !strings.Contains(string(raw), "book-api") {
		t.Errorf("root body = %s", raw)
	}
}

func TestHealthCheck(t *testing.T) {
	srv := newTestServer(t)
	resp, raw, _ := doJSON(t, http.MethodGet, srv.URL+"/health", nil)
	checkStatus(t, resp, http.StatusOK)
	if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	if !strings.Contains(string(raw), "ok") {
		t.Errorf("health body = %s", raw)
	}
}

func TestCreateBook(t *testing.T) {
	srv := newTestServer(t)

	resp, _, book := doJSON(t, http.MethodPost, srv.URL+"/books", map[string]any{
		"title": "The Go Programming Language",
		"author": "Donovan & Kernighan",
		"year":   2015,
		"isbn":   "978-0134190440",
	})
	checkStatus(t, resp, http.StatusCreated)
	if book.ID == 0 {
		t.Error("expected a non-zero id on created book")
	}
	if book.Title != "The Go Programming Language" || book.Author != "Donovan & Kernighan" {
		t.Errorf("book = %+v, fields not echoed", book)
	}
	if book.Year == nil || *book.Year != 2015 {
		t.Errorf("year = %v, want 2015", book.Year)
	}
	if book.ISBN != "978-0134190440" {
		t.Errorf("isbn = %q", book.ISBN)
	}
	loc := resp.Header.Get("Location")
	if loc != fmt.Sprintf("/books/%d", book.ID) {
		t.Errorf("Location = %q", loc)
	}

	// Optional fields may be omitted.
	resp, _, book = doJSON(t, http.MethodPost, srv.URL+"/books", map[string]any{
		"title":  "Untitled",
		"author": "Someone",
	})
	checkStatus(t, resp, http.StatusCreated)
	if book.Year != nil || book.ISBN != "" {
		t.Errorf("expected omitted year/isbn, got %+v", book)
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv := newTestServer(t)

	cases := []struct {
		name string
		body string
	}{
		{"missing title", `{"author": "A"}`},
		{"empty title", `{"title": "  ", "author": "A"}`},
		{"missing author", `{"title": "T"}`},
		{"empty author", `{"title": "T", "author": ""}`},
		{"bad year", `{"title": "T", "author": "A", "year": 0}`},
		{"year too large", `{"title": "T", "author": "A", "year": 10000}`},
		{"malformed json", `{"title": "T",`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, err := http.Post(srv.URL+"/books", "application/json", strings.NewReader(tc.body))
			if err != nil {
				t.Fatalf("post: %v", err)
			}
			defer resp.Body.Close()
			checkStatus(t, resp, http.StatusBadRequest)
			data, _ := io.ReadAll(resp.Body)
			if !strings.Contains(string(data), "error") {
				t.Errorf("expected error JSON body, got %s", data)
			}
		})
	}
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	doJSON(t, http.MethodPost, srv.URL+"/books", map[string]any{"title": "A", "author": "Alice"})
	doJSON(t, http.MethodPost, srv.URL+"/books", map[string]any{"title": "B", "author": "Bob"})
	doJSON(t, http.MethodPost, srv.URL+"/books", map[string]any{"title": "C", "author": "Alice"})

	// All books.
	resp, raw, _ := doJSON(t, http.MethodGet, srv.URL+"/books", nil)
	checkStatus(t, resp, http.StatusOK)
	var all []Book
	if err := json.Unmarshal(raw, &all); err != nil {
		t.Fatalf("unmarshal list: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	// Filtered by author (case-insensitive).
	resp, raw, _ = doJSON(t, http.MethodGet, srv.URL+"/books?author=alice", nil)
	checkStatus(t, resp, http.StatusOK)
	var filtered []Book
	if err := json.Unmarshal(raw, &filtered); err != nil {
		t.Fatalf("unmarshal filtered: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("len(filtered) = %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if !strings.EqualFold(b.Author, "alice") {
			t.Errorf("filtered list contains author %q", b.Author)
		}
	}

	// Unknown author returns an empty list, not an error.
	resp, raw, _ = doJSON(t, http.MethodGet, srv.URL+"/books?author=nobody", nil)
	checkStatus(t, resp, http.StatusOK)
	var empty []Book
	if err := json.Unmarshal(raw, &empty); err != nil {
		t.Fatalf("unmarshal empty: %v", err)
	}
	if len(empty) != 0 {
		t.Errorf("len(empty) = %d, want 0", len(empty))
	}
}

func TestGetBook(t *testing.T) {
	srv := newTestServer(t)
	_, _, created := doJSON(t, http.MethodPost, srv.URL+"/books", map[string]any{"title": "T", "author": "A"})

	resp, _, got := doJSON(t, http.MethodGet, srv.URL+"/books/"+fmt.Sprint(created.ID), nil)
	checkStatus(t, resp, http.StatusOK)
	if got.Title != "T" || got.Author != "A" {
		t.Errorf("got = %+v", got)
	}

	resp, _, _ = doJSON(t, http.MethodGet, srv.URL+"/books/99999", nil)
	checkStatus(t, resp, http.StatusNotFound)

	resp, _, _ = doJSON(t, http.MethodGet, srv.URL+"/books/notanumber", nil)
	checkStatus(t, resp, http.StatusBadRequest)
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	_, _, created := doJSON(t, http.MethodPost, srv.URL+"/books", map[string]any{
		"title": "Old Title", "author": "Old Author", "year": 2000,
	})

	resp, _, updated := doJSON(t, http.MethodPut, srv.URL+"/books/"+fmt.Sprint(created.ID), map[string]any{
		"title": "New Title", "author": "New Author",
	})
	checkStatus(t, resp, http.StatusOK)
	if updated.Title != "New Title" || updated.Author != "New Author" {
		t.Errorf("updated = %+v", updated)
	}
	if updated.Year != nil {
		t.Errorf("year should have been cleared, got %v", *updated.Year)
	}
	if updated.ID != created.ID {
		t.Errorf("id changed: %d -> %d", created.ID, updated.ID)
	}

	// Updating a missing book -> 404.
	resp, _, _ = doJSON(t, http.MethodPut, srv.URL+"/books/99999", map[string]any{"title": "X", "author": "Y"})
	checkStatus(t, resp, http.StatusNotFound)

	// Validation still applies on update.
	resp, _, _ = doJSON(t, http.MethodPut, srv.URL+"/books/"+fmt.Sprint(created.ID), map[string]any{"author": "Y"})
	checkStatus(t, resp, http.StatusBadRequest)

	// Verify the update persisted.
	resp, _, got := doJSON(t, http.MethodGet, srv.URL+"/books/"+fmt.Sprint(created.ID), nil)
	checkStatus(t, resp, http.StatusOK)
	if got.Title != "New Title" {
		t.Errorf("persisted title = %q", got.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	_, _, created := doJSON(t, http.MethodPost, srv.URL+"/books", map[string]any{"title": "T", "author": "A"})

	resp, _, _ := doJSON(t, http.MethodDelete, srv.URL+"/books/"+fmt.Sprint(created.ID), nil)
	checkStatus(t, resp, http.StatusNoContent)

	// Gone now.
	resp, _, _ = doJSON(t, http.MethodGet, srv.URL+"/books/"+fmt.Sprint(created.ID), nil)
	checkStatus(t, resp, http.StatusNotFound)

	// Deleting again -> 404.
	resp, _, _ = doJSON(t, http.MethodDelete, srv.URL+"/books/"+fmt.Sprint(created.ID), nil)
	checkStatus(t, resp, http.StatusNotFound)

	// Invalid id -> 400.
	resp, _, _ = doJSON(t, http.MethodDelete, srv.URL+"/books/xyz", nil)
	checkStatus(t, resp, http.StatusBadRequest)
}

func TestValidationUnit(t *testing.T) {
	year := 2020
	valid := bookInput{Title: "T", Author: "A", Year: &year}
	if msg := validateBookInput(&valid); msg != "" {
		t.Errorf("valid input rejected: %s", msg)
	}
	noYear := bookInput{Title: "T", Author: "A"}
	if msg := validateBookInput(&noYear); msg != "" {
		t.Errorf("input without year rejected: %s", msg)
	}
	badYear := 0
	bad := bookInput{Title: "T", Author: "A", Year: &badYear}
	if msg := validateBookInput(&bad); msg == "" {
		t.Error("year 0 should be rejected")
	}
}
