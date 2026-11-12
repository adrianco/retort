package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"
)

func TestHealthEndpoint(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	healthHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]string
	err := json.NewDecoder(w.Body).Decode(&resp)
	if err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok', got %s", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	reqBody, _ := json.Marshal(CreateBookRequest{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	})

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	createBookHandler(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", w.Code)
	}

	var book Book
	err := json.NewDecoder(w.Body).Decode(&book)
	if err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if book.Title != "The Great Gatsby" {
		t.Errorf("expected title 'The Great Gatsby', got %s", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("expected author 'F. Scott Fitzgerald', got %s", book.Author)
	}
	if book.Year != 1925 {
		t.Errorf("expected year 1925, got %d", book.Year)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
}

func TestCreateBookMissingTitle(t *testing.T) {
	reqBody, _ := json.Marshal(CreateBookRequest{
		Author: "Some Author",
	})

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	createBookHandler(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()

	listBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	err := json.NewDecoder(w.Body).Decode(&books)
	if err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	// Should have at least the book created in TestCreateBook
	if len(books) < 1 {
		t.Error("expected at least one book")
	}
}

func TestListBooksByAuthor(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/books?author=F.%20Scott%20Fitzgerald", nil)
	w := httptest.NewRecorder()

	listBooksHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	err := json.NewDecoder(w.Body).Decode(&books)
	if err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if len(books) < 1 {
		t.Errorf("expected at least 1 book, got %d", len(books))
	}
	found := false
	for _, b := range books {
		if b.Author == "F. Scott Fitzgerald" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected at least one book by F. Scott Fitzgerald")
	}
}

func TestGetBook(t *testing.T) {
	// Create a book first
	reqBody, _ := json.Marshal(CreateBookRequest{
		Title:  "1984",
		Author: "George Orwell",
		Year:   1949,
		ISBN:   "978-0451524935",
	})
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	var newBook Book
	json.NewDecoder(w.Body).Decode(&newBook)

	// Now get it
	req = httptest.NewRequest(http.MethodGet, "/books/"+strconv.Itoa(newBook.ID), nil)
	w = httptest.NewRecorder()
	getBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	err := json.NewDecoder(w.Body).Decode(&book)
	if err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if book.Title != "1984" {
		t.Errorf("expected title '1984', got %s", book.Title)
	}
}

func TestUpdateBook(t *testing.T) {
	// Create a book first
	reqBody, _ := json.Marshal(CreateBookRequest{
		Title:  "Brave New World",
		Author: "Aldous Huxley",
		Year:   1932,
	})
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	var newBook Book
	json.NewDecoder(w.Body).Decode(&newBook)

	// Update it
	title := "Brave New World (Updated)"
	reqBody, _ = json.Marshal(UpdateBookRequest{Title: &title})
	req = httptest.NewRequest(http.MethodPut, "/books/"+strconv.Itoa(newBook.ID), bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	updateBookHandler(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var book Book
	json.NewDecoder(w.Body).Decode(&book)
	if book.Title != "Brave New World (Updated)" {
		t.Errorf("expected updated title, got %s", book.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	// Create a book first
	reqBody, _ := json.Marshal(CreateBookRequest{
		Title:  "To Kill a Mockingbird",
		Author: "Harper Lee",
		Year:   1960,
	})
	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewBuffer(reqBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	createBookHandler(w, req)

	var newBook Book
	json.NewDecoder(w.Body).Decode(&newBook)

	// Delete it
	req = httptest.NewRequest(http.MethodDelete, "/books/"+strconv.Itoa(newBook.ID), nil)
	w = httptest.NewRecorder()
	deleteBookHandler(w, req)

	if w.Code != http.StatusNoContent {
		t.Errorf("expected status 204, got %d", w.Code)
	}
}

func TestDeleteNonExistentBook(t *testing.T) {
	req := httptest.NewRequest(http.MethodDelete, "/books/9999", nil)
	w := httptest.NewRecorder()
	deleteBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestGetNonExistentBook(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/books/9999", nil)
	w := httptest.NewRecorder()
	getBookHandler(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

// Test that the full server works end-to-end
func TestFullServer(t *testing.T) {
	// Create a book
	reqBody, _ := json.Marshal(CreateBookRequest{
		Title:  "Test Book",
		Author: "Test Author",
		Year:   2024,
	})
	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			listBooksHandler(w, r)
		case http.MethodPost:
			createBookHandler(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})
	mux.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			getBookHandler(w, r)
		case http.MethodPut:
			updateBookHandler(w, r)
		case http.MethodDelete:
			deleteBookHandler(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	server := httptest.NewServer(mux)
	defer server.Close()

	// Test health
	resp, err := http.Get(server.URL + "/health")
	if err != nil {
		t.Fatalf("failed to get health: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
	_ = resp.Body.Close()

	// Test create
	resp, err = http.Post(server.URL+"/books", "application/json", bytes.NewBuffer(reqBody))
	if err != nil {
		t.Fatalf("failed to create book: %v", err)
	}
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("expected 201, got %d", resp.StatusCode)
	}

	// Test list
	resp, err = http.Get(server.URL + "/books")
	if err != nil {
		t.Fatalf("failed to list books: %v", err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected 200, got %d", resp.StatusCode)
	}
}

func TestMain(m *testing.M) {
	// Ensure db is closed after tests
	code := m.Run()
	closeDB()
	os.Exit(code)
}
