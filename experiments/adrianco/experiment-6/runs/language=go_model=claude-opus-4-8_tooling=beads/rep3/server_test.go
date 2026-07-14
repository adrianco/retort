package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

// newTestServer spins up a Server backed by a fresh in-memory database.
func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("new store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store).Routes()
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, path, nil)
	} else {
		r = httptest.NewRequest(method, path, strings.NewReader(body))
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, r)
	return rec
}

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/health", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", rec.Code)
	}
	var got map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got["status"] != "ok" {
		t.Fatalf("status field = %q, want ok", got["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestServer(t)

	rec := do(t, h, http.MethodPost, "/books",
		`{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want 201 (body: %s)", rec.Code, rec.Body)
	}
	var created Book
	if err := json.Unmarshal(rec.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero ID on created book")
	}
	if created.Title != "The Go Programming Language" {
		t.Fatalf("title = %q", created.Title)
	}

	// Fetch it back.
	rec = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")
	if rec.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200", rec.Code)
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

	// Missing author.
	rec := do(t, h, http.MethodPost, "/books", `{"title":"No Author"}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
	// Missing title.
	rec = do(t, h, http.MethodPost, "/books", `{"author":"Someone"}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
	// Malformed JSON.
	rec = do(t, h, http.MethodPost, "/books", `{not json`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", rec.Code)
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)

	mustCreate(t, h, `{"title":"Book A","author":"Alice"}`)
	mustCreate(t, h, `{"title":"Book B","author":"Bob"}`)
	mustCreate(t, h, `{"title":"Book C","author":"Alice"}`)

	// No filter -> all 3.
	rec := do(t, h, http.MethodGet, "/books", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("list status = %d", rec.Code)
	}
	var all []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &all); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(all) != 3 {
		t.Fatalf("len(all) = %d, want 3", len(all))
	}

	// Filter by Alice -> 2.
	rec = do(t, h, http.MethodGet, "/books?author=Alice", "")
	var alice []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &alice); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(alice) != 2 {
		t.Fatalf("len(alice) = %d, want 2", len(alice))
	}
	for _, b := range alice {
		if b.Author != "Alice" {
			t.Fatalf("unexpected author %q in filtered result", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestServer(t)
	id := mustCreate(t, h, `{"title":"Old Title","author":"Author","year":2000}`)

	rec := do(t, h, http.MethodPut, "/books/"+itoa(id),
		`{"title":"New Title","author":"Author","year":2024,"isbn":"123"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("update status = %d, want 200 (body: %s)", rec.Code, rec.Body)
	}
	var updated Book
	if err := json.Unmarshal(rec.Body.Bytes(), &updated); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if updated.Title != "New Title" || updated.Year != 2024 || updated.ID != id {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	// Updating a non-existent book -> 404.
	rec = do(t, h, http.MethodPut, "/books/99999",
		`{"title":"X","author":"Y"}`)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("update missing status = %d, want 404", rec.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	h := newTestServer(t)
	id := mustCreate(t, h, `{"title":"Doomed","author":"Author"}`)

	rec := do(t, h, http.MethodDelete, "/books/"+itoa(id), "")
	if rec.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", rec.Code)
	}

	// Now gone.
	rec = do(t, h, http.MethodGet, "/books/"+itoa(id), "")
	if rec.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", rec.Code)
	}

	// Deleting again -> 404.
	rec = do(t, h, http.MethodDelete, "/books/"+itoa(id), "")
	if rec.Code != http.StatusNotFound {
		t.Fatalf("delete missing status = %d, want 404", rec.Code)
	}
}

func TestGetNotFound(t *testing.T) {
	h := newTestServer(t)
	rec := do(t, h, http.MethodGet, "/books/12345", "")
	if rec.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", rec.Code)
	}
}

// --- test helpers ---

func mustCreate(t *testing.T, h http.Handler, body string) int64 {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	if rec.Code != http.StatusCreated {
		t.Fatalf("mustCreate status = %d (body: %s)", rec.Code, rec.Body)
	}
	var b Book
	if err := json.Unmarshal(rec.Body.Bytes(), &b); err != nil {
		t.Fatalf("mustCreate decode: %v", err)
	}
	return b.ID
}

func itoa(id int64) string {
	var buf bytes.Buffer
	json.NewEncoder(&buf).Encode(id)
	return strings.TrimSpace(buf.String())
}
