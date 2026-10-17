package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

// newTestServer starts the API backed by a fresh SQLite file in a temp dir.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })

	ts := httptest.NewServer(NewServer(store))
	t.Cleanup(ts.Close)
	return ts
}

func do(t *testing.T, ts *httptest.Server, method, path, body string) (*http.Response, []byte) {
	t.Helper()
	var reader io.Reader
	if body != "" {
		reader = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, ts.URL+path, reader)
	if err != nil {
		t.Fatalf("new request: %v", err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := ts.Client().Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return resp, data
}

func expectStatus(t *testing.T, resp *http.Response, body []byte, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("status = %d, want %d; body: %s", resp.StatusCode, want, body)
	}
}

func decodeBook(t *testing.T, data []byte) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(data, &b); err != nil {
		t.Fatalf("decode book %q: %v", data, err)
	}
	return b
}

func createBook(t *testing.T, ts *httptest.Server, body string) Book {
	t.Helper()
	resp, data := do(t, ts, http.MethodPost, "/books", body)
	expectStatus(t, resp, data, http.StatusCreated)
	return decodeBook(t, data)
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}`

func TestBookLifecycle(t *testing.T) {
	ts := newTestServer(t)

	// Create
	created := createBook(t, ts, dune)
	if created.ID == 0 {
		t.Fatal("created book has no id")
	}
	if created.Title != "Dune" || created.Author != "Frank Herbert" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if created.ISBN != "9780441172719" {
		t.Errorf("isbn = %q, want normalized 9780441172719", created.ISBN)
	}

	path := fmt.Sprintf("/books/%d", created.ID)

	// Get
	resp, data := do(t, ts, http.MethodGet, path, "")
	expectStatus(t, resp, data, http.StatusOK)
	if got := decodeBook(t, data); got != created {
		t.Fatalf("get = %+v, want %+v", got, created)
	}

	// Update
	resp, data = do(t, ts, http.MethodPut, path,
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":""}`)
	expectStatus(t, resp, data, http.StatusOK)
	updated := decodeBook(t, data)
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != 1969 || updated.ISBN != "" {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	// Delete
	resp, data = do(t, ts, http.MethodDelete, path, "")
	expectStatus(t, resp, data, http.StatusNoContent)

	// Gone
	resp, data = do(t, ts, http.MethodGet, path, "")
	expectStatus(t, resp, data, http.StatusNotFound)
}

func TestListAndAuthorFilter(t *testing.T) {
	ts := newTestServer(t)

	resp, data := do(t, ts, http.MethodGet, "/books", "")
	expectStatus(t, resp, data, http.StatusOK)
	if strings.TrimSpace(string(data)) != "[]" {
		t.Fatalf("empty list body = %s, want []", data)
	}

	createBook(t, ts, dune)
	createBook(t, ts, `{"title":"Children of Dune","author":"Frank Herbert"}`)
	createBook(t, ts, `{"title":"Neuromancer","author":"William Gibson"}`)

	resp, data = do(t, ts, http.MethodGet, "/books", "")
	expectStatus(t, resp, data, http.StatusOK)
	var all []Book
	if err := json.Unmarshal(data, &all); err != nil {
		t.Fatal(err)
	}
	if len(all) != 3 {
		t.Fatalf("list length = %d, want 3", len(all))
	}

	resp, data = do(t, ts, http.MethodGet, "/books?author=frank%20herbert", "")
	expectStatus(t, resp, data, http.StatusOK)
	var filtered []Book
	if err := json.Unmarshal(data, &filtered); err != nil {
		t.Fatal(err)
	}
	if len(filtered) != 2 {
		t.Fatalf("filtered length = %d, want 2 (body: %s)", len(filtered), data)
	}
	for _, b := range filtered {
		if !strings.EqualFold(b.Author, "Frank Herbert") {
			t.Errorf("filter leaked book by %q", b.Author)
		}
	}
}

func TestCreateValidation(t *testing.T) {
	ts := newTestServer(t)

	tests := []struct {
		name   string
		body   string
		fields []string
	}{
		{"missing title and author", `{"year":2000}`, []string{"title", "author"}},
		{"blank title", `{"title":"   ","author":"A"}`, []string{"title"}},
		{"blank author", `{"title":"T","author":""}`, []string{"author"}},
		{"bad year", `{"title":"T","author":"A","year":42}`, []string{"year"}},
		{"bad isbn", `{"title":"T","author":"A","isbn":"123"}`, []string{"isbn"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			resp, data := do(t, ts, http.MethodPost, "/books", tt.body)
			expectStatus(t, resp, data, http.StatusBadRequest)

			var out struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			if err := json.Unmarshal(data, &out); err != nil {
				t.Fatalf("decode error body: %v", err)
			}
			for _, f := range tt.fields {
				if _, ok := out.Fields[f]; !ok {
					t.Errorf("expected error for field %q, got fields %v", f, out.Fields)
				}
			}
		})
	}
}

func TestMalformedRequests(t *testing.T) {
	ts := newTestServer(t)

	cases := []struct {
		name, method, path, body string
		want                     int
	}{
		{"invalid json", http.MethodPost, "/books", `{"title":`, http.StatusBadRequest},
		{"unknown field", http.MethodPost, "/books", `{"title":"T","author":"A","pages":10}`, http.StatusBadRequest},
		{"trailing data", http.MethodPost, "/books", `{"title":"T","author":"A"} {}`, http.StatusBadRequest},
		{"wrong type", http.MethodPost, "/books", `{"title":"T","author":"A","year":"1999"}`, http.StatusBadRequest},
		{"non-numeric id", http.MethodGet, "/books/abc", "", http.StatusBadRequest},
		{"zero id", http.MethodGet, "/books/0", "", http.StatusBadRequest},
		{"update missing", http.MethodPut, "/books/999", dune, http.StatusNotFound},
		{"delete missing", http.MethodDelete, "/books/999", "", http.StatusNotFound},
		{"get missing", http.MethodGet, "/books/999", "", http.StatusNotFound},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			resp, data := do(t, ts, c.method, c.path, c.body)
			expectStatus(t, resp, data, c.want)
		})
	}
}

func TestDuplicateISBNConflicts(t *testing.T) {
	ts := newTestServer(t)

	createBook(t, ts, dune)
	resp, data := do(t, ts, http.MethodPost, "/books",
		`{"title":"Other","author":"Someone","isbn":"9780441172719"}`)
	expectStatus(t, resp, data, http.StatusConflict)

	// Books without an ISBN do not collide with each other.
	createBook(t, ts, `{"title":"A","author":"X"}`)
	createBook(t, ts, `{"title":"B","author":"X"}`)
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)

	resp, data := do(t, ts, http.MethodGet, "/health", "")
	expectStatus(t, resp, data, http.StatusOK)
	if !bytes.Contains(data, []byte(`"ok"`)) {
		t.Fatalf("health body = %s", data)
	}
}

func TestResponsesAreJSON(t *testing.T) {
	ts := newTestServer(t)

	resp, _ := do(t, ts, http.MethodGet, "/health", "")
	if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
}
