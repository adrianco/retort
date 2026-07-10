package main

import (
	"database/sql"
	"fmt"

	_ "github.com/mattn/go-sqlite3"
)

// BookRepository handles all SQLite operations for books.
type BookRepository struct {
	db *sql.DB
}

// NewBookRepository creates a new repository and initializes the schema.
func NewBookRepository(dbPath string) (*BookRepository, error) {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	repo := &BookRepository{db: db}
	if err := repo.initSchema(); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to initialize schema: %w", err)
	}

	return repo, nil
}

// Close closes the database connection.
func (r *BookRepository) Close() error {
	return r.db.Close()
}

func (r *BookRepository) initSchema() error {
	schema := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL UNIQUE
	);`
	_, err := r.db.Exec(schema)
	return err
}

// CreateBook inserts a book and returns it with the generated ID.
func (r *BookRepository) CreateBook(book *Book) error {
	result, err := r.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN,
	)
	if err != nil {
		return fmt.Errorf("failed to insert book: %w", err)
	}
	id, err := result.LastInsertId()
	if err != nil {
		return fmt.Errorf("failed to get last insert id: %w", err)
	}
	book.ID = int(id)
	return nil
}

// GetAllBooks returns all books, optionally filtered by author.
func (r *BookRepository) GetAllBooks(authorFilter string) ([]*Book, error) {
	var query string
	var args []interface{}

	if authorFilter != "" {
		query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
		args = []interface{}{authorFilter}
	} else {
		query = "SELECT id, title, author, year, isbn FROM books"
	}

	rows, err := r.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query books: %w", err)
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("failed to scan book row: %w", err)
		}
		books = append(books, &b)
	}
	return books, nil
}

// GetBookByID returns a single book by its ID. Returns sql.ErrNoRows if not found.
func (r *BookRepository) GetBookByID(id int) (*Book, error) {
	var b Book
	err := r.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		return nil, err
	}
	return &b, nil
}

// UpdateBook updates an existing book. Returns sql.ErrNoRows if ID doesn't exist.
func (r *BookRepository) UpdateBook(book *Book) error {
	result, err := r.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, book.ID,
	)
	if err != nil {
		return fmt.Errorf("failed to update book: %w", err)
	}
	rows, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to get rows affected: %w", err)
	}
	if rows == 0 {
		return sql.ErrNoRows
	}
	return nil
}

// DeleteBook deletes a book by ID. Returns sql.ErrNoRows if not found.
func (r *BookRepository) DeleteBook(id int) error {
	result, err := r.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}
	rows, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to get rows affected: %w", err)
	}
	if rows == 0 {
		return sql.ErrNoRows
	}
	return nil
}
