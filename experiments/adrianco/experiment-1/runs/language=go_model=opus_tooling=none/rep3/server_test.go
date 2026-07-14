package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	dir := t.TempDir()
	s, err := NewServer(filepath.Join(dir, "test.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func do(t *testing.T, s *Server, method, path string, body interface{}) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatal(err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	s.Handler().ServeHTTP(rr, req)
	return rr
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)
	rr := do(t, s, "GET", "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	s := newTestServer(t)
	rr := do(t, s, "POST", "/books", map[string]interface{}{
		"title": "Go", "author": "Alan", "year": 2020, "isbn": "123",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d body=%s", rr.Code, rr.Body.String())
	}
	var b Book
	if err := json.Unmarshal(rr.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID == 0 || b.Title != "Go" {
		t.Fatalf("bad book: %+v", b)
	}

	rr = do(t, s, "GET", "/books/"+strconv.FormatInt(b.ID, 10), nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
	var got Book
	json.Unmarshal(rr.Body.Bytes(), &got)
	if got.Author != "Alan" {
		t.Fatalf("bad author: %+v", got)
	}
}

func TestValidationMissingFields(t *testing.T) {
	s := newTestServer(t)
	rr := do(t, s, "POST", "/books", map[string]interface{}{"author": "x"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rr.Code)
	}
	rr = do(t, s, "POST", "/books", map[string]interface{}{"title": "x"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rr.Code)
	}
}

func TestListFilterUpdateDelete(t *testing.T) {
	s := newTestServer(t)
	do(t, s, "POST", "/books", map[string]interface{}{"title": "A", "author": "X"})
	do(t, s, "POST", "/books", map[string]interface{}{"title": "B", "author": "Y"})
	do(t, s, "POST", "/books", map[string]interface{}{"title": "C", "author": "X"})

	rr := do(t, s, "GET", "/books?author=X", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("list: %d", rr.Code)
	}
	var list []Book
	json.Unmarshal(rr.Body.Bytes(), &list)
	if len(list) != 2 {
		t.Fatalf("expected 2 books by X, got %d", len(list))
	}

	id := list[0].ID
	rr = do(t, s, "PUT", "/books/"+strconv.FormatInt(id, 10), map[string]interface{}{
		"title": "A2", "author": "X",
	})
	if rr.Code != http.StatusOK {
		t.Fatalf("update: %d", rr.Code)
	}

	rr = do(t, s, "DELETE", "/books/"+strconv.FormatInt(id, 10), nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("delete: %d", rr.Code)
	}

	rr = do(t, s, "GET", "/books/"+strconv.FormatInt(id, 10), nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", rr.Code)
	}
}
