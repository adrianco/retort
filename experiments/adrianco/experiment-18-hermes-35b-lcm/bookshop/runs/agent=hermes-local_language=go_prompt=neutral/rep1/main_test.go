package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func newTestStoreAndHandler(t *testing.T) (*BookStore, *BookHandler) {
	t.Helper()
	store, err := NewBookStore(":memory:")
	if err != nil {
		t.Fatalf("failed to create store: %v", err)
	}
	return store, NewBookHandler(store)
}

func createBookRequest(t *testing.T, req CreateBookRequest) *http.Request {
	t.Helper()
	body, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}
	return httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
}

func getBookRequest(path string) *http.Request {
	return httptest.NewRequest(http.MethodGet, path, nil)
}

func testBook() CreateBookRequest {
	return CreateBookRequest{
		Title:  "The Great Gatsby",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}
}

func TestHealth(t *testing.T) {
	store, handler := newTestStoreAndHandler(t)
	defer store.Close()

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()

	handler.Health(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp map[string]string
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if resp["status"] != "ok" {
		t.Errorf("expected status 'ok', got '%s'", resp["status"])
	}
}

func TestCreateBook(t *testing.T) {
	store, handler := newTestStoreAndHandler(t)
	defer store.Close()

	req := createBookRequest(t, testBook())
	w := httptest.NewRecorder()

	handler.createBook(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d: %s", w.Code, w.Body.String())
	}

	var book Book
	if err := json.NewDecoder(w.Body).Decode(&book); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if book.ID != 1 {
		t.Errorf("expected ID 1, got %d", book.ID)
	}
	if book.Title != "The Great Gatsby" {
		t.Errorf("expected title 'The Great Gatsby', got '%s'", book.Title)
	}
	if book.Author != "F. Scott Fitzgerald" {
		t.Errorf("expected author 'F. Scott Fitzgerald', got '%s'", book.Author)
	}
	if book.Year != 1925 {
		t.Errorf("expected year 1925, got %d", book.Year)
	}
	if book.ISBN != "978-0743273565" {
		t.Errorf("expected isbn '978-0743273565', got '%s'", book.ISBN)
	}
}

func TestCreateBookValidation(t *testing.T) {
	tests := []struct {
		name   string
		req    CreateBookRequest
		field  string
	}{
		{
			name:   "missing title",
			req:    CreateBookRequest{Author: "Test Author", Year: 2020, ISBN: "123"},
			field:  "title",
		},
		{
			name:   "missing author",
			req:    CreateBookRequest{Title: "Test Title", Year: 2020, ISBN: "123"},
			field:  "author",
		},
		{
			name:   "missing both",
			req:    CreateBookRequest{Year: 2020},
			field:  "title",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			store, handler := newTestStoreAndHandler(t)
			defer store.Close()

			body, err := json.Marshal(tt.req)
			if err != nil {
				t.Fatalf("failed to marshal: %v", err)
			}
			req := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
			w := httptest.NewRecorder()

			handler.createBook(w, req)

			if w.Code != http.StatusBadRequest {
				t.Errorf("expected status 400, got %d", w.Code)
			}

			var resp ValidationErrorsBody
			if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
				t.Fatalf("failed to decode response: %v", err)
			}

			if len(resp.Errors) == 0 {
				t.Fatal("expected validation errors, got none")
			}

			found := false
			for _, e := range resp.Errors {
				if e.Field == tt.field {
					found = true
				}
			}
			if !found {
				t.Errorf("expected validation error for field '%s', got errors: %+v", tt.field, resp.Errors)
			}
		})
	}
}

func TestListBooks(t *testing.T) {
	store, handler := newTestStoreAndHandler(t)
	defer store.Close()

	testBook1 := testBook()
	testBook2 := CreateBookRequest{
		Title:  "1984",
		Author: "George Orwell",
		Year:   1949,
		ISBN:   "978-0451524935",
	}

	body1, _ := json.Marshal(testBook1)
	body2, _ := json.Marshal(testBook2)

	req1 := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body1))
	w1 := httptest.NewRecorder()
	handler.createBook(w1, req1)

	req2 := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body2))
	w2 := httptest.NewRecorder()
	handler.createBook(w2, req2)

	listReq := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()
	handler.listBooks(w, listReq)

	if w.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if len(books) != 2 {
		t.Errorf("expected 2 books, got %d", len(books))
	}

	authorFilterReq := httptest.NewRequest(http.MethodGet, "/books?author=F.+Scott+Fitzgerald", nil)
	filterW := httptest.NewRecorder()
	handler.listBooks(filterW, authorFilterReq)

	if filterW.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", filterW.Code)
	}

	var filtered []Book
	if err := json.NewDecoder(filterW.Body).Decode(&filtered); err != nil {
		t.Fatalf("failed to decode filtered response: %v", err)
	}

	if len(filtered) != 1 {
		t.Errorf("expected 1 filtered book, got %d", len(filtered))
	}
	if filtered[0].Author != "F. Scott Fitzgerald" {
		t.Errorf("expected filtered author 'F. Scott Fitzgerald', got '%s'", filtered[0].Author)
	}
}

func TestGetBook(t *testing.T) {
	store, handler := newTestStoreAndHandler(t)
	defer store.Close()

	body, _ := json.Marshal(testBook())
	createReq := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	createW := httptest.NewRecorder()
	handler.createBook(createW, createReq)

	var book Book
	json.NewDecoder(createW.Body).Decode(&book)

	w := httptest.NewRecorder()
	handler.getBook(w, book.ID)

	if w.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d: %s", w.Code, w.Body.String())
	}

	var got Book
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if got.ID != book.ID {
		t.Errorf("expected ID %d, got %d", book.ID, got.ID)
	}
	if got.Title != book.Title {
		t.Errorf("expected title '%s', got '%s'", book.Title, got.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	_, handler := newTestStoreAndHandler(t)
	defer handler.Store.Close()

	w := httptest.NewRecorder()
	handler.getBook(w, 999)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}

	var resp ErrorResponse
	if err := json.NewDecoder(w.Body).Decode(&resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if resp.Error != "book not found" {
		t.Errorf("expected error 'book not found', got '%s'", resp.Error)
	}
}

func TestUpdateBook(t *testing.T) {
	store, handler := newTestStoreAndHandler(t)
	defer store.Close()

	body, _ := json.Marshal(testBook())
	createReq := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	createW := httptest.NewRecorder()
	handler.createBook(createW, createReq)

	var created Book
	json.NewDecoder(createW.Body).Decode(&created)

	updateReq := CreateBookRequest{
		Title:  "The Great Gatsby (Revised Edition)",
		Author: "F. Scott Fitzgerald",
		Year:   1925,
		ISBN:   "978-0743273565",
	}
	updateBody, _ := json.Marshal(updateReq)
	updateHttpReq := httptest.NewRequest(http.MethodPut, "/books/"+strconv.Itoa(created.ID), bytes.NewReader(updateBody))
	updateW := httptest.NewRecorder()
	handler.updateBook(updateW, created.ID, updateHttpReq)

	if updateW.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d: %s", updateW.Code, updateW.Body.String())
	}

	var updated Book
	if err := json.NewDecoder(updateW.Body).Decode(&updated); err != nil {
		t.Fatalf("failed to decode updated book: %v", err)
	}

	if updated.Title != "The Great Gatsby (Revised Edition)" {
		t.Errorf("expected updated title, got '%s'", updated.Title)
	}
	if updated.ID != created.ID {
		t.Errorf("expected same ID, got %d vs %d", created.ID, updated.ID)
	}
}

func TestUpdateBookValidation(t *testing.T) {
	store, handler := newTestStoreAndHandler(t)
	defer store.Close()

	body, _ := json.Marshal(testBook())
	createReq := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	createW := httptest.NewRecorder()
	handler.createBook(createW, createReq)

	var created Book
	json.NewDecoder(createW.Body).Decode(&created)

	updateReq := CreateBookRequest{
		Title:  "",
		Author: "New Author",
		Year:   2020,
		ISBN:   "123",
	}
	updateBody, _ := json.Marshal(updateReq)
	updateReq2 := httptest.NewRequest(http.MethodPut, "/books/"+strconv.Itoa(created.ID), bytes.NewReader(updateBody))
	updateW := httptest.NewRecorder()
	handler.updateBook(updateW, created.ID, updateReq2)

	if updateW.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", updateW.Code)
	}

	var resp ValidationErrorsBody
	json.NewDecoder(updateW.Body).Decode(&resp)

	found := false
	for _, e := range resp.Errors {
		if e.Field == "title" {
			found = true
		}
	}
	if !found {
		t.Errorf("expected validation error for 'title' field")
	}
}

func TestDeleteBook(t *testing.T) {
	store, handler := newTestStoreAndHandler(t)
	defer store.Close()

	body, _ := json.Marshal(testBook())
	createReq := httptest.NewRequest(http.MethodPost, "/books", bytes.NewReader(body))
	createW := httptest.NewRecorder()
	handler.createBook(createW, createReq)

	var created Book
	json.NewDecoder(createW.Body).Decode(&created)

	deleteW := httptest.NewRecorder()
	handler.deleteBook(deleteW, created.ID)

	if deleteW.Code != http.StatusNoContent {
		t.Errorf("expected status 204, got %d", deleteW.Code)
	}

	getW := httptest.NewRecorder()
	handler.getBook(getW, created.ID)

	if getW.Code != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", getW.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	_, handler := newTestStoreAndHandler(t)
	defer handler.Store.Close()

	w := httptest.NewRecorder()
	handler.deleteBook(w, 999)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestCreateEmptyList(t *testing.T) {
	_, handler := newTestStoreAndHandler(t)
	defer handler.Store.Close()

	req := httptest.NewRequest(http.MethodGet, "/books", nil)
	w := httptest.NewRecorder()
	handler.listBooks(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", w.Code)
	}

	var books []Book
	if err := json.NewDecoder(w.Body).Decode(&books); err != nil {
		t.Fatalf("failed to decode: %v", err)
	}

	if len(books) != 0 {
		t.Errorf("expected empty list, got %d books", len(books))
	}
}
