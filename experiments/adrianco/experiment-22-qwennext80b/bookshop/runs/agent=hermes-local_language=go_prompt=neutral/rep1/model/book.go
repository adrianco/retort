package model

import (
	"database/sql"
	"errors"
	"fmt"
	_ "github.com/mattn/go-sqlite3"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

type BookStore struct {
	db *sql.DB
}

func NewBookStore(dbPath string) (*BookStore, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, err
	}

	// Create table if not exists
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL
	);`

	_, err = db.Exec(createTableSQL)
	if err != nil {
		return nil, err
	}

	return &BookStore{db: db}, nil
}

func (bs *BookStore) Close() error {
	return bs.db.Close()
}

func (bs *BookStore) CreateBook(book *Book) error {
	insertSQL := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	result, err := bs.db.Exec(insertSQL, book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		return err
	}

	id, err := result.LastInsertId()
	if err != nil {
		return err
	}

	book.ID = int(id)
	return nil
}

func (bs *BookStore) GetBook(id int) (*Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	book := &Book{}
	err := bs.db.QueryRow(query, id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, errors.New("book not found")
		}
		return nil, err
	}
	return book, nil
}

func (bs *BookStore) UpdateBook(book *Book) error {
	updateSQL := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	result, err := bs.db.Exec(updateSQL, book.Title, book.Author, book.Year, book.ISBN, book.ID)
	if err != nil {
		return err
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}

	if rowsAffected == 0 {
		return errors.New("book not found")
	}

	return nil
}

func (bs *BookStore) DeleteBook(id int) error {
	deleteSQL := `DELETE FROM books WHERE id = ?`
	result, err := bs.db.Exec(deleteSQL, id)
	if err != nil {
		return err
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}

	if rowsAffected == 0 {
		return errors.New("book not found")
	}

	return nil
}

func (bs *BookStore) ListBooks(authorFilter string) ([]Book, error) {
	var query string
	var rows *sql.Rows
	var err error

	if authorFilter != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?`
		rows, err = bs.db.Query(query, "%"+authorFilter+"%")
	} else {
		query = `SELECT id, title, author, year, isbn FROM books`
		rows, err = bs.db.Query(query)
	}

	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		if err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN); err != nil {
			return nil, err
		}
		books = append(books, book)
	}

	if err = rows.Err(); err != nil {
		return nil, err
	}

	return books, nil
}

func (bs *BookStore) HealthCheck() error {
	return bs.db.Ping()
}

// Validation functions
func ValidateBook(book *Book) error {
	if book.Title == "" {
		return errors.New("title is required")
	}
	if book.Author == "" {
		return errors.New("author is required")
	}
	if book.Year <= 0 {
		return errors.New("year must be a positive integer")
	}
	if book.ISBN == "" {
		return errors.New("isbn is required")
	}
	return nil
}

func CreateError(message string, code int) map[string]string {
	return map[string]string{
		"error":   message,
		"code":    fmt.Sprintf("%d", code),
		"message": message,
	}
}
