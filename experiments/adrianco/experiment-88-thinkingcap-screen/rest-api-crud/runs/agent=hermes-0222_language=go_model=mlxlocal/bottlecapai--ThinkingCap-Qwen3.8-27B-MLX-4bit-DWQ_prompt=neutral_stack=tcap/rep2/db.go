package main

import (
	"database/sql"
	"errors"
	"strings"

	_ "modernc.org/sqlite"
)

// Book is a single entry in the collection. Year 0 means "not set".
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")

// Store wraps the SQLite database for the book collection.
type Store struct {
	db *sql.DB
}

// NewStore opens (or creates) the SQLite database at path and ensures
// the schema exists. Use ":memory:" for an in-memory database.
func NewStore(path string) (*Store, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	// SQLite allows a single writer; serialize access to avoid SQLITE_BUSY.
	db.SetMaxOpenConns(1)

	schema := `CREATE TABLE IF NOT EXISTS books (
		id     INTEGER PRIMARY KEY AUTOINCREMENT,
		title  TEXT NOT NULL,
		author TEXT NOT NULL,
		year   INTEGER NOT NULL DEFAULT 0,
		isbn   TEXT NOT NULL DEFAULT ''
	)`
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

// Close closes the underlying database.
func (s *Store) Close() error { return s.db.Close() }

// Ping checks database connectivity.
func (s *Store) Ping() error { return s.db.Ping() }

// Create inserts b and sets b.ID to the new row id.
func (s *Store) Create(b *Book) error {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN,
	)
	if err != nil {
		return err
	}
	b.ID, err = res.LastInsertId()
	return err
}

// Get returns the book with the given id, or ErrNotFound.
func (s *Store) Get(id int64) (*Book, error) {
	return scanBook(s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id))
}

// List returns all books, optionally filtered by author
// (case-insensitive exact match).
func (s *Store) List(author string) ([]Book, error) {
	var (
		rows *sql.Rows
		err  error
	)
	if strings.TrimSpace(author) == "" {
		rows, err = s.db.Query(`SELECT id, title, author, year, isbn FROM books ORDER BY id`)
	} else {
		rows, err = s.db.Query(
			`SELECT id, title, author, year, isbn FROM books WHERE author = ? COLLATE NOCASE ORDER BY id`,
			author)
	}
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

// Update replaces the fields of the book with the given id.
// Returns ErrNotFound if no such book exists.
func (s *Store) Update(b *Book) error {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, b.ID,
	)
	if err != nil {
		return err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

// Delete removes the book with the given id.
// Returns ErrNotFound if no such book exists.
func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}

func scanBook(row *sql.Row) (*Book, error) {
	var b Book
	err := row.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, err
	}
	return &b, nil
}
