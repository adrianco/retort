package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestServer spins up an in-memory backed server for testing.
func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
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

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, http.MethodPost, "/books", BookInput{
		Title: "The Go Programming Language", Author: "Donovan", Year: 2015, ISBN: "9780134190440",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want 201 (body: %s)", rec.Code, rec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal created: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("created book has no ID")
	}

	rec = do(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200", rec.Code)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal got: %v", err)
	}
	if got.Title != "The Go Programming Language" || got.Author != "Donovan" {
		t.Fatalf("unexpected book: %+v", got)
	}
}

func TestCreateBookValidation(t *testing.T) {
	h := newTestServer(t)

	// Missing title and author.
	rec := do(t, h, http.MethodPost, "/books", BookInput{Year: 2020})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
	var resp struct {
		Errors []string `json:"errors"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(resp.Errors) != 2 {
		t.Fatalf("errors = %v, want 2", resp.Errors)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)
	do(t, h, http.MethodPost, "/books", BookInput{Title: "A", Author: "Alice"})
	do(t, h, http.MethodPost, "/books", BookInput{Title: "B", Author: "Bob"})
	do(t, h, http.MethodPost, "/books", BookInput{Title: "C", Author: "Alice"})

	rec := do(t, h, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	var books []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &books); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("got %d books, want 2", len(books))
	}
	for _, b := range books {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author %q in filtered list", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)
	do(t, h, http.MethodPost, "/books", BookInput{Title: "Old", Author: "Auth"})

	rec := do(t, h, http.MethodPut, "/books/1", BookInput{Title: "New", Author: "Auth", Year: 2021})
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, want 200 (body: %s)", rec.Code, rec.Body.String())
	}
	var got Book
	json.Unmarshal(rec.Body.Bytes(), &got)
	if got.Title != "New" || got.Year != 2021 {
		t.Fatalf("update not applied: %+v", got)
	}

	// Updating a missing book returns 404.
	rec = do(t, h, http.MethodPut, "/books/999", BookInput{Title: "X", Author: "Y"})
	if rec.Code != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)
	do(t, h, http.MethodPost, "/books", BookInput{Title: "Doomed", Author: "Auth"})

	rec := do(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", rec.Code)
	}

	rec = do(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", rec.Code)
	}

	// Deleting again returns 404.
	rec = do(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("re-delete status = %d, want 404", rec.Code)
	}
}

func TestGetInvalidID(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/books/abc", nil)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
}
