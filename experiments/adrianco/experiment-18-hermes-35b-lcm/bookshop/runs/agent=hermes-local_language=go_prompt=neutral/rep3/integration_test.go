package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

// setupTestDB creates a temporary SQLite database for testing.
func setupTestDB(t *testing.T) *DB {
	t.Helper()
	tmpFile, err := os.CreateTemp("", "books-test-*.db")
	if err != nil {
		t.Fatalf("failed to create temp db: %v", err)
	}
	tmpFile.Close()

	db, err := NewDB(tmpFile.Name())
	if err != nil {
		os.Remove(tmpFile.Name())
		t.Fatalf("failed to open test db: %v", err)
	}

	t.Cleanup(func() {
		db.Close()
		os.Remove(tmpFile.Name())
	})

	return db
}

// setupTestServer creates a Handlers with a test DB and returns the handler.
func setupTestServer(t *testing.T) *Handlers {
	t.Helper()
	db := setupTestDB(t)
	return &Handlers{DB: db}
}

// dispatchRequest mimics the routing logic from main.go.
func dispatchRequest(h *Handlers, req *http.Request, w http.ResponseWriter) {
	path := req.URL.Path

	switch req.Method {
	case http.MethodGet:
		switch path {
		case "/health":
			newJSONHandler(h.healthHandler)(w, req)
		case "/books":
			newJSONHandler(h.listBooksHandler)(w, req)
		default:
			newJSONHandler(h.getBookHandler)(w, req)
		}
	case http.MethodPost:
		switch path {
		case "/books":
			newJSONHandler(h.createBookHandler)(w, req)
		default:
			http.Error(w, "not found", http.StatusNotFound)
		}
	case http.MethodPut:
		if len(path) > len("/books/") {
			newJSONHandler(h.updateBookHandler)(w, req)
		} else {
			http.Error(w, "not found", http.StatusNotFound)
		}
	case http.MethodDelete:
		if len(path) > len("/books/") {
			newJSONHandler(h.deleteBookHandler)(w, req)
		} else {
			http.Error(w, "not found", http.StatusNotFound)
		}
	default:
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
	}
}

// doRequest makes an HTTP request and returns the response.
func doRequest(t *testing.T, h *Handlers, method, path string, body interface{}) *http.Response {
	t.Helper()

	var bodyReader *bytes.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("failed to marshal request body: %v", err)
		}
		bodyReader = bytes.NewReader(data)
	} else {
		bodyReader = bytes.NewReader(nil)
	}

	req := httptest.NewRequest(method, path, bodyReader)
	w := httptest.NewRecorder()

	dispatchRequest(h, req, w)

	resp := w.Result()
	return resp
}

// expectStatus checks the response has the expected status code.
func expectStatus(t *testing.T, resp *http.Response, expected int) {
	t.Helper()
	if resp.StatusCode != expected {
		t.Errorf("expected status %d, got %d", expected, resp.StatusCode)
	}
}

func TestCreateBook(t *testing.T) {
	h := setupTestServer(t)

	req := CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	}

	resp := doRequest(t, h, http.MethodPost, "/books", req)
	expectStatus(t, resp, http.StatusCreated)

	var success SuccessResponse
	if err := json.NewDecoder(resp.Body).Decode(&success); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if success.Book.Title != "The Go Programming Language" {
		t.Errorf("expected title 'The Go Programming Language', got '%s'", success.Book.Title)
	}
	if success.Book.Author != "Alan Donovan" {
		t.Errorf("expected author 'Alan Donovan', got '%s'", success.Book.Author)
	}
	if success.Book.Year != 2015 {
		t.Errorf("expected year 2015, got %d", success.Book.Year)
	}
	if success.Book.ISBN != "978-0134190440" {
		t.Errorf("expected isbn '978-0134190440', got '%s'", success.Book.ISBN)
	}
	if success.Book.ID <= 0 {
		t.Errorf("expected positive ID, got %d", success.Book.ID)
	}
}

func TestCreateBookValidation(t *testing.T) {
	h := setupTestServer(t)

	req := CreateBookRequest{
		Title:  "",
		Author: "",
		Year:   2020,
		ISBN:   "123",
	}

	resp := doRequest(t, h, http.MethodPost, "/books", req)
	expectStatus(t, resp, http.StatusBadRequest)

	var errResp ErrorResponse
	if err := json.NewDecoder(resp.Body).Decode(&errResp); err != nil {
		t.Fatalf("failed to decode error response: %v", err)
	}

	if errResp.Error != "validation failed" {
		t.Errorf("expected 'validation failed', got '%s'", errResp.Error)
	}
	if len(errResp.Validations) != 2 {
		t.Errorf("expected 2 validations, got %d", len(errResp.Validations))
	}
}

func TestListBooks(t *testing.T) {
	h := setupTestServer(t)

	book1 := CreateBookRequest{Title: "Book One", Author: "Author A", Year: 2020, ISBN: "isbn1"}
	book2 := CreateBookRequest{Title: "Book Two", Author: "Author B", Year: 2021, ISBN: "isbn2"}
	book3 := CreateBookRequest{Title: "Book Three", Author: "Author A", Year: 2022, ISBN: "isbn3"}

	doRequest(t, h, http.MethodPost, "/books", book1)
	doRequest(t, h, http.MethodPost, "/books", book2)
	doRequest(t, h, http.MethodPost, "/books", book3)

	// List all books
	resp := doRequest(t, h, http.MethodGet, "/books", nil)
	expectStatus(t, resp, http.StatusOK)

	var books []Book
	if err := json.NewDecoder(resp.Body).Decode(&books); err != nil {
		t.Fatalf("failed to decode books: %v", err)
	}

	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}

	// List with author filter
	resp = doRequest(t, h, http.MethodGet, "/books?author=Author+A", nil)
	expectStatus(t, resp, http.StatusOK)

	var filtered []Book
	if err := json.NewDecoder(resp.Body).Decode(&filtered); err != nil {
		t.Fatalf("failed to decode filtered books: %v", err)
	}

	if len(filtered) != 2 {
		t.Errorf("expected 2 books for 'Author+A', got %d", len(filtered))
	}
}

func TestGetBook(t *testing.T) {
	h := setupTestServer(t)

	req := CreateBookRequest{Title: "Get Me", Author: "Test Author", Year: 2023, ISBN: "isbn-42"}
	resp := doRequest(t, h, http.MethodPost, "/books", req)

	var success SuccessResponse
	json.NewDecoder(resp.Body).Decode(&success)
	id := success.Book.ID

	resp = doRequest(t, h, http.MethodGet, fmt.Sprintf("/books/%d", id), nil)
	expectStatus(t, resp, http.StatusOK)

	var book Book
	json.NewDecoder(resp.Body).Decode(&book)

	if book.ID != id {
		t.Errorf("expected ID %d, got %d", id, book.ID)
	}
	if book.Title != "Get Me" {
		t.Errorf("expected title 'Get Me', got '%s'", book.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	h := setupTestServer(t)

	resp := doRequest(t, h, http.MethodGet, "/books/999", nil)
	expectStatus(t, resp, http.StatusNotFound)
}

func TestUpdateBook(t *testing.T) {
	h := setupTestServer(t)

	req := CreateBookRequest{Title: "Original Title", Author: "Original Author", Year: 2020, ISBN: "isbn-upd"}
	resp := doRequest(t, h, http.MethodPost, "/books", req)

	var success SuccessResponse
	json.NewDecoder(resp.Body).Decode(&success)
	id := success.Book.ID

	newTitle := "Updated Title"
	update := UpdateBookRequest{Title: &newTitle}

	resp = doRequest(t, h, http.MethodPut, fmt.Sprintf("/books/%d", id), update)
	expectStatus(t, resp, http.StatusOK)

	var updated Book
	json.NewDecoder(resp.Body).Decode(&updated)

	if updated.Title != "Updated Title" {
		t.Errorf("expected title 'Updated Title', got '%s'", updated.Title)
	}
	if updated.Author != "Original Author" {
		t.Errorf("expected author unchanged 'Original Author', got '%s'", updated.Author)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	h := setupTestServer(t)

	resp := doRequest(t, h, http.MethodPut, "/books/999", UpdateBookRequest{Title: ptrString("test")})
	expectStatus(t, resp, http.StatusNotFound)
}

func TestDeleteBook(t *testing.T) {
	h := setupTestServer(t)

	req := CreateBookRequest{Title: "Delete Me", Author: "Delete Author", Year: 2023, ISBN: "isbn-del"}
	resp := doRequest(t, h, http.MethodPost, "/books", req)

	var success SuccessResponse
	json.NewDecoder(resp.Body).Decode(&success)
	id := success.Book.ID

	resp = doRequest(t, h, http.MethodDelete, fmt.Sprintf("/books/%d", id), nil)
	expectStatus(t, resp, http.StatusOK)

	resp = doRequest(t, h, http.MethodGet, fmt.Sprintf("/books/%d", id), nil)
	expectStatus(t, resp, http.StatusNotFound)
}

func TestDeleteBookNotFound(t *testing.T) {
	h := setupTestServer(t)

	resp := doRequest(t, h, http.MethodDelete, "/books/999", nil)
	expectStatus(t, resp, http.StatusNotFound)
}

func TestHealthCheck(t *testing.T) {
	h := setupTestServer(t)

	resp := doRequest(t, h, http.MethodGet, "/health", nil)
	expectStatus(t, resp, http.StatusOK)

	var health map[string]string
	json.NewDecoder(resp.Body).Decode(&health)

	if health["status"] != "ok" {
		t.Errorf("expected status 'ok', got '%s'", health["status"])
	}
}

func TestListBooksEmpty(t *testing.T) {
	h := setupTestServer(t)

	resp := doRequest(t, h, http.MethodGet, "/books", nil)
	expectStatus(t, resp, http.StatusOK)

	var books []Book
	json.NewDecoder(resp.Body).Decode(&books)

	if books == nil {
		t.Error("expected empty slice, got nil")
	}
	if len(books) != 0 {
		t.Errorf("expected 0 books, got %d", len(books))
	}
}

func ptrString(s string) *string {
	return &s
}

func ptrInt(i int) *int {
	return &i
}
