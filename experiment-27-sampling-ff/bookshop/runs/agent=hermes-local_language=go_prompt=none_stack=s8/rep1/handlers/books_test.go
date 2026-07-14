package handlers

import (
	"book-api/db"
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gorilla/mux"
)

func setupTestDB(t *testing.T) (*db.Database, func()) {
	t.Helper()

	tmpFile := t.TempDir() + "/test.db"
	database, err := db.New(tmpFile)
	if err != nil {
		t.Fatalf("Failed to create test database: %v", err)
	}

	return database, func() {
		database.Close()
		os.Remove(tmpFile)
	}
}

func setupRouter(t *testing.T, database *db.Database) *mux.Router {
	t.Helper()

	r := mux.NewRouter()
	h := NewBooksHandler(database)

	r.HandleFunc("/health", h.HealthCheck).Methods("GET")
	r.HandleFunc("/books", h.CreateBook).Methods("POST")
	r.HandleFunc("/books", h.GetBooks).Methods("GET")
	r.HandleFunc("/books/{id}", h.GetBook).Methods("GET")
	r.HandleFunc("/books/{id}", h.UpdateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", h.DeleteBook).Methods("DELETE")

	return r
}

func TestHealthCheck(t *testing.T) {
	database, cleanup := setupTestDB(t)
	defer cleanup()

	router := setupRouter(t, database)

	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]interface{}
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if resp["status"] != "healthy" {
		t.Errorf("expected status 'healthy', got '%v'", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	database, cleanup := setupTestDB(t)
	defer cleanup()

	router := setupRouter(t, database)

	tests := []struct {
		name           string
		body           map[string]interface{}
		expectedStatus int
		expectError    bool
	}{
		{
			name: "valid book",
			body: map[string]interface{}{
				"title":  "The Go Programming Language",
				"author": "Donovan & Kernighan",
				"year":   2015,
				"isbn":   "978-0134190440",
			},
			expectedStatus: http.StatusCreated,
			expectError:    false,
		},
		{
			name: "missing title",
			body: map[string]interface{}{
				"title":  "",
				"author": "Test Author",
				"year":   2020,
				"isbn":   "123",
			},
			expectedStatus: http.StatusBadRequest,
			expectError:    true,
		},
		{
			name: "missing author",
			body: map[string]interface{}{
				"title":  "Some Book",
				"author": "",
				"year":   2020,
				"isbn":   "123",
			},
			expectedStatus: http.StatusBadRequest,
			expectError:    true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			body, err := json.Marshal(tt.body)
			if err != nil {
				t.Fatalf("failed to marshal request body: %v", err)
			}

			req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()

			router.ServeHTTP(w, req)

			if w.Code != tt.expectedStatus {
				t.Errorf("expected status %d, got %d. body: %s", tt.expectedStatus, w.Code, w.Body.String())
			}

			if !tt.expectError && w.Code == http.StatusCreated {
				var book map[string]interface{}
				if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
					t.Fatalf("failed to decode response: %v", err)
				}

				if book["id"] == nil {
					t.Error("expected book id to be set")
				}
			}
		})
	}
}

func TestGetAllBooks(t *testing.T) {
	database, cleanup := setupTestDB(t)
	defer cleanup()

	router := setupRouter(t, database)

	// Create test books first
	testBooks := []map[string]interface{}{
		{"title": "Book A", "author": "Author X", "year": 2020, "isbn": "111"},
		{"title": "Book B", "author": "Author X", "year": 2021, "isbn": "222"},
		{"title": "Book C", "author": "Author Y", "year": 2022, "isbn": "333"},
	}

	for _, tb := range testBooks {
		body, _ := json.Marshal(tb)
		req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusCreated {
			t.Fatalf("failed to create test book: %s", w.Body.String())
		}
	}

	// Test get all books
	t.Run("get all books", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []map[string]interface{}
		if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
			t.Fatalf("failed to decode response: %v", err)
		}

		if len(books) != 3 {
			t.Errorf("expected 3 books, got %d", len(books))
		}
	})

	// Test get books by author filter
	t.Run("filter by author", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books?author=Author+X", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []map[string]interface{}
		if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
			t.Fatalf("failed to decode response: %v", err)
		}

		if len(books) != 2 {
			t.Errorf("expected 2 books for Author X, got %d", len(books))
		}

		for _, book := range books {
			if book["author"] != "Author X" {
				t.Errorf("expected author 'Author X', got '%v'", book["author"])
			}
		}
	})

	// Test empty filter returns all
	t.Run("empty author filter", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books?author=", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var books []map[string]interface{}
		if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
			t.Fatalf("failed to decode response: %v", err)
		}

		if len(books) != 3 {
			t.Errorf("expected all 3 books, got %d", len(books))
		}
	})
}

func TestGetBookByID(t *testing.T) {
	database, cleanup := setupTestDB(t)
	defer cleanup()

	router := setupRouter(t, database)

	// Create a test book first
	testBook := map[string]interface{}{
		"title":  "Test Book",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "ISBN-TEST",
	}

	body, _ := json.Marshal(testBook)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("failed to create test book: %s", w.Body.String())
	}

	t.Run("existing book", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books/1", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d", w.Code)
		}

		var book map[string]interface{}
		if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
			t.Fatalf("failed to decode response: %v", err)
		}

		if book["title"] != "Test Book" {
			t.Errorf("expected title 'Test Book', got '%v'", book["title"])
		}
	})

	t.Run("non-existent book", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books/9999", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", w.Code)
		}
	})

	t.Run("invalid book ID", func(t *testing.T) {
		req := httptest.NewRequest("GET", "/books/abc", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", w.Code)
		}
	})
}

func TestUpdateBook(t *testing.T) {
	database, cleanup := setupTestDB(t)
	defer cleanup()

	router := setupRouter(t, database)

	// Create a test book first
	testBook := map[string]interface{}{
		"title":  "Original Title",
		"author": "Original Author",
		"year":   2020,
		"isbn":   "OLD-ISBN",
	}

	body, _ := json.Marshal(testBook)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	t.Run("update title only", func(t *testing.T) {
		update := map[string]interface{}{
			"title": "Updated Title",
		}

		updateBody, _ := json.Marshal(update)
		req := httptest.NewRequest("PUT", "/books/1", bytes.NewBuffer(updateBody))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d: %s", w.Code, w.Body.String())
			return
		}

		var book map[string]interface{}
		if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
			t.Fatalf("failed to decode response: %v", err)
		}

		if book["title"] != "Updated Title" {
			t.Errorf("expected title 'Updated Title', got '%v'", book["title"])
		}

		if book["author"] != "Original Author" {
			t.Errorf("expected author unchanged, got '%v'", book["author"])
		}
	})

	t.Run("update all fields", func(t *testing.T) {
		update := map[string]interface{}{
			"title":  "Full Update",
			"author": "New Author",
			"year":   2024,
			"isbn":   "NEW-ISBN",
		}

		updateBody, _ := json.Marshal(update)
		req := httptest.NewRequest("PUT", "/books/1", bytes.NewBuffer(updateBody))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusOK {
			t.Errorf("expected status 200, got %d: %s", w.Code, w.Body.String())
			return
		}

		var book map[string]interface{}
		if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
			t.Fatalf("failed to decode response: %v", err)
		}

		if book["title"] != "Full Update" {
			t.Errorf("expected title 'Full Update', got '%v'", book["title"])
		}

		if book["author"] != "New Author" {
			t.Errorf("expected author 'New Author', got '%v'", book["author"])
		}

		if int(book["year"].(float64)) != 2024 {
			t.Errorf("expected year 2024, got %v", book["year"])
		}

		if book["isbn"] != "NEW-ISBN" {
			t.Errorf("expected isbn 'NEW-ISBN', got '%v'", book["isbn"])
		}
	})

	t.Run("empty title validation", func(t *testing.T) {
		update := map[string]interface{}{
			"title": "",
		}

		updateBody, _ := json.Marshal(update)
		req := httptest.NewRequest("PUT", "/books/1", bytes.NewBuffer(updateBody))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("expected status 400 for empty title, got %d", w.Code)
		}
	})

	t.Run("non-existent book update", func(t *testing.T) {
		update := map[string]interface{}{
			"title": "Ghost Book",
		}

		updateBody, _ := json.Marshal(update)
		req := httptest.NewRequest("PUT", "/books/9999", bytes.NewBuffer(updateBody))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404 for non-existent book, got %d", w.Code)
		}
	})
}

func TestDeleteBook(t *testing.T) {
	database, cleanup := setupTestDB(t)
	defer cleanup()

	router := setupRouter(t, database)

	// Create a test book first
	testBook := map[string]interface{}{
		"title":  "To Be Deleted",
		"author": "Author",
		"year":   2023,
		"isbn":   "DELETE-ME",
	}

	body, _ := json.Marshal(testBook)
	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	t.Run("delete existing book", func(t *testing.T) {
		req := httptest.NewRequest("DELETE", "/books/1", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusNoContent {
			t.Errorf("expected status 204, got %d", w.Code)
		}

		// Verify it is actually deleted
		req = httptest.NewRequest("GET", "/books/1", nil)
		w = httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected book to be deleted (404), got %d", w.Code)
		}
	})

	t.Run("delete non-existent book", func(t *testing.T) {
		req := httptest.NewRequest("DELETE", "/books/9999", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusNotFound {
			t.Errorf("expected status 404, got %d", w.Code)
		}
	})

	t.Run("delete with invalid ID", func(t *testing.T) {
		req := httptest.NewRequest("DELETE", "/books/abc", nil)
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)

		if w.Code != http.StatusBadRequest {
			t.Errorf("expected status 400, got %d", w.Code)
		}
	})
}

func TestIntegrationCreateAndRetrieve(t *testing.T) {
	database, cleanup := setupTestDB(t)
	defer cleanup()

	router := setupRouter(t, database)

	// Create a book
	createBody, _ := json.Marshal(map[string]interface{}{
		"title":  "Integration Test Book",
		"author": "Integration Author",
		"year":   2024,
		"isbn":   "INT-ISBN",
	})

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(createBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %s", w.Body.String())
	}

	// Retrieve it back
	req = httptest.NewRequest("GET", "/books/1", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("get failed: %s", w.Body.String())
	}

	var retrieved map[string]interface{}
	json.NewDecoder(w.Body).Decode(&retrieved)

	if retrieved["title"] != "Integration Test Book" {
		t.Errorf("expected title 'Integration Test Book', got '%v'", retrieved["title"])
	}

	if retrieved["author"] != "Integration Author" {
		t.Errorf("expected author 'Integration Author', got '%v'", retrieved["author"])
	}

	if int(retrieved["year"].(float64)) != 2024 {
		t.Errorf("expected year 2024, got %v", retrieved["year"])
	}

	if retrieved["isbn"] != "INT-ISBN" {
		t.Errorf("expected isbn 'INT-ISBN', got '%v'", retrieved["isbn"])
	}
}

func TestIntegrationCRUD(t *testing.T) {
	database, cleanup := setupTestDB(t)
	defer cleanup()

	router := setupRouter(t, database)

	// CREATE
	createBody, _ := json.Marshal(map[string]interface{}{
		"title":  "CRUD Test",
		"author": "Test Author",
		"year":   2023,
		"isbn":   "CRUD-ISBN",
	})

	req := httptest.NewRequest("POST", "/books", bytes.NewBuffer(createBody))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %s", w.Body.String())
	}

	// READ
	req = httptest.NewRequest("GET", "/books/1", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("get failed: %s", w.Body.String())
	}

	var book map[string]interface{}
	json.NewDecoder(w.Body).Decode(&book)
	if book["title"] != "CRUD Test" {
		t.Errorf("expected title 'CRUD Test', got '%v'", book["title"])
	}

	// UPDATE
	updateBody, _ := json.Marshal(map[string]interface{}{
		"title": "Updated CRUD",
	})

	req = httptest.NewRequest("PUT", "/books/1", bytes.NewBuffer(updateBody))
	req.Header.Set("Content-Type", "application/json")
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("update failed: %s", w.Body.String())
	}

	json.NewDecoder(w.Body).Decode(&book)
	if book["title"] != "Updated CRUD" {
		t.Errorf("expected title 'Updated CRUD', got '%v'", book["title"])
	}

	if book["author"] != "Test Author" {
		t.Errorf("expected author unchanged, got '%v'", book["author"])
	}

	// LIST (all)
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("list failed: %s", w.Body.String())
	}

	var books []map[string]interface{}
	json.NewDecoder(w.Body).Decode(&books)
	if len(books) != 1 {
		t.Errorf("expected 1 book in list, got %d", len(books))
	}

	// DELETE
	req = httptest.NewRequest("DELETE", "/books/1", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNoContent {
		t.Fatalf("delete failed: %d", w.Code)
	}

	// Verify deleted
	req = httptest.NewRequest("GET", "/books/1", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", w.Code)
	}

	// Verify list is empty
	req = httptest.NewRequest("GET", "/books", nil)
	w = httptest.NewRecorder()
	router.ServeHTTP(w, req)

	json.NewDecoder(w.Body).Decode(&books)
	if len(books) != 0 {
		t.Errorf("expected empty list after delete, got %d books", len(books))
	}
}
