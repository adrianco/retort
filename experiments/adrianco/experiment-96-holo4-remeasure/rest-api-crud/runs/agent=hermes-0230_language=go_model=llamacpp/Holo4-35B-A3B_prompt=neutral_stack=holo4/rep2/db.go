package main

import (
	"database/sql"
	"fmt"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

func initDB() error {
	var err error
	db, err = sql.Open("sqlite3", "./books.db")
	if err != nil {
		return err
	}

	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);`

	_, err = db.Exec(createTable)
	if err != nil {
		return err
	}

	return nil
}

func getAllBooks(author string) ([]Book, error) {
	var query string
	var rows *sql.Rows
	var err error

	if author != "" {
		query = "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ?"
		rows, err = db.Query(query, author)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
	} else {
		query = "SELECT id, title, author, year, isbn, created_at, updated_at FROM books"
		rows, err = db.Query(query)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
	}

	var books []Book
	for rows.Next() {
		var b Book
		var createdAt, updatedAt string
		err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt)
		if err != nil {
			return nil, err
		}
		books = append(books, b)
	}

	return books, nil
}

func getBookByID(id int) (*Book, error) {
	query := "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?"
	row := db.QueryRow(query, id)

	var b Book
	var createdAt, updatedAt string
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("book not found")
		}
		return nil, err
	}

	return &b, nil
}

func createBook(req CreateBookRequest) (*Book, error) {
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	result, err := db.Exec(query, req.Title, req.Author, req.Year, req.ISBN)
	if err != nil {
		return nil, err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, err
	}

	return getBookByID(int(id))
}

func updateBook(id int, req UpdateBookRequest) (*Book, error) {
	book, err := getBookByID(id)
	if err != nil {
		return nil, err
	}

	if req.Title != nil {
		book.Title = *req.Title
	}
	if req.Author != nil {
		book.Author = *req.Author
	}
	if req.Year != nil {
		book.Year = *req.Year
	}
	if req.ISBN != nil {
		book.ISBN = *req.ISBN
	}

	query := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?`
	_, err = db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, book.ID)
	if err != nil {
		return nil, err
	}

	return book, nil
}

func deleteBook(id int) error {
	_, err := getBookByID(id)
	if err != nil {
		return err
	}

	query := "DELETE FROM books WHERE id = ?"
	_, err = db.Exec(query, id)
	return err
}

func closeDB() {
	if db != nil {
		db.Close()
	}
}

func init() {
	err := initDB()
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
}
