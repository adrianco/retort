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
	s, err := NewServer(dbPath)
	if err != nil {
		t.Fatalf("NewServer: %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func do(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatal(err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s.Routes(), http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	s := newTestServer(t)
	h := s.Routes()
	rec := do(t, h, http.MethodPost, "/books", Book{Title: "Dune", Author: "Herbert", Year: 1965, ISBN: "111"})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d body=%s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 || created.Title != "Dune" {
		t.Fatalf("unexpected: %+v", created)
	}

	rec = do(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d", rec.Code)
	}
	var got Book
	_ = json.Unmarshal(rec.Body.Bytes(), &got)
	if got.Author != "Herbert" {
		t.Fatalf("author = %s", got.Author)
	}
}

func TestCreateValidation(t *testing.T) {
	s := newTestServer(t)
	rec := do(t, s.Routes(), http.MethodPost, "/books", Book{Author: "X"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d", rec.Code)
	}
}

func TestListFilterByAuthor(t *testing.T) {
	s := newTestServer(t)
	h := s.Routes()
	do(t, h, http.MethodPost, "/books", Book{Title: "A", Author: "Alice"})
	do(t, h, http.MethodPost, "/books", Book{Title: "B", Author: "Bob"})
	do(t, h, http.MethodPost, "/books", Book{Title: "C", Author: "Alice"})

	rec := do(t, h, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d", rec.Code)
	}
	var books []Book
	_ = json.Unmarshal(rec.Body.Bytes(), &books)
	if len(books) != 2 {
		t.Fatalf("got %d books, want 2", len(books))
	}
}

func TestUpdateAndDelete(t *testing.T) {
	s := newTestServer(t)
	h := s.Routes()
	do(t, h, http.MethodPost, "/books", Book{Title: "Old", Author: "A"})

	rec := do(t, h, http.MethodPut, "/books/1", Book{Title: "New", Author: "A", Year: 2020})
	if rec.Code != http.StatusOK {
		t.Fatalf("put status = %d", rec.Code)
	}
	rec = do(t, h, http.MethodGet, "/books/1", nil)
	var b Book
	_ = json.Unmarshal(rec.Body.Bytes(), &b)
	if b.Title != "New" || b.Year != 2020 {
		t.Fatalf("update failed: %+v", b)
	}

	rec = do(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", rec.Code)
	}
	rec = do(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get-after-delete status = %d", rec.Code)
	}
}
