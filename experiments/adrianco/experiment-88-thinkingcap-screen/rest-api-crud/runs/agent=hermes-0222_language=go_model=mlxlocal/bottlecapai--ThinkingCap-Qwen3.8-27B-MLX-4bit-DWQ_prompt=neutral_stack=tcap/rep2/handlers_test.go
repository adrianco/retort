package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"

	"github.com/gin-gonic/gin"
)

func init() { gin.SetMode(gin.TestMode) }

// newTestRouter builds a fresh API + engine backed by a temp-file SQLite DB.
func newTestRouter(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open test store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewRouter(store)
}

// do performs a request against the handler and returns the recorder.
func do(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var reader *bytes.Reader
	if body == nil {
		reader = bytes.NewReader(nil)
	} else if s, ok := body.(string); ok {
		reader = bytes.NewReader([]byte(s))
	} else {
		data, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("marshal body: %v", err)
		}
		reader = bytes.NewReader(data)
	}
	req := httptest.NewRequest(method, path, reader)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	h.ServeHTTP(w, req)
	return w
}

// decode unmarshals the response body into out.
func decode(t *testing.T, w *httptest.ResponseRecorder, out any) {
	t.Helper()
	if err := json.Unmarshal(w.Body.Bytes(), out); err != nil {
		t.Fatalf("decode response %q: %v", w.Body.String(), err)
	}
}

func TestHealthEndpoint(t *testing.T) {
	w := do(t, newTestRouter(t), http.MethodGet, "/health", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body: %s)", w.Code, w.Body.String())
	}
	var resp struct {
		Status string `json:"status"`
	}
	decode(t, w, &resp)
	if resp.Status != "ok" {
		t.Fatalf("status = %q, want ok", resp.Status)
	}
}

func TestCreateBook_Success(t *testing.T) {
	h := newTestRouter(t)
	body := map[string]any{"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0547928227"}
	w := do(t, h, http.MethodPost, "/books", body)
	if w.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201 (body: %s)", w.Code, w.Body.String())
	}
	var created Book
	decode(t, w, &created)
	if created.ID == 0 {
		t.Fatalf("expected auto-assigned id, got 0")
	}
	if created.Title != "The Hobbit" || created.Author != "J.R.R. Tolkien" || created.Year != 1937 || created.ISBN != "978-0547928227" {
		t.Fatalf("created book = %+v, fields not echoed", created)
	}

	// Optional fields may be omitted.
	w = do(t, h, http.MethodPost, "/books", map[string]any{"title": "Dune", "author": "Frank Herbert"})
	if w.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201 (body: %s)", w.Code, w.Body.String())
	}
	var dune Book
	decode(t, w, &dune)
	if dune.Year != 0 || dune.ISBN != "" {
		t.Fatalf("omitted fields not defaulted: %+v", dune)
	}
}

func TestCreateBook_Validation(t *testing.T) {
	h := newTestRouter(t)
	cases := []struct {
		name string
		body string
	}{
		{"missing title", `{"author":"A"}`},
		{"missing author", `{"title":"T"}`},
		{"empty title", `{"title":"  ","author":"A"}`},
		{"empty author", `{"title":"T","author":""}`},
		{"negative year", `{"title":"T","author":"A","year":-5}`},
		{"malformed json", `{"title":`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			w := do(t, h, http.MethodPost, "/books", tc.body)
			if w.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400 (body: %s)", w.Code, w.Body.String())
			}
		})
	}

	// Nothing should have been persisted.
	w := do(t, h, http.MethodGet, "/books", nil)
	var books []Book
	decode(t, w, &books)
	if len(books) != 0 {
		t.Fatalf("expected empty list after failed creates, got %d books", len(books))
	}
}

func TestListBooks_AuthorFilter(t *testing.T) {
	h := newTestRouter(t)
	for _, b := range []map[string]any{
		{"title": "A", "author": "Alice"},
		{"title": "B", "author": "Alice"},
		{"title": "C", "author": "Bob"},
	} {
		if w := do(t, h, http.MethodPost, "/books", b); w.Code != http.StatusCreated {
			t.Fatalf("setup create failed: %d %s", w.Code, w.Body.String())
		}
	}

	w := do(t, h, http.MethodGet, "/books", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	var all []Book
	decode(t, w, &all)
	if len(all) != 3 {
		t.Fatalf("all books = %d, want 3", len(all))
	}

	// Case-insensitive exact match.
	w = do(t, h, http.MethodGet, "/books?author=alice", nil)
	var alice []Book
	decode(t, w, &alice)
	if len(alice) != 2 {
		t.Fatalf("filtered books = %d, want 2", len(alice))
	}
	for _, b := range alice {
		if b.Author != "Alice" {
			t.Fatalf("filter returned wrong author: %q", b.Author)
		}
	}

	// No matches returns an empty list, not null.
	w = do(t, h, http.MethodGet, "/books?author=nobody", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	if got := w.Body.String(); got != "[]" {
		t.Fatalf("empty filter result = %s, want []", got)
	}
}

func TestGetBook(t *testing.T) {
	h := newTestRouter(t)
	w := do(t, h, http.MethodPost, "/books", map[string]any{"title": "T", "author": "A", "year": 2000})
	var created Book
	decode(t, w, &created)

	w = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body: %s)", w.Code, w.Body.String())
	}
	var got Book
	decode(t, w, &got)
	if got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}

	if w = do(t, h, http.MethodGet, "/books/99999", nil); w.Code != http.StatusNotFound {
		t.Fatalf("missing id status = %d, want 404", w.Code)
	}
	if w = do(t, h, http.MethodGet, "/books/notanumber", nil); w.Code != http.StatusBadRequest {
		t.Fatalf("invalid id status = %d, want 400", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestRouter(t)
	w := do(t, h, http.MethodPost, "/books", map[string]any{"title": "Old", "author": "A"})
	var created Book
	decode(t, w, &created)

	w = do(t, h, http.MethodPut, "/books/"+itoa(created.ID),
		map[string]any{"title": "New", "author": "B", "year": 1999, "isbn": "x-1"})
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body: %s)", w.Code, w.Body.String())
	}
	var updated Book
	decode(t, w, &updated)
	if updated.Title != "New" || updated.Author != "B" || updated.Year != 1999 || updated.ISBN != "x-1" || updated.ID != created.ID {
		t.Fatalf("updated = %+v, fields wrong", updated)
	}

	// Persistence check via GET.
	w = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil)
	decode(t, w, &updated)
	if updated.Title != "New" {
		t.Fatalf("GET after PUT = %+v, update not persisted", updated)
	}

	// 404 for unknown id.
	if w = do(t, h, http.MethodPut, "/books/99999", map[string]any{"title": "X", "author": "Y"}); w.Code != http.StatusNotFound {
		t.Fatalf("update missing id status = %d, want 404", w.Code)
	}
	// 400 on validation failure.
	if w = do(t, h, http.MethodPut, "/books/"+itoa(created.ID), map[string]any{"author": "only"}); w.Code != http.StatusBadRequest {
		t.Fatalf("update missing title status = %d, want 400", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestRouter(t)
	w := do(t, h, http.MethodPost, "/books", map[string]any{"title": "T", "author": "A"})
	var created Book
	decode(t, w, &created)

	w = do(t, h, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if w.Code != http.StatusNoContent {
		t.Fatalf("status = %d, want 204 (body: %s)", w.Code, w.Body.String())
	}

	// Gone afterwards.
	if w = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil); w.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", w.Code)
	}
	// Delete again -> 404.
	if w = do(t, h, http.MethodDelete, "/books/"+itoa(created.ID), nil); w.Code != http.StatusNotFound {
		t.Fatalf("second delete status = %d, want 404", w.Code)
	}
}

func TestRootEndpoint(t *testing.T) {
	w := do(t, newTestRouter(t), http.MethodGet, "/", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body: %s)", w.Code, w.Body.String())
	}
	var resp struct {
		Service string `json:"service"`
	}
	decode(t, w, &resp)
	if resp.Service != "book-api" {
		t.Fatalf("service = %q, want book-api", resp.Service)
	}
}

func TestUnknownRoute_ReturnsJSON404(t *testing.T) {
	w := do(t, newTestRouter(t), http.MethodGet, "/nope", nil)
	if w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", w.Code)
	}
	var errResp struct {
		Error string `json:"error"`
	}
	decode(t, w, &errResp)
	if errResp.Error == "" {
		t.Fatalf("expected JSON error body, got %s", w.Body.String())
	}
}
