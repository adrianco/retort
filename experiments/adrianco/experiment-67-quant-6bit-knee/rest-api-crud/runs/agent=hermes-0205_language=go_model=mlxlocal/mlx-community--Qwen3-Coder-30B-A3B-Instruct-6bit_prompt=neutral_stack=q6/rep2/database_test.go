package main

import (
	"database/sql"
	"os"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func TestMain(m *testing.M) {
	// Create a test database file
	os.Remove("./test_books.db")
	
	// Run tests
	code := m.Run()
	
	// Clean up
	os.Remove("./test_books.db")
	
	os.Exit(code)
}

func TestDatabaseOperations(t *testing.T) {
	// Open test database
	testDB, err := sql.Open("sqlite3", "./test_books.db")
	if err != nil {
		t.Fatal("Failed to open test database:", err)
	}
	defer testDB.Close()

	// Create books table
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	);`

	_, err = testDB.Exec(createTableSQL)
	if err != nil {
		t.Fatal("Failed to create table:", err)
	}

	// Test inserting a book
	insertSQL := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	_, err = testDB.Exec(insertSQL, "Test Book", "Test Author", 2023, "1234567890")
	if err != nil {
		t.Fatal("Failed to insert book:", err)
	}

	// Test querying books
	rows, err := testDB.Query(`SELECT id, title, author, year, isbn FROM books`)
	if err != nil {
		t.Fatal("Failed to query books:", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			t.Fatal("Failed to scan book:", err)
		}
		books = append(books, book)
	}

	if len(books) != 1 {
		t.Errorf("Expected 1 book, got %d", len(books))
	}

	if books[0].Title != "Test Book" {
		t.Errorf("Expected title 'Test Book', got '%s'", books[0].Title)
	}

	if books[0].Author != "Test Author" {
		t.Errorf("Expected author 'Test Author', got '%s'", books[0].Author)
	}

	if books[0].Year != 2023 {
		t.Errorf("Expected year 2023, got %d", books[0].Year)
	}

	if books[0].ISBN != "1234567890" {
		t.Errorf("Expected ISBN '1234567890', got '%s'", books[0].ISBN)
	}

	// Test updating a book
	updateSQL := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	_, err = testDB.Exec(updateSQL, "Updated Book", "Updated Author", 2024, "0987654321", 1)
	if err != nil {
		t.Fatal("Failed to update book:", err)
	}

	// Verify update
	row := testDB.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, 1)
	var updatedBook Book
	err = row.Scan(&updatedBook.ID, &updatedBook.Title, &updatedBook.Author, &updatedBook.Year, &updatedBook.ISBN)
	if err != nil {
		t.Fatal("Failed to scan updated book:", err)
	}

	if updatedBook.Title != "Updated Book" {
		t.Errorf("Expected updated title 'Updated Book', got '%s'", updatedBook.Title)
	}

	if updatedBook.Author != "Updated Author" {
		t.Errorf("Expected updated author 'Updated Author', got '%s'", updatedBook.Author)
	}

	if updatedBook.Year != 2024 {
		t.Errorf("Expected updated year 2024, got %d", updatedBook.Year)
	}

	if updatedBook.ISBN != "0987654321" {
		t.Errorf("Expected updated ISBN '0987654321', got '%s'", updatedBook.ISBN)
	}

	// Test deleting a book
	deleteSQL := `DELETE FROM books WHERE id = ?`
	_, err = testDB.Exec(deleteSQL, 1)
	if err != nil {
		t.Fatal("Failed to delete book:", err)
	}

	// Verify deletion
	rows, err = testDB.Query(`SELECT id FROM books`)
	if err != nil {
		t.Fatal("Failed to query books after deletion:", err)
	}
	defer rows.Close()

	count := 0
	for rows.Next() {
		count++
	}

	if count != 0 {
		t.Errorf("Expected 0 books after deletion, got %d", count)
	}
}