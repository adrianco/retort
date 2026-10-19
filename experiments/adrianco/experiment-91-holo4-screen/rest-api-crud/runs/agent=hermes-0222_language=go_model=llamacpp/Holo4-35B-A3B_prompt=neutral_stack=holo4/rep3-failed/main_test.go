package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"testing"
)

func newTestDB(t *testing.T, name string) {
	t.Helper()
	// Close any existing db
	if db != nil {
		db.Close()
	}
	var err error
	db, err = sql.Open("sqlite", "file:"+name+"?cache=shared&mode=rwc")
	if err != nil {
		t.Fatalf("Failed to open test DB: %v", err)
	}
	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	_, err = db.Exec(createTable)
	if err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}
}

func cleanup(t *testing.T, name string) {
	t.Helper()
	if db != nil {
		db.Close()
		db = nil
	}
	os.Remove(name)
}

func TestHealthEndpoint(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	healthHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]string
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok', got %s", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	newTestDB(t, "test_create.db")
	defer cleanup(t, "test_create.db")

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	})

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if book.Title != "The Go Programming Language" {
		t.Errorf("expected title 'The Go Programming Language', got %s", book.Title)
	}
	if book.ID != 1 {
		t.Errorf("expected ID 1, got %d", book.ID)
	}
}

func TestCreateBookMissingTitle(t *testing.T) {
	newTestDB(t, "test_missing_title.db")
	defer cleanup(t, "test_missing_title.db")

	body, _ := json.Marshal(CreateBookRequest{
		Author: "Some Author",
	})

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	createBookHandler(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	newTestDB(t, "test_list.db")
	defer cleanup(t, "test_list.db")

	// Insert test data
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "isbn-1")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "isbn-2")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Three", "Author A", 2022, "isbn-3")

	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()

	listBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}
}

func TestListBooksFilterByAuthor(t *testing.T) {
	newTestDB(t, "test_filter.db")
	defer cleanup(t, "test_filter.db")

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "isbn-1")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "isbn-2")

	// URL-encode the query parameter to avoid spaces in the request target
	u := url.URL{Path: "/books"}
	q := u.Query()
	q.Set("author", "Author A")
	u.RawQuery = q.Encode()

	req := httptest.NewRequest(http.MethodGet, u.String(), nil)
	w := httptest.NewRecorder()

	listBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if len(books) != 1 {
		t.Errorf("expected 1 book, got %d", len(books))
	}
	if books[0].Author != "Author A" {
		t.Errorf("expected author 'Author A', got %s", books[0].Author)
	}
}

func TestGetBook(t *testing.T) {
	newTestDB(t, "test_get.db")
	defer cleanup(t, "test_get.db")

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "isbn-test")

	req := httptest.NewRequest(http.MethodGet, "/books/1", nil)
	w := httptest.NewRecorder()

	getBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if book.Title != "Test Book" {
		t.Errorf("expected title 'Test Book', got %s", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	newTestDB(t, "test_get404.db")
	defer cleanup(t, "test_get404.db")

	req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
	w := httptest.NewRecorder()

	getBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	newTestDB(t, "test_update.db")
	defer cleanup(t, "test_update.db")

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Old Title", "Old Author", 2020, "isbn-old")

	body, _ := json.Marshal(UpdateBookRequest{
		Title: ptrStr("New Title"),
		Year:  ptrInt(2024),
	})

	req := httptest.NewRequest(http.MethodPut, "/books/1", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	updateBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}
	if book.Title != "New Title" {
		t.Errorf("expected title 'New Title', got %s", book.Title)
	}
	if book.Year != 2024 {
		t.Errorf("expected year 2024, got %d", book.Year)
	}
	if book.Author != "Old Author" {
		t.Errorf("expected author unchanged 'Old Author', got %s", book.Author)
	}
}

func TestDeleteBook(t *testing.T) {
	newTestDB(t, "test_delete.db")
	defer cleanup(t, "test_delete.db")

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Delete Me", "Author", 2020, "isbn-del")

	req := httptest.NewRequest(http.MethodDelete, "/books/1", nil)
	w := httptest.NewRecorder()

	deleteBookHandler(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("expected status 204, got %d", w.Code)
	}

	// Verify it's gone
	var count int
	db.QueryRow("SELECT COUNT(*) FROM books").Scan(&count)
	if count != 0 {
		t.Errorf("expected 0 books after delete, got %d", count)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	newTestDB(t, "test_delete404.db")
	defer cleanup(t, "test_delete404.db")

	req := httptest.NewRequest(http.MethodDelete, "/books/999", nil)
	w := httptest.NewRecorder()

	deleteBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func ptrStr(s string) *string { return &s }
func ptrInt(i int) *int       { return &i }
