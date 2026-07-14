package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// createTestServer returns a Server backed by an in-memory SQLite database.
func createTestServer() *Server {
	db, err := NewDatabase(":memory:")
	if err != nil {
		panic("failed to create test database: " + err.Error())
	}
	return NewServer(db)
}

// --- Acceptance Tests: executable specification driven by the problem domain ---

func TestAcceptance_HealthCheckReturns200(t *testing.T) {
	srv := createTestServer()
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()

	srv.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var body map[string]string
	json.NewDecoder(w.Body).Decode(&body)
	if body["status"] != "ok" {
		t.Errorf("expected status 'ok', got %q", body["status"])
	}
}

func TestAcceptance_CreateBookReturns201(t *testing.T) {
	srv := createTestServer()
	payload, _ := json.Marshal(Book{Title: "The Go Way", Author: "Jane Smith", Year: 2024, ISBN: "978-0-00-000001"})
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	srv.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201 Created, got %d — body: %s", w.Code, w.Body.String())
	}

	var book Book
	json.NewDecoder(w.Body).Decode(&book)
	if book.Title != "The Go Way" {
		t.Errorf("expected title 'The Go Way', got %q", book.Title)
	}
	if book.ID == 0 {
		t.Error("expected created book to have a non-zero ID")
	}
}

func TestAcceptance_ListBooksReturnsEmptyListInitially(t *testing.T) {
	srv := createTestServer()
	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()

	srv.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.NewDecoder(w.Body).Decode(&books)
	if len(books) != 0 {
		t.Errorf("expected empty list, got %d books", len(books))
	}
}

func TestAcceptance_CreateAndGetBookById(t *testing.T) {
	srv := createTestServer()

	// Create a book
	payload, _ := json.Marshal(Book{Title: "Atomic Habits", Author: "James Clear", Year: 2018, ISBN: "978-0-7352-1165"})
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %d %s", w.Code, w.Body.String())
	}
	var created Book
	json.NewDecoder(w.Body).Decode(&created)

	// Get the book by ID
	req2 := httptest.NewRequest("GET", "/books/1", nil)
	w2 := httptest.NewRecorder()
	srv.ServeHTTP(w2, req2)

	if w2.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d — body: %s", w2.Code, w2.Body.String())
	}

	var fetched Book
	json.NewDecoder(w2.Body).Decode(&fetched)
	if fetched.Title != "Atomic Habits" {
		t.Errorf("expected title 'Atomic Habits', got %q", fetched.Title)
	}
	if fetched.Author != "James Clear" {
		t.Errorf("expected author 'James Clear', got %q", fetched.Author)
	}
	if fetched.Year != 2018 {
		t.Errorf("expected year 2018, got %d", fetched.Year)
	}
	if fetched.ISBN != "978-0-7352-1165" {
		t.Errorf("expected isbn '978-0-7352-1165', got %q", fetched.ISBN)
	}
}

func TestAcceptance_ListBooksByAuthorFilter(t *testing.T) {
	srv := createTestServer()

	// Create three books — two by the same author, one by another
	payloads := []Book{
		{Title: "Clean Code", Author: "Robert Martin", Year: 2008, ISBN: "isbn1"},
		{Title: "Refactoring", Author: "Martin Fowler", Year: 1999, ISBN: "isbn2"},
		{Title: "SOLID Design", Author: "Robert Martin", Year: 2020, ISBN: "isbn3"},
	}

	for _, p := range payloads {
		b, _ := json.Marshal(p)
		req := httptest.NewRequest("POST", "/books", bytes.NewReader(b))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		srv.ServeHTTP(w, req)
		if w.Code != http.StatusCreated {
			t.Fatalf("create book %s failed: %s", p.Title, w.Body.String())
		}
	}

	// Filter by Robert Martin — should return exactly 2
	req := httptest.NewRequest("GET", "/books?author=Robert+Martin", nil)
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.NewDecoder(w.Body).Decode(&books)
	if len(books) != 2 {
		t.Errorf("expected 2 books by Robert Martin, got %d", len(books))
	}
	for _, b := range books {
		if b.Author != "Robert Martin" {
			t.Errorf("unexpected author %q in filtered results", b.Author)
		}
	}
}

func TestAcceptance_UpdateBookReturns200(t *testing.T) {
	srv := createTestServer()

	// Create a book first
	payload, _ := json.Marshal(Book{Title: "Old Title", Author: "Old Author", Year: 2000, ISBN: "old"})
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %s", w.Body.String())
	}

	// Update it
	update, _ := json.Marshal(Book{Title: "New Title", Author: "New Author", Year: 2025, ISBN: "new-isbn"})
	req2 := httptest.NewRequest("PUT", "/books/1", bytes.NewReader(update))
	req2.Header.Set("Content-Type", "application/json")
	w2 := httptest.NewRecorder()
	srv.ServeHTTP(w2, req2)

	if w2.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d — body: %s", w2.Code, w2.Body.String())
	}

	var updated Book
	json.NewDecoder(w2.Body).Decode(&updated)
	if updated.Title != "New Title" {
		t.Errorf("expected title 'New Title', got %q", updated.Title)
	}
	if updated.ISBN != "new-isbn" {
		t.Errorf("expected isbn 'new-isbn', got %q", updated.ISBN)
	}
}

func TestAcceptance_DeleteBookReturns204(t *testing.T) {
	srv := createTestServer()

	// Create a book
	payload, _ := json.Marshal(Book{Title: "ToDelete", Author: "Delete Me", Year: 2023, ISBN: "x"})
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %s", w.Body.String())
	}

	// Delete it
	req2 := httptest.NewRequest("DELETE", "/books/1", nil)
	w2 := httptest.NewRecorder()
	srv.ServeHTTP(w2, req2)

	if w2.Code != http.StatusNoContent {
		t.Errorf("expected status 204 No Content, got %d", w2.Code)
	}

	// Verify it is gone
	req3 := httptest.NewRequest("GET", "/books/1", nil)
	w3 := httptest.NewRecorder()
	srv.ServeHTTP(w3, req3)
	if w3.Code != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", w3.Code)
	}
}

func TestAcceptance_CreateBookMissingTitleReturns400(t *testing.T) {
	srv := createTestServer()
	payload, _ := json.Marshal(Book{Author: "Only Author"})
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	srv.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d — body: %s", w.Code, w.Body.String())
	}

	var errResp map[string]string
	json.NewDecoder(w.Body).Decode(&errResp)
	if errResp["error"] != "title is required" {
		t.Errorf("expected error 'title is required', got %q", errResp["error"])
	}
}

func TestAcceptance_CreateBookMissingAuthorReturns400(t *testing.T) {
	srv := createTestServer()
	payload, _ := json.Marshal(Book{Title: "Only Title"})
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	srv.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d — body: %s", w.Code, w.Body.String())
	}

	var errResp map[string]string
	json.NewDecoder(w.Body).Decode(&errResp)
	if errResp["error"] != "author is required" {
		t.Errorf("expected error 'author is required', got %q", errResp["error"])
	}
}

func TestAcceptance_GetNonExistentBookReturns404(t *testing.T) {
	srv := createTestServer()
	req := httptest.NewRequest("GET", "/books/9999", nil)
	w := httptest.NewRecorder()

	srv.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestAcceptance_UpdateNonExistentBookReturns404(t *testing.T) {
	srv := createTestServer()
	payload, _ := json.Marshal(Book{Title: "Ghost", Author: "Nobody", Year: 2020, ISBN: "0"})
	req := httptest.NewRequest("PUT", "/books/9999", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	srv.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestAcceptance_DeleteNonExistentBookReturns404(t *testing.T) {
	srv := createTestServer()
	req := httptest.NewRequest("DELETE", "/books/9999", nil)
	w := httptest.NewRecorder()

	srv.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestAcceptance_UpdateBookWithMissingTitleReturns400(t *testing.T) {
	srv := createTestServer()

	// Create a book first
	payload, _ := json.Marshal(Book{Title: "Original", Author: "Original", Year: 2020, ISBN: "x"})
	req := httptest.NewRequest("POST", "/books", bytes.NewReader(payload))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)
	if w.Code != http.StatusCreated {
		t.Fatalf("create failed: %s", w.Body.String())
	}

	// Update with missing title
	update, _ := json.Marshal(Book{Title: "", Author: "Updated", Year: 2025, ISBN: "y"})
	req2 := httptest.NewRequest("PUT", "/books/1", bytes.NewReader(update))
	req2.Header.Set("Content-Type", "application/json")
	w2 := httptest.NewRecorder()
	srv.ServeHTTP(w2, req2)

	if w2.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d — body: %s", w2.Code, w2.Body.String())
	}

	var errResp map[string]string
	json.NewDecoder(w2.Body).Decode(&errResp)
	if errResp["error"] != "title is required" {
		t.Errorf("expected error 'title is required', got %q", errResp["error"])
	}
}

func TestAcceptance_MultipleBooksListedInOrder(t *testing.T) {
	srv := createTestServer()

	// Create three books
	for i, book := range []Book{
		{Title: "First Book", Author: "Author A", Year: 2010, ISBN: "a"},
		{Title: "Second Book", Author: "Author B", Year: 2015, ISBN: "b"},
		{Title: "Third Book", Author: "Author A", Year: 2020, ISBN: "c"},
	} {
		b, _ := json.Marshal(book)
		req := httptest.NewRequest("POST", "/books", bytes.NewReader(b))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		srv.ServeHTTP(w, req)
		if w.Code != http.StatusCreated {
			t.Fatalf("create book %d failed: %s", i, w.Body.String())
		}
	}

	req := httptest.NewRequest("GET", "/books", nil)
	w := httptest.NewRecorder()
	srv.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	var books []Book
	json.NewDecoder(w.Body).Decode(&books)
	if len(books) != 3 {
		t.Fatalf("expected 3 books, got %d", len(books))
	}
	if books[0].Title != "First Book" {
		t.Errorf("expected first book 'First Book', got %q", books[0].Title)
	}
	if books[1].Title != "Second Book" {
		t.Errorf("expected second book 'Second Book', got %q", books[1].Title)
	}
	if books[2].Title != "Third Book" {
		t.Errorf("expected third book 'Third Book', got %q", books[2].Title)
	}
}
