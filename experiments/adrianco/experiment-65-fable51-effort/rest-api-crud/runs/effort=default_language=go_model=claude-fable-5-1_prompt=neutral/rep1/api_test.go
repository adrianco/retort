package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"reflect"
	"testing"
)

// newTestServer spins up an httptest server backed by a fresh on-disk SQLite
// database in a temp directory (removed automatically when the test ends).
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	ts := httptest.NewServer(NewServer(store, log.New(io.Discard, "", 0)).Handler())
	t.Cleanup(ts.Close)
	return ts
}

func doJSON(t *testing.T, method, url string, body any) (*http.Response, []byte) {
	t.Helper()
	var buf io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		buf = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, url, buf)
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
	data, _ := io.ReadAll(resp.Body)
	return resp, data
}

func decodeBook(t *testing.T, data []byte) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(data, &b); err != nil {
		t.Fatalf("decode book from %q: %v", data, err)
	}
	return b
}

func createBook(t *testing.T, base string, payload map[string]any) Book {
	t.Helper()
	resp, data := doJSON(t, http.MethodPost, base+"/books", payload)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create: want 201, got %d: %s", resp.StatusCode, data)
	}
	return decodeBook(t, data)
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	resp, data := doJSON(t, http.MethodGet, ts.URL+"/health", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200, got %d: %s", resp.StatusCode, data)
	}
	if ct := resp.Header.Get("Content-Type"); ct != "application/json; charset=utf-8" {
		t.Errorf("unexpected content type %q", ct)
	}
	var body map[string]string
	if err := json.Unmarshal(data, &body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body["status"] != "ok" || body["database"] != "ok" {
		t.Errorf("unexpected health body: %v", body)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	ts := newTestServer(t)

	resp, data := doJSON(t, http.MethodPost, ts.URL+"/books", map[string]any{
		"title": "  The Go Programming Language ", "author": "Alan Donovan", "year": 2015, "isbn": "978-0-13-419044-0",
	})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("want 201, got %d: %s", resp.StatusCode, data)
	}
	created := decodeBook(t, data)
	if created.ID == 0 {
		t.Fatal("expected non-zero id")
	}
	if got := resp.Header.Get("Location"); got != fmt.Sprintf("/books/%d", created.ID) {
		t.Errorf("Location = %q", got)
	}
	if created.Title != "The Go Programming Language" {
		t.Errorf("title not trimmed: %q", created.Title)
	}
	if created.ISBN != "9780134190440" {
		t.Errorf("isbn not normalized: %q", created.ISBN)
	}
	if created.Year == nil || *created.Year != 2015 {
		t.Errorf("year = %v", created.Year)
	}
	if created.CreatedAt.IsZero() || created.UpdatedAt.IsZero() {
		t.Error("timestamps should be set")
	}

	resp, data = doJSON(t, http.MethodGet, fmt.Sprintf("%s/books/%d", ts.URL, created.ID), nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("get: want 200, got %d: %s", resp.StatusCode, data)
	}
	got := decodeBook(t, data)
	if !reflect.DeepEqual(got, created) {
		t.Errorf("get mismatch:\n got %+v\nwant %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	ts := newTestServer(t)

	cases := []struct {
		name       string
		body       any
		wantStatus int
		wantFields []string
	}{
		{"missing both", map[string]any{"year": 2000}, http.StatusUnprocessableEntity, []string{"title", "author"}},
		{"blank title", map[string]any{"title": "   ", "author": "X"}, http.StatusUnprocessableEntity, []string{"title"}},
		{"missing author", map[string]any{"title": "T"}, http.StatusUnprocessableEntity, []string{"author"}},
		{"bad year", map[string]any{"title": "T", "author": "A", "year": 99999}, http.StatusUnprocessableEntity, []string{"year"}},
		{"bad isbn", map[string]any{"title": "T", "author": "A", "isbn": "123"}, http.StatusUnprocessableEntity, []string{"isbn"}},
		{"unknown field", map[string]any{"title": "T", "author": "A", "publisher": "P"}, http.StatusBadRequest, nil},
		{"wrong type", map[string]any{"title": "T", "author": "A", "year": "2001"}, http.StatusBadRequest, nil},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			resp, data := doJSON(t, http.MethodPost, ts.URL+"/books", tc.body)
			if resp.StatusCode != tc.wantStatus {
				t.Fatalf("want %d, got %d: %s", tc.wantStatus, resp.StatusCode, data)
			}
			var er errorResponse
			if err := json.Unmarshal(data, &er); err != nil {
				t.Fatalf("decode error body: %v", err)
			}
			if er.Error == "" {
				t.Error("expected error message")
			}
			for _, f := range tc.wantFields {
				if _, ok := er.Details[f]; !ok {
					t.Errorf("expected validation detail for %q, got %v", f, er.Details)
				}
			}
		})
	}

	t.Run("malformed json", func(t *testing.T) {
		req, _ := http.NewRequest(http.MethodPost, ts.URL+"/books", bytes.NewBufferString("{not json"))
		req.Header.Set("Content-Type", "application/json")
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatal(err)
		}
		resp.Body.Close()
		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("want 400, got %d", resp.StatusCode)
		}
	})

	t.Run("wrong content type", func(t *testing.T) {
		req, _ := http.NewRequest(http.MethodPost, ts.URL+"/books", bytes.NewBufferString(`{"title":"T","author":"A"}`))
		req.Header.Set("Content-Type", "text/plain")
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			t.Fatal(err)
		}
		resp.Body.Close()
		if resp.StatusCode != http.StatusUnsupportedMediaType {
			t.Errorf("want 415, got %d", resp.StatusCode)
		}
	})

	// Nothing should have been persisted by any of the rejected requests.
	resp, data := doJSON(t, http.MethodGet, ts.URL+"/books", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("list: %d", resp.StatusCode)
	}
	var books []Book
	_ = json.Unmarshal(data, &books)
	if len(books) != 0 {
		t.Errorf("expected empty collection, got %d books", len(books))
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	// Empty collection serializes as [] not null.
	resp, data := doJSON(t, http.MethodGet, ts.URL+"/books", nil)
	if resp.StatusCode != http.StatusOK || bytes.TrimSpace(data) == nil || string(bytes.TrimSpace(data)) != "[]" {
		t.Fatalf("empty list: %d %q", resp.StatusCode, data)
	}

	createBook(t, ts.URL, map[string]any{"title": "Dune", "author": "Frank Herbert", "year": 1965})
	createBook(t, ts.URL, map[string]any{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969})
	createBook(t, ts.URL, map[string]any{"title": "Neuromancer", "author": "William Gibson", "year": 1984})

	resp, data = doJSON(t, http.MethodGet, ts.URL+"/books", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("list: %d", resp.StatusCode)
	}
	var all []Book
	if err := json.Unmarshal(data, &all); err != nil {
		t.Fatal(err)
	}
	if len(all) != 3 {
		t.Fatalf("want 3 books, got %d", len(all))
	}
	if all[0].Title != "Dune" || all[2].Title != "Neuromancer" {
		t.Errorf("unexpected order: %v", all)
	}

	// Filter is exact-match on author and case-insensitive.
	resp, data = doJSON(t, http.MethodGet, ts.URL+"/books?author=frank+herbert", nil)
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("filtered list: %d", resp.StatusCode)
	}
	var filtered []Book
	if err := json.Unmarshal(data, &filtered); err != nil {
		t.Fatal(err)
	}
	if len(filtered) != 2 {
		t.Fatalf("want 2 Herbert books, got %d: %v", len(filtered), filtered)
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" {
			t.Errorf("unexpected author %q in filtered result", b.Author)
		}
	}

	resp, data = doJSON(t, http.MethodGet, ts.URL+"/books?author=Nobody", nil)
	if resp.StatusCode != http.StatusOK || string(bytes.TrimSpace(data)) != "[]" {
		t.Errorf("no-match filter: %d %q", resp.StatusCode, data)
	}
}

func TestUpdateBook(t *testing.T) {
	ts := newTestServer(t)
	b := createBook(t, ts.URL, map[string]any{"title": "Draft", "author": "Anon", "year": 2000, "isbn": "0306406152"})

	resp, data := doJSON(t, http.MethodPut, fmt.Sprintf("%s/books/%d", ts.URL, b.ID), map[string]any{
		"title": "Final", "author": "Real Name",
	})
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200, got %d: %s", resp.StatusCode, data)
	}
	updated := decodeBook(t, data)
	if updated.ID != b.ID || updated.Title != "Final" || updated.Author != "Real Name" {
		t.Errorf("unexpected updated book: %+v", updated)
	}
	// PUT is a full replacement: omitted optional fields are cleared.
	if updated.Year != nil || updated.ISBN != "" {
		t.Errorf("expected year and isbn cleared, got year=%v isbn=%q", updated.Year, updated.ISBN)
	}
	if !updated.CreatedAt.Equal(b.CreatedAt) {
		t.Error("created_at should not change on update")
	}
	if updated.UpdatedAt.Before(b.UpdatedAt) {
		t.Error("updated_at should not go backwards")
	}

	// Validation applies to updates too.
	resp, data = doJSON(t, http.MethodPut, fmt.Sprintf("%s/books/%d", ts.URL, b.ID), map[string]any{"title": "", "author": "A"})
	if resp.StatusCode != http.StatusUnprocessableEntity {
		t.Errorf("want 422, got %d: %s", resp.StatusCode, data)
	}

	// Unknown ID.
	resp, data = doJSON(t, http.MethodPut, ts.URL+"/books/9999", map[string]any{"title": "T", "author": "A"})
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("want 404, got %d: %s", resp.StatusCode, data)
	}
}

func TestDeleteBook(t *testing.T) {
	ts := newTestServer(t)
	b := createBook(t, ts.URL, map[string]any{"title": "Ephemeral", "author": "Gone Soon"})
	url := fmt.Sprintf("%s/books/%d", ts.URL, b.ID)

	resp, data := doJSON(t, http.MethodDelete, url, nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("want 204, got %d: %s", resp.StatusCode, data)
	}
	if len(data) != 0 {
		t.Errorf("204 should have empty body, got %q", data)
	}

	resp, _ = doJSON(t, http.MethodGet, url, nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("get after delete: want 404, got %d", resp.StatusCode)
	}
	resp, _ = doJSON(t, http.MethodDelete, url, nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("second delete: want 404, got %d", resp.StatusCode)
	}
}

func TestNotFoundAndBadIDs(t *testing.T) {
	ts := newTestServer(t)
	for _, path := range []string{"/books/abc", "/books/0", "/books/-1"} {
		resp, _ := doJSON(t, http.MethodGet, ts.URL+path, nil)
		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("GET %s: want 400, got %d", path, resp.StatusCode)
		}
	}
	resp, _ := doJSON(t, http.MethodGet, ts.URL+"/books/123456", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("want 404, got %d", resp.StatusCode)
	}
	resp, _ = doJSON(t, http.MethodGet, ts.URL+"/nope", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("unknown route: want 404, got %d", resp.StatusCode)
	}
	resp, _ = doJSON(t, http.MethodPatch, ts.URL+"/books/1", nil)
	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("PATCH: want 405, got %d", resp.StatusCode)
	}
}

func TestDuplicateISBNConflict(t *testing.T) {
	ts := newTestServer(t)
	createBook(t, ts.URL, map[string]any{"title": "First", "author": "A", "isbn": "9780306406157"})

	resp, data := doJSON(t, http.MethodPost, ts.URL+"/books", map[string]any{"title": "Second", "author": "B", "isbn": "978-0-306-40615-7"})
	if resp.StatusCode != http.StatusConflict {
		t.Fatalf("want 409, got %d: %s", resp.StatusCode, data)
	}

	// Books without an ISBN never conflict with each other.
	createBook(t, ts.URL, map[string]any{"title": "No ISBN 1", "author": "C"})
	createBook(t, ts.URL, map[string]any{"title": "No ISBN 2", "author": "D"})
}

func TestPersistenceAcrossReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")

	store, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	b, err := store.Create(t.Context(), "Persisted", "Author", nil, "")
	if err != nil {
		t.Fatal(err)
	}
	store.Close()

	store, err = OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	got, err := store.Get(t.Context(), b.ID)
	if err != nil {
		t.Fatalf("book should survive reopen: %v", err)
	}
	if got.Title != "Persisted" {
		t.Errorf("title = %q", got.Title)
	}
}

func TestValidISBN(t *testing.T) {
	valid := []string{"0306406152", "0-306-40615-2", "9780306406157", "978-0-306-40615-7", "080442957X", "0-8044-2957-x"}
	invalid := []string{"0306406153", "9780306406158", "123", "abcdefghij", "030640615X", "9780306406157X"}
	for _, s := range valid {
		if !validISBN(normalizeISBN(s)) {
			t.Errorf("%q should be valid", s)
		}
	}
	for _, s := range invalid {
		if validISBN(normalizeISBN(s)) {
			t.Errorf("%q should be invalid", s)
		}
	}
}
