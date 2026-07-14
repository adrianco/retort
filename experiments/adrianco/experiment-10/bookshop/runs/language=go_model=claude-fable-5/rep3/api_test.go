package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func doRequest(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
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

func decodeBookResp(t *testing.T, rec *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.NewDecoder(rec.Body).Decode(&b); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	return b
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("got status %d, want 200", rec.Code)
	}
	if !strings.Contains(rec.Body.String(), "ok") {
		t.Errorf("body = %q, want it to contain %q", rec.Body.String(), "ok")
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	rec := doRequest(t, srv, http.MethodPost, "/books", Book{
		Title: "Sun Performance and Tuning", Author: "Adrian Cockcroft", Year: 1998, ISBN: "978-0130952493",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: got status %d, want 201; body: %s", rec.Code, rec.Body)
	}
	created := decodeBookResp(t, rec)
	if created.ID == 0 {
		t.Fatal("create: expected non-zero ID")
	}

	rec = doRequest(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: got status %d, want 200; body: %s", rec.Code, rec.Body)
	}
	got := decodeBookResp(t, rec)
	if got != created {
		t.Errorf("get = %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)

	cases := []struct {
		name string
		body any
	}{
		{"missing title", Book{Author: "Someone"}},
		{"missing author", Book{Title: "Untitled"}},
		{"whitespace title", Book{Title: "   ", Author: "Someone"}},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := doRequest(t, srv, http.MethodPost, "/books", tc.body)
			if rec.Code != http.StatusBadRequest {
				t.Errorf("got status %d, want 400; body: %s", rec.Code, rec.Body)
			}
		})
	}

	// Malformed JSON.
	req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader("{not json"))
	rec := httptest.NewRecorder()
	srv.ServeHTTP(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("malformed JSON: got status %d, want 400", rec.Code)
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	for _, b := range []Book{
		{Title: "Book One", Author: "Alice", Year: 2001},
		{Title: "Book Two", Author: "Bob", Year: 2002},
		{Title: "Book Three", Author: "Alice", Year: 2003},
	} {
		if rec := doRequest(t, srv, http.MethodPost, "/books", b); rec.Code != http.StatusCreated {
			t.Fatalf("seed create failed: %d %s", rec.Code, rec.Body)
		}
	}

	rec := doRequest(t, srv, http.MethodGet, "/books", nil)
	var all []Book
	if err := json.NewDecoder(rec.Body).Decode(&all); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(all) != 3 {
		t.Errorf("list all: got %d books, want 3", len(all))
	}

	rec = doRequest(t, srv, http.MethodGet, "/books?author=Alice", nil)
	var filtered []Book
	if err := json.NewDecoder(rec.Body).Decode(&filtered); err != nil {
		t.Fatalf("decode filtered list: %v", err)
	}
	if len(filtered) != 2 {
		t.Fatalf("filtered list: got %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Errorf("filtered list contains author %q, want only Alice", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)

	rec := doRequest(t, srv, http.MethodPost, "/books", Book{Title: "Old Title", Author: "Author"})
	created := decodeBookResp(t, rec)

	rec = doRequest(t, srv, http.MethodPut, "/books/1", Book{Title: "New Title", Author: "Author", Year: 2020})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: got status %d, want 200; body: %s", rec.Code, rec.Body)
	}
	updated := decodeBookResp(t, rec)
	if updated.Title != "New Title" || updated.Year != 2020 || updated.ID != created.ID {
		t.Errorf("update = %+v, want title=New Title year=2020 id=%d", updated, created.ID)
	}

	// Updating a missing book returns 404.
	rec = doRequest(t, srv, http.MethodPut, "/books/999", Book{Title: "X", Author: "Y"})
	if rec.Code != http.StatusNotFound {
		t.Errorf("update missing: got status %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)

	doRequest(t, srv, http.MethodPost, "/books", Book{Title: "Doomed", Author: "Author"})

	rec := doRequest(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: got status %d, want 204", rec.Code)
	}

	rec = doRequest(t, srv, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("get after delete: got status %d, want 404", rec.Code)
	}

	rec = doRequest(t, srv, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Errorf("double delete: got status %d, want 404", rec.Code)
	}
}

func TestInvalidID(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodGet, "/books/abc", nil)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("got status %d, want 400", rec.Code)
	}
}
