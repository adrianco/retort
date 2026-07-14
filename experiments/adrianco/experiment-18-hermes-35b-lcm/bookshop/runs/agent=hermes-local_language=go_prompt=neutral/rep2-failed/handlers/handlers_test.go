package handlers

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"book-api/database"
	"book-api/models"
)

// setupTestDB creates an in-memory SQLite database for testing.
func setupTestDB(t *testing.T) *database.DB {
	t.Helper()
	db, err := database.New(":memory:")
	if err != nil {
		t.Fatalf("failed to create test database: %v", err)
	}
	return db
}

func TestHealthCheck(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	h := NewBookHandler(db)
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()

	h.HealthCheck(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", rec.Code)
	}

	var resp map[string]string
	json.NewDecoder(rec.Body).Decode(&resp)
	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok', got '%s'", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	h := NewBookHandler(db)

	tests := []struct {
		name          string
		body          string
		expectedCode  int
		expectedTitle string
	}{
		{
			name:          "valid book",
			body:          `{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":1925,"isbn":"978-0743273565"}`,
			expectedCode:  http.StatusCreated,
			expectedTitle: "The Great Gatsby",
		},
		{
			name:       "missing title",
			body:       `{"author":"F. Scott Fitzgerald","year":1925}`,
			expectedCode: http.StatusBadRequest,
		},
		{
			name:       "missing author",
			body:       `{"title":"The Great Gatsby","year":1925}`,
			expectedCode: http.StatusBadRequest,
		},
		{
			name:       "invalid year",
			body:       `{"title":"The Great Gatsby","author":"F. Scott Fitzgerald","year":-1}`,
			expectedCode: http.StatusBadRequest,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			body := strings.NewReader(tt.body)
			req := httptest.NewRequest(http.MethodPost, "/books", body)
			rec := httptest.NewRecorder()

			h.CreateBook(rec, req)

			if rec.Code != tt.expectedCode {
				t.Errorf("CreateBook() code = %d; want %d, body: %s", rec.Code, tt.expectedCode, rec.Body.String())
			}

			if tt.expectedCode == http.StatusCreated {
				var book models.Book
				if err := json.NewDecoder(rec.Body).Decode(&book); err != nil {
					t.Fatalf("failed to decode response: %v", err)
				}
				if book.Title != tt.expectedTitle {
					t.Errorf("title = %q; want %q", book.Title, tt.expectedTitle)
				}
				if book.ID == "" {
					t.Error("expected non-empty ID")
				}
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	h := NewBookHandler(db)

	// Create some test books
	books := []models.CreateBookRequest{
		{Title: "1984", Author: "George Orwell", Year: 1949, ISBN: "978-0451524935"},
		{Title: "Animal Farm", Author: "George Orwell", Year: 1945, ISBN: "978-0451526342"},
		{Title: "Brave New World", Author: "Aldous Huxley", Year: 1932, ISBN: "978-0060850524"},
	}

	for _, b := range books {
		body := bytes.NewReader(mustEncode(b))
		req := httptest.NewRequest(http.MethodPost, "/books", body)
		rec := httptest.NewRecorder()
		h.CreateBook(rec, req)
		if rec.Code != http.StatusCreated {
			t.Fatalf("create failed: %d %s", rec.Code, rec.Body.String())
		}
	}

	// Test: list all
	t.Run("list all books", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/books", nil)
		rec := httptest.NewRecorder()
		h.ListBooks(rec, req)

		if rec.Code != http.StatusOK {
			t.Errorf("status = %d; want 200", rec.Code)
		}

		var result []models.Book
		json.NewDecoder(rec.Body).Decode(&result)
		if len(result) != 3 {
			t.Errorf("got %d books; want 3", len(result))
		}
	})

	// Test: filter by author
	t.Run("filter by author", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/books?author=George%20Orwell", nil)
		rec := httptest.NewRecorder()
		h.ListBooks(rec, req)

		if rec.Code != http.StatusOK {
			t.Errorf("status = %d; want 200", rec.Code)
		}

		var result []models.Book
		json.NewDecoder(rec.Body).Decode(&result)
		if len(result) != 2 {
			t.Errorf("got %d books; want 2", len(result))
		}
		for _, b := range result {
			if b.Author != "George Orwell" {
				t.Errorf("expected author 'George Orwell', got %q", b.Author)
			}
		}
	})
}

func TestGetBook(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	h := NewBookHandler(db)

	// Create a book
	body := bytes.NewReader(mustEncode(models.CreateBookRequest{
		Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441172719",
	}))
	req := httptest.NewRequest(http.MethodPost, "/books", body)
	rec := httptest.NewRecorder()
	h.CreateBook(rec, req)

	var created models.Book
	json.NewDecoder(rec.Body).Decode(&created)

	// Test: get by ID
	t.Run("get existing book", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/books/"+created.ID, nil)
		rec := httptest.NewRecorder()
		h.GetBook(rec, req)

		if rec.Code != http.StatusOK {
			t.Errorf("status = %d; want 200", rec.Code)
		}

		var book models.Book
		json.NewDecoder(rec.Body).Decode(&book)
		if book.Title != "Dune" {
			t.Errorf("title = %q; want 'Dune'", book.Title)
		}
	})

	// Test: get non-existent book
	t.Run("get non-existent book", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/books/999", nil)
		rec := httptest.NewRecorder()
		h.GetBook(rec, req)

		if rec.Code != http.StatusNotFound {
			t.Errorf("status = %d; want 404", rec.Code)
		}
	})
}

func TestUpdateBook(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	h := NewBookHandler(db)

	// Create a book first
	body := bytes.NewReader(mustEncode(models.CreateBookRequest{
		Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441172719",
	}))
	req := httptest.NewRequest(http.MethodPost, "/books", body)
	rec := httptest.NewRecorder()
	h.CreateBook(rec, req)

	var created models.Book
	json.NewDecoder(rec.Body).Decode(&created)

	// Test: update title
	t.Run("update title", func(t *testing.T) {
		newTitle := "Dune: Deluxe Edition"
		payload := models.UpdateBookRequest{Title: &newTitle}
		body := bytes.NewReader(mustEncode(payload))
		req := httptest.NewRequest(http.MethodPut, "/books/"+created.ID, body)
		rec := httptest.NewRecorder()
		h.UpdateBook(rec, req)

		if rec.Code != http.StatusOK {
			t.Fatalf("status = %d; want 200, body: %s", rec.Code, rec.Body.String())
		}

		var book models.Book
		json.NewDecoder(rec.Body).Decode(&book)
		if book.Title != newTitle {
			t.Errorf("title = %q; want %q", book.Title, newTitle)
		}
		// Other fields should be unchanged
		if book.Author != "Frank Herbert" {
			t.Errorf("author = %q; want 'Frank Herbert'", book.Author)
		}
	})

	// Test: update non-existent book
	t.Run("update non-existent book", func(t *testing.T) {
		newTitle := "Nonexistent"
		payload := models.UpdateBookRequest{Title: &newTitle}
		body := bytes.NewReader(mustEncode(payload))
		req := httptest.NewRequest(http.MethodPut, "/books/999", body)
		rec := httptest.NewRecorder()
		h.UpdateBook(rec, req)

		if rec.Code != http.StatusNotFound {
			t.Errorf("status = %d; want 404", rec.Code)
		}
	})

	// Test: empty title in update
	t.Run("empty title in update", func(t *testing.T) {
		empty := ""
		payload := models.UpdateBookRequest{Title: &empty}
		body := bytes.NewReader(mustEncode(payload))
		req := httptest.NewRequest(http.MethodPut, "/books/"+created.ID, body)
		rec := httptest.NewRecorder()
		h.UpdateBook(rec, req)

		if rec.Code != http.StatusBadRequest {
			t.Errorf("status = %d; want 400", rec.Code)
		}
	})
}

func TestDeleteBook(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	h := NewBookHandler(db)

	// Create a book
	body := bytes.NewReader(mustEncode(models.CreateBookRequest{
		Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441172719",
	}))
	req := httptest.NewRequest(http.MethodPost, "/books", body)
	rec := httptest.NewRecorder()
	h.CreateBook(rec, req)

	var created models.Book
	json.NewDecoder(rec.Body).Decode(&created)

	// Test: delete existing book
	t.Run("delete existing book", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodDelete, "/books/"+created.ID, nil)
		rec := httptest.NewRecorder()
		h.DeleteBook(rec, req)

		if rec.Code != http.StatusOK {
			t.Errorf("status = %d; want 200", rec.Code)
		}

		// Verify it's gone
		var resp map[string]string
		json.NewDecoder(rec.Body).Decode(&resp)
		if resp["message"] != "book deleted successfully" {
			t.Errorf("unexpected message: %s", resp["message"])
		}
	})

	// Test: delete non-existent book
	t.Run("delete non-existent book", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodDelete, "/books/999", nil)
		rec := httptest.NewRecorder()
		h.DeleteBook(rec, req)

		if rec.Code != http.StatusNotFound {
			t.Errorf("status = %d; want 404", rec.Code)
		}
	})
}

func TestFullLifecycle(t *testing.T) {
	db := setupTestDB(t)
	defer db.Close()

	h := NewBookHandler(db)

	// 1. Create
	title := "Test Book"
	author := "Test Author"
	year := 2024
	isbn := "111-222"

	createBody := bytes.NewReader(mustEncode(models.CreateBookRequest{
		Title: title, Author: author, Year: year, ISBN: isbn,
	}))
	req := httptest.NewRequest(http.MethodPost, "/books", createBody)
	rec := httptest.NewRecorder()
	h.CreateBook(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("create failed: %d %s", rec.Code, rec.Body.String())
	}

	var book models.Book
	json.NewDecoder(rec.Body).Decode(&book)

	// 2. Read
	req = httptest.NewRequest(http.MethodGet, "/books/"+book.ID, nil)
	rec = httptest.NewRecorder()
	h.GetBook(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("get failed: %d %s", rec.Code, rec.Body.String())
	}
	json.NewDecoder(rec.Body).Decode(&book)
	if book.Title != title {
		t.Errorf("title mismatch after get: %q", book.Title)
	}

	// 3. Update
	newTitle := "Updated Title"
	payload := models.UpdateBookRequest{Title: &newTitle}
	uptBody := bytes.NewReader(mustEncode(payload))
	req = httptest.NewRequest(http.MethodPut, "/books/"+book.ID, uptBody)
	rec = httptest.NewRecorder()
	h.UpdateBook(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("update failed: %d %s", rec.Code, rec.Body.String())
	}
	json.NewDecoder(rec.Body).Decode(&book)
	if book.Title != newTitle {
		t.Errorf("title mismatch after update: %q", book.Title)
	}

	// 4. List
	req = httptest.NewRequest(http.MethodGet, "/books?author=Test%20Author", nil)
	rec = httptest.NewRecorder()
	h.ListBooks(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("list failed: %d %s", rec.Code, rec.Body.String())
	}
	var books []models.Book
	json.NewDecoder(rec.Body).Decode(&books)
	if len(books) != 1 {
		t.Errorf("expected 1 book in list, got %d", len(books))
	}

	// 5. Delete
	req = httptest.NewRequest(http.MethodDelete, "/books/"+book.ID, nil)
	rec = httptest.NewRecorder()
	h.DeleteBook(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("delete failed: %d %s", rec.Code, rec.Body.String())
	}

	// Verify it's gone
	req = httptest.NewRequest(http.MethodGet, "/books/"+book.ID, nil)
	rec = httptest.NewRecorder()
	h.GetBook(rec, req)
	if rec.Code != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", rec.Code)
	}
}

func mustEncode(v interface{}) []byte {
	data, err := json.Marshal(v)
	if err != nil {
		panic(err)
	}
	return data
}
