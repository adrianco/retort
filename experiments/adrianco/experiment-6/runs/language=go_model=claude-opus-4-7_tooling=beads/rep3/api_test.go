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
	dsn := filepath.Join(t.TempDir(), "test.db")
	store, err := OpenStore(dsn)
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func doJSON(t *testing.T, srv *Server, method, target string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, target, &buf)
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	srv.ServeHTTP(rr, req)
	return rr
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rr := doJSON(t, srv, http.MethodGet, "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rr.Code)
	}
	var got map[string]string
	if err := json.Unmarshal(rr.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got["status"] != "ok" {
		t.Fatalf("status = %q, want %q", got["status"], "ok")
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv := newTestServer(t)

	// Missing title
	rr := doJSON(t, srv, http.MethodPost, "/books", map[string]any{"author": "Dan"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("missing title status = %d, want 400", rr.Code)
	}

	// Missing author
	rr = doJSON(t, srv, http.MethodPost, "/books", map[string]any{"title": "Some Title"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("missing author status = %d, want 400", rr.Code)
	}

	// Whitespace-only title
	rr = doJSON(t, srv, http.MethodPost, "/books", map[string]any{"title": "   ", "author": "Dan"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("blank title status = %d, want 400", rr.Code)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)
	rr := doJSON(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "The Pragmatic Programmer", "author": "Hunt", "year": 1999, "isbn": "978-0201616224",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want 201: %s", rr.Code, rr.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rr.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("created.ID = 0, want assigned")
	}

	rr = doJSON(t, srv, http.MethodGet, "/books/"+strconv.FormatInt(created.ID, 10), nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200", rr.Code)
	}
	var got Book
	if err := json.Unmarshal(rr.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got != created {
		t.Fatalf("get = %+v, want %+v", got, created)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	books := []Book{
		{Title: "Book A", Author: "Alice", Year: 2001},
		{Title: "Book B", Author: "Bob", Year: 2002},
		{Title: "Book C", Author: "Alice", Year: 2003},
	}
	for _, b := range books {
		rr := doJSON(t, srv, http.MethodPost, "/books", b)
		if rr.Code != http.StatusCreated {
			t.Fatalf("seed status = %d", rr.Code)
		}
	}

	rr := doJSON(t, srv, http.MethodGet, "/books", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("list status = %d", rr.Code)
	}
	var all []Book
	if err := json.Unmarshal(rr.Body.Bytes(), &all); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	rr = doJSON(t, srv, http.MethodGet, "/books?author=Alice", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("filter status = %d", rr.Code)
	}
	var filtered []Book
	if err := json.Unmarshal(rr.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("len(filtered) = %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("got author = %q, want Alice", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	rr := doJSON(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "Original", "author": "Author",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create status = %d", rr.Code)
	}
	var b Book
	if err := json.Unmarshal(rr.Body.Bytes(), &b); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	rr = doJSON(t, srv, http.MethodPut, "/books/"+strconv.FormatInt(b.ID, 10), map[string]any{
		"title": "Updated", "author": "Author", "year": 2026, "isbn": "abc",
	})
	if rr.Code != http.StatusOK {
		t.Fatalf("put status = %d: %s", rr.Code, rr.Body.String())
	}
	var got Book
	if err := json.Unmarshal(rr.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got.Title != "Updated" || got.Year != 2026 || got.ISBN != "abc" {
		t.Fatalf("update result = %+v", got)
	}

	// Update non-existent
	rr = doJSON(t, srv, http.MethodPut, "/books/99999", map[string]any{
		"title": "x", "author": "y",
	})
	if rr.Code != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want 404", rr.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	rr := doJSON(t, srv, http.MethodPost, "/books", map[string]any{
		"title": "ToDelete", "author": "X",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("create status = %d", rr.Code)
	}
	var b Book
	if err := json.Unmarshal(rr.Body.Bytes(), &b); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}

	rr = doJSON(t, srv, http.MethodDelete, "/books/"+strconv.FormatInt(b.ID, 10), nil)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", rr.Code)
	}

	rr = doJSON(t, srv, http.MethodGet, "/books/"+strconv.FormatInt(b.ID, 10), nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("get-after-delete status = %d, want 404", rr.Code)
	}

	rr = doJSON(t, srv, http.MethodDelete, "/books/99999", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("delete missing status = %d, want 404", rr.Code)
	}
}

func TestGetNotFound(t *testing.T) {
	srv := newTestServer(t)
	rr := doJSON(t, srv, http.MethodGet, "/books/9999", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rr.Code)
	}
}
