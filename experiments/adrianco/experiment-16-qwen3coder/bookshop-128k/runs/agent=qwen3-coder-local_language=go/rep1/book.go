package main

import (
	"database/sql"
)

type Book struct {
	ID     int    `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// BookStore interface for database operations
type BookStore interface {
	CreateBook(book *Book) error
	GetBooks(author string) ([]Book, error)
	GetBook(id int) (*Book, error)
	UpdateBook(id int, book *Book) error
	DeleteBook(id int) error
	HealthCheck() error
}

// SQLiteStore implements BookStore using SQLite
type SQLiteStore struct {
	db *sql.DB
}

// NewSQLiteStore creates a new SQLiteStore
func NewSQLiteStore(db *sql.DB) *SQLiteStore {
	return &SQLiteStore{db: db}
}

// CreateBook adds a new book to the database
func (s *SQLiteStore) CreateBook(book *Book) error {
	query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
	_, err := s.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
	return err
}

// GetBooks retrieves all books, optionally filtered by author
func (s *SQLiteStore) GetBooks(author string) ([]Book, error) {
	var query string
	var rows *sql.Rows
	var err error

	if author != "" {
		query = `SELECT id, title, author, year, isbn FROM books WHERE author = ?`
		rows, err = s.db.Query(query, author)
	} else {
		query = `SELECT id, title, author, year, isbn FROM books`
		rows, err = s.db.Query(query)
	}

	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []Book
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			return nil, err
		}
		books = append(books, book)
	}

	return books, nil
}

// GetBook retrieves a single book by ID
func (s *SQLiteStore) GetBook(id int) (*Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books WHERE id = ?`
	row := s.db.QueryRow(query, id)

	var book Book
	err := row.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
	if err != nil {
		return nil, err
	}

	return &book, nil
}

// UpdateBook updates an existing book
func (s *SQLiteStore) UpdateBook(id int, book *Book) error {
	query := `UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`
	_, err := s.db.Exec(query, book.Title, book.Author, book.Year, book.ISBN, id)
	return err
}

// DeleteBook removes a book from the database
func (s *SQLiteStore) DeleteBook(id int) error {
	query := `DELETE FROM books WHERE id = ?`
	_, err := s.db.Exec(query, id)
	return err
}

// HealthCheck checks if the database is accessible
func (s *SQLiteStore) HealthCheck() error {
	query := `SELECT 1`
	_, err := s.db.Exec(query)
	return err
}

// initDB initializes the database and creates the books table if it doesn't exist
func initDB() (*sql.DB, error) {
	db, err := sql.Open("sqlite3", "./books.db")
	if err != nil {
		return nil, err
	}

	// Create the books table
	query := `CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER,
		isbn TEXT
	)`

	_, err = db.Exec(query)
	if err != nil {
		return nil, err
	}

	// Create index on author for better query performance
	_, err = db.Exec(`CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)`)
	if err != nil {
		return nil, err
	}

	return db, nil
}