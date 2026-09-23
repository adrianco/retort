package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

// newTestServer starts an httptest server backed by a fresh in-memory store.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	ts := httptest.NewServer(NewServer(store).Routes())
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
		t.Fatalf("new request: %v", err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	t.Cleanup(func() { resp.Body.Close() })
	return resp
}

func decode[T any](t *testing.T, resp *http.Response) T {
	t.Helper()
	var v T
	if err := json.NewDecoder(resp.Body).Decode(&v); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	return v
}

func expectStatus(t *testing.T, resp *http.Response, want int) {
	t.Helper()
	if resp.StatusCode != want {
		var buf bytes.Buffer
		buf.ReadFrom(resp.Body)
		t.Fatalf("%s %s: status = %d, want %d; body: %s",
			resp.Request.Method, resp.Request.URL.Path, resp.StatusCode, want, buf.String())
	}
}

func createBook(t *testing.T, ts *httptest.Server, title, author string, year int, isbn string) Book {
	t.Helper()
	body := fmt.Sprintf(`{"title":%q,"author":%q,"year":%d,"isbn":%q}`, title, author, year, isbn)
	resp := do(t, ts, http.MethodPost, "/books", body)
	expectStatus(t, resp, http.StatusCreated)
	return decode[Book](t, resp)
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	resp := do(t, ts, http.MethodGet, "/health", "")
	expectStatus(t, resp, http.StatusOK)
	if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	got := decode[map[string]string](t, resp)
	if got["status"] != "ok" {
		t.Errorf("status = %q, want ok", got["status"])
	}
}

func TestBookCRUDLifecycle(t *testing.T) {
	ts := newTestServer(t)

	// Create
	resp := do(t, ts, http.MethodPost, "/books",
		`{"title":"  The Go Programming Language ","author":"Alan Donovan","year":2015,"isbn":"978-0134190440"}`)
	expectStatus(t, resp, http.StatusCreated)
	created := decode[Book](t, resp)
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "The Go Programming Language" {
		t.Errorf("title not trimmed: %q", created.Title)
	}
	if loc, want := resp.Header.Get("Location"), fmt.Sprintf("/books/%d", created.ID); loc != want {
		t.Errorf("Location = %q, want %q", loc, want)
	}

	// Get
	resp = do(t, ts, http.MethodGet, fmt.Sprintf("/books/%d", created.ID), "")
	expectStatus(t, resp, http.StatusOK)
	if got := decode[Book](t, resp); got != created {
		t.Errorf("get = %+v, want %+v", got, created)
	}

	// Update
	resp = do(t, ts, http.MethodPut, fmt.Sprintf("/books/%d", created.ID),
		`{"title":"The Go Programming Language (2nd ed.)","author":"Alan Donovan","year":2016,"isbn":"978-0134190440"}`)
	expectStatus(t, resp, http.StatusOK)
	updated := decode[Book](t, resp)
	want := Book{ID: created.ID, Title: "The Go Programming Language (2nd ed.)", Author: "Alan Donovan", Year: 2016, ISBN: "978-0134190440"}
	if updated != want {
		t.Errorf("update = %+v, want %+v", updated, want)
	}

	// Update is persisted
	resp = do(t, ts, http.MethodGet, fmt.Sprintf("/books/%d", created.ID), "")
	expectStatus(t, resp, http.StatusOK)
	if got := decode[Book](t, resp); got != want {
		t.Errorf("get after update = %+v, want %+v", got, want)
	}

	// Delete
	resp = do(t, ts, http.MethodDelete, fmt.Sprintf("/books/%d", created.ID), "")
	expectStatus(t, resp, http.StatusNoContent)

	// Gone
	resp = do(t, ts, http.MethodGet, fmt.Sprintf("/books/%d", created.ID), "")
	expectStatus(t, resp, http.StatusNotFound)
	resp = do(t, ts, http.MethodDelete, fmt.Sprintf("/books/%d", created.ID), "")
	expectStatus(t, resp, http.StatusNotFound)
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	// Empty collection returns [] rather than null.
	resp := do(t, ts, http.MethodGet, "/books", "")
	expectStatus(t, resp, http.StatusOK)
	if books := decode[[]Book](t, resp); books == nil || len(books) != 0 {
		t.Fatalf("empty list = %#v, want []", books)
	}

	createBook(t, ts, "Dune", "Frank Herbert", 1965, "")
	createBook(t, ts, "Children of Dune", "Frank Herbert", 1976, "")
	createBook(t, ts, "Neuromancer", "William Gibson", 1984, "")

	resp = do(t, ts, http.MethodGet, "/books", "")
	expectStatus(t, resp, http.StatusOK)
	if books := decode[[]Book](t, resp); len(books) != 3 {
		t.Fatalf("list all: got %d books, want 3", len(books))
	}

	resp = do(t, ts, http.MethodGet, "/books?author=frank+herbert", "")
	expectStatus(t, resp, http.StatusOK)
	books := decode[[]Book](t, resp)
	if len(books) != 2 {
		t.Fatalf("filter by author: got %d books, want 2: %+v", len(books), books)
	}
	for _, b := range books {
		if b.Author != "Frank Herbert" {
			t.Errorf("unexpected author %q in filtered results", b.Author)
		}
	}

	resp = do(t, ts, http.MethodGet, "/books?author=Nobody", "")
	expectStatus(t, resp, http.StatusOK)
	if books := decode[[]Book](t, resp); len(books) != 0 {
		t.Errorf("filter by unknown author: got %d books, want 0", len(books))
	}
}

func TestCreateBookValidation(t *testing.T) {
	ts := newTestServer(t)

	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string
	}{
		{"missing title", `{"author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"missing author", `{"title":"T"}`, http.StatusBadRequest, []string{"author"}},
		{"blank title and author", `{"title":"   ","author":""}`, http.StatusBadRequest, []string{"title", "author"}},
		{"negative year", `{"title":"T","author":"A","year":-5}`, http.StatusBadRequest, []string{"year"}},
		{"future year", `{"title":"T","author":"A","year":99999}`, http.StatusBadRequest, []string{"year"}},
		{"isbn too long", `{"title":"T","author":"A","isbn":"` + strings.Repeat("9", 40) + `"}`, http.StatusBadRequest, []string{"isbn"}},
		{"malformed json", `{"title":`, http.StatusBadRequest, nil},
		{"wrong type", `{"title":"T","author":"A","year":"nineteen"}`, http.StatusBadRequest, nil},
		{"empty body", ``, http.StatusBadRequest, nil},
		{"multiple objects", `{"title":"T","author":"A"}{"title":"T"}`, http.StatusBadRequest, nil},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			resp := do(t, ts, http.MethodPost, "/books", tc.body)
			expectStatus(t, resp, tc.wantStatus)
			got := decode[errorResponse](t, resp)
			if got.Error == "" {
				t.Error("expected non-empty error message")
			}
			for _, f := range tc.wantFields {
				if _, ok := got.Details[f]; !ok {
					t.Errorf("expected validation error for field %q, got %v", f, got.Details)
				}
			}
		})
	}

	// Nothing invalid should have been stored.
	resp := do(t, ts, http.MethodGet, "/books", "")
	expectStatus(t, resp, http.StatusOK)
	if books := decode[[]Book](t, resp); len(books) != 0 {
		t.Errorf("invalid creates stored %d books", len(books))
	}
}

func TestUpdateBookErrors(t *testing.T) {
	ts := newTestServer(t)
	b := createBook(t, ts, "Original", "Author", 2000, "")

	resp := do(t, ts, http.MethodPut, fmt.Sprintf("/books/%d", b.ID), `{"title":"","author":"Author"}`)
	expectStatus(t, resp, http.StatusBadRequest)

	resp = do(t, ts, http.MethodPut, "/books/9999", `{"title":"T","author":"A"}`)
	expectStatus(t, resp, http.StatusNotFound)

	// Failed updates must not modify the stored book.
	resp = do(t, ts, http.MethodGet, fmt.Sprintf("/books/%d", b.ID), "")
	expectStatus(t, resp, http.StatusOK)
	if got := decode[Book](t, resp); got != b {
		t.Errorf("book changed after failed update: %+v, want %+v", got, b)
	}
}

func TestInvalidAndMissingIDs(t *testing.T) {
	ts := newTestServer(t)
	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
		body := ""
		if method == http.MethodPut {
			body = `{"title":"T","author":"A"}`
		}
		for _, id := range []string{"abc", "0", "-1"} {
			resp := do(t, ts, method, "/books/"+id, body)
			expectStatus(t, resp, http.StatusBadRequest)
		}
		resp := do(t, ts, method, "/books/12345", body)
		expectStatus(t, resp, http.StatusNotFound)
	}
}

func TestPersistenceAcrossRestart(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")

	store, err := OpenStore(path)
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	created, err := store.Create(t.Context(), BookInput{Title: "Persisted", Author: "Writer", Year: 1999, ISBN: "123"})
	if err != nil {
		t.Fatalf("create: %v", err)
	}
	store.Close()

	store, err = OpenStore(path)
	if err != nil {
		t.Fatalf("reopen store: %v", err)
	}
	defer store.Close()
	got, err := store.Get(t.Context(), created.ID)
	if err != nil {
		t.Fatalf("get after reopen: %v", err)
	}
	if got != created {
		t.Errorf("after reopen = %+v, want %+v", got, created)
	}
}
