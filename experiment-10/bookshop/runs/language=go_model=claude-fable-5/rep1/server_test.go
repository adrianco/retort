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
	store, err := NewStore(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func doJSON(t *testing.T, srv *Server, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	return rec
}

func decodeBody[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode response %q: %v", rec.Body.String(), err)
	}
	return v
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rec := doJSON(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("got status %d, want 200", rec.Code)
	}
	body := decodeBody[map[string]string](t, rec)
	if body["status"] != "ok" {
		t.Errorf("got status %q, want %q", body["status"], "ok")
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	rec := doJSON(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "Mythical Man-Month", "author": "Fred Brooks", "year": 1975, "isbn": "978-0201835953",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: got status %d, want 201; body: %s", rec.Code, rec.Body)
	}
	created := decodeBody[Book](t, rec)
	if created.ID == 0 {
		t.Fatal("create: expected non-zero ID")
	}
	if created.Title != "Mythical Man-Month" || created.Author != "Fred Brooks" {
		t.Errorf("create: unexpected book %+v", created)
	}

	rec = doJSON(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: got status %d, want 200", rec.Code)
	}
	got := decodeBody[Book](t, rec)
	if got != created {
		t.Errorf("get: got %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	cases := []struct {
		name string
		body map[string]any
	}{
		{"missing title", map[string]any{"author": "Someone"}},
		{"missing author", map[string]any{"title": "Untitled"}},
		{"blank title", map[string]any{"title": "   ", "author": "Someone"}},
		{"negative year", map[string]any{"title": "T", "author": "A", "year": -5}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := doJSON(t, srv, http.MethodPost, "/books", tc.body)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("got status %d, want 400; body: %s", rec.Code, rec.Body)
			}
		})
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	for _, b := range []map[string]any{
		{"title": "Book One", "author": "Alice"},
		{"title": "Book Two", "author": "Bob"},
		{"title": "Book Three", "author": "Alice"},
	} {
		if rec := doJSON(t, srv, http.MethodPost, "/books", b); rec.Code != http.StatusCreated {
			t.Fatalf("seed create failed: %d %s", rec.Code, rec.Body)
		}
	}

	rec := doJSON(t, srv, http.MethodGet, "/books", nil)
	if all := decodeBody[[]Book](t, rec); len(all) != 3 {
		t.Errorf("list all: got %d books, want 3", len(all))
	}

	rec = doJSON(t, srv, http.MethodGet, "/books?author=Alice", nil)
	filtered := decodeBody[[]Book](t, rec)
	if len(filtered) != 2 {
		t.Fatalf("filtered list: got %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Errorf("filtered list contains wrong author: %+v", b)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	doJSON(t, srv, http.MethodPost, "/books", map[string]any{"title": "Old Title", "author": "Alice"})

	rec := doJSON(t, srv, http.MethodPut, "/books/1", map[string]any{
		"title": "New Title", "author": "Alice", "year": 2020,
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: got status %d, want 200; body: %s", rec.Code, rec.Body)
	}
	updated := decodeBody[Book](t, rec)
	if updated.Title != "New Title" || updated.Year != 2020 {
		t.Errorf("update: got %+v", updated)
	}

	rec = doJSON(t, srv, http.MethodPut, "/books/999", map[string]any{"title": "X", "author": "Y"})
	if rec.Code != http.StatusNotFound {
		t.Errorf("update missing: got status %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	doJSON(t, srv, http.MethodPost, "/books", map[string]any{"title": "Doomed", "author": "Alice"})

	rec := doJSON(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: got status %d, want 204", rec.Code)
	}

	rec = doJSON(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("get after delete: got status %d, want 404", rec.Code)
	}

	rec = doJSON(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("double delete: got status %d, want 404", rec.Code)
	}
}

func TestGetInvalidID(t *testing.T) {
	srv := newTestServer(t)
	rec := doJSON(t, srv, http.MethodGet, "/books/abc", nil)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("got status %d, want 400", rec.Code)
	}
}
