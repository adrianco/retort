package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) *Server {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "test.db")
	store, err := NewStore(dbPath)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func doRequest(t *testing.T, srv *Server, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	rec := httptest.NewRecorder()
	srv.Routes().ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", rec.Code)
	}
	var got map[string]string
	if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got["status"] != "ok" {
		t.Fatalf("want status=ok, got %v", got)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)
	in := Book{Title: "The Go Programming Language", Author: "Donovan & Kernighan", Year: 2015, ISBN: "978-0134190440"}

	rec := doRequest(t, srv, http.MethodPost, "/books", in)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: want 201, got %d body=%s", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.NewDecoder(rec.Body).Decode(&created); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("expected non-zero id")
	}
	if created.Title != in.Title || created.Author != in.Author {
		t.Fatalf("payload mismatch: %+v", created)
	}

	rec = doRequest(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: want 200, got %d", rec.Code)
	}
	var got Book
	if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got != created {
		t.Fatalf("want %+v, got %+v", created, got)
	}
}

func TestCreateValidationMissingFields(t *testing.T) {
	srv := newTestServer(t)

	rec := doRequest(t, srv, http.MethodPost, "/books", map[string]any{"author": "Someone"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("missing title: want 400, got %d body=%s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "title") {
		t.Fatalf("expected title error, got %s", rec.Body.String())
	}

	rec = doRequest(t, srv, http.MethodPost, "/books", map[string]any{"title": "T"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("missing author: want 400, got %d body=%s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "author") {
		t.Fatalf("expected author error, got %s", rec.Body.String())
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	books := []Book{
		{Title: "A", Author: "Alice", Year: 2001},
		{Title: "B", Author: "Bob", Year: 2002},
		{Title: "C", Author: "Alice", Year: 2003},
	}
	for _, b := range books {
		rec := doRequest(t, srv, http.MethodPost, "/books", b)
		if rec.Code != http.StatusCreated {
			t.Fatalf("seed: %d %s", rec.Code, rec.Body.String())
		}
	}

	rec := doRequest(t, srv, http.MethodGet, "/books", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list: %d", rec.Code)
	}
	var all []Book
	if err := json.NewDecoder(rec.Body).Decode(&all); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("want 3 books, got %d", len(all))
	}

	rec = doRequest(t, srv, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list alice: %d", rec.Code)
	}
	var alice []Book
	if err := json.NewDecoder(rec.Body).Decode(&alice); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(alice) != 2 {
		t.Fatalf("want 2 alice books, got %d: %+v", len(alice), alice)
	}
	for _, b := range alice {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author: %+v", b)
		}
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodPost, "/books", Book{Title: "Old", Author: "Auth"})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: %d", rec.Code)
	}
	var created Book
	_ = json.NewDecoder(rec.Body).Decode(&created)

	rec = doRequest(t, srv, http.MethodPut, "/books/"+itoa(created.ID),
		Book{Title: "New", Author: "Auth2", Year: 2020, ISBN: "x"})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: %d body=%s", rec.Code, rec.Body.String())
	}
	var updated Book
	_ = json.NewDecoder(rec.Body).Decode(&updated)
	if updated.Title != "New" || updated.Author != "Auth2" || updated.Year != 2020 {
		t.Fatalf("update failed: %+v", updated)
	}

	rec = doRequest(t, srv, http.MethodPut, "/books/999999", Book{Title: "x", Author: "y"})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("update missing: want 404, got %d", rec.Code)
	}

	rec = doRequest(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: want 204, got %d", rec.Code)
	}

	rec = doRequest(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete: want 404, got %d", rec.Code)
	}

	rec = doRequest(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("delete missing: want 404, got %d", rec.Code)
	}
}

func itoa(n int64) string {
	return strings.TrimSpace(jsonNum(n))
}

func jsonNum(n int64) string {
	b, _ := json.Marshal(n)
	return string(b)
}
