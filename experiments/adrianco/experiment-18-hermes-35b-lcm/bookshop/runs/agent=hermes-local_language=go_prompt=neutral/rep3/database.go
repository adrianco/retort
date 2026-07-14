package main

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

// DB wraps the sql.DB with helpers for book operations.
type DB struct {
	conn *sql.DB
}

// NewDB opens (or creates) a SQLite database at the given path and creates the books table.
func NewDB(dbPath string) (*DB, error) {
	conn, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	// Verify connectivity
	if err := conn.Ping(); err != nil {
		return nil, fmt.Errorf("ping database: %w", err)
	}

	db := &DB{conn: conn}
	if err := db.createTable(); err != nil {
		return nil, fmt.Errorf("create table: %w", err)
	}

	return db, nil
}

// createTable creates the books table if it does not exist.
func (d *DB) createTable() error {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id          INTEGER PRIMARY KEY AUTOINCREMENT,
		title       TEXT    NOT NULL,
		author      TEXT    NOT NULL,
		year        INTEGER NOT NULL,
		isbn        TEXT    NOT NULL,
		created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
		updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
	);`
	_, err := d.conn.Exec(query)
	return err
}

// CreateBook inserts a new book and returns it with the generated ID and timestamps.
func (d *DB) CreateBook(title, author string, year int, isbn string) (*Book, error) {
	now := time.Now().UTC().Format(time.RFC3339)
	result, err := d.conn.Exec(
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
		CreatedAt: nowTime(now),
		UpdatedAt: nowTime(now),
	}, nil
}

// ListBooks returns all books, optionally filtered by author.
func (d *DB) ListBooks(authorFilter *string) ([]Book, error) {
	var rows *sql.Rows
	var err error

	if authorFilter != nil && *authorFilter != "" {
		rows, err = d.conn.Query("SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ?", *authorFilter)
	} else {
		rows, err = d.conn.Query("SELECT id, title, author, year, isbn, created_at, updated_at FROM books")
	}
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		var createdAt, updatedAt string
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt); err != nil {
			return nil, fmt.Errorf("scan book: %w", err)
		}
		b.CreatedAt = nowTime(createdAt)
		b.UpdatedAt = nowTime(updatedAt)
		books = append(books, b)
	}
	return books, rows.Err()
}

// GetBook returns a single book by ID.
func (d *DB) GetBook(id int64) (*Book, error) {
	var b Book
	var createdAt, updatedAt string
	err := d.conn.QueryRow(
		"SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("query book by id %d: %w", id, err)
	}
	b.CreatedAt = nowTime(createdAt)
	b.UpdatedAt = nowTime(updatedAt)
	return &b, nil
}

// UpdateBook updates fields of an existing book (only non-nil fields are updated).
func (d *DB) UpdateBook(id int64, req *UpdateBookRequest) (*Book, error) {
	// First check if the book exists
	existing, err := d.GetBook(id)
	if err != nil {
		return nil, err
	}
	if existing == nil {
		return nil, nil
	}

	// Build dynamic update
	updates := []string{"updated_at = ?"}
	args := []interface{}{time.Now().UTC().Format(time.RFC3339)}

	if req.Title != nil {
		updates = append(updates, "title = ?")
		args = append(args, *req.Title)
	}
	if req.Author != nil {
		updates = append(updates, "author = ?")
		args = append(args, *req.Author)
	}
	if req.Year != nil {
		updates = append(updates, "year = ?")
		args = append(args, *req.Year)
	}
	if req.ISBN != nil {
		updates = append(updates, "isbn = ?")
		args = append(args, *req.ISBN)
	}

	args = append(args, id)
	_, err = d.conn.Exec(
		fmt.Sprintf("UPDATE books SET %s WHERE id = ?", joinStrings(updates, ", ")), args...,
	)
	if err != nil {
		return nil, fmt.Errorf("update book %d: %w", id, err)
	}

	// Return the updated book
	return d.GetBook(id)
}

// DeleteBook deletes a book by ID.
func (d *DB) DeleteBook(id int64) error {
	result, err := d.conn.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("delete book %d: %w", id, err)
	}
	rows, _ := result.RowsAffected()
	if rows == 0 {
		return nil // not found is treated as success for idempotency
	}
	return nil
}

// Close closes the database connection.
func (d *DB) Close() error {
	return d.conn.Close()
}

// HealthCheck verifies the database connection is live.
func (d *DB) HealthCheck() error {
	return d.conn.Ping()
}

// nowTime parses an RFC3339 timestamp string into a time.Time.
func nowTime(s string) time.Time {
	t, err := time.Parse(time.RFC3339, s)
	if err != nil {
		return time.Time{}
	}
	return t
}

// joinStrings joins a slice of strings with a separator.
func joinStrings(parts []string, sep string) string {
	result := ""
	for i, p := range parts {
		if i > 0 {
			result += sep
		}
		result += p
	}
	return result
}

// Context returns the underlying sql.Conn for advanced operations.
func (d *DB) Context() context.Context {
	return context.Background()
}
