package api

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

	"bookapi/internal/store"
)

type testEnv struct {
	t      *testing.T
	server http.Handler
}

func newTestEnv(t *testing.T) *testEnv {
	t.Helper()
	st, err := store.Open(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { st.Close() })
	return &testEnv{t: t, server: New(st)}
}

func (e *testEnv) do(method, path string, body any) (*httptest.ResponseRecorder, any) {
	e.t.Helper()
	var reader *bytes.Reader
	switch b := body.(type) {
	case nil:
		reader = bytes.NewReader(nil)
	case string:
		reader = bytes.NewReader([]byte(b))
	default:
		data, err := json.Marshal(b)
		if err != nil {
			e.t.Fatalf("marshal body: %v", err)
		}
		reader = bytes.NewReader(data)
	}
	req := httptest.NewRequest(method, path, reader)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	e.server.ServeHTTP(w, req)

	var decoded any
	if w.Body.Len() > 0 {
		if err := json.Unmarshal(w.Body.Bytes(), &decoded); err != nil {
			e.t.Fatalf("decode response %q: %v", w.Body.String(), err)
		}
	}
	return w, decoded
}

func asObject(t *testing.T, v any) map[string]any {
	t.Helper()
	m, ok := v.(map[string]any)
	if !ok {
		t.Fatalf("response is not a JSON object: %v", v)
	}
	return m
}

func asList(t *testing.T, v any) []map[string]any {
	t.Helper()
	arr, ok := v.([]any)
	if !ok {
		t.Fatalf("response is not a JSON array: %v", v)
	}
	out := make([]map[string]any, 0, len(arr))
	for _, item := range arr {
		m, ok := item.(map[string]any)
		if !ok {
			t.Fatalf("list item is not an object: %v", item)
		}
		out = append(out, m)
	}
	return out
}

func (e *testEnv) createBook(t *testing.T, title, author string, extra map[string]any) map[string]any {
	t.Helper()
	body := map[string]any{"title": title, "author": author}
	for k, v := range extra {
		body[k] = v
	}
	w, decoded := e.do(http.MethodPost, "/books", body)
	if w.Code != http.StatusCreated {
		t.Fatalf("POST /books = %d (%s), want 201", w.Code, w.Body.String())
	}
	return asObject(t, decoded)
}

func idOf(t *testing.T, m map[string]any) int64 {
	t.Helper()
	f, ok := m["id"].(float64)
	if !ok {
		t.Fatalf("missing numeric id in %v", m)
	}
	return int64(f)
}

func TestHealth(t *testing.T) {
	e := newTestEnv(t)
	w, decoded := e.do(http.MethodGet, "/health", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("GET /health = %d, want 200", w.Code)
	}
	if asObject(t, decoded)["status"] != "ok" {
		t.Fatalf("health status = %v, want ok", decoded)
	}
}

func TestCreateBook(t *testing.T) {
	e := newTestEnv(t)
	w, decoded := e.do(http.MethodPost, "/books", map[string]any{
		"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719",
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("POST /books = %d, want 201", w.Code)
	}
	created := asObject(t, decoded)
	if created["title"] != "Dune" || created["author"] != "Frank Herbert" {
		t.Fatalf("created book = %v, want Dune by Frank Herbert", created)
	}
	id := idOf(t, created)

	gw, got := e.do(http.MethodGet, fmt.Sprintf("/books/%d", id), nil)
	if gw.Code != http.StatusOK {
		t.Fatalf("GET /books/%d = %d, want 200", id, gw.Code)
	}
	gotObj := asObject(t, got)
	if gotObj["title"] != "Dune" || gotObj["year"].(float64) != 1965 || gotObj["isbn"] != "978-0441172719" {
		t.Fatalf("GET round-trip = %v, want original values", gotObj)
	}
}

func TestCreateBookValidation(t *testing.T) {
	e := newTestEnv(t)
	cases := []struct {
		name string
		body any
		want string
	}{
		{"missing title", map[string]any{"author": "A"}, "title is required"},
		{"missing author", map[string]any{"title": "T"}, "author is required"},
		{"blank title", map[string]any{"title": "   ", "author": "A"}, "title is required"},
		{"blank author", map[string]any{"title": "T", "author": "  "}, "author is required"},
		{"bad year", map[string]any{"title": "T", "author": "A", "year": 12345}, "year must be between 0 and 9999"},
		{"negative year", map[string]any{"title": "T", "author": "A", "year": -1}, "year must be between 0 and 9999"},
		{"malformed json", "{not json", "invalid JSON body"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			w, decoded := e.do(http.MethodPost, "/books", tc.body)
			if w.Code != http.StatusBadRequest {
				t.Fatalf("POST = %d, want 400", w.Code)
			}
			if msg, _ := asObject(t, decoded)["error"].(string); !strings.Contains(msg, tc.want) {
				t.Fatalf("error = %q, want it to contain %q", msg, tc.want)
			}
		})
	}
}

func TestGetBook(t *testing.T) {
	e := newTestEnv(t)
	created := e.createBook(t, "Hyperion", "Dan Simmons", map[string]any{"year": 1989})
	id := idOf(t, created)

	w, decoded := e.do(http.MethodGet, fmt.Sprintf("/books/%d", id), nil)
	if w.Code != http.StatusOK {
		t.Fatalf("GET = %d, want 200", w.Code)
	}
	if asObject(t, decoded)["title"] != "Hyperion" {
		t.Fatalf("GET = %v, want Hyperion", decoded)
	}

	if w, _ := e.do(http.MethodGet, "/books/999999", nil); w.Code != http.StatusNotFound {
		t.Fatalf("GET missing = %d, want 404", w.Code)
	}
	if w, _ := e.do(http.MethodGet, "/books/notanumber", nil); w.Code != http.StatusBadRequest {
		t.Fatalf("GET bad id = %d, want 400", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	e := newTestEnv(t)
	e.createBook(t, "Dune", "Frank Herbert", nil)
	e.createBook(t, "Neuromancer", "William Gibson", nil)
	e.createBook(t, "Dune Messiah", "Frank Herbert", nil)

	w, decoded := e.do(http.MethodGet, "/books", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("GET /books = %d, want 200", w.Code)
	}
	if books := asList(t, decoded); len(books) != 3 {
		t.Fatalf("list returned %d books, want 3", len(books))
	}

	w, decoded = e.do(http.MethodGet, "/books?author=Frank%20Herbert", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("GET /books?author = %d, want 200", w.Code)
	}
	books := asList(t, decoded)
	if len(books) != 2 {
		t.Fatalf("filtered list returned %d books, want 2", len(books))
	}
	for _, b := range books {
		if b["author"] != "Frank Herbert" {
			t.Fatalf("filtered list contains wrong author: %v", b)
		}
	}

	w, decoded = e.do(http.MethodGet, "/books?author=Unknown", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("GET /books?author=Unknown = %d, want 200", w.Code)
	}
	if books := asList(t, decoded); len(books) != 0 {
		t.Fatalf("expected empty list, got %v", books)
	}
}

func TestUpdateBook(t *testing.T) {
	e := newTestEnv(t)
	created := e.createBook(t, "Old Title", "A. Author", map[string]any{"year": 1999, "isbn": "old"})
	id := idOf(t, created)

	// Full update.
	w, decoded := e.do(http.MethodPut, fmt.Sprintf("/books/%d", id), map[string]any{
		"title": "New Title", "author": "B. Author", "year": 2001, "isbn": "new",
	})
	if w.Code != http.StatusOK {
		t.Fatalf("PUT = %d (%s), want 200", w.Code, w.Body.String())
	}
	updated := asObject(t, decoded)
	if updated["title"] != "New Title" || updated["author"] != "B. Author" ||
		updated["year"].(float64) != 2001 || updated["isbn"] != "new" {
		t.Fatalf("PUT response = %v, want updated values", updated)
	}

	// Partial update: omit year/isbn, they keep stored values.
	w, decoded = e.do(http.MethodPut, fmt.Sprintf("/books/%d", id), map[string]any{
		"title": "Newer Title", "author": "B. Author",
	})
	if w.Code != http.StatusOK {
		t.Fatalf("PUT partial = %d (%s), want 200", w.Code, w.Body.String())
	}
	updated = asObject(t, decoded)
	if updated["year"].(float64) != 2001 || updated["isbn"] != "new" {
		t.Fatalf("partial update lost year/isbn: %v", updated)
	}

	// Validation: missing title.
	w, decoded = e.do(http.MethodPut, fmt.Sprintf("/books/%d", id), map[string]any{"author": "B. Author"})
	if w.Code != http.StatusBadRequest {
		t.Fatalf("PUT missing title = %d, want 400", w.Code)
	}
	if msg, _ := asObject(t, decoded)["error"].(string); !strings.Contains(msg, "title is required") {
		t.Fatalf("error = %q, want title required", msg)
	}

	// Missing book.
	if w, _ = e.do(http.MethodPut, "/books/999999", map[string]any{"title": "T", "author": "A"}); w.Code != http.StatusNotFound {
		t.Fatalf("PUT missing book = %d, want 404", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	e := newTestEnv(t)
	created := e.createBook(t, "Ephemeral", "E. Author", nil)
	id := idOf(t, created)

	w, _ := e.do(http.MethodDelete, fmt.Sprintf("/books/%d", id), nil)
	if w.Code != http.StatusNoContent {
		t.Fatalf("DELETE = %d, want 204", w.Code)
	}
	if w.Body.Len() != 0 {
		t.Fatalf("DELETE body = %q, want empty", w.Body.String())
	}

	if w, _ := e.do(http.MethodGet, fmt.Sprintf("/books/%d", id), nil); w.Code != http.StatusNotFound {
		t.Fatalf("GET after delete = %d, want 404", w.Code)
	}
	if w, _ = e.do(http.MethodDelete, fmt.Sprintf("/books/%d", id), nil); w.Code != http.StatusNotFound {
		t.Fatalf("second DELETE = %d, want 404", w.Code)
	}
	if w, _ = e.do(http.MethodDelete, "/books/notanumber", nil); w.Code != http.StatusBadRequest {
		t.Fatalf("DELETE bad id = %d, want 400", w.Code)
	}
}

func TestPersistenceAcrossStoreReopens(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "books.db")
	ctx := context.Background()

	st, err := store.Open(path)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	if _, err := st.Create(ctx, store.Book{Title: "Keeper", Author: "K. Author"}); err != nil {
		t.Fatalf("create: %v", err)
	}
	st.Close()

	st2, err := store.Open(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer st2.Close()
	books, err := st2.List(ctx, "")
	if err != nil {
		t.Fatalf("list: %v", err)
	}
	if len(books) != 1 || books[0].Title != "Keeper" {
		t.Fatalf("after reopen list = %+v, want 1 book 'Keeper'", books)
	}
}
