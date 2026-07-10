package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gorilla/mux"
)

// setupTestDB creates an in-memory SQLite database for testing.
func setupTestDB(t *testing.T) *Database {
	t.Helper()
	db, err := NewDatabase(":memory:")
	if err != nil {
		t.Fatalf("failed to create test database: %v", err)
	}
	return db
}

func TestHealthCheck(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	req := httptest.NewRequest("GET", "/health", nil)
	rec := httptest.NewRecorder()

	handler.HealthCheck(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}

	var resp map[string]string
	json.NewDecoder(rec.Body).Decode(&resp)
	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok', got '%s'", resp["status"])
	}
}

func TestCreateBook_Success(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	payload, _ := json.Marshal(CreateBookRequest{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	})

	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	handler.CreateBook(rec, req)

	if rec.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", rec.Code)
	}

	var book Book
	json.NewDecoder(rec.Body).Decode(&book)

	if book.Title != "The Great Gatsby" {
		t.Errorf("expected title 'The Great Gatsby', got '%s'", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("expected author 'F. Scott Fitzgerald', got '%s'", book.Author)
	}
	if book.Year != 1925 {
		t.Errorf("expected year 1925, got %d", book.Year)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
	if book.ISBN != "978-0743273565" {
		t.Errorf("expected ISBN '978-0743273565', got '%s'", book.ISBN)
	}
}

func TestCreateBook_MissingTitle(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	payload, _ := json.Marshal(CreateBookRequest{
		Title:  "",
		Author: "Test Author",
		Year:   2020,
		ISBN:   "test",
	})

	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	handler.CreateBook(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", rec.Code)
	}

	var resp ErrorResponse
	json.NewDecoder(rec.Body).Decode(&resp)
	if resp.Error != "Title is required" {
		t.Errorf("expected error 'Title is required', got '%s'", resp.Error)
	}
}

func TestCreateBook_MissingAuthor(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	payload, _ := json.Marshal(CreateBookRequest{
		Title:  "Test Book",
		Author: "",
		Year:   2020,
		ISBN:   "test",
	})

	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	handler.CreateBook(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", rec.Code)
	}

	var resp ErrorResponse
	json.NewDecoder(rec.Body).Decode(&resp)
	if resp.Error != "Author is required" {
		t.Errorf("expected error 'Author is required', got '%s'", resp.Error)
	}
}

func TestListBooks_AllBooks(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	handler.CreateBook(httptest.NewRecorder(), httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "isbn1"}))))
	handler.CreateBook(httptest.NewRecorder(), httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "isbn2"}))))
	handler.CreateBook(httptest.NewRecorder(), httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Book 3", Author: "Author A", Year: 2022, ISBN: "isbn3"}))))

	req := httptest.NewRequest("GET", "/books", nil)
	rec := httptest.NewRecorder()
	handler.ListBooks(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}

	var books []*Book
	json.NewDecoder(rec.Body).Decode(&books)
	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}
}

func TestListBooks_FilterByAuthor(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	handler.CreateBook(httptest.NewRecorder(), httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "isbn1"}))))
	handler.CreateBook(httptest.NewRecorder(), httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "isbn2"}))))
	handler.CreateBook(httptest.NewRecorder(), httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Book 3", Author: "Author A", Year: 2022, ISBN: "isbn3"}))))

	req := httptest.NewRequest("GET", "/books?author=Author%20A", nil)
	rec := httptest.NewRecorder()
	handler.ListBooks(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}

	var books []*Book
	json.NewDecoder(rec.Body).Decode(&books)
	if len(books) != 2 {
		t.Errorf("expected 2 books for Author A, got %d", len(books))
	}
	for _, b := range books {
		if b.Author != "Author A" {
			t.Errorf("expected all books by Author A, got '%s'", b.Author)
		}
	}
}

// testBookRouter creates a mux router with the book detail routes (GET, PUT, DELETE).
func testBookRouter(handler *Handler) *mux.Router {
	r := mux.NewRouter()
	r.HandleFunc("/books/{id}", handler.GetBook).Methods("GET")
	r.HandleFunc("/books/{id}", handler.UpdateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", handler.DeleteBook).Methods("DELETE")
	return r
}

func TestGetBook_Success(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	resp := httptest.NewRecorder()
	handler.CreateBook(resp, httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Test Book", Author: "Test Author", Year: 2023, ISBN: "isbn-test"}))))

	var created Book
	json.NewDecoder(resp.Body).Decode(&created)

	r := testBookRouter(handler)
	req := httptest.NewRequest("GET", fmt.Sprintf("/books/%d", created.ID), nil)
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d\nbody: %s", rec.Code, rec.Body.String())
	}

	var book Book
	json.NewDecoder(rec.Body).Decode(&book)
	if book.ID != created.ID {
		t.Errorf("expected ID %d, got %d", created.ID, book.ID)
	}
	if book.Title != "Test Book" {
		t.Errorf("expected title 'Test Book', got '%s'", book.Title)
	}
}

func TestGetBook_NotFound(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	r := testBookRouter(handler)
	req := httptest.NewRequest("GET", "/books/999", nil)
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", rec.Code)
	}
}

func TestUpdateBook_Success(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	resp := httptest.NewRecorder()
	handler.CreateBook(resp, httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Original", Author: "Original Author", Year: 2020, ISBN: "isbn-old"}))))

	var created Book
	json.NewDecoder(resp.Body).Decode(&created)

	updateTitle := "Updated Title"
	payload, _ := json.Marshal(UpdateBookRequest{Title: &updateTitle, Year: ptrInt(2024)})

	r := testBookRouter(handler)
	req := httptest.NewRequest("PUT", fmt.Sprintf("/books/%d", created.ID), bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d\nbody: %s", rec.Code, rec.Body.String())
	}

	var book Book
	json.NewDecoder(rec.Body).Decode(&book)
	if book.Title != "Updated Title" {
		t.Errorf("expected title 'Updated Title', got '%s'", book.Title)
	}
	if book.Year != 2024 {
		t.Errorf("expected year 2024, got %d", book.Year)
	}
	if book.Author != "Original Author" {
		t.Errorf("expected author preserved, got '%s'", book.Author)
	}
	if book.ISBN != "isbn-old" {
		t.Errorf("expected ISBN preserved, got '%s'", book.ISBN)
	}
}

func TestDeleteBook_Success(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	resp := httptest.NewRecorder()
	handler.CreateBook(resp, httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Delete Me", Author: "Author", Year: 2023, ISBN: "isbn-del"}))))

	r := testBookRouter(handler)
	req := httptest.NewRequest("DELETE", "/books/1", nil)
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)

	if rec.Code != http.StatusNoContent {
		t.Errorf("expected status 204, got %d\nbody: %s", rec.Code, rec.Body.String())
	}

	r2 := mux.NewRouter()
	r2.HandleFunc("/books/{id}", handler.GetBook).Methods("GET")
	req2 := httptest.NewRequest("GET", "/books/1", nil)
	rec2 := httptest.NewRecorder()
	r2.ServeHTTP(rec2, req2)

	if rec2.Code != http.StatusNotFound {
		t.Errorf("expected book to be deleted (404), got %d", rec2.Code)
	}
}

func TestDeleteBook_NotFound(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	r := testBookRouter(handler)
	req := httptest.NewRequest("DELETE", "/books/999", nil)
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", rec.Code)
	}
}

func TestListBooks_Empty(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	req := httptest.NewRequest("GET", "/books", nil)
	rec := httptest.NewRecorder()
	handler.ListBooks(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}

	var books []*Book
	json.NewDecoder(rec.Body).Decode(&books)
	if len(books) != 0 {
		t.Errorf("expected 0 books, got %d", len(books))
	}
}

func TestListBooks_NoFilter(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	handler.CreateBook(httptest.NewRecorder(), httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Book 1", Author: "Author A", Year: 2020, ISBN: "isbn1"}))))
	handler.CreateBook(httptest.NewRecorder(), httptest.NewRequest("POST", "/books",
		bytes.NewReader(mustMarshal(t, CreateBookRequest{Title: "Book 2", Author: "Author B", Year: 2021, ISBN: "isbn2"}))))

	req := httptest.NewRequest("GET", "/books", nil)
	rec := httptest.NewRecorder()
	handler.ListBooks(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}

	var books []*Book
	json.NewDecoder(rec.Body).Decode(&books)
	if len(books) != 2 {
		t.Errorf("expected 2 books, got %d", len(books))
	}
}

func TestCreateBook_InvalidJSON(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	handler := &Handler{DB: db}

	req := httptest.NewRequest("POST", "/books", strings.NewReader("not json"))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()

	handler.CreateBook(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", rec.Code)
	}
}

func mustMarshal(t *testing.T, v interface{}) []byte {
	t.Helper()
	data, err := json.Marshal(v)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	return data
}

func ptrInt(i int) *int {
	return &i
}
