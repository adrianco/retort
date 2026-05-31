package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
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

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestCreateAndGet(t *testing.T) {
	h := newTestServer(t)

	rec := doRequest(t, h, http.MethodPost, "/books", bookInput{
		Title:  "The Go Programming Language",
		Author: "Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: expected 201, got %d (%s)", rec.Code, rec.Body)
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected title: %q", created.Title)
	}

	rec = doRequest(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get: expected 200, got %d", rec.Code)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode get: %v", err)
	}
	if got.ID != created.ID || got.Author != "Donovan" {
		t.Fatalf("mismatch: %+v vs %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestServer(t)

	// Missing author.
	rec := doRequest(t, h, http.MethodPost, "/books", bookInput{Title: "No Author"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing author, got %d", rec.Code)
	}

	// Missing title (whitespace only).
	rec = doRequest(t, h, http.MethodPost, "/books", bookInput{Title: "   ", Author: "Someone"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for blank title, got %d", rec.Code)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)

	doRequest(t, h, http.MethodPost, "/books", bookInput{Title: "A", Author: "Alice"})
	doRequest(t, h, http.MethodPost, "/books", bookInput{Title: "B", Author: "Bob"})
	doRequest(t, h, http.MethodPost, "/books", bookInput{Title: "C", Author: "Alice"})

	rec := doRequest(t, h, http.MethodGet, "/books", nil)
	var all []Book
	json.Unmarshal(rec.Body.Bytes(), &all)
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	rec = doRequest(t, h, http.MethodGet, "/books?author=Alice", nil)
	var filtered []Book
	json.Unmarshal(rec.Body.Bytes(), &filtered)
	if len(filtered) != 2 {
		t.Fatalf("expected 2 books by Alice, got %d", len(filtered))
	}
}

func TestUpdate(t *testing.T) {
	h := newTestServer(t)
	doRequest(t, h, http.MethodPost, "/books", bookInput{Title: "Old", Author: "Author"})

	rec := doRequest(t, h, http.MethodPut, "/books/1", bookInput{
		Title: "New Title", Author: "Author", Year: 2020, ISBN: "123",
	})
	if rec.Code != http.StatusOK {
		t.Fatalf("update: expected 200, got %d (%s)", rec.Code, rec.Body)
	}
	var updated Book
	json.Unmarshal(rec.Body.Bytes(), &updated)
	if updated.Title != "New Title" || updated.Year != 2020 {
		t.Fatalf("update not applied: %+v", updated)
	}

	// Updating a missing book yields 404.
	rec = doRequest(t, h, http.MethodPut, "/books/999", bookInput{Title: "X", Author: "Y"})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}

func TestDelete(t *testing.T) {
	h := newTestServer(t)
	doRequest(t, h, http.MethodPost, "/books", bookInput{Title: "Doomed", Author: "Author"})

	rec := doRequest(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete: expected 204, got %d", rec.Code)
	}

	rec = doRequest(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", rec.Code)
	}

	// Deleting again yields 404.
	rec = doRequest(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 on second delete, got %d", rec.Code)
	}
}

func TestGetNotFound(t *testing.T) {
	h := newTestServer(t)
	rec := doRequest(t, h, http.MethodGet, "/books/42", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}
