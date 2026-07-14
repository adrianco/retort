package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

// newTestServer builds a Server backed by a fresh in-memory database.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := NewStore(":memory:")
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
	srv.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	var got map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got["status"] != "ok" {
		t.Fatalf("status field = %q, want ok", got["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	rec := doRequest(t, srv, http.MethodPost, "/books", bookInput{
		Title: "The Go Programming Language", Author: "Donovan", Year: 2015, ISBN: "9780134190440",
	})
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want 201, body=%s", rec.Code, rec.Body)
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("expected non-zero ID")
	}

	rec = doRequest(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200", rec.Code)
	}
	var got Book
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if got.Title != "The Go Programming Language" || got.Author != "Donovan" {
		t.Fatalf("got %+v, fields mismatch", got)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodPost, "/books", bookInput{Year: 2020})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
	var resp map[string][]string
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(resp["errors"]) != 2 {
		t.Fatalf("expected 2 validation errors, got %v", resp["errors"])
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	srv := newTestServer(t)
	doRequest(t, srv, http.MethodPost, "/books", bookInput{Title: "A", Author: "Alice"})
	doRequest(t, srv, http.MethodPost, "/books", bookInput{Title: "B", Author: "Bob"})
	doRequest(t, srv, http.MethodPost, "/books", bookInput{Title: "C", Author: "Alice"})

	rec := doRequest(t, srv, http.MethodGet, "/books?author=Alice", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	var books []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &books); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("expected 2 books by Alice, got %d", len(books))
	}
}

func TestUpdateAndDelete(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodPost, "/books", bookInput{Title: "Old", Author: "Auth"})
	var created Book
	json.Unmarshal(rec.Body.Bytes(), &created)

	rec = doRequest(t, srv, http.MethodPut, "/books/"+itoa(created.ID), bookInput{Title: "New", Author: "Auth", Year: 2021})
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, want 200", rec.Code)
	}
	var updated Book
	json.Unmarshal(rec.Body.Bytes(), &updated)
	if updated.Title != "New" || updated.Year != 2021 {
		t.Fatalf("update did not apply: %+v", updated)
	}

	rec = doRequest(t, srv, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", rec.Code)
	}

	rec = doRequest(t, srv, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", rec.Code)
	}
}

func TestGetMissingBook(t *testing.T) {
	srv := newTestServer(t)
	rec := doRequest(t, srv, http.MethodGet, "/books/9999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
