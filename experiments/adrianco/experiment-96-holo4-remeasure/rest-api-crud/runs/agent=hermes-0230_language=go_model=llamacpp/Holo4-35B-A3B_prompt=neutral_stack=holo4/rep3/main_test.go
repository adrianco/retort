package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// TestCreateBook verifies POST /books creates a book and validates required fields.
func TestCreateBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	handler := booksHandler(db)

	// Valid book.
	body := bytes.NewBufferString(`{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}`)
	req := httptest.NewRequestWithContext(context.Background(), http.MethodPost, "/books", body)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Errorf("create book status = %d, want %d", w.Code, http.StatusCreated)
	}

	var book Book
	if err := json.Unmarshal(w.Body.Bytes(), &book); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	if book.Title != "The Go Programming Language" || book.ID == 0 {
		t.Errorf("unexpected book: %+v", book)
	}

	// Missing title should fail.
	body = bytes.NewBufferString(`{"author":"Someone","year":2020,"isbn":"000"}`)
	req = httptest.NewRequestWithContext(context.Background(), http.MethodPost, "/books", body)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusBadRequest {
		t.Errorf("missing title status = %d, want %d", w.Code, http.StatusBadRequest)
	}
}

// TestListBooks verifies GET /books and the author filter.
func TestListBooks(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	handler := booksHandler(db)

	// Seed data.
	db.CreateBook("Book A", "Author X", 2020, "isbn-a")
	db.CreateBook("Book B", "Author Y", 2021, "isbn-b")
	db.CreateBook("Book C", "Author X", 2022, "isbn-c")

	req := httptest.NewRequestWithContext(context.Background(), http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("list books status = %d", w.Code)
	}
	var books []Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(books) != 3 {
		t.Errorf("got %d books, want 3", len(books))
	}

	// Filter by author.
	req = httptest.NewRequestWithContext(context.Background(), http.MethodGet, "/books?author=Author+X", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("filter status = %d", w.Code)
	}
	var filtered []Book
	if err := json.Unmarshal(w.Body.Bytes(), &filtered); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if len(filtered) != 2 {
		t.Errorf("filtered got %d books, want 2", len(filtered))
	}
}

// TestGetBook verifies GET /books/{id} and 404 for missing book.
func TestGetBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	handler := booksHandler(db)
	db.CreateBook("Test Book", "Test Author", 2023, "isbn-test")

	req := httptest.NewRequestWithContext(context.Background(), http.MethodGet, "/books/1", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("get book status = %d", w.Code)
	}
	var book Book
	if err := json.Unmarshal(w.Body.Bytes(), &book); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if book.Title != "Test Book" {
		t.Errorf("title = %q, want %q", book.Title, "Test Book")
	}

	// Non-existent book should 404.
	req = httptest.NewRequestWithContext(context.Background(), http.MethodGet, "/books/999", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Errorf("missing book status = %d, want %d", w.Code, http.StatusNotFound)
	}
}

// TestUpdateBook verifies PUT /books/{id}.
func TestUpdateBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	handler := booksHandler(db)
	db.CreateBook("Old Title", "Old Author", 2020, "isbn-upd")

	body := bytes.NewBufferString(`{"title":"New Title","author":"New Author","year":2024,"isbn":"isbn-upd"}`)
	req := httptest.NewRequestWithContext(context.Background(), http.MethodPut, "/books/1", body)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusOK {
		t.Fatalf("update status = %d", w.Code)
	}
	var book Book
	if err := json.Unmarshal(w.Body.Bytes(), &book); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	if book.Title != "New Title" || book.Author != "New Author" {
		t.Errorf("unexpected book: %+v", book)
	}
}

// TestDeleteBook verifies DELETE /books/{id}.
func TestDeleteBook(t *testing.T) {
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	defer db.Close()

	handler := booksHandler(db)
	db.CreateBook("ToDelete", "Author", 2020, "isbn-del")

	req := httptest.NewRequestWithContext(context.Background(), http.MethodDelete, "/books/1", nil)
	w := httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", w.Code)
	}

	// Should now 404.
	req = httptest.NewRequestWithContext(context.Background(), http.MethodGet, "/books/1", nil)
	w = httptest.NewRecorder()
	handler.ServeHTTP(w, req)
	if w.Code != http.StatusNotFound {
		t.Errorf("after delete status = %d, want %d", w.Code, http.StatusNotFound)
	}
}
