package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

// newTestAPI starts the full HTTP stack against a fresh on-disk SQLite
// database that is removed when the test ends.
func newTestAPI(t *testing.T) *httptest.Server {
	t.Helper()
	store, err := OpenStore(context.Background(), filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	ts := httptest.NewServer(NewServer(store, logger).Routes())
	t.Cleanup(func() {
		ts.Close()
		store.Close()
	})
	return ts
}

// do sends a request with an optional JSON body and returns the status code
// and raw response body.
func do(t *testing.T, ts *httptest.Server, method, path, body string) (*http.Response, []byte) {
	t.Helper()
	var reader io.Reader
	if body != "" {
		reader = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, ts.URL+path, reader)
	if err != nil {
		t.Fatalf("build request: %v", err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := ts.Client().Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read response: %v", err)
	}
	return resp, raw
}

func wantStatus(t *testing.T, resp *http.Response, raw []byte, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("%s %s: status = %d, want %d (body: %s)",
			resp.Request.Method, resp.Request.URL.Path, resp.StatusCode, want, raw)
	}
}

func wantJSON(t *testing.T, resp *http.Response) {
	t.Helper()
	if ct := resp.Header.Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
}

func decode[T any](t *testing.T, raw []byte) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(raw, &v); err != nil {
		t.Fatalf("decode %q: %v", raw, err)
	}
	return v
}

func createBook(t *testing.T, ts *httptest.Server, body string) Book {
	t.Helper()
	resp, raw := do(t, ts, http.MethodPost, "/books", body)
	wantStatus(t, resp, raw, http.StatusCreated)
	return decode[Book](t, raw)
}

func TestHealth(t *testing.T) {
	ts := newTestAPI(t)

	resp, raw := do(t, ts, http.MethodGet, "/health", "")
	wantStatus(t, resp, raw, http.StatusOK)
	wantJSON(t, resp)
	if got := decode[map[string]string](t, raw)["status"]; got != "ok" {
		t.Errorf("status = %q, want %q", got, "ok")
	}
}

func TestCreateAndGetBook(t *testing.T) {
	ts := newTestAPI(t)

	resp, raw := do(t, ts, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	wantStatus(t, resp, raw, http.StatusCreated)
	wantJSON(t, resp)

	created := decode[Book](t, raw)
	want := Book{ID: created.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	if created.ID <= 0 {
		t.Fatalf("created book has no ID: %+v", created)
	}
	if created != want {
		t.Errorf("created = %+v, want %+v", created, want)
	}
	location := fmt.Sprintf("/books/%d", created.ID)
	if got := resp.Header.Get("Location"); got != location {
		t.Errorf("Location = %q, want %q", got, location)
	}

	resp, raw = do(t, ts, http.MethodGet, location, "")
	wantStatus(t, resp, raw, http.StatusOK)
	wantJSON(t, resp)
	if got := decode[Book](t, raw); got != want {
		t.Errorf("fetched = %+v, want %+v", got, want)
	}
}

func TestCreateBookOptionalFields(t *testing.T) {
	ts := newTestAPI(t)

	got := createBook(t, ts, `{"title":"  Untitled  ","author":" Anonymous "}`)
	want := Book{ID: got.ID, Title: "Untitled", Author: "Anonymous"}
	if got != want {
		t.Errorf("created = %+v, want %+v", got, want)
	}
}

func TestCreateBookRejectsInvalidInput(t *testing.T) {
	ts := newTestAPI(t)

	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string // fields expected in the validation error, if any
	}{
		{"missing title", `{"author":"Frank Herbert"}`, http.StatusBadRequest, []string{"title"}},
		{"missing author", `{"title":"Dune"}`, http.StatusBadRequest, []string{"author"}},
		{"missing both", `{}`, http.StatusBadRequest, []string{"title", "author"}},
		{"blank title", `{"title":"   ","author":"Frank Herbert"}`, http.StatusBadRequest, []string{"title"}},
		{"null title", `{"title":null,"author":"Frank Herbert"}`, http.StatusBadRequest, []string{"title"}},
		{"negative year", `{"title":"Dune","author":"Frank Herbert","year":-1}`, http.StatusBadRequest, []string{"year"}},
		{"year too large", `{"title":"Dune","author":"Frank Herbert","year":10000}`, http.StatusBadRequest, []string{"year"}},
		{"title too long", `{"title":"` + strings.Repeat("x", maxTitleLen+1) + `","author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"year wrong type", `{"title":"Dune","author":"Frank Herbert","year":"1965"}`, http.StatusBadRequest, nil},
		{"title wrong type", `{"title":42,"author":"Frank Herbert"}`, http.StatusBadRequest, nil},
		{"malformed JSON", `{"title":"Dune",`, http.StatusBadRequest, nil},
		{"not an object", `["Dune"]`, http.StatusBadRequest, nil},
		{"trailing data", `{"title":"Dune","author":"Frank Herbert"} {}`, http.StatusBadRequest, nil},
		{"empty body", ``, http.StatusBadRequest, nil},
		{"body too large", `{"title":"` + strings.Repeat("x", maxBodyBytes) + `","author":"A"}`, http.StatusRequestEntityTooLarge, nil},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			resp, raw := do(t, ts, http.MethodPost, "/books", tt.body)
			wantStatus(t, resp, raw, tt.wantStatus)
			wantJSON(t, resp)

			got := decode[errorResponse](t, raw)
			if got.Error == "" {
				t.Errorf("response has no error message: %s", raw)
			}
			if len(got.Fields) != len(tt.wantFields) {
				t.Errorf("fields = %v, want exactly %v", got.Fields, tt.wantFields)
			}
			for _, f := range tt.wantFields {
				if got.Fields[f] == "" {
					t.Errorf("fields = %v, want an entry for %q", got.Fields, f)
				}
			}
		})
	}

	// None of the rejected requests may have stored anything.
	resp, raw := do(t, ts, http.MethodGet, "/books", "")
	wantStatus(t, resp, raw, http.StatusOK)
	if books := decode[[]Book](t, raw); len(books) != 0 {
		t.Errorf("rejected requests stored %d book(s): %+v", len(books), books)
	}
}

func TestListBooks(t *testing.T) {
	ts := newTestAPI(t)

	t.Run("empty collection is an empty array", func(t *testing.T) {
		resp, raw := do(t, ts, http.MethodGet, "/books", "")
		wantStatus(t, resp, raw, http.StatusOK)
		wantJSON(t, resp)
		if got := strings.TrimSpace(string(raw)); got != "[]" {
			t.Errorf("body = %s, want []", got)
		}
	})

	dune := createBook(t, ts, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	emma := createBook(t, ts, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	messiah := createBook(t, ts, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)

	tests := []struct {
		name  string
		query string
		want  []Book
	}{
		{"no filter returns everything in ID order", "", []Book{dune, emma, messiah}},
		{"author filter", "?author=Frank+Herbert", []Book{dune, messiah}},
		{"author filter is case-insensitive", "?author=jane%20austen", []Book{emma}},
		{"author filter matches the whole name", "?author=Frank", []Book{}},
		{"unknown author", "?author=Nobody", []Book{}},
		{"empty author filter is ignored", "?author=", []Book{dune, emma, messiah}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			resp, raw := do(t, ts, http.MethodGet, "/books"+tt.query, "")
			wantStatus(t, resp, raw, http.StatusOK)

			got := decode[[]Book](t, raw)
			if got == nil {
				t.Fatalf("body = %s, want a JSON array", raw)
			}
			if len(got) != len(tt.want) {
				t.Fatalf("got %d book(s) %+v, want %d %+v", len(got), got, len(tt.want), tt.want)
			}
			for i := range got {
				if got[i] != tt.want[i] {
					t.Errorf("book[%d] = %+v, want %+v", i, got[i], tt.want[i])
				}
			}
		})
	}
}

func TestUpdateBook(t *testing.T) {
	ts := newTestAPI(t)
	created := createBook(t, ts, `{"title":"Dune","author":"F. Herbert","year":1965,"isbn":"9780441013593"}`)
	path := fmt.Sprintf("/books/%d", created.ID)

	t.Run("replaces every field", func(t *testing.T) {
		// isbn is omitted, so a full replacement must clear it.
		resp, raw := do(t, ts, http.MethodPut, path, `{"title":"Dune (1st ed.)","author":"Frank Herbert","year":1966}`)
		wantStatus(t, resp, raw, http.StatusOK)
		wantJSON(t, resp)

		want := Book{ID: created.ID, Title: "Dune (1st ed.)", Author: "Frank Herbert", Year: 1966}
		if got := decode[Book](t, raw); got != want {
			t.Errorf("response = %+v, want %+v", got, want)
		}

		resp, raw = do(t, ts, http.MethodGet, path, "")
		wantStatus(t, resp, raw, http.StatusOK)
		if got := decode[Book](t, raw); got != want {
			t.Errorf("stored = %+v, want %+v", got, want)
		}
	})

	t.Run("ignores an id in the body", func(t *testing.T) {
		resp, raw := do(t, ts, http.MethodPut, path, `{"id":999,"title":"Dune","author":"Frank Herbert"}`)
		wantStatus(t, resp, raw, http.StatusOK)
		if got := decode[Book](t, raw); got.ID != created.ID {
			t.Errorf("id = %d, want %d", got.ID, created.ID)
		}
	})

	t.Run("rejects invalid input and leaves the book unchanged", func(t *testing.T) {
		_, before := do(t, ts, http.MethodGet, path, "")

		resp, raw := do(t, ts, http.MethodPut, path, `{"title":"","author":"Frank Herbert"}`)
		wantStatus(t, resp, raw, http.StatusBadRequest)
		if got := decode[errorResponse](t, raw); got.Fields["title"] == "" {
			t.Errorf("fields = %v, want an entry for title", got.Fields)
		}

		_, after := do(t, ts, http.MethodGet, path, "")
		if string(before) != string(after) {
			t.Errorf("book changed after a rejected update: %s -> %s", before, after)
		}
	})

	t.Run("unknown id is not found", func(t *testing.T) {
		resp, raw := do(t, ts, http.MethodPut, "/books/9999", `{"title":"Ghost","author":"Nobody"}`)
		wantStatus(t, resp, raw, http.StatusNotFound)
		wantJSON(t, resp)

		// A failed update must not create the book as a side effect.
		resp, raw = do(t, ts, http.MethodGet, "/books/9999", "")
		wantStatus(t, resp, raw, http.StatusNotFound)
	})
}

func TestDeleteBook(t *testing.T) {
	ts := newTestAPI(t)
	doomed := createBook(t, ts, `{"title":"Dune","author":"Frank Herbert"}`)
	kept := createBook(t, ts, `{"title":"Emma","author":"Jane Austen"}`)
	path := fmt.Sprintf("/books/%d", doomed.ID)

	resp, raw := do(t, ts, http.MethodDelete, path, "")
	wantStatus(t, resp, raw, http.StatusNoContent)
	if len(raw) != 0 {
		t.Errorf("204 response has a body: %s", raw)
	}

	resp, raw = do(t, ts, http.MethodGet, path, "")
	wantStatus(t, resp, raw, http.StatusNotFound)

	resp, raw = do(t, ts, http.MethodDelete, path, "")
	wantStatus(t, resp, raw, http.StatusNotFound)
	wantJSON(t, resp)

	resp, raw = do(t, ts, http.MethodGet, "/books", "")
	wantStatus(t, resp, raw, http.StatusOK)
	if got := decode[[]Book](t, raw); len(got) != 1 || got[0] != kept {
		t.Errorf("remaining books = %+v, want only %+v", got, kept)
	}
}

func TestBookIDErrors(t *testing.T) {
	ts := newTestAPI(t)
	valid := `{"title":"Dune","author":"Frank Herbert"}`

	tests := []struct {
		name       string
		method     string
		path       string
		body       string
		wantStatus int
	}{
		{"get unknown id", http.MethodGet, "/books/1", "", http.StatusNotFound},
		{"get non-numeric id", http.MethodGet, "/books/abc", "", http.StatusBadRequest},
		{"get zero id", http.MethodGet, "/books/0", "", http.StatusBadRequest},
		{"get negative id", http.MethodGet, "/books/-1", "", http.StatusBadRequest},
		{"get overflowing id", http.MethodGet, "/books/99999999999999999999", "", http.StatusBadRequest},
		{"put non-numeric id", http.MethodPut, "/books/abc", valid, http.StatusBadRequest},
		{"delete non-numeric id", http.MethodDelete, "/books/abc", "", http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			resp, raw := do(t, ts, tt.method, tt.path, tt.body)
			wantStatus(t, resp, raw, tt.wantStatus)
			wantJSON(t, resp)
			if got := decode[errorResponse](t, raw); got.Error == "" {
				t.Errorf("response has no error message: %s", raw)
			}
		})
	}
}

func TestUnsupportedRoutes(t *testing.T) {
	ts := newTestAPI(t)

	tests := []struct {
		name       string
		method     string
		path       string
		wantStatus int
		wantAllow  string
	}{
		{"delete collection", http.MethodDelete, "/books", http.StatusMethodNotAllowed, "GET, HEAD, POST"},
		{"post to item", http.MethodPost, "/books/1", http.StatusMethodNotAllowed, "GET, HEAD, PUT, DELETE"},
		{"post to health", http.MethodPost, "/health", http.StatusMethodNotAllowed, "GET, HEAD"},
		{"unknown path", http.MethodGet, "/authors", http.StatusNotFound, ""},
		{"root", http.MethodGet, "/", http.StatusNotFound, ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			resp, raw := do(t, ts, tt.method, tt.path, "")
			wantStatus(t, resp, raw, tt.wantStatus)
			wantJSON(t, resp)
			if got := resp.Header.Get("Allow"); got != tt.wantAllow {
				t.Errorf("Allow = %q, want %q", got, tt.wantAllow)
			}
			if got := decode[errorResponse](t, raw); got.Error == "" {
				t.Errorf("response has no error message: %s", raw)
			}
		})
	}
}
