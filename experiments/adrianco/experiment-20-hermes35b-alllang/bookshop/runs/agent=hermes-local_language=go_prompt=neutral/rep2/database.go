package main

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

// BookRepository defines the interface for book data operations.
type BookRepository interface {
	CreateBook(title, author string, year int, isbn string) (*Book, error)
	ListBooks(authorFilter *string) ([]Book, error)
	GetBook(id int) (*Book, error)
	UpdateBook(id int, req UpdateBookRequest) (*Book, error)
	DeleteBook(id int) error
}

// SQLiteRepo implements BookRepository using SQLite.
type SQLiteRepo struct {
	db *sql.DB
}

// NewSQLiteRepo opens (or creates) the SQLite database and ensures the books table exists.
func NewSQLiteRepo(dsn string) (*SQLiteRepo, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	if err := db.Ping(); err != nil {
		return nil, fmt.Errorf("ping database: %w", err)
	}

	sqliteDDL := `
	CREATE TABLE IF NOT EXISTS books (
		id      INTEGER PRIMARY KEY AUTOINCREMENT,
		title   TEXT NOT NULL,
		author  TEXT NOT NULL,
		year    INTEGER NOT NULL,
		isbn    TEXT NOT NULL
	);`

	if _, err := db.Exec(sqliteDDL); err != nil {
		return nil, fmt.Errorf("create books table: %w", err)
	}

	return &SQLiteRepo{db: db}, nil
}

// Close shuts down the database connection.
func (r *SQLiteRepo) Close() error {
	return r.db.Close()
}

// CreateBook inserts a book and returns the inserted record with its generated ID.
func (r *SQLiteRepo) CreateBook(title, author string, year int, isbn string) (*Book, error) {
	result, err := r.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		title, author, year, isbn,
	)
	if err != nil {
		return nil, fmt.Errorf("insert book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("get last insert id: %w", err)
	}

	return &Book{
		ID:     int(id),
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// ListBooks returns all books, optionally filtered by author.
func (r *SQLiteRepo) ListBooks(authorFilter *string) ([]Book, error) {
	var rows *sql.Rows
	var err error

	if authorFilter != nil && *authorFilter != "" {
		rows, err = r.db.Query("SELECT id, title, author, year, isbn FROM books WHERE author = ?", *authorFilter)
	} else {
		rows, err = r.db.Query("SELECT id, title, author, year, isbn FROM books")
	}
	if err != nil {
		return nil, fmt.Errorf("query books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, fmt.Errorf("scan book row: %w", err)
		}
		books = append(books, b)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows iteration: %w", err)
	}

	return books, nil
}

// GetBook returns a book by its ID, or ErrNotFound if not found.
func (r *SQLiteRepo) GetBook(id int) (*Book, error) {
	var b Book
	err := r.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, ErrNotFound
		}
		return nil, fmt.Errorf("get book id=%d: %w", id, err)
	}
	return &b, nil
}

// UpdateBook partially updates an existing book.
// Only non-nil fields in the request are updated.
func (r *SQLiteRepo) UpdateBook(id int, req UpdateBookRequest) (*Book, error) {
	// First, check the book exists.
	existing, err := r.GetBook(id)
	if err != nil {
		return nil, err
	}

	// Apply updates (use pointers to distinguish "not set" from zero value).
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

	_, err = r.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		title, author, year, isbn, id,
	)
	if err != nil {
		return nil, fmt.Errorf("update book id=%d: %w", id, err)
	}

	return &Book{ID: id, Title: title, Author: author, Year: year, ISBN: isbn}, nil
}

// DeleteBook removes a book by ID. Returns ErrNotFound if the book does not exist.
func (r *SQLiteRepo) DeleteBook(id int) error {
	result, err := r.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("delete book id=%d: %w", id, err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("check delete rows affected: %w", err)
	}
	if rowsAffected == 0 {
		return ErrNotFound
	}

	return nil
}
