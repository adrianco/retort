package main

import (
	"database/sql"
	"errors"

	_ "modernc.org/sqlite"
)

// ErrNotFound is returned when a book does not exist.
var ErrNotFound = errors.New("book not found")

// Book is a single entry in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// Store persists books in SQLite.
type Store struct {
	db *sql.DB
}

// NewStore opens (and if necessary creates) the database at dsn.
// Use ":memory:" for an ephemeral database.
func NewStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	// A single connection keeps ":memory:" databases consistent and
	// serialises writes, which is all SQLite supports anyway.
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

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) Ping() error { return s.db.Ping() }

func (s *Store) Create(b *Book) error {
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return err
	}
	b.ID, err = res.LastInsertId()
	return err
}

// List returns all books ordered by ID. If author is non-empty only books
// by that author (case-insensitive exact match) are returned.
func (s *Store) List(author string) ([]Book, error) {
	query := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		query += ` WHERE author = ? COLLATE NOCASE`
		args = append(args, author)
	}
	query += ` ORDER BY id`

	rows, err := s.db.Query(query, args...)
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

func (s *Store) Get(id int64) (Book, error) {
	var b Book
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return b, ErrNotFound
	}
	return b, err
}

// Update replaces the book identified by b.ID.
func (s *Store) Update(b Book) error {
	res, err := s.db.Exec(
		`UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?`,
		b.Title, b.Author, b.Year, b.ISBN, b.ID)
	if err != nil {
		return err
	}
	return requireAffected(res)
}

func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	return requireAffected(res)
}

func requireAffected(res sql.Result) error {
	n, err := res.RowsAffected()
	if err != nil {
		return err
	}
	if n == 0 {
		return ErrNotFound
	}
	return nil
}
