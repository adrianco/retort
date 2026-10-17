package main

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

// newTestServer starts the API backed by a fresh SQLite file in a temporary directory.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
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
	resp, err := http.DefaultClient.Do(req)
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
		t.Fatalf("decode book %s: %v", data, err)
	}
	return b
}

func TestBookLifecycle(t *testing.T) {
	ts := newTestServer(t)

	// Create
	resp, body := do(t, ts, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	expectStatus(t, resp, body, http.StatusCreated)
	created := decodeBook(t, body)
	if created.ID == 0 || created.Title != "Dune" || created.Year != 1965 {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := resp.Header.Get("Location"); loc != "/books/"+strconv.FormatInt(created.ID, 10) {
		t.Errorf("Location = %q", loc)
	}

	// Get
	resp, body = do(t, ts, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")
	expectStatus(t, resp, body, http.StatusOK)
	if got := decodeBook(t, body); got != created {
		t.Errorf("GET returned %+v, want %+v", got, created)
	}

	// Update (full replacement)
	resp, body = do(t, ts, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10),
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	expectStatus(t, resp, body, http.StatusOK)
	updated := decodeBook(t, body)
	if updated.Title != "Dune Messiah" || updated.Year != 1969 || updated.ISBN != "" {
		t.Errorf("unexpected updated book: %+v", updated)
	}

	// Delete
	resp, body = do(t, ts, http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), "")
	expectStatus(t, resp, body, http.StatusNoContent)

	resp, body = do(t, ts, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), "")
	expectStatus(t, resp, body, http.StatusNotFound)
}

func TestListFiltersByAuthor(t *testing.T) {
	ts := newTestServer(t)
	for _, b := range []string{
		`{"title":"Dune","author":"Frank Herbert","year":1965}`,
		`{"title":"Emma","author":"Jane Austen","year":1815}`,
		`{"title":"Children of Dune","author":"frank herbert","year":1976}`,
	} {
		resp, body := do(t, ts, http.MethodPost, "/books", b)
		expectStatus(t, resp, body, http.StatusCreated)
	}

	resp, body := do(t, ts, http.MethodGet, "/books", "")
	expectStatus(t, resp, body, http.StatusOK)
	var all []Book
	if err := json.Unmarshal(body, &all); err != nil {
		t.Fatal(err)
	}
	if len(all) != 3 {
		t.Errorf("unfiltered list has %d books, want 3", len(all))
	}

	resp, body = do(t, ts, http.MethodGet, "/books?author=Frank+Herbert", "")
	expectStatus(t, resp, body, http.StatusOK)
	var filtered []Book
	if err := json.Unmarshal(body, &filtered); err != nil {
		t.Fatal(err)
	}
	if len(filtered) != 2 {
		t.Fatalf("author filter returned %d books, want 2: %+v", len(filtered), filtered)
	}
	for _, b := range filtered {
		if !strings.EqualFold(b.Author, "Frank Herbert") {
			t.Errorf("unexpected book in filtered result: %+v", b)
		}
	}
}

func TestListEmptyReturnsJSONArray(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, ts, http.MethodGet, "/books", "")
	expectStatus(t, resp, body, http.StatusOK)
	if s := strings.TrimSpace(string(body)); s != "[]" {
		t.Errorf("empty list body = %q, want []", s)
	}
}

func TestCreateValidation(t *testing.T) {
	ts := newTestServer(t)
	cases := []struct {
		name   string
		body   string
		fields []string
	}{
		{"missing title and author", `{"year":2000}`, []string{"title", "author"}},
		{"blank title", `{"title":"  ","author":"A","year":2000}`, []string{"title"}},
		{"bad isbn", `{"title":"T","author":"A","year":2000,"isbn":"123"}`, []string{"isbn"}},
		{"future year", `{"title":"T","author":"A","year":9999}`, []string{"year"}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			resp, body := do(t, ts, http.MethodPost, "/books", c.body)
			expectStatus(t, resp, body, http.StatusBadRequest)
			var payload struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			if err := json.Unmarshal(body, &payload); err != nil {
				t.Fatal(err)
			}
			if payload.Error != "validation failed" {
				t.Errorf("error = %q", payload.Error)
			}
			for _, f := range c.fields {
				if payload.Fields[f] == "" {
					t.Errorf("expected problem reported for %q, got %v", f, payload.Fields)
				}
			}
		})
	}
}

func TestMalformedBodies(t *testing.T) {
	ts := newTestServer(t)
	for name, body := range map[string]string{
		"not json":         `{"title":`,
		"unknown field":    `{"title":"T","author":"A","pages":10}`,
		"trailing content": `{"title":"T","author":"A"} {"title":"U"}`,
	} {
		t.Run(name, func(t *testing.T) {
			resp, data := do(t, ts, http.MethodPost, "/books", body)
			expectStatus(t, resp, data, http.StatusBadRequest)
		})
	}
}

func TestDuplicateISBNConflicts(t *testing.T) {
	ts := newTestServer(t)
	first := `{"title":"A","author":"X","year":2000,"isbn":"0-306-40615-2"}`
	resp, body := do(t, ts, http.MethodPost, "/books", first)
	expectStatus(t, resp, body, http.StatusCreated)

	resp, body = do(t, ts, http.MethodPost, "/books",
		`{"title":"B","author":"Y","year":2001,"isbn":"0306406152"}`)
	expectStatus(t, resp, body, http.StatusConflict)

	// Books without an ISBN do not conflict with each other.
	for i := 0; i < 2; i++ {
		resp, body = do(t, ts, http.MethodPost, "/books", `{"title":"C","author":"Z","year":2002}`)
		expectStatus(t, resp, body, http.StatusCreated)
	}
}

func TestNotFoundAndBadIDs(t *testing.T) {
	ts := newTestServer(t)

	resp, body := do(t, ts, http.MethodGet, "/books/999", "")
	expectStatus(t, resp, body, http.StatusNotFound)

	resp, body = do(t, ts, http.MethodPut, "/books/999", `{"title":"T","author":"A","year":2000}`)
	expectStatus(t, resp, body, http.StatusNotFound)

	resp, body = do(t, ts, http.MethodDelete, "/books/999", "")
	expectStatus(t, resp, body, http.StatusNotFound)

	for _, id := range []string{"abc", "0", "-1"} {
		resp, body = do(t, ts, http.MethodGet, "/books/"+id, "")
		expectStatus(t, resp, body, http.StatusBadRequest)
	}
}

func TestUpdateValidatesInput(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, ts, http.MethodPost, "/books", `{"title":"T","author":"A","year":2000}`)
	expectStatus(t, resp, body, http.StatusCreated)
	id := decodeBook(t, body).ID

	resp, body = do(t, ts, http.MethodPut, "/books/"+strconv.FormatInt(id, 10), `{"title":"","author":"A","year":2000}`)
	expectStatus(t, resp, body, http.StatusBadRequest)

	// The original record must be unchanged after a rejected update.
	resp, body = do(t, ts, http.MethodGet, "/books/"+strconv.FormatInt(id, 10), "")
	expectStatus(t, resp, body, http.StatusOK)
	if got := decodeBook(t, body).Title; got != "T" {
		t.Errorf("title changed to %q after rejected update", got)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, ts, http.MethodPatch, "/books/1", "")
	expectStatus(t, resp, body, http.StatusMethodNotAllowed)
}

func TestHealth(t *testing.T) {
	ts := newTestServer(t)
	resp, body := do(t, ts, http.MethodGet, "/health", "")
	expectStatus(t, resp, body, http.StatusOK)
	var payload map[string]string
	if err := json.Unmarshal(body, &payload); err != nil {
		t.Fatal(err)
	}
	if payload["status"] != "ok" {
		t.Errorf("health payload = %v", payload)
	}
}

func TestOversizedBodyRejected(t *testing.T) {
	ts := newTestServer(t)
	big := `{"title":"` + strings.Repeat("a", maxBodyBytes) + `","author":"A","year":2000}`
	resp, body := do(t, ts, http.MethodPost, "/books", big)
	expectStatus(t, resp, body, http.StatusRequestEntityTooLarge)
}

func TestResponsesAreJSON(t *testing.T) {
	ts := newTestServer(t)
	resp, _ := do(t, ts, http.MethodGet, "/books", "")
	if ct := resp.Header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}
}
