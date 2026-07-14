package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func setupTestServer(t *testing.T) http.Handler {
	t.Helper()
	db, err := initDB(":memory:")
	if err != nil {
		t.Fatalf("initDB: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	return newMux(db)
}

func TestHealth(t *testing.T) {
	mux := setupTestServer(t)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var body map[string]string
	json.NewDecoder(rec.Body).Decode(&body)
	if body["status"] != "ok" {
		t.Fatalf("expected status ok, got %q", body["status"])
	}
}

func TestCreateAndGetBook(t *testing.T) {
	mux := setupTestServer(t)

	// Create
	payload := `{"title":"The Go Programming Language","author":"Donovan","year":2015,"isbn":"978-0134190440"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", rec.Code, rec.Body.String())
	}
	var created Book
	json.NewDecoder(rec.Body).Decode(&created)
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected title %q", created.Title)
	}

	// Get by ID
	req2 := httptest.NewRequest(http.MethodGet, "/books/1", nil)
	rec2 := httptest.NewRecorder()
	mux.ServeHTTP(rec2, req2)

	if rec2.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec2.Code)
	}
	var fetched Book
	json.NewDecoder(rec2.Body).Decode(&fetched)
	if fetched.ID != created.ID || fetched.Title != created.Title {
		t.Fatalf("fetched book mismatch: %+v", fetched)
	}
}

func TestCreateBook_ValidationError(t *testing.T) {
	mux := setupTestServer(t)

	// Missing author
	payload := `{"title":"Orphan Title"}`
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec.Code)
	}

	// Missing title
	payload2 := `{"author":"Some Author"}`
	req2 := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(payload2))
	req2.Header.Set("Content-Type", "application/json")
	rec2 := httptest.NewRecorder()
	mux.ServeHTTP(rec2, req2)

	if rec2.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", rec2.Code)
	}
}

func TestListBooks_AuthorFilter(t *testing.T) {
	mux := setupTestServer(t)

	for _, p := range []string{
		`{"title":"Book A","author":"Alice"}`,
		`{"title":"Book B","author":"Bob"}`,
		`{"title":"Book C","author":"Alice"}`,
	} {
		req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(p))
		req.Header.Set("Content-Type", "application/json")
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
		if rec.Code != http.StatusCreated {
			t.Fatalf("create failed: %d", rec.Code)
		}
	}

	// List all
	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	var all []Book
	json.NewDecoder(rec.Body).Decode(&all)
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	// Filter by author
	req2 := httptest.NewRequest(http.MethodGet, "/books?author=Alice", nil)
	rec2 := httptest.NewRecorder()
	mux.ServeHTTP(rec2, req2)
	var filtered []Book
	json.NewDecoder(rec2.Body).Decode(&filtered)
	if len(filtered) != 2 {
		t.Fatalf("expected 2 Alice books, got %d", len(filtered))
	}
}

func TestUpdateBook(t *testing.T) {
	mux := setupTestServer(t)

	// Create
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(`{"title":"Old Title","author":"Author"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	var created Book
	json.NewDecoder(rec.Body).Decode(&created)

	// Update
	update := `{"title":"New Title","author":"Author","year":2024}`
	req2 := httptest.NewRequest(http.MethodPut, "/books/1", bytes.NewBufferString(update))
	req2.Header.Set("Content-Type", "application/json")
	rec2 := httptest.NewRecorder()
	mux.ServeHTTP(rec2, req2)

	if rec2.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rec2.Code, rec2.Body.String())
	}
	var updated Book
	json.NewDecoder(rec2.Body).Decode(&updated)
	if updated.Title != "New Title" {
		t.Fatalf("expected updated title, got %q", updated.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	mux := setupTestServer(t)

	// Create
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBufferString(`{"title":"To Delete","author":"Author"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	// Delete
	req2 := httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	rec2 := httptest.NewRecorder()
	mux.ServeHTTP(rec2, req2)

	if rec2.Code != http.StatusNoContent {
		t.Fatalf("expected 204, got %d", rec2.Code)
	}

	// Confirm gone
	req3 := httptest.NewRequest(http.MethodGet, "/books/1", nil)
	rec3 := httptest.NewRecorder()
	mux.ServeHTTP(rec3, req3)
	if rec3.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", rec3.Code)
	}
}

func TestGetBook_NotFound(t *testing.T) {
	mux := setupTestServer(t)
	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}
