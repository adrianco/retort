package main

import (
	"database/sql"
	"errors"

	_ "modernc.org/sqlite"
)

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")

// Store persists books in SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (and migrates) a SQLite database at dsn.
func NewStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	// A single connection keeps in-memory databases consistent and avoids
	// SQLITE_BUSY errors from concurrent writers.
	db.SetMaxOpenConns(1)
	const schema = `CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER NOT NULL DEFAULT 0,
		isbn   TEXT NOT NULL DEFAULT ''
	);
	CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);`
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

// Close releases the database.
func (s *Store) Close() error { return s.db.Close() }

// Ping checks database connectivity.
func (s *Store) Ping() error { return s.db.Ping() }

// Create inserts a book and returns it with its new ID.
func (s *Store) Create(b Book) (Book, error) {
	res, err := s.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return Book{}, err
	}
	b.ID, err = res.LastInsertId()
	return b, err
}

// List returns all books, optionally filtered by exact author name.
func (s *Store) List(author string) ([]Book, error) {
	q := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		q += ` WHERE author = ?`
		args = append(args, author)
	}
	q += ` ORDER BY id`
	rows, err := s.db.Query(q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	books := []Book{}
	for rows.Next() {
		var b Book
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN); err != nil {
			return nil, err
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

// Get returns a single book by ID.
func (s *Store) Get(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return Book{}, ErrNotFound
	}
	return b, err
}

// Update replaces the fields of an existing book.
func (s *Store) Update(id int64, b Book) (Book, error) {
	res, err := s.db.Exec(`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, id)
	if err != nil {
		return Book{}, err
	}
	if n, _ := res.RowsAffected(); n == 0 {
		return Book{}, ErrNotFound
	}
	b.ID = id
	return b, nil
}

// Delete removes a book by ID.
func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	if n, _ := res.RowsAffected(); n == 0 {
		return ErrNotFound
	}
	return nil
}
