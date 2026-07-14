package main

import (
	"database/sql"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

type Database struct {
	db *sql.DB
}

func NewDatabase(dbPath string) (*Database, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Set connection pool settings
	db.SetMaxOpenConns(1) // SQLite prefers single-writer
	db.SetMaxIdleConns(1)

	d := &Database{db: db}
	if err := d.createTables(); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to create tables: %w", err)
	}

	return d, nil
}

func (d *Database) createTables() error {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL,
		created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
		updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
	);`

	_, err := d.db.Exec(query)
	if err != nil {
		return err
	}
	return nil
}

func (d *Database) Close() error {
	return d.db.Close()
}

func (d *Database) CreateBook(title, author string, year int, isbn string) (*Book, error) {
	now := time.Now().Format("2006-01-02 15:04:05")
	result, err := d.db.Exec(
		"INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
		title, author, year, isbn, now, now,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return nil, fmt.Errorf("failed to get last insert id: %w", err)
	}

	return &Book{
		ID:        int(id),
		Title:     title,
		Author:    author,
		Year:      year,
		ISBN:      isbn,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}, nil
}

func (d *Database) GetAllBooks(authorFilter string) ([]Book, error) {
	var query string
	var args []interface{}

	if authorFilter != "" {
		query = "SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author LIKE ? ORDER BY id"
		args = []interface{}{"%" + authorFilter + "%"}
	} else {
		query = "SELECT id, title, author, year, isbn, created_at, updated_at FROM books ORDER BY id"
	}

	rows, err := d.db.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query books: %w", err)
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var b Book
		var createdAt, updatedAt string
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt); err != nil {
			return nil, fmt.Errorf("failed to scan book: %w", err)
		}
		b.CreatedAt, _ = time.Parse("2006-01-02 15:04:05", createdAt)
		b.UpdatedAt, _ = time.Parse("2006-01-02 15:04:05", updatedAt)
		books = append(books, b)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("rows iteration error: %w", err)
	}

	return books, nil
}

func (d *Database) GetBook(id int) (*Book, error) {
	var b Book
	var createdAt, updatedAt string
	err := d.db.QueryRow(
		"SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?", id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &createdAt, &updatedAt)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("book with id %d not found", id)
		}
		return nil, fmt.Errorf("failed to get book: %w", err)
	}
	b.CreatedAt, _ = time.Parse("2006-01-02 15:04:05", createdAt)
	b.UpdatedAt, _ = time.Parse("2006-01-02 15:04:05", updatedAt)
	return &b, nil
}

func (d *Database) UpdateBook(id int, req *UpdateBookRequest) (*Book, error) {
	// Get existing book
	existing, err := d.GetBook(id)
	if err != nil {
		return nil, err
	}

	// Apply updates
	title := existing.Title
	author := existing.Author
	year := existing.Year
	isbn := existing.ISBN

	if req.Title != nil {
		title = *req.Title
	}
	if req.Author != nil {
		author = *req.Author
	}
	if req.Year != nil {
		year = *req.Year
	}
	if req.ISBN != nil {
		isbn = *req.ISBN
	}

	now := time.Now().Format("2006-01-02 15:04:05")
	_, err = d.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?",
		title, author, year, isbn, now, id,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to update book: %w", err)
	}

	existing.Title = title
	existing.Author = author
	existing.Year = year
	existing.ISBN = isbn
	existing.UpdatedAt, _ = time.Parse("2006-01-02 15:04:05", now)

	return existing, nil
}

func (d *Database) DeleteBook(id int) error {
	result, err := d.db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to check rows affected: %w", err)
	}

	if rowsAffected == 0 {
		return fmt.Errorf("book with id %d not found", id)
	}

	return nil
}
