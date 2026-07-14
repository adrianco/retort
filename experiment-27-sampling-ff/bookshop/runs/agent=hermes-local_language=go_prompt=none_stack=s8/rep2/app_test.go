package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strconv"
	"testing"

	"github.com/gin-gonic/gin"
)

func setupTestRouter(t *testing.T) *gin.Engine {
	t.Helper()
	var err error
	db, err = sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open test db: %v", err)
	}

	createTable := `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`
	if _, err = db.Exec(createTable); err != nil {
		t.Fatalf("Failed to create table: %v", err)
	}

	gin.SetMode(gin.TestMode)
	r := gin.Default()

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	r.POST("/books", func(c *gin.Context) {
		var req CreateBookRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		result, err := db.Exec(
			"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
			req.Title, req.Author, req.Year, req.ISBN,
		)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		id, _ := result.LastInsertId()
		book := Book{ID: int(id), Title: req.Title, Author: req.Author, Year: req.Year, ISBN: req.ISBN}
		c.JSON(http.StatusCreated, book)
	})

	r.GET("/books", func(c *gin.Context) {
		author := c.Query("author")

		var rows *sql.Rows
		var err error

		if author != "" {
			rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", author)
		} else {
			rows, err = db.Query("SELECT id, title, author, year, isbn FROM books")
		}

		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}
		defer rows.Close()

		var books []Book
		for rows.Next() {
			b, err := scanRow(rows)
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
				return
			}
			books = append(books, b)
		}

		if books == nil {
			books = []Book{}
		}

		c.JSON(http.StatusOK, books)
	})

	r.GET("/books/:id", func(c *gin.Context) {
		id, err := strconv.Atoi(c.Param("id"))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
			return
		}

		var b Book
		err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
			Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
			return
		}
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		c.JSON(http.StatusOK, b)
	})

	r.PUT("/books/:id", func(c *gin.Context) {
		id, err := strconv.Atoi(c.Param("id"))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
			return
		}

		var req UpdateBookRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		result, err := db.Exec(
			"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
			req.Title, req.Author, req.Year, req.ISBN, id,
		)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		rowsAffected, _ := result.RowsAffected()
		if rowsAffected == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
			return
		}

		var b Book
		db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).
			Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)

		c.JSON(http.StatusOK, b)
	})

	r.DELETE("/books/:id", func(c *gin.Context) {
		id, err := strconv.Atoi(c.Param("id"))
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
			return
		}

		result, err := db.Exec("DELETE FROM books WHERE id = ?", id)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		rowsAffected, _ := result.RowsAffected()
		if rowsAffected == 0 {
			c.JSON(http.StatusNotFound, gin.H{"error": "book not found"})
			return
		}

		c.JSON(http.StatusOK, gin.H{"message": "book deleted"})
	})

	return r
}

func TestMain(m *testing.M) {
	os.Remove("books.db")
	code := m.Run()
	os.Exit(code)
}

func TestHealthCheck(t *testing.T) {
	r := setupTestRouter(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var body map[string]string
	json.Unmarshal(w.Body.Bytes(), &body)
	if body["status"] != "ok" {
		t.Errorf("expected status 'ok', got '%s'", body["status"])
	}
}

func TestCreateBook(t *testing.T) {
	r := setupTestRouter(t)

	payload := `{"title":"The Go Programming Language","author":"Donovan & Kernighan","year":2015,"isbn":"978-0134190440"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Errorf("expected status 201, got %d", w.Code)
	}

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	if book.Title != "The Go Programming Language" {
		t.Errorf("expected title 'The Go Programming Language', got '%s'", book.Title)
	}
	if book.Author != "Donovan & Kernighan" {
		t.Errorf("expected author 'Donovan & Kernighan', got '%s'", book.Author)
	}
	if book.Year != 2015 {
		t.Errorf("expected year 2015, got %d", book.Year)
	}
	if book.ISBN != "978-0134190440" {
		t.Errorf("expected isbn '978-0134190440', got '%s'", book.ISBN)
	}
	if book.ID == 0 {
		t.Error("expected a non-zero ID")
	}
}

func TestCreateBookMissingFields(t *testing.T) {
	r := setupTestRouter(t)

	payload := `{"title":"Missing Author"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestListBooks(t *testing.T) {
	r := setupTestRouter(t)

	payload := `{"title":"Clean Code","author":"Robert C. Martin","year":2008,"isbn":"978-0132350884"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	w2 := httptest.NewRecorder()
	req2, _ := http.NewRequest("GET", "/books", nil)
	r.ServeHTTP(w2, req2)

	if w2.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w2.Code)
	}

	var books []Book
	json.Unmarshal(w2.Body.Bytes(), &books)

	if len(books) != 1 {
		t.Errorf("expected 1 book, got %d", len(books))
	}
	if books[0].Title != "Clean Code" {
		t.Errorf("expected title 'Clean Code', got '%s'", books[0].Title)
	}
}

func TestListBooksByAuthor(t *testing.T) {
	r := setupTestRouter(t)

	payloads := []string{
		`{"title":"Book A","author":"Author X","year":2020,"isbn":"111"}`,
		`{"title":"Book B","author":"Author Y","year":2021,"isbn":"222"}`,
		`{"title":"Book C","author":"Author X","year":2022,"isbn":"333"}`,
	}

	for _, p := range payloads {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(p))
		req.Header.Set("Content-Type", "application/json")
		r.ServeHTTP(w, req)
	}

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books?author=Author+X", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var books []Book
	json.Unmarshal(w.Body.Bytes(), &books)

	if len(books) != 2 {
		t.Errorf("expected 2 books for Author X, got %d", len(books))
	}
	for _, b := range books {
		if b.Author != "Author X" {
			t.Errorf("expected author 'Author X', got '%s'", b.Author)
		}
	}
}

func TestGetBook(t *testing.T) {
	r := setupTestRouter(t)

	payload := `{"title":"Effective Go","author":"Google","year":2009,"isbn":"978-0943396514"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	var book Book
	json.Unmarshal(w.Body.Bytes(), &book)

	w2 := httptest.NewRecorder()
	req2, _ := http.NewRequest("GET", "/books/1", nil)
	r.ServeHTTP(w2, req2)

	if w2.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w2.Code)
	}

	var got Book
	json.Unmarshal(w2.Body.Bytes(), &got)

	if got.ID != book.ID {
		t.Errorf("expected id %d, got %d", book.ID, got.ID)
	}
	if got.Title != "Effective Go" {
		t.Errorf("expected title 'Effective Go', got '%s'", got.Title)
	}
}

func TestGetBookNotFound(t *testing.T) {
	r := setupTestRouter(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/books/999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	r := setupTestRouter(t)

	payload := `{"title":"Old Title","author":"Old Author","year":2000,"isbn":"000"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	update := `{"title":"New Title","author":"New Author","year":2025,"isbn":"NEW"}`
	w2 := httptest.NewRecorder()
	req2, _ := http.NewRequest("PUT", "/books/1", bytes.NewBufferString(update))
	req2.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w2, req2)

	if w2.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w2.Code)
	}

	var book Book
	json.Unmarshal(w2.Body.Bytes(), &book)

	if book.Title != "New Title" {
		t.Errorf("expected title 'New Title', got '%s'", book.Title)
	}
	if book.Author != "New Author" {
		t.Errorf("expected author 'New Author', got '%s'", book.Author)
	}
	if book.Year != 2025 {
		t.Errorf("expected year 2025, got %d", book.Year)
	}
	if book.ISBN != "NEW" {
		t.Errorf("expected isbn 'NEW', got '%s'", book.ISBN)
	}
}

func TestDeleteBook(t *testing.T) {
	r := setupTestRouter(t)

	payload := `{"title":"To Delete","author":"Nobody","year":2024,"isbn":"DEL"}`
	w := httptest.NewRecorder()
	req, _ := http.NewRequest("POST", "/books", bytes.NewBufferString(payload))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	w2 := httptest.NewRecorder()
	req2, _ := http.NewRequest("DELETE", "/books/1", nil)
	r.ServeHTTP(w2, req2)

	if w2.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w2.Code)
	}

	var resp map[string]string
	json.Unmarshal(w2.Body.Bytes(), &resp)
	if resp["message"] != "book deleted" {
		t.Errorf("expected message 'book deleted', got '%s'", resp["message"])
	}

	w3 := httptest.NewRecorder()
	req3, _ := http.NewRequest("GET", "/books/1", nil)
	r.ServeHTTP(w3, req3)

	if w3.Code != http.StatusNotFound {
		t.Errorf("expected status 404 after delete, got %d", w3.Code)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	r := setupTestRouter(t)

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("DELETE", "/books/999", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Errorf("expected status 404, got %d", w.Code)
	}
}
