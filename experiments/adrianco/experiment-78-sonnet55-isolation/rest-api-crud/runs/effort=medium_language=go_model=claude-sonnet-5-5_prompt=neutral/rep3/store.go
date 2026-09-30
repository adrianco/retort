package main

import (
	"database/sql"
	"errors"

	_ "modernc.org/sqlite"
)

// Book is a book in the collection.
type Book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

var errNotFound = errors.New("not found")

// Store persists books in SQLite.
type Store struct{ db *sql.DB }

// NewStore opens the database at dsn and ensures the schema exists.
func NewStore(dsn string) (*Store, error) {
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1) // keeps in-memory DBs consistent and avoids lock errors
	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL DEFAULT 0,
		isbn TEXT NOT NULL DEFAULT ''
	)`)
	if err != nil {
		db.Close()
		return nil, err
	}
	return &Store{db: db}, nil
}

func (s *Store) Close() error { return s.db.Close() }

func (s *Store) Create(b *Book) error {
	res, err := s.db.Exec(`INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`,
		b.Title, b.Author, b.Year, b.ISBN)
	if err != nil {
		return err
	}
	b.ID, err = res.LastInsertId()
	return err
}

func (s *Store) List(author string) ([]Book, error) {
	q := `SELECT id, title, author, year, isbn FROM books`
	var args []any
	if author != "" {
		q += ` WHERE author = ?`
		args = append(args, author)
	}
	rows, err := s.db.Query(q+` ORDER BY id`, args...)
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

func (s *Store) Get(id int64) (*Book, error) {
	var b Book
	err := s.db.QueryRow(`SELECT id, title, author, year, isbn FROM books WHERE id = ?`, id).
		Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, errNotFound
	}
	return &b, err
}

func (s *Store) Update(b *Book) error {
	res, err := s.db.Exec(`UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?`,
		b.Title, b.Author, b.Year, b.ISBN, b.ID)
	if err != nil {
		return err
	}
	if n, _ := res.RowsAffected(); n == 0 {
		return errNotFound
	}
	return nil
}

func (s *Store) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	if n, _ := res.RowsAffected(); n == 0 {
		return errNotFound
	}
	return nil
}
