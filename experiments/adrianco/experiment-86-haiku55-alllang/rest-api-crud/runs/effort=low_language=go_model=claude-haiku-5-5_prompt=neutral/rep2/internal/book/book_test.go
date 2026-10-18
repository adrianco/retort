package book

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"
)

func newTestHandler(t *testing.T) (*Handler, *Store) {
	t.Helper()
	store, err := Open(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewHandler(store), store
}

func do(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestAPIEndToEnd(t *testing.T) {
	h, _ := newTestHandler(t)

	// Create
	rec := do(t, h, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719"})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: want 201, got %d: %s", rec.Code, rec.Body)
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode create: %v", err)
	}
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected created book: %+v", created)
	}
	if loc := rec.Header().Get("Location"); loc == "" {
		t.Error("create: missing Location header")
	}

	// Get
	rec = do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: want 200, got %d", rec.Code)
	}

	// Update
	rec = do(t, h, http.MethodPut, "/books/"+strconv.FormatInt(created.ID, 10), Book{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: want 200, got %d: %s", rec.Code, rec.Body)
	}
	var updated Book
	_ = json.Unmarshal(rec.Body.Bytes(), &updated)
	if updated.Title != "Dune Messiah" || updated.ID != created.ID {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	// Delete
	rec = do(t, h, http.MethodDelete, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: want 204, got %d", rec.Code)
	}
	rec = do(t, h, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete: want 404, got %d", rec.Code)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h, _ := newTestHandler(t)
	for _, b := range []Book{
		{Title: "Dune", Author: "Frank Herbert"},
		{Title: "Emma", Author: "Jane Austen"},
		{Title: "Children of Dune", Author: "frank herbert"},
	} {
		if rec := do(t, h, http.MethodPost, "/books", b); rec.Code != http.StatusCreated {
			t.Fatalf("seed: %d", rec.Code)
		}
	}

	var all []Book
	rec := do(t, h, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list: want 200, got %d", rec.Code)
	}
	_ = json.Unmarshal(rec.Body.Bytes(), &all)
	if len(all) != 3 {
		t.Fatalf("list: want 3 books, got %d", len(all))
	}

	var filtered []Book
	rec = do(t, h, http.MethodGet, "/books?author=Frank+Herbert", nil)
	_ = json.Unmarshal(rec.Body.Bytes(), &filtered)
	if len(filtered) != 2 {
		t.Fatalf("filter: want 2 books, got %d", len(filtered))
	}

	var empty []Book
	rec = do(t, h, http.MethodGet, "/books?author=Nobody", nil)
	_ = json.Unmarshal(rec.Body.Bytes(), &empty)
	if rec.Code != http.StatusOK || empty == nil || len(empty) != 0 {
		t.Fatalf("empty filter: want 200 and [], got %d %s", rec.Code, rec.Body)
	}
}

func TestValidationAndErrors(t *testing.T) {
	h, _ := newTestHandler(t)

	cases := []struct {
		name   string
		method string
		path   string
		body   any
		want   int
	}{
		{"missing title", http.MethodPost, "/books", Book{Author: "A"}, http.StatusBadRequest},
		{"missing author", http.MethodPost, "/books", Book{Title: "T"}, http.StatusBadRequest},
		{"blank title", http.MethodPost, "/books", Book{Title: "   ", Author: "A"}, http.StatusBadRequest},
		{"negative year", http.MethodPost, "/books", Book{Title: "T", Author: "A", Year: -1}, http.StatusBadRequest},
		{"bad id", http.MethodGet, "/books/abc", nil, http.StatusBadRequest},
		{"zero id", http.MethodGet, "/books/0", nil, http.StatusBadRequest},
		{"get missing", http.MethodGet, "/books/999", nil, http.StatusNotFound},
		{"update missing", http.MethodPut, "/books/999", Book{Title: "T", Author: "A"}, http.StatusNotFound},
		{"update invalid", http.MethodPut, "/books/999", Book{}, http.StatusBadRequest},
		{"delete missing", http.MethodDelete, "/books/999", nil, http.StatusNotFound},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := do(t, h, tc.method, tc.path, tc.body)
			if rec.Code != tc.want {
				t.Fatalf("want %d, got %d: %s", tc.want, rec.Code, rec.Body)
			}
		})
	}

	// Unknown fields and malformed JSON are rejected.
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(`{"title":"T","author":"A","bogus":1}`))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("unknown field: want 400, got %d", rec.Code)
	}
	req = httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(`{not json`))
	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("malformed json: want 400, got %d", rec.Code)
	}
}

func TestHealth(t *testing.T) {
	h, store := newTestHandler(t)
	rec := do(t, h, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("health: want 200, got %d", rec.Code)
	}

	store.Close()
	rec = do(t, h, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusServiceUnavailable {
		t.Fatalf("health after close: want 503, got %d", rec.Code)
	}
}

func TestStoreValidationType(t *testing.T) {
	store, err := Open(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	_, err = store.Create(Book{})
	var ve *ValidationError
	if !errors.As(err, &ve) {
		t.Fatalf("want ValidationError, got %v", err)
	}
	if _, ok := ve.Fields["title"]; !ok {
		t.Error("expected title field error")
	}
}
