package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// Database wraps a sqlite3 connection with convenience methods.
type Database struct {
	conn *sql.DB
}

// NewDatabase opens (or creates) the SQLite database and ensures the books table exists.
func NewDatabase(dbPath string) (*Database, error) {
	conn, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	// Enable WAL mode for better concurrency
	if _, err := conn.Exec("PRAGMA journal_mode=WAL"); err != nil {
		return nil, fmt.Errorf("enable WAL: %w", err)
	}

	// Create the books table if it doesn't exist
	createTable := `
	CREATE TABLE IF NOT EXISTS books (
		id         INTEGER PRIMARY KEY AUTOINCREMENT,
		title      TEXT    NOT NULL,
		author     TEXT    NOT NULL,
		year       INTEGER NOT NULL,
		isbn       TEXT    NOT NULL,
		created_at DATETIME NOT NULL DEFAULT (datetime('now')),
		updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
	);`

	if _, err := conn.Exec(createTable); err != nil {
		return nil, fmt.Errorf("create table: %w", err)
	}

	return &Database{conn: conn}, nil
}

// Close closes the database connection.
func (db *Database) Close() error {
	return db.conn.Close()
}

// CreateBook inserts a new book and returns the created Book with its generated ID.
func (db *Database) CreateBook(title, author string, year int, isbn string) (*Book, error) {
	now := time.Now().UTC()
	result, err := db.conn.Exec(
		"INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
		title, author, year, isbn, now, now,
	)
	if err != nil {
		return nil, fmt.Errorf("insert book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("get last insert id: %w", err)
	}

	return &Book{
		ID:        id,
		Title:     title,
		Author:    author,
		Year:      year,
		ISBN:      isbn,
		CreatedAt: now,
		UpdatedAt: now,
	}, nil
}

// GetBookByID retrieves a book by its ID.
func (db *Database) GetBookByID(id int64) (*Book, error) {
	row := db.conn.QueryRow(
		"SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?", id,
	)
	return scanBook(row)
}

// ListBooks returns all books, optionally filtered by author.
func (db *Database) ListBooks(authorFilter *string) ([]*Book, error) {
	query := "SELECT id, title, author, year, isbn, created_at, updated_at FROM books"
	args := []interface{}{}

	if authorFilter != nil && *authorFilter != "" {
		query += " WHERE author = ?"
		args = append(args, *authorFilter)
	}

	query += " ORDER BY created_at DESC"

	rows, err := db.conn.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		book, err := scanBook(rows)
		if err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		books = append(books, book)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate rows: %w", err)
	}

	if books == nil {
		books = []*Book{}
	}
	return books, nil
}

// UpdateBook modifies fields of an existing book. Only non-nil fields in the request are updated.
func (db *Database) UpdateBook(id int64, req *UpdateBookRequest) (*Book, error) {
	// First, fetch the existing book
	existing, err := db.GetBookByID(id)
	if err != nil {
		return nil, err
	}

	title := existing.Title
	if req.Title != nil {
		title = *req.Title
	}
	author := existing.Author
	if req.Author != nil {
		author = *req.Author
	}
	year := existing.Year
	if req.Year != nil {
		year = *req.Year
	}
	isbn := existing.ISBN
	if req.ISBN != nil {
		isbn = *req.ISBN
	}

	now := time.Now().UTC()
	_, err = db.conn.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?",
		title, author, year, isbn, now, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update book: %w", err)
	}

	return &Book{
		ID:        id,
		Title:     title,
		Author:    author,
		Year:      year,
		ISBN:      isbn,
		CreatedAt: existing.CreatedAt,
		UpdatedAt: now,
	}, nil
}

// DeleteBook removes a book by its ID. Returns true if a row was deleted.
func (db *Database) DeleteBook(id int64) (bool, error) {
	result, err := db.conn.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return false, fmt.Errorf("delete book: %w", err)
	}
	rows, err := result.RowsAffected()
	if err != nil {
		return false, fmt.Errorf("get rows affected: %w", err)
	}
	return rows > 0, nil
}

// scanBook reads a single Book from a row interface.
type scanner interface {
	Scan(dest ...interface{}) error
}

func scanBook(s scanner) (*Book, error) {
	var b Book
	var year int
	var createdAt, updatedAt string
	err := s.Scan(&b.ID, &b.Title, &b.Author, &year, &b.ISBN, &createdAt, &updatedAt)
	if err != nil {
		return nil, fmt.Errorf("scan: %w", err)
	}
	b.Year = year
	b.CreatedAt, _ = time.Parse("2006-01-02 15:04:05", createdAt)
	b.UpdatedAt, _ = time.Parse("2006-01-02 15:04:05", updatedAt)
	return &b, nil
}

func init() {
	log.SetFlags(log.Ldate | log.Ltime | log.Lshortfile)
}
