package main

import (
	"database/sql"
	"errors"

	_ "github.com/mattn/go-sqlite3"
)

// Database provides CRUD operations on the books table backed by SQLite.
type Database struct {
	db *sql.DB
}

// NewDatabase opens (or creates) the SQLite database and ensures the
// books table exists. Use ":memory:" for in-memory testing.
func NewDatabase(dsn string) (*Database, error) {
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		return nil, err
	}

	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id       INTEGER PRIMARY KEY AUTOINCREMENT,
			title    TEXT NOT NULL,
			author   TEXT NOT NULL,
			year     INTEGER DEFAULT 0,
			isbn     TEXT DEFAULT ''
		)
	`)
	if err != nil {
		return nil, err
	}

	return &Database{db: db}, nil
}

// Close releases the database connection.
func (d *Database) Close() error {
	return d.db.Close()
}

// CreateBook inserts a new book and sets its ID.
func (d *Database) CreateBook(book *Book) error {
	result, err := d.db.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN,
	)
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

// GetBook retrieves a book by its ID. Returns an error if the ID does not exist.
func (d *Database) GetBook(id int) (*Book, error) {
	book := &Book{}
	err := d.db.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, errors.New("book not found")
		}
		return nil, err
	}
	return book, nil
}

// UpdateBook replaces the fields of an existing book.
func (d *Database) UpdateBook(book *Book) error {
	_, err := d.db.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		book.Title, book.Author, book.Year, book.ISBN, book.ID,
	)
	return err
}

// DeleteBook removes a book by its ID.
func (d *Database) DeleteBook(id int) error {
	_, err := d.db.Exec("DELETE FROM books WHERE id = ?", id)
	return err
}

// ListBooks returns all books ordered by ID.
func (d *Database) ListBooks() ([]*Book, error) {
	rows, err := d.db.Query("SELECT id, title, author, year, isbn FROM books ORDER BY id")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	books := make([]*Book, 0)
	for rows.Next() {
		b := &Book{}
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, nil
}

// ListBooksByAuthor returns all books written by the given author.
func (d *Database) ListBooksByAuthor(author string) ([]*Book, error) {
	rows, err := d.db.Query(
		"SELECT id, title, author, year, isbn FROM books WHERE author = ? ORDER BY id", author,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	books := make([]*Book, 0)
	for rows.Next() {
		b := &Book{}
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, nil
}
