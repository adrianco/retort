package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "test.db")
	store, err := NewStore(dbPath)
	if err != nil {
		t.Fatalf("store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, srv *Server, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatal(err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	rr := httptest.NewRecorder()
	srv.ServeHTTP(rr, req)
	return rr
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rr := do(t, srv, http.MethodGet, "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("code=%d", rr.Code)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)
	rr := do(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "Go", "author": "Alan", "year": 2020, "isbn": "123",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create code=%d body=%s", rr.Code, rr.Body.String())
	}
	var b Book
	if err := json.Unmarshal(rr.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID == 0 || b.Title != "Go" {
		t.Fatalf("bad book: %+v", b)
	}

	rr = do(t, srv, http.MethodGet, "/books/1", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("get code=%d", rr.Code)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	rr := do(t, srv, http.MethodPost, "/books", map[string]any{"title": "No Author"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rr.Code)
	}
}

func TestListFilterByAuthor(t *testing.T) {
	srv := newTestServer(t)
	do(t, srv, http.MethodPost, "/books", map[string]any{"title": "A", "author": "X"})
	do(t, srv, http.MethodPost, "/books", map[string]any{"title": "B", "author": "Y"})
	do(t, srv, http.MethodPost, "/books", map[string]any{"title": "C", "author": "X"})

	rr := do(t, srv, http.MethodGet, "/books?author=X", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("code=%d", rr.Code)
	}
	var books []Book
	if err := json.Unmarshal(rr.Body.Bytes(), &books); err != nil {
		t.Fatal(err)
	}
	if len(books) != 2 {
		t.Fatalf("expected 2, got %d", len(books))
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)
	do(t, srv, http.MethodPost, "/books", map[string]any{"title": "A", "author": "X"})

	rr := do(t, srv, http.MethodPut, "/books/1", map[string]any{"title": "A2", "author": "X", "year": 2021})
	if rr.Code != http.StatusOK {
		t.Fatalf("put code=%d", rr.Code)
	}

	rr = do(t, srv, http.MethodDelete, "/books/1", nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("delete code=%d", rr.Code)
	}

	rr = do(t, srv, http.MethodGet, "/books/1", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rr.Code)
	}
}
