package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestServer spins up an in-memory store and HTTP handler for testing.
func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

// do performs a request against the handler and returns the recorder.
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
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusOK)
	}
	var resp map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if resp["status"] != "ok" {
		t.Fatalf("status field = %q, want ok", resp["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestServer(t)

	in := BookInput{Title: "The Go Programming Language", Author: "Donovan", Year: 2015, ISBN: "9780134190440"}
	rec := do(t, h, http.MethodPost, "/books", in)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want %d (body=%s)", rec.Code, http.StatusCreated, rec.Body)
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 || created.Title != in.Title {
		t.Fatalf("unexpected created book: %+v", created)
	}

	rec = do(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want %d", rec.Code, http.StatusOK)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode got: %v", err)
	}
	if got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestServer(t)

	// Missing title.
	rec := do(t, h, http.MethodPost, "/books", BookInput{Author: "Nobody"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("missing title status = %d, want %d", rec.Code, http.StatusBadRequest)
	}

	// Missing author.
	rec = do(t, h, http.MethodPost, "/books", BookInput{Title: "Untitled"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("missing author status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)

	books := []BookInput{
		{Title: "A", Author: "Alice"},
		{Title: "B", Author: "Bob"},
		{Title: "C", Author: "Alice"},
	}
	for _, b := range books {
		if rec := do(t, h, http.MethodPost, "/books", b); rec.Code != http.StatusCreated {
			t.Fatalf("seed create failed: %d", rec.Code)
		}
	}

	rec := do(t, h, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("list status = %d, want %d", rec.Code, http.StatusOK)
	}
	var got []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("filtered list len = %d, want 2", len(got))
	}
	for _, b := range got {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author in filtered list: %q", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)

	do(t, h, http.MethodPost, "/books", BookInput{Title: "Old", Author: "Author"})

	upd := BookInput{Title: "New", Author: "Author", Year: 2020, ISBN: "123"}
	rec := do(t, h, http.MethodPut, "/books/1", upd)
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, want %d", rec.Code, http.StatusOK)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got.Title != "New" || got.Year != 2020 {
		t.Fatalf("update not applied: %+v", got)
	}

	// Updating a missing book returns 404.
	rec = do(t, h, http.MethodPut, "/books/999", upd)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)

	do(t, h, http.MethodPost, "/books", BookInput{Title: "Temp", Author: "Author"})

	rec := do(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want %d", rec.Code, http.StatusNoContent)
	}

	rec = do(t, h, http.MethodGet, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want %d", rec.Code, http.StatusNotFound)
	}

	// Deleting again returns 404.
	rec = do(t, h, http.MethodDelete, "/books/1", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("delete missing status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}

func TestGetNotFound(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/books/42", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusNotFound)
	}
}
