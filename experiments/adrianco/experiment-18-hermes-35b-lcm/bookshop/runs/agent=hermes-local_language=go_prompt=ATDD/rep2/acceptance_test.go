package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

// newTestApp creates a fresh App with an in-memory SQLite database for testing.
func newTestApp(t *testing.T) *App {
	t.Helper()
	repo, err := NewBookRepository(":memory:")
	if err != nil {
		t.Fatalf("failed to create test repo: %v", err)
	}
	return &App{Repo: repo}
}

// helperRequest creates and executes an HTTP request against the test app's router.
func helperRequest(t *testing.T, app *App, method, path string, body interface{}) *http.Response {
	t.Helper()
	var bodyReader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("failed to marshal request body: %v", err)
		}
		bodyReader = bytes.NewReader(data)
	}

	req := httptest.NewRequest(method, path, bodyReader)
	w := httptest.NewRecorder()

	router(app).ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode == http.StatusInternalServerError {
		bodyBytes, _ := io.ReadAll(resp.Body)
		t.Logf("GET /books response (500): %s", string(bodyBytes))
	}
	return resp
}

// router returns an http.Handler that routes all the required endpoints.
func router(app *App) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", app.HealthCheck)
	mux.HandleFunc("/books/", app.handleBookByID)
	mux.HandleFunc("/books", app.handleBooks)
	return mux
}

// -------------------------------------------------------------------
// Acceptance Tests — external client perspective, each starts clean
// -------------------------------------------------------------------

// AT-001: Health check returns 200 with JSON status ok
func TestAcceptance_HealthCheckReturnsOk(t *testing.T) {
	app := newTestApp(t)

	resp := helperRequest(t, app, http.MethodGet, "/health", nil)

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	bodyBytes, _ := io.ReadAll(resp.Body)
	var result map[string]string
	if err := json.Unmarshal(bodyBytes, &result); err != nil {
		t.Fatalf("expected valid JSON response, got error: %v", err)
	}
	if result["status"] != "ok" {
		t.Errorf("expected status 'ok', got %q", result["status"])
	}
}

// AT-002: Create a book — POST /books returns 201 with created book
func TestAcceptance_CreateBookReturns201(t *testing.T) {
	app := newTestApp(t)

	book := map[string]interface{}{
		"title":  "The Go Programming Language",
		"author": "Alan Donovan",
		"year":   2015,
		"isbn":   "978-0134190440",
	}

	resp := helperRequest(t, app, http.MethodPost, "/books", book)

	if resp.StatusCode != http.StatusCreated {
		t.Errorf("expected status 201 Created, got %d", resp.StatusCode)
	}

	var createdBook Book
	if err := json.NewDecoder(resp.Body).Decode(&createdBook); err != nil {
		t.Fatalf("expected valid JSON response, got error: %v", err)
	}
	if createdBook.ID == 0 {
		t.Error("expected auto-generated ID in response, got 0")
	}
	if createdBook.Title != "The Go Programming Language" {
		t.Errorf("expected title 'The Go Programming Language', got %q", createdBook.Title)
	}
}

// AT-003: Reject creating a book with missing title — POST /books returns 400
func TestAcceptance_RejectBookWithMissingTitle(t *testing.T) {
	app := newTestApp(t)

	book := map[string]interface{}{
		"author": "Some Author",
		"year":   2020,
		"isbn":   "999",
	}

	resp := helperRequest(t, app, http.MethodPost, "/books", book)

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400 Bad Request, got %d", resp.StatusCode)
	}
}

// AT-004: Reject creating a book with missing author — POST /books returns 400
func TestAcceptance_RejectBookWithMissingAuthor(t *testing.T) {
	app := newTestApp(t)

	book := map[string]interface{}{
		"title": "Some Book",
		"year":  2020,
		"isbn":  "999",
	}

	resp := helperRequest(t, app, http.MethodPost, "/books", book)

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400 Bad Request, got %d", resp.StatusCode)
	}
}

// AT-005: Reject creating a book with both title and author missing
func TestAcceptance_RejectBookWithMissingTitleAndAuthor(t *testing.T) {
	app := newTestApp(t)

	book := map[string]interface{}{
		"year": 2020,
		"isbn": "999",
	}

	resp := helperRequest(t, app, http.MethodPost, "/books", book)

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400 Bad Request, got %d", resp.StatusCode)
	}
}

// AT-006: List all books — GET /books returns 200 with JSON array
func TestAcceptance_ListAllBooks(t *testing.T) {
	app := newTestApp(t)

	// Seed some books
	for i := 0; i < 3; i++ {
		book := map[string]interface{}{
			"title":  fmt.Sprintf("Book %d", i+1),
			"author": "Test Author",
			"year":   2020 + i,
			"isbn":   fmt.Sprintf("isbn%d", i+1),
		}
		resp := helperRequest(t, app, http.MethodPost, "/books", book)
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("failed to seed book %d: status %d", i+1, resp.StatusCode)
		}
	}

	resp := helperRequest(t, app, http.MethodGet, "/books", nil)

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var books []Book
	if err := json.NewDecoder(resp.Body).Decode(&books); err != nil {
		t.Fatalf("expected valid JSON array response, got error: %v", err)
	}
	if len(books) != 3 {
		t.Errorf("expected 3 books, got %d", len(books))
	}
}

// AT-007: List all books returns empty array when no books exist
func TestAcceptance_ListBooksReturnsEmptyArray(t *testing.T) {
	app := newTestApp(t)

	resp := helperRequest(t, app, http.MethodGet, "/books", nil)

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var books []Book
	if err := json.NewDecoder(resp.Body).Decode(&books); err != nil {
		t.Fatalf("expected valid JSON array, got error: %v", err)
	}
	if len(books) != 0 {
		t.Errorf("expected empty array, got %d books", len(books))
	}
}

// AT-008: Filter books by author — GET /books?author=... returns matching books
func TestAcceptance_FilterBooksByAuthor(t *testing.T) {
	app := newTestApp(t)

	// Seed books for two authors
	aliceBooks := []map[string]interface{}{
		{"title": "Alice Book 1", "author": "Alice", "year": 2020, "isbn": "a1"},
		{"title": "Alice Book 2", "author": "Alice", "year": 2021, "isbn": "a2"},
	}
	bobBooks := []map[string]interface{}{
		{"title": "Bob Book 1", "author": "Bob", "year": 2020, "isbn": "b1"},
	}
	for _, b := range aliceBooks {
		resp := helperRequest(t, app, http.MethodPost, "/books", b)
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("failed to seed alice book: status %d", resp.StatusCode)
		}
	}
	for _, b := range bobBooks {
		resp := helperRequest(t, app, http.MethodPost, "/books", b)
		if resp.StatusCode != http.StatusCreated {
			t.Fatalf("failed to seed bob book: status %d", resp.StatusCode)
		}
	}

	resp := helperRequest(t, app, http.MethodGet, "/books?author=Alice", nil)

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var books []Book
	if err := json.NewDecoder(resp.Body).Decode(&books); err != nil {
		t.Fatalf("expected valid JSON array, got error: %v", err)
	}
	if len(books) != 2 {
		t.Errorf("expected 2 books by Alice, got %d", len(books))
	}
	for _, b := range books {
		if b.Author != "Alice" {
			t.Errorf("expected all results to be by Alice, got %q", b.Author)
		}
	}
}

// AT-009: Get a single book — GET /books/{id} returns 200 with book
func TestAcceptance_GetSingleBook(t *testing.T) {
	app := newTestApp(t)

	book := map[string]interface{}{
		"title":  "Effective Go",
		"author": "Rob Pike",
		"year":   2015,
		"isbn":   "eg001",
	}
	createResp := helperRequest(t, app, http.MethodPost, "/books", book)
	if createResp.StatusCode != http.StatusCreated {
		t.Fatalf("failed to seed book: status %d", createResp.StatusCode)
	}

	var createdBook Book
	json.NewDecoder(createResp.Body).Decode(&createdBook)

	resp := helperRequest(t, app, http.MethodGet, fmt.Sprintf("/books/%d", createdBook.ID), nil)

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var gotBook Book
	if err := json.NewDecoder(resp.Body).Decode(&gotBook); err != nil {
		t.Fatalf("expected valid JSON, got error: %v", err)
	}
	if gotBook.ID != createdBook.ID {
		t.Errorf("expected ID %d, got %d", createdBook.ID, gotBook.ID)
	}
	if gotBook.Title != createdBook.Title {
		t.Errorf("expected title %q, got %q", createdBook.Title, gotBook.Title)
	}
}

// AT-010: Get a non-existent book returns 404
func TestAcceptance_GetNonExistentBookReturns404(t *testing.T) {
	app := newTestApp(t)

	resp := helperRequest(t, app, http.MethodGet, "/books/9999", nil)

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", resp.StatusCode)
	}
}

// AT-011: Update a book — PUT /books/{id} returns 200 with updated book
func TestAcceptance_UpdateBook(t *testing.T) {
	app := newTestApp(t)

	book := map[string]interface{}{
		"title":  "Original",
		"author": "Author",
		"year":   2020,
		"isbn":   "upd01",
	}
	createResp := helperRequest(t, app, http.MethodPost, "/books", book)
	var createdBook Book
	json.NewDecoder(createResp.Body).Decode(&createdBook)

	updated := map[string]interface{}{
		"title":  "Updated Title",
		"author": "Updated Author",
		"year":   2022,
		"isbn":   "upd01",
	}
	updatePath := fmt.Sprintf("/books/%d", createdBook.ID)
	resp := helperRequest(t, app, http.MethodPut, updatePath, updated)

	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var gotBook Book
	if err := json.NewDecoder(resp.Body).Decode(&gotBook); err != nil {
		t.Fatalf("expected valid JSON, got error: %v", err)
	}
	if gotBook.Title != "Updated Title" {
		t.Errorf("expected title 'Updated Title', got %q", gotBook.Title)
	}
	if gotBook.Author != "Updated Author" {
		t.Errorf("expected author 'Updated Author', got %q", gotBook.Author)
	}
	if gotBook.Year != 2022 {
		t.Errorf("expected year 2022, got %d", gotBook.Year)
	}
}

// AT-012: Update a non-existent book returns 404
func TestAcceptance_UpdateNonExistentBookReturns404(t *testing.T) {
	app := newTestApp(t)

	update := map[string]interface{}{
		"title":  "Ghost",
		"author": "Nobody",
		"year":   2020,
		"isbn":   "ghost",
	}
	resp := helperRequest(t, app, http.MethodPut, "/books/9999", update)

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", resp.StatusCode)
	}
}

// AT-013: Update a book with missing title returns 400
func TestAcceptance_UpdateBookWithMissingTitleReturns400(t *testing.T) {
	app := newTestApp(t)

	book := map[string]interface{}{
		"title":  "Existing",
		"author": "Author",
		"year":   2020,
		"isbn":   "upm01",
	}
	createResp := helperRequest(t, app, http.MethodPost, "/books", book)
	var createdBook Book
	json.NewDecoder(createResp.Body).Decode(&createdBook)

	update := map[string]interface{}{
		"title":  "",
		"author": "Author",
		"year":   2021,
		"isbn":   "upm01",
	}
	updatePath := fmt.Sprintf("/books/%d", createdBook.ID)
	resp := helperRequest(t, app, http.MethodPut, updatePath, update)

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", resp.StatusCode)
	}
}

// AT-014: Delete a book — DELETE /books/{id} returns 204
func TestAcceptance_DeleteBook(t *testing.T) {
	app := newTestApp(t)

	book := map[string]interface{}{
		"title":  "To Delete",
		"author": "Author",
		"year":   2020,
		"isbn":   "del01",
	}
	createResp := helperRequest(t, app, http.MethodPost, "/books", book)
	var createdBook Book
	json.NewDecoder(createResp.Body).Decode(&createdBook)

	resp := helperRequest(t, app, http.MethodDelete, fmt.Sprintf("/books/%d", createdBook.ID), nil)

	if resp.StatusCode != http.StatusNoContent {
		t.Errorf("expected status 204, got %d", resp.StatusCode)
	}

	// Verify it's gone
	getResp := helperRequest(t, app, http.MethodGet, fmt.Sprintf("/books/%d", createdBook.ID), nil)
	if getResp.StatusCode != http.StatusNotFound {
		t.Errorf("expected deleted book to return 404, got %d", getResp.StatusCode)
	}
}

// AT-015: Delete a non-existent book returns 404
func TestAcceptance_DeleteNonExistentBookReturns404(t *testing.T) {
	app := newTestApp(t)

	resp := helperRequest(t, app, http.MethodDelete, "/books/9999", nil)

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", resp.StatusCode)
	}
}

// AT-016: Full lifecycle — create, read, update, delete
func TestAcceptance_FullLifecycle(t *testing.T) {
	app := newTestApp(t)

	// Create
	book := map[string]interface{}{
		"title":  "Lifecycle Test",
		"author": "Lifecycle Author",
		"year":   2023,
		"isbn":   "lc001",
	}
	createResp := helperRequest(t, app, http.MethodPost, "/books", book)
	if createResp.StatusCode != http.StatusCreated {
		t.Fatalf("create failed: status %d", createResp.StatusCode)
	}
	var createdBook Book
	json.NewDecoder(createResp.Body).Decode(&createdBook)

	// Read
	getResp := helperRequest(t, app, http.MethodGet, fmt.Sprintf("/books/%d", createdBook.ID), nil)
	if getResp.StatusCode != http.StatusOK {
		t.Fatalf("get failed: status %d", getResp.StatusCode)
	}
	var gotBook Book
	json.NewDecoder(getResp.Body).Decode(&gotBook)
	if gotBook.Title != "Lifecycle Test" {
		t.Errorf("expected 'Lifecycle Test', got %q", gotBook.Title)
	}

	// Update
	update := map[string]interface{}{
		"title":  "Updated Lifecycle",
		"author": "Lifecycle Author",
		"year":   2024,
		"isbn":   "lc001",
	}
	updatePath := fmt.Sprintf("/books/%d", createdBook.ID)
	updateResp := helperRequest(t, app, http.MethodPut, updatePath, update)
	if updateResp.StatusCode != http.StatusOK {
		t.Fatalf("update failed: status %d", updateResp.StatusCode)
	}
	var updatedBook Book
	json.NewDecoder(updateResp.Body).Decode(&updatedBook)
	if updatedBook.Title != "Updated Lifecycle" {
		t.Errorf("expected 'Updated Lifecycle', got %q", updatedBook.Title)
	}

	// Delete
	deleteResp := helperRequest(t, app, http.MethodDelete, updatePath, nil)
	if deleteResp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete failed: status %d", deleteResp.StatusCode)
	}

	// Verify gone
	getResp2 := helperRequest(t, app, http.MethodGet, updatePath, nil)
	if getResp2.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", getResp2.StatusCode)
	}
}

// AT-017: Duplicate ISBN is rejected — returns 409 Conflict
func TestAcceptance_DuplicateISBNReturnsConflict(t *testing.T) {
	app := newTestApp(t)

	book := map[string]interface{}{
		"title":  "First",
		"author": "Author",
		"year":   2020,
		"isbn":   "dup01",
	}
	helperRequest(t, app, http.MethodPost, "/books", book)

	// Try to create another book with same ISBN
	book2 := map[string]interface{}{
		"title":  "Duplicate",
		"author": "Another Author",
		"year":   2021,
		"isbn":   "dup01",
	}
	resp := helperRequest(t, app, http.MethodPost, "/books", book2)

	if resp.StatusCode != http.StatusConflict {
		t.Errorf("expected status 409 Conflict for duplicate ISBN, got %d", resp.StatusCode)
	}
}

// AT-018: Invalid JSON body returns 400
func TestAcceptance_InvalidJSONBodyReturns400(t *testing.T) {
	app := newTestApp(t)

	req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader([]byte("not json")))
	w := httptest.NewRecorder()
	router(app).ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400 for invalid JSON, got %d", resp.StatusCode)
	}
}

// AT-019: POST /books/{id} returns method not allowed
func TestAcceptance_MethodNotAllowedOnBooksID(t *testing.T) {
	app := newTestApp(t)

	resp := helperRequest(t, app, http.MethodPost, "/books/1", nil)

	if resp.StatusCode != http.StatusMethodNotAllowed {
		t.Errorf("expected status 405, got %d", resp.StatusCode)
	}
}

