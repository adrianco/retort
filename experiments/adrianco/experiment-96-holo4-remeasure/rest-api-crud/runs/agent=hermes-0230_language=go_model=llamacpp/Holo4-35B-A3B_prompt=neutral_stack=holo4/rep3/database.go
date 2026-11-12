package main

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// Database wraps a sqlite3 connection with helper methods.
type Database struct {
	db *sql.DB
}

// NewDatabase opens (or creates) the SQLite database and runs migrations.
func NewDatabase(path string) (*Database, error) {
	db, err := sql.Open("sqlite3", path)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	// Enable WAL mode for better concurrency.
	if _, err := db.Exec("PRAGMA journal_mode=WAL"); err != nil {
		db.Close()
		return nil, fmt.Errorf("set journal mode: %w", err)
	}

	d := &Database{db: db}
	if err := d.migrate(); err != nil {
		db.Close()
		return nil, err
	}
	return d, nil
}

// migrate creates the books table if it does not exist.
func (d *Database) migrate() error {
	_, err := d.db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			title      TEXT    NOT NULL,
			author     TEXT    NOT NULL,
			year       INTEGER NOT NULL,
			isbn       TEXT    NOT NULL UNIQUE,
			created_at DATETIME NOT NULL DEFAULT (datetime('now')),
			updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
		);
	`)
	return err
}

// Close closes the database connection.
func (d *Database) Close() error {
	return d.db.Close()
}

// CreateBook inserts a new book and returns it with its generated ID.
func (d *Database) CreateBook(title, author string, year int, isbn string) (*Book, error) {
	ctx := context.Background()
	res, err := d.db.ExecContext(ctx,
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		title, author, year, isbn,
	)
	if err != nil {
		return nil, fmt.Errorf("insert book: %w", err)
	}
	id, err := res.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("get last insert id: %w", err)
	}
	return d.GetBook(id)
}

// ListBooks returns all books, optionally filtered by author.
func (d *Database) ListBooks(author string) ([]Book, error) {
	ctx := context.Background()
	var rows *sql.Rows
	var err error
	if author != "" {
		rows, err = d.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ?`,
			author,
		)
	} else {
		rows, err = d.db.QueryContext(ctx,
			`SELECT id, title, author, year, isbn, created_at, updated_at FROM books`,
		)
	}
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		var createdAt, updatedAt string
		err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt)
		if err != nil {
			return nil, fmt.Errorf("scan book row: %w", err)
		}
		b.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
		b.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
		books = append(books, b)
	}
	return books, rows.Err()
}

// GetBook returns a single book by ID.
func (d *Database) GetBook(id int64) (*Book, error) {
	ctx := context.Background()
	var b Book
	var createdAt, updatedAt string
	err := d.db.QueryRowContext(ctx,
		`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt)
	if err == sql.ErrNoRows {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("get book: %w", err)
	}
	b.CreatedAt, _ = time.Parse(time.RFC3339, createdAt)
	b.UpdatedAt, _ = time.Parse(time.RFC3339, updatedAt)
	return &b, nil
}

// UpdateBook updates a book by ID and returns the updated book.
func (d *Database) UpdateBook(id int64, title, author string, year int, isbn string) (*Book, error) {
	ctx := context.Background()
	res, err := d.db.ExecContext(ctx,
		`UPDATE books SET title=?, author=?, year=?, isbn=?, updated_at=datetime('now') WHERE id=?`,
		title, author, year, isbn, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update book: %w", err)
	}
	rows, _ := res.RowsAffected()
	if rows == 0 {
		return nil, ErrNotFound
	}
	return d.GetBook(id)
}

// DeleteBook deletes a book by ID.
func (d *Database) DeleteBook(id int64) error {
	ctx := context.Background()
	res, err := d.db.ExecContext(ctx, `DELETE FROM books WHERE id=?`, id)
	if err != nil {
		return fmt.Errorf("delete book: %w", err)
	}
	rows, _ := res.RowsAffected()
	if rows == 0 {
		return ErrNotFound
	}
	return nil
}
