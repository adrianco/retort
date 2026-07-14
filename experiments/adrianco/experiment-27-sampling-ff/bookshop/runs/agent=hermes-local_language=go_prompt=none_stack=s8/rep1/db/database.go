package db

import (
	"book-api/models"
	"database/sql"
	"fmt"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// Database wraps the SQLite connection with helper methods.
type Database struct {
	conn *sql.DB
}

// New creates a new Database instance and initializes the schema.
func New(dbPath string) (*Database, error) {
	conn, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	db := &Database{conn: conn}
	if err := db.initializeSchema(); err != nil {
		conn.Close()
		return nil, fmt.Errorf("failed to initialize schema: %w", err)
	}

	return db, nil
}

// Close closes the database connection.
func (d *Database) Close() error {
	return d.conn.Close()
}

// initializeSchema creates the books table if it doesn't exist.
func (d *Database) initializeSchema() error {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL,
		created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
		updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
	);`

	_, err := d.conn.Exec(query)
	if err != nil {
		return fmt.Errorf("failed to create books table: %w", err)
	}

	return nil
}

// CreateBook inserts a new book and returns it with generated ID.
func (d *Database) CreateBook(title, author string, year int, isbn string) (*models.Book, error) {
	now := time.Now()
	result, err := d.conn.Exec(
		"INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
		title, author, year, isbn, now, now,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to insert book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("failed to get book ID: %w", err)
	}

	return &models.Book{
		ID:        int(id),
		Title:     title,
		Author:    author,
		Year:      year,
		ISBN:      isbn,
		CreatedAt: now,
		UpdatedAt: now,
	}, nil
}

// GetAllBooks returns all books, optionally filtered by author.
func (d *Database) GetAllBooks(authorFilter string) ([]*models.Book, error) {
	var query string
	var args []interface{}

	if authorFilter != "" {
		query = "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ? ORDER BY id"
		args = append(args, authorFilter)
	} else {
		query = "SELECT id, title, author, year, isbn, created_at, updated_at FROM books ORDER BY id"
	}

	rows, err := d.conn.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query books: %w", err)
	}
	defer rows.Close()

	var books []*models.Book
	for rows.Next() {
		var b models.Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt); err != nil {
			return nil, fmt.Errorf("failed to scan book: %w", err)
		}
		books = append(books, &b)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("row iteration error: %w", err)
	}

	return books, nil
}

// GetBookByID returns a single book by its ID.
func (d *Database) GetBookByID(id int) (*models.Book, error) {
	var b models.Book
	err := d.conn.QueryRow(
		"SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?",
		id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &b.CreatedAt, &b.UpdatedAt)

	if err == sql.ErrNoRows {
		return nil, fmt.Errorf("book with id %d not found", id)
	}
	if err != nil {
		return nil, fmt.Errorf("failed to query book: %w", err)
	}

	return &b, nil
}

// UpdateBook updates a book's fields. Only non-nil fields in the request are updated.
func (d *Database) UpdateBook(id int, title *string, author *string, year *int, isbn *string) (*models.Book, error) {
	// Check if book exists
	existing, err := d.GetBookByID(id)
	if err != nil {
		return nil, err
	}

	// Apply updates from request
	if title != nil {
		existing.Title = *title
	}
	if author != nil {
		existing.Author = *author
	}
	if year != nil {
		existing.Year = *year
	}
	if isbn != nil {
		existing.ISBN = *isbn
	}

	now := time.Now()
	_, err = d.conn.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?",
		existing.Title, existing.Author, existing.Year, existing.ISBN, now, id,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to update book: %w", err)
	}

	existing.UpdatedAt = now

	return existing, nil
}

// DeleteBook removes a book by its ID. Returns an error if not found.
func (d *Database) DeleteBook(id int) error {
	result, err := d.conn.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to check deletion: %w", err)
	}

	if rowsAffected == 0 {
		return fmt.Errorf("book with id %d not found", id)
	}

	return nil
}
