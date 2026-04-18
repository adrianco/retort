package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func newTestApp(t *testing.T) *App {
	t.Helper()
	app, err := NewApp(":memory:")
	if err != nil {
		t.Fatalf("failed to create test app: %v", err)
	}
	t.Cleanup(func() { app.Close() })
	return app
}

func do(t *testing.T, app *App, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatalf("encode body: %v", err)
		}
	}
	req := httptest.NewRequest(method, path, &buf)
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()
	app.ServeHTTP(rr, req)
	return rr
}

func decodeBook(t *testing.T, rr *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.NewDecoder(rr.Body).Decode(&b); err != nil {
		t.Fatalf("decode book: %v", err)
	}
	return b
}

func decodeBooks(t *testing.T, rr *httptest.ResponseRecorder) []Book {
	t.Helper()
	var books []Book
	if err := json.NewDecoder(rr.Body).Decode(&books); err != nil {
		t.Fatalf("decode books: %v", err)
	}
	return books
}

func TestHealth(t *testing.T) {
	app := newTestApp(t)
	rr := do(t, app, http.MethodGet, "/health", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	app := newTestApp(t)

	rr := do(t, app, http.MethodPost, "/books", map[string]any{
		"title":  "The Go Programming Language",
		"author": "Donovan & Kernighan",
		"year":   2015,
		"isbn":   "978-0134190440",
	})
	if rr.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", rr.Code, rr.Body)
	}
	created := decodeBook(t, rr)
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "The Go Programming Language" {
		t.Fatalf("unexpected title: %s", created.Title)
	}

	rr2 := do(t, app, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rr2.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr2.Code)
	}
	fetched := decodeBook(t, rr2)
	if fetched.ID != created.ID {
		t.Fatalf("ID mismatch: %d vs %d", fetched.ID, created.ID)
	}
}

func TestCreateBookValidation(t *testing.T) {
	app := newTestApp(t)

	// Missing title
	rr := do(t, app, http.MethodPost, "/books", map[string]any{"author": "Someone"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing title, got %d", rr.Code)
	}

	// Missing author
	rr = do(t, app, http.MethodPost, "/books", map[string]any{"title": "Something"})
	if rr.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing author, got %d", rr.Code)
	}
}

func TestListAndFilterBooks(t *testing.T) {
	app := newTestApp(t)

	do(t, app, http.MethodPost, "/books", map[string]any{"title": "Book A", "author": "Alice"})
	do(t, app, http.MethodPost, "/books", map[string]any{"title": "Book B", "author": "Bob"})
	do(t, app, http.MethodPost, "/books", map[string]any{"title": "Book C", "author": "Alice"})

	// List all
	rr := do(t, app, http.MethodGet, "/books", nil)
	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}
	all := decodeBooks(t, rr)
	if len(all) != 3 {
		t.Fatalf("expected 3 books, got %d", len(all))
	}

	// Filter by author
	rr2 := do(t, app, http.MethodGet, "/books?author=Alice", nil)
	if rr2.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr2.Code)
	}
	filtered := decodeBooks(t, rr2)
	if len(filtered) != 2 {
		t.Fatalf("expected 2 books for Alice, got %d", len(filtered))
	}
}

func TestUpdateBook(t *testing.T) {
	app := newTestApp(t)

	rr := do(t, app, http.MethodPost, "/books", map[string]any{"title": "Old Title", "author": "Author"})
	created := decodeBook(t, rr)

	rr2 := do(t, app, http.MethodPut, "/books/"+itoa(created.ID), map[string]any{
		"title":  "New Title",
		"author": "New Author",
		"year":   2024,
	})
	if rr2.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", rr2.Code, rr2.Body)
	}
	updated := decodeBook(t, rr2)
	if updated.Title != "New Title" {
		t.Fatalf("expected updated title, got %s", updated.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	app := newTestApp(t)

	rr := do(t, app, http.MethodPost, "/books", map[string]any{"title": "To Delete", "author": "Author"})
	created := decodeBook(t, rr)

	rr2 := do(t, app, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if rr2.Code != http.StatusNoContent {
		t.Fatalf("expected 204, got %d", rr2.Code)
	}

	// Confirm gone
	rr3 := do(t, app, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if rr3.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", rr3.Code)
	}
}

func TestNotFound(t *testing.T) {
	app := newTestApp(t)
	rr := do(t, app, http.MethodGet, "/books/9999", nil)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rr.Code)
	}
}

func itoa(n int) string {
	return strconv.Itoa(n)
}
