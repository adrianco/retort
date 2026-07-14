package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func setupTestDB(t *testing.T) (*BookStore, string) {
	t.Helper()
	f, err := os.CreateTemp("", "books-*.db")
	if err != nil {
		t.Fatalf("failed to create temp db: %v", err)
	}
	f.Close()

	store, err := NewBookStore(f.Name())
	if err != nil {
		os.Remove(f.Name())
		t.Fatalf("failed to open test db: %v", err)
	}

	t.Cleanup(func() {
		store.Close()
		os.Remove(f.Name())
	})

	return store, f.Name()
}


func TestHealthCheck(t *testing.T) {
	store, _ := setupTestDB(t)
	api := NewAPI(store)

	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	api.HealthCheck(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}

	var resp map[string]string
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("expected status=ok, got %s", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	store, _ := setupTestDB(t)
	api := NewAPI(store)

	body := `{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}`
	req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	api.CreateBook(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected 201, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if book.Title != "The Go Programming Language" {
		t.Errorf("expected title 'The Go Programming Language', got '%s'", book.Title)
	}
	if book.Author != "Donovan & Kernighan" {
		t.Errorf("expected author 'Donovan & Kernighan', got '%s'", book.Author)
	}
	if book.Year != 2015 {
		t.Errorf("expected year 2015, got %d", book.Year)
	}
	if book.ID <= 0 {
		t.Errorf("expected positive ID, got %d", book.ID)
	}

	// Verify it was persisted in the DB
	dbBook, err := store.GetByID(book.ID)
	if err != nil {
		t.Fatalf("book not found in DB: %v", err)
	}
	if dbBook.Title != book.Title {
		t.Errorf("DB title mismatch: got '%s'", dbBook.Title)
	}
}

func TestCreateBookValidation(t *testing.T) {
	store, _ := setupTestDB(t)
	api := NewAPI(store)

	tests := []struct {
		name   string
		body   string
		expect int
	}{
		{"empty title", `{"title":"","author":"Someone","year":2020,"isbn":"111"}`, http.StatusBadRequest},
		{"empty author", `{"title":"Book","author":"","year":2020,"isbn":"111"}`, http.StatusBadRequest},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(tt.body))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			api.CreateBook(w, req)

			if w.Code != tt.expect {
				t.Errorf("expected %d, got %d (body: %s)", tt.expect, w.Code, w.Body.String())
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	store, _ := setupTestDB(t)
	api := NewAPI(store)

	// Insert two books by different authors
	store.Create(CreateBookRequest{Title: "Go Web", Author: "Alice", Year: 2021, ISBN: "isbn-1"})
	store.Create(CreateBookRequest{Title: "Go Systems", Author: "Bob", Year: 2022, ISBN: "isbn-2"})
	store.Create(CreateBookRequest{Title: "Go Concurrency", Author: "Alice", Year: 2023, ISBN: "isbn-3"})

	// List all
	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	api.ListBooks(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}

	var books []*Book
	json.NewDecoder(w.Body).Decode(&books)

	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}

	// Filter by author=Alice
	req = httptest.NewRequest("GET", "/books?author=Alice", nil)
	w = httptest.NewRecorder()
	api.ListBooks(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}

	var aliceBooks []*Book
	json.NewDecoder(w.Body).Decode(&aliceBooks)

	if len(aliceBooks) != 2 {
		t.Errorf("expected 2 Alice books, got %d", len(aliceBooks))
	}
}

func TestGetBook(t *testing.T) {
	store, _ := setupTestDB(t)
	api := NewAPI(store)

	book, err := store.Create(CreateBookRequest{Title: "Test Book", Author: "Author", Year: 2024, ISBN: "isbn-get"})
	if err != nil {
		t.Fatalf("failed to create test book: %v", err)
	}

	req := httptest.NewRequest("GET", "/books/1", nil)
	w := httptest.NewRecorder()
	api.GetBook(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}

	var resp Book
	json.NewDecoder(w.Body).Decode(&resp)

	if resp.ID != book.ID {
		t.Errorf("expected ID %d, got %d", book.ID, resp.ID)
	}
	if resp.Title != "Test Book" {
		t.Errorf("expected title 'Test Book', got '%s'", resp.Title)
	}

	// Test 404 for non-existent book
	req = httptest.NewRequest("GET", "/books/999", nil)
	w = httptest.NewRecorder()
	api.GetBook(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404 for non-existent book, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	store, _ := setupTestDB(t)
	api := NewAPI(store)

	book, err := store.Create(CreateBookRequest{Title: "Old Title", Author: "Old Author", Year: 2020, ISBN: "isbn-upd"})
	if err != nil {
		t.Fatalf("failed to create test book: %v", err)
	}

	newTitle := "New Title"
	body, _ := json.Marshal(UpdateBookRequest{Title: &newTitle})

	req := httptest.NewRequest("PUT", "/books/1", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	api.UpdateBook(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", w.Code)
	}

	var resp Book
	json.NewDecoder(w.Body).Decode(&resp)

	if resp.Title != "New Title" {
		t.Errorf("expected title 'New Title', got '%s'", resp.Title)
	}

	// Verify DB was updated
	dbBook, _ := store.GetByID(book.ID)
	if dbBook.Title != "New Title" {
		t.Errorf("DB title not updated: got '%s'", dbBook.Title)
	}

	// Test 404 for non-existent book
	req = httptest.NewRequest("PUT", "/books/999", bytes.NewBuffer(body))
	w = httptest.NewRecorder()
	api.UpdateBook(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404 for non-existent book, got %d", w.Code)
	}
}

func TestDeleteBook(t *testing.T) {
	store, _ := setupTestDB(t)
	api := NewAPI(store)

	_, err := store.Create(CreateBookRequest{Title: "To Delete", Author: "Author", Year: 2024, ISBN: "isbn-del"})
	if err != nil {
		t.Fatalf("failed to create test book: %v", err)
	}

	req := httptest.NewRequest("DELETE", "/books/1", nil)
	w := httptest.NewRecorder()

	api.DeleteBook(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("expected 204, got %d", w.Code)
	}

	// Verify it's gone
	req = httptest.NewRequest("GET", "/books/1", nil)
	w = httptest.NewRecorder()
	api.GetBook(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", w.Code)
	}

	// Test 404 for non-existent book - create a book first so IDs don't collide
	_, err = store.Create(CreateBookRequest{Title: "Placeholder", Author: "X", Year: 2024, ISBN: "placeholder"})
	if err != nil {
		t.Fatalf("failed to create placeholder: %v", err)
	}

	req = httptest.NewRequest("DELETE", "/books/999", nil)
	w = httptest.NewRecorder()
	api.DeleteBook(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404 for non-existent book, got %d", w.Code)
	}
}

func TestDuplicateISBN(t *testing.T) {
	store, _ := setupTestDB(t)
	api := NewAPI(store)

	store.Create(CreateBookRequest{Title: "Book 1", Author: "Author", Year: 2024, ISBN: "dup-isbn"})

	body := `{"title":"Book 2","author":"Author","year":2024,"isbn":"dup-isbn"}`
	req := httptest.NewRequest("POST", "/books", bytes.NewBufferString(body))
	w := httptest.NewRecorder()

	api.CreateBook(w, req)

	if w.Code != http.StatusConflict {
		t.Errorf("expected 409 for duplicate ISBN, got %d", w.Code)
	}
}

// TestStoreCRUD tests the BookStore layer directly.
func TestStoreCRUD(t *testing.T) {
	store, _ := setupTestDB(t)

	// Create
	book1, err := store.Create(CreateBookRequest{Title: "A", Author: "B", Year: 2020, ISBN: "a1"})
	if err != nil {
		t.Fatalf("create failed: %v", err)
	}

	// Read
	got, err := store.GetByID(book1.ID)
	if err != nil {
		t.Fatalf("get failed: %v", err)
	}
	if got.Title != "A" || got.Author != "B" {
		t.Errorf("got wrong book: %+v", got)
	}

	// Update
	newAuthor := "Updated"
	updated, err := store.Update(book1.ID, UpdateBookRequest{Author: &newAuthor})
	if err != nil {
		t.Fatalf("update failed: %v", err)
	}
	if updated.Author != "Updated" {
		t.Errorf("update didn't change author")
	}

	// Delete
	if err := store.Delete(book1.ID); err != nil {
		t.Fatalf("delete failed: %v", err)
	}

	if _, err := store.GetByID(book1.ID); !errors.Is(err, sql.ErrNoRows) {
		t.Errorf("expected book to be deleted")
	}
}
