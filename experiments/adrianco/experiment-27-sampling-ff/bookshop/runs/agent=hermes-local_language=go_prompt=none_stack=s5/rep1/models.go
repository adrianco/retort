package main

import (
	"database/sql"
	"time"

	_ "modernc.org/sqlite"
)

// Book represents a book in the collection.
type Book struct {
	ID        int64      `json:"id"`
	Title     string     `json:"title"`
	Author    string     `json:"author"`
	Year      int        `json:"year"`
	ISBN      string     `json:"isbn"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt *time.Time `json:"updated_at,omitempty"`
}

// CreateBookRequest represents the JSON body for creating a book.
type CreateBookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

// UpdateBookRequest represents the JSON body for updating a book.
type UpdateBookRequest struct {
	Title  *string `json:"title,omitempty"`
	Author *string `json:"author,omitempty"`
	Year   *int    `json:"year,omitempty"`
	ISBN   *string `json:"isbn,omitempty"`
}

// BookStore provides CRUD operations backed by SQLite.
type BookStore struct {
	db *sql.DB
}

// NewBookStore opens (or creates) the SQLite database and ensures the schema exists.
func NewBookStore(dataSourceName string) (*BookStore, error) {
	db, err := sql.Open("sqlite", dataSourceName)
	if err != nil {
		return nil, err
	}

	store := &BookStore{db: db}
	if err := store.initSchema(); err != nil {
		db.Close()
		return nil, err
	}

	return store, nil
}

// initSchema creates the books table if it does not exist.
func (s *BookStore) initSchema() error {
	_, err := s.db.Exec(`
		CREATE TABLE IF NOT EXISTS books (
			id         INTEGER PRIMARY KEY AUTOINCREMENT,
			title      TEXT    NOT NULL,
			author     TEXT    NOT NULL,
			year       INTEGER NOT NULL,
			isbn       TEXT    NOT NULL UNIQUE,
			created_at TEXT    NOT NULL DEFAULT (datetime('now')),
			updated_at TEXT
		);
	`)
	return err
}

// Create inserts a new book and returns it with the generated ID.
func (s *BookStore) Create(req CreateBookRequest) (*Book, error) {
	now := time.Now().UTC()
	res, err := s.db.Exec(
		`INSERT INTO books (title, author, year, isbn, created_at) VALUES (?, ?, ?, ?, ?)`,
		req.Title, req.Author, req.Year, req.ISBN, now.Format(time.RFC3339),
	)
	if err != nil {
		return nil, err
	}

	id, _ := res.LastInsertId()
	return &Book{
		ID:        id,
		Title:     req.Title,
		Author:    req.Author,
		Year:      req.Year,
		ISBN:      req.ISBN,
		CreatedAt: now,
	}, nil
}

// GetAll returns all books, optionally filtered by author.
func (s *BookStore) GetAll(authorFilter string) ([]*Book, error) {
	var query string
	var args []interface{}

	if authorFilter != "" {
		query = `SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE author = ? ORDER BY id`
		args = append(args, authorFilter)
	} else {
		query = `SELECT id, title, author, year, isbn, created_at, updated_at FROM books ORDER BY id`
	}

	rows, err := s.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var books []*Book
	for rows.Next() {
		b := &Book{}
		var created, updated sql.NullString
		if err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &created, &updated); err != nil {
			return nil, err
		}
		if created.Valid {
			t, _ := time.Parse(time.RFC3339, created.String)
			b.CreatedAt = t
		}
		if updated.Valid {
			t, _ := time.Parse(time.RFC3339, updated.String)
			b.UpdatedAt = &t
		}
		books = append(books, b)
	}
	return books, rows.Err()
}

// GetByID returns a single book by its ID.
func (s *BookStore) GetByID(id int64) (*Book, error) {
	b := &Book{}
	var created, updated sql.NullString
	err := s.db.QueryRow(
		`SELECT id, title, author, year, isbn, created_at, updated_at FROM books WHERE id = ?`, id,
	).Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN, &created, &updated)
	if err != nil {
		return nil, err
	}

	if created.Valid {
		t, _ := time.Parse(time.RFC3339, created.String)
		b.CreatedAt = t
	}
	if updated.Valid {
		t, _ := time.Parse(time.RFC3339, updated.String)
		b.UpdatedAt = &t
	}

	return b, nil
}

// Update modifies an existing book and returns the updated record.
func (s *BookStore) Update(id int64, req UpdateBookRequest) (*Book, error) {
	book, err := s.GetByID(id)
	if err != nil {
		return nil, err
	}

	if req.Title != nil {
		book.Title = *req.Title
	}
	if req.Author != nil {
		book.Author = *req.Author
	}
	if req.Year != nil {
		book.Year = *req.Year
	}
	if req.ISBN != nil {
		book.ISBN = *req.ISBN
	}

	now := time.Now().UTC()
	_, err = s.db.Exec(
		`UPDATE books SET title=?, author=?, year=?, isbn=?, updated_at=? WHERE id=?`,
		book.Title, book.Author, book.Year, book.ISBN, now.Format(time.RFC3339), id,
	)
	if err != nil {
		return nil, err
	}

	book.UpdatedAt = &now
	return book, nil
}

// Delete removes a book by ID. Returns sql.ErrNoRows if not found.
func (s *BookStore) Delete(id int64) error {
	res, err := s.db.Exec(`DELETE FROM books WHERE id = ?`, id)
	if err != nil {
		return err
	}
	rows, _ := res.RowsAffected()
	if rows == 0 {
		return sql.ErrNoRows
	}
	return nil
}

// Close closes the database connection.
func (s *BookStore) Close() error {
	return s.db.Close()
}
