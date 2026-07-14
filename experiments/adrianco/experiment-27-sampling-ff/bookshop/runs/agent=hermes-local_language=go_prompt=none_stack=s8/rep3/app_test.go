package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/gin-gonic/gin"
)

func resetDB() {
	os.Remove("./books.db")
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		panic(err)
	}
	createTable := `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`
	db.Exec(createTable)
}

func teardownDB() {
	if db != nil {
		db.Close()
	}
	os.Remove("./books.db")
	db = nil
}

func TestMain(m *testing.M) {
	gin.SetMode(gin.TestMode)
	resetDB()
	code := m.Run()
	teardownDB()
	os.Exit(code)
}


func setBookID(c *gin.Context, id string) {
	c.Params = gin.Params{{Key: "id", Value: id}}
}

func TestHealthCheck(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("GET", "/health", nil)
	healthCheck(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var body map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&body)
	if body["status"] != "ok" {
		t.Errorf("expected status 'ok', got %v", body["status"])
	}
}

func TestCreateBook(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "The Go Programming Language",
		Author: "Alan Donovan",
		Year:   2015,
		ISBN:   "978-0134190440",
	})

	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body))
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("expected status 201, got %d", resp.StatusCode)
	}

	var book Book
	json.NewDecoder(resp.Body).Decode(&book)
	if book.Title != "The Go Programming Language" {
		t.Errorf("expected title 'The Go Programming Language', got %s", book.Title)
	}
	if book.ID == 0 {
		t.Error("expected non-zero ID")
	}
}

func TestCreateBookValidation(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "",
		Author: "Test Author",
	})

	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body))
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", resp.StatusCode)
	}

	var errResp map[string]string
	json.NewDecoder(resp.Body).Decode(&errResp)
	if errResp["error"] != "title is required" {
		t.Errorf("expected 'title is required', got %s", errResp["error"])
	}
}

func TestCreateBookMissingAuthor(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "Some Book",
		Author: "",
	})

	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body))
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", resp.StatusCode)
	}

	var errResp map[string]string
	json.NewDecoder(resp.Body).Decode(&errResp)
	if errResp["error"] != "author is required" {
		t.Errorf("expected 'author is required', got %s", errResp["error"])
	}
}

func TestCreateBookInvalidJSON(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader([]byte("{invalid")))
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", resp.StatusCode)
	}
}

func TestListBooks(t *testing.T) {
	resetDB()
	defer teardownDB()

	// Insert test data via direct DB access so IDs are predictable
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "isbn-1")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "isbn-2")

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("GET", "/books", nil)
	listBooks(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var books []Book
	json.NewDecoder(resp.Body).Decode(&books)
	if len(books) != 2 {
		t.Errorf("expected 2 books, got %d", len(books))
	}
	if books[0].Title != "Book One" {
		t.Errorf("expected first book 'Book One', got %s", books[0].Title)
	}
	if books[1].Author != "Author B" {
		t.Errorf("expected second book author 'Author B', got %s", books[1].Author)
	}
}

func TestListBooksEmpty(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("GET", "/books", nil)
	listBooks(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var books []Book
	json.NewDecoder(resp.Body).Decode(&books)
	if len(books) != 0 {
		t.Errorf("expected empty list, got %d books", len(books))
	}
	if books == nil {
		t.Error("expected non-nil empty slice")
	}
}

func TestListBooksByAuthor(t *testing.T) {
	resetDB()
	defer teardownDB()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book One", "Author A", 2020, "isbn-3")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Two", "Author B", 2021, "isbn-4")
	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book Three", "Author A", 2022, "isbn-5")

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("GET", "/books?author=Author+A", nil)
	listBooks(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var books []Book
	json.NewDecoder(resp.Body).Decode(&books)
	if len(books) != 2 {
		t.Errorf("expected 2 books for Author A, got %d", len(books))
	}

	for _, b := range books {
		if b.Author != "Author A" {
			t.Errorf("expected all authors to be 'Author A', got %s", b.Author)
		}
	}

	w2 := httptest.NewRecorder()
	c2, _ := gin.CreateTestContext(w2)

	c2.Request, _ = http.NewRequest("GET", "/books?author=Author+Z", nil)
	listBooks(c2)

	resp2 := w2.Result()
	if resp2.StatusCode != http.StatusOK {
		t.Errorf("expected status 200 for non-existent author, got %d", resp2.StatusCode)
	}

	var emptyBooks []Book
	json.NewDecoder(resp2.Body).Decode(&emptyBooks)
	if len(emptyBooks) != 0 {
		t.Errorf("expected 0 books for non-existent author, got %d", len(emptyBooks))
	}
}

func TestGetBook(t *testing.T) {
	resetDB()
	defer teardownDB()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Test Book", "Test Author", 2023, "isbn-test")

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("GET", "/books/1", nil)
	getBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var book Book
	json.NewDecoder(resp.Body).Decode(&book)
	if book.Title != "Test Book" {
		t.Errorf("expected 'Test Book', got %s", book.Title)
	}
	if book.Author != "Test Author" {
		t.Errorf("expected 'Test Author', got %s", book.Author)
	}
	if book.ISBN != "isbn-test" {
		t.Errorf("expected 'isbn-test', got %s", book.ISBN)
	}
	if book.Year != 2023 {
		t.Errorf("expected year 2023, got %d", book.Year)
	}
}

func TestGetBookNotFound(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	setBookID(c, "999")

	c.Request, _ = http.NewRequest("GET", "/books/999", nil)
	getBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", resp.StatusCode)
	}

	var errResp map[string]string
	json.NewDecoder(resp.Body).Decode(&errResp)
	if errResp["error"] != "book not found" {
		t.Errorf("expected 'book not found', got %s", errResp["error"])
	}
}

func TestGetBookInvalidID(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	setBookID(c, "abc")

	c.Request, _ = http.NewRequest("GET", "/books/abc", nil)
	getBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", resp.StatusCode)
	}

	var errResp map[string]string
	json.NewDecoder(resp.Body).Decode(&errResp)
	if errResp["error"] != "invalid book ID" {
		t.Errorf("expected 'invalid book ID', got %s", errResp["error"])
	}
}

func TestUpdateBook(t *testing.T) {
	resetDB()
	defer teardownDB()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Old Title", "Author A", 2020, "isbn-update")

	body, _ := json.Marshal(UpdateBookRequest{
		Title:  "Updated Title",
		Author: "Author A Updated",
		Year:   2024,
		ISBN:   "isbn-updated",
	})

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("PUT", "/books/1", bytes.NewReader(body))
	updateBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var msgResp map[string]string
	json.NewDecoder(resp.Body).Decode(&msgResp)
	if msgResp["message"] != "book updated successfully" {
		t.Errorf("expected success message, got %s", msgResp["message"])
	}

	// Verify the update in DB
	var book Book
	db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = 1").Scan(
		&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN,
	)
	if book.Title != "Updated Title" {
		t.Errorf("expected updated title, got %s", book.Title)
	}
	if book.ISBN != "isbn-updated" {
		t.Errorf("expected updated ISBN, got %s", book.ISBN)
	}
	if book.Year != 2024 {
		t.Errorf("expected updated year, got %d", book.Year)
	}
}

func TestUpdateBookValidation(t *testing.T) {
	resetDB()
	defer teardownDB()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Book", "Author", 2023, "isbn-val")

	body, _ := json.Marshal(UpdateBookRequest{
		Title:  "",
		Author: "New Author",
	})

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("PUT", "/books/1", bytes.NewReader(body))
	updateBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", resp.StatusCode)
	}

	var errResp map[string]string
	json.NewDecoder(resp.Body).Decode(&errResp)
	if errResp["error"] != "title is required" {
		t.Errorf("expected 'title is required', got %s", errResp["error"])
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	resetDB()
	defer teardownDB()

	body, _ := json.Marshal(UpdateBookRequest{
		Title:  "New Title",
		Author: "New Author",
	})

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	setBookID(c, "999")

	c.Request, _ = http.NewRequest("PUT", "/books/999", bytes.NewReader(body))
	updateBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", resp.StatusCode)
	}

	var errResp map[string]string
	json.NewDecoder(resp.Body).Decode(&errResp)
	if errResp["error"] != "book not found" {
		t.Errorf("expected 'book not found', got %s", errResp["error"])
	}
}

func TestDeleteBook(t *testing.T) {
	resetDB()
	defer teardownDB()

	db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		"Delete Me", "Author A", 2023, "isbn-delete")

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("DELETE", "/books/1", nil)
	deleteBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var msgResp map[string]string
	json.NewDecoder(resp.Body).Decode(&msgResp)
	if msgResp["message"] != "book deleted successfully" {
		t.Errorf("expected delete message, got %s", msgResp["message"])
	}

	// Verify deletion: trying to get it should return 404
	w2 := httptest.NewRecorder()
	c2, _ := gin.CreateTestContext(w2)

	setBookID(c2, "1")
	c2.Request, _ = http.NewRequest("GET", "/books/1", nil)
	getBook(c2)

	resp2 := w2.Result()
	if resp2.StatusCode != http.StatusNotFound {
		t.Errorf("expected 404 after delete, got %d", resp2.StatusCode)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	setBookID(c, "999")

	c.Request, _ = http.NewRequest("DELETE", "/books/999", nil)
	deleteBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", resp.StatusCode)
	}

	var errResp map[string]string
	json.NewDecoder(resp.Body).Decode(&errResp)
	if errResp["error"] != "book not found" {
		t.Errorf("expected 'book not found', got %s", errResp["error"])
	}
}

func TestCreateBookDuplicateISBN(t *testing.T) {
	resetDB()
	defer teardownDB()

	// Insert first book with an ISBN via handler
	body1, _ := json.Marshal(CreateBookRequest{
		Title:  "First Book",
		Author: "Author A",
		Year:   2023,
		ISBN:   "isbn-dup",
	})

	w1 := httptest.NewRecorder()
	c1, _ := gin.CreateTestContext(w1)

	c1.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body1))
	createBook(c1)

	resp1 := w1.Result()
	if resp1.StatusCode != http.StatusCreated {
		t.Errorf("first create: expected 201, got %d", resp1.StatusCode)
	}

	// Try to create a second book with the same ISBN
	body2, _ := json.Marshal(CreateBookRequest{
		Title:  "Second Book",
		Author: "Author B",
		Year:   2024,
		ISBN:   "isbn-dup",
	})

	w2 := httptest.NewRecorder()
	c2, _ := gin.CreateTestContext(w2)

	c2.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body2))
	createBook(c2)

	resp2 := w2.Result()
	if resp2.StatusCode != http.StatusInternalServerError {
		t.Errorf("expected status 500 for duplicate ISBN, got %d", resp2.StatusCode)
	}

	var errResp map[string]string
	json.NewDecoder(resp2.Body).Decode(&errResp)
	if errResp["error"] != "failed to create book" {
		t.Errorf("expected 'failed to create book', got %s", errResp["error"])
	}

	// Verify only one book exists
	w3 := httptest.NewRecorder()
	c3, _ := gin.CreateTestContext(w3)

	c3.Request, _ = http.NewRequest("GET", "/books", nil)
	listBooks(c3)

	resp3 := w3.Result()
	var books []Book
	json.NewDecoder(resp3.Body).Decode(&books)
	if len(books) != 1 {
		t.Errorf("expected 1 book after duplicate insert attempt, got %d", len(books))
	}
	if books[0].Title != "First Book" {
		t.Errorf("expected 'First Book', got %s", books[0].Title)
	}
}

func TestCreateBookIntegrated(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "Clean Code",
		Author: "Robert C. Martin",
		Year:   2008,
		ISBN:   "978-0132350884",
	})

	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body))
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("expected status 201, got %d", resp.StatusCode)
	}

	var book Book
	json.NewDecoder(resp.Body).Decode(&book)
	if book.Title != "Clean Code" {
		t.Errorf("expected title 'Clean Code', got %s", book.Title)
	}
	if book.Author != "Robert C. Martin" {
		t.Errorf("expected author 'Robert C. Martin', got %s", book.Author)
	}

	// Verify it exists in DB via handler
	w2 := httptest.NewRecorder()
	c2, _ := gin.CreateTestContext(w2)

	setBookID(c2, "1")
	c2.Request, _ = http.NewRequest("GET", "/books/1", nil)
	getBook(c2)

	resp2 := w2.Result()
	if resp2.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp2.StatusCode)
	}

	var book2 Book
	json.NewDecoder(resp2.Body).Decode(&book2)
	if book2.ISBN != "978-0132350884" {
		t.Errorf("expected ISBN '978-0132350884', got %s", book2.ISBN)
	}
	if book2.Year != 2008 {
		t.Errorf("expected year 2008, got %d", book2.Year)
	}
}

func TestListBooksIntegrated(t *testing.T) {
	resetDB()
	defer teardownDB()

	// Create books via handler for realism
	for i, b := range []CreateBookRequest{
		{Title: "Book A", Author: "Author X", Year: 2020, ISBN: "isbn-ax"},
		{Title: "Book B", Author: "Author X", Year: 2021, ISBN: "isbn-bx"},
		{Title: "Book C", Author: "Author Y", Year: 2022, ISBN: "isbn-cy"},
	} {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)

		body, _ := json.Marshal(b)
		c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body))
		createBook(c)

		resp := w.Result()
		if resp.StatusCode != http.StatusCreated {
			t.Errorf("create book %d: expected 201, got %d", i+1, resp.StatusCode)
		}
	}

	// Get all books
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("GET", "/books", nil)
	listBooks(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp.StatusCode)
	}

	var allBooks []Book
	json.NewDecoder(resp.Body).Decode(&allBooks)
	if len(allBooks) != 3 {
		t.Errorf("expected 3 total books, got %d", len(allBooks))
	}

	// Filter by Author X
	w2 := httptest.NewRecorder()
	c2, _ := gin.CreateTestContext(w2)

	c2.Request, _ = http.NewRequest("GET", "/books?author=Author+X", nil)
	listBooks(c2)

	resp2 := w2.Result()
	if resp2.StatusCode != http.StatusOK {
		t.Errorf("expected status 200, got %d", resp2.StatusCode)
	}

	var filteredBooks []Book
	json.NewDecoder(resp2.Body).Decode(&filteredBooks)
	if len(filteredBooks) != 2 {
		t.Errorf("expected 2 books for Author X, got %d", len(filteredBooks))
	}

	for _, b := range filteredBooks {
		if b.Author != "Author X" {
			t.Errorf("expected author 'Author X', got %s", b.Author)
		}
	}
}

func TestFullCRUDLifecycle(t *testing.T) {
	resetDB()
	defer teardownDB()

	// 1. Create
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "Lifecycle Book",
		Author: "Test Author",
		Year:   2024,
		ISBN:   "isbn-lifecycle",
	})

	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body))
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("create: expected 201, got %d", resp.StatusCode)
	}

	var created Book
	json.NewDecoder(resp.Body).Decode(&created)
	if created.Title != "Lifecycle Book" {
		t.Errorf("create: expected title 'Lifecycle Book', got %s", created.Title)
	}

	// 2. Read (via handler, not DB)
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("GET", "/books/1", nil)
	getBook(c)

	resp = w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("read: expected 200, got %d", resp.StatusCode)
	}

	var read Book
	json.NewDecoder(resp.Body).Decode(&read)
	if read.Title != "Lifecycle Book" {
		t.Errorf("read: expected title 'Lifecycle Book', got %s", read.Title)
	}

	// 3. Update
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	updateBody, _ := json.Marshal(UpdateBookRequest{
		Title:  "Updated Lifecycle",
		Author: "Test Author Updated",
	})

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("PUT", "/books/1", bytes.NewReader(updateBody))
	updateBook(c)

	resp = w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("update: expected 200, got %d", resp.StatusCode)
	}

	var updateResp map[string]string
	json.NewDecoder(resp.Body).Decode(&updateResp)
	if updateResp["message"] != "book updated successfully" {
		t.Errorf("update: unexpected message %s", updateResp["message"])
	}

	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("GET", "/books/1", nil)
	getBook(c)

	resp = w.Result()
	var updated Book
	json.NewDecoder(resp.Body).Decode(&updated)
	if updated.Title != "Updated Lifecycle" {
		t.Errorf("read after update: expected 'Updated Lifecycle', got %s", updated.Title)
	}

	// 4. Delete
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("DELETE", "/books/1", nil)
	deleteBook(c)

	resp = w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("delete: expected 200, got %d", resp.StatusCode)
	}

	var deleteResp map[string]string
	json.NewDecoder(resp.Body).Decode(&deleteResp)
	if deleteResp["message"] != "book deleted successfully" {
		t.Errorf("delete: unexpected message %s", deleteResp["message"])
	}

	// 5. Verify deleted via handler (not DB)
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("GET", "/books/1", nil)
	getBook(c)

	resp = w.Result()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("read after delete: expected 404, got %d", resp.StatusCode)
	}
}

func TestListBooksMultipleAuthors(t *testing.T) {
	resetDB()
	defer teardownDB()

	// Create books via handler for multiple authors
	for i, b := range []CreateBookRequest{
		{Title: "A1", Author: "Alice", Year: 2020, ISBN: "isbn-a1"},
		{Title: "A2", Author: "Alice", Year: 2021, ISBN: "isbn-a2"},
		{Title: "B1", Author: "Bob", Year: 2022, ISBN: "isbn-b1"},
	} {
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)

		body, _ := json.Marshal(b)
		c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body))
		createBook(c)

		resp := w.Result()
		if resp.StatusCode != http.StatusCreated {
			t.Errorf("create %d: expected 201, got %d", i+1, resp.StatusCode)
		}
	}

	// List all: expect 3
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("GET", "/books", nil)
	listBooks(c)

	resp := w.Result()
	var all []Book
	json.NewDecoder(resp.Body).Decode(&all)
	if len(all) != 3 {
		t.Errorf("expected 3 total, got %d", len(all))
	}

	// Filter Alice: expect 2
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("GET", "/books?author=Alice", nil)
	listBooks(c)

	resp = w.Result()
	var alice []Book
	json.NewDecoder(resp.Body).Decode(&alice)
	if len(alice) != 2 {
		t.Errorf("expected 2 Alice books, got %d", len(alice))
	}

	// Filter Bob: expect 1
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("GET", "/books?author=Bob", nil)
	listBooks(c)

	resp = w.Result()
	var bob []Book
	json.NewDecoder(resp.Body).Decode(&bob)
	if len(bob) != 1 {
		t.Errorf("expected 1 Bob book, got %d", len(bob))
	}

	// Filter unknown: expect 0
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	c.Request, _ = http.NewRequest("GET", "/books?author=Charlie", nil)
	listBooks(c)

	resp = w.Result()
	var none []Book
	json.NewDecoder(resp.Body).Decode(&none)
	if len(none) != 0 {
		t.Errorf("expected 0 Charlie books, got %d", len(none))
	}
}

func TestCreateBookWithYearZero(t *testing.T) {
	resetDB()
	defer teardownDB()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "Old Book",
		Author: "Unknown Author",
		Year:   0,
		ISBN:   "isbn-zero-year",
	})

	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body))
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("expected status 201, got %d", resp.StatusCode)
	}

	var book Book
	json.NewDecoder(resp.Body).Decode(&book)
	if book.Year != 0 {
		t.Errorf("expected year 0, got %d", book.Year)
	}
}

func TestDeleteThenCreate(t *testing.T) {
	resetDB()
	defer teardownDB()

	// Create a book
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	body, _ := json.Marshal(CreateBookRequest{
		Title:  "First",
		Author: "Author A",
		Year:   2020,
		ISBN:   "isbn-first",
	})

	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body))
	createBook(c)

	resp := w.Result()
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("first create: expected 201, got %d", resp.StatusCode)
	}

	// Delete it
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	setBookID(c, "1")

	c.Request, _ = http.NewRequest("DELETE", "/books/1", nil)
	deleteBook(c)

	resp = w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("delete: expected 200, got %d", resp.StatusCode)
	}

	// Create another book - should succeed even though ID 1 was used before
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	body2, _ := json.Marshal(CreateBookRequest{
		Title:  "Second",
		Author: "Author B",
		Year:   2021,
		ISBN:   "isbn-second",
	})

	c.Request, _ = http.NewRequest("POST", "/books", bytes.NewReader(body2))
	createBook(c)

	resp = w.Result()
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("second create: expected 201, got %d", resp.StatusCode)
	}

	var book Book
	json.NewDecoder(resp.Body).Decode(&book)
	if book.Title != "Second" {
		t.Errorf("expected title 'Second', got %s", book.Title)
	}

	// Verify first is gone, second exists
	w = httptest.NewRecorder()
	c, _ = gin.CreateTestContext(w)

	setBookID(c, "2")

	c.Request, _ = http.NewRequest("GET", "/books/2", nil)
	getBook(c)

	resp = w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("read second: expected 200, got %d", resp.StatusCode)
	}

	var book2 Book
	json.NewDecoder(resp.Body).Decode(&book2)
	if book2.Title != "Second" {
		t.Errorf("read second: expected 'Second', got %s", book2.Title)
	}
}
