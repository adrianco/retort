package database

import (
	"book-api/models"
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

// New creates a new database instance with the books table.
func New(dataSourceName string) (*DB, error) {
	conn, err := sql.Open("sqlite", dataSourceName)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	if err := conn.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	if err := createTable(conn); err != nil {
		return nil, fmt.Errorf("failed to create table: %w", err)
	}

	return &DB{conn: conn}, nil
}

func createTable(conn *sql.DB) error {
	query := `
	CREATE TABLE IF NOT EXISTS books (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		title TEXT NOT NULL,
		author TEXT NOT NULL,
		year INTEGER NOT NULL,
		isbn TEXT NOT NULL DEFAULT ''
	);`
	_, err := conn.Exec(query)
	return err
}

// Ensure DB implements models.BookStore.
var _ models.BookStore = (*DB)(nil)

type DB struct {
	conn *sql.DB
}

// Close closes the database connection.
func (d *DB) Close() error {
	return d.conn.Close()
}

// Create inserts a new book into the database.
func (d *DB) Create(book *models.Book) error {
	result, err := d.conn.Exec(
		"INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
		book.Title, book.Author, book.Year, book.ISBN,
	)
	if err != nil {
		return fmt.Errorf("failed to create book: %w", err)
	}

	id, err := result.LastInsertId()
	if err != nil {
		return fmt.Errorf("failed to get last insert id: %w", err)
	}

	book.ID = fmt.Sprintf("%d", id)
	return nil
}

// GetByID retrieves a book by its ID.
func (d *DB) GetByID(id string) (*models.Book, error) {
	var bookID int
	var title, author, isbn string
	var year int

	err := d.conn.QueryRow(
		"SELECT id, title, author, year, isbn FROM books WHERE id = ?", id,
	).Scan(&bookID, &title, &author, &year, &isbn)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, fmt.Errorf("book with id %s not found", id)
		}
		return nil, fmt.Errorf("failed to get book: %w", err)
	}

	return &models.Book{
		ID:     fmt.Sprintf("%d", bookID),
		Title:  title,
		Author: author,
		Year:   year,
		ISBN:   isbn,
	}, nil
}

// List returns all books, optionally filtered by author.
func (d *DB) List(authorFilter string) ([]models.Book, error) {
	var query string
	var args []interface{}

	if authorFilter != "" {
		query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
		args = append(args, authorFilter)
	} else {
		query = "SELECT id, title, author, year, isbn FROM books"
	}

	rows, err := d.conn.Query(query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query books: %w", err)
	}
	defer rows.Close()

	var books []models.Book
	for rows.Next() {
		var bookID int
		var title, author, isbn string
		var year int

		if err := rows.Scan(&bookID, &title, &author, &year, &isbn); err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		books = append(books, models.Book{
			ID:     fmt.Sprintf("%d", bookID),
			Title:  title,
			Author: author,
			Year:   year,
			ISBN:   isbn,
		})
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("row iteration error: %w", err)
	}

	if books == nil {
		books = []models.Book{}
	}

	return books, nil
}

// Update modifies an existing book.
func (d *DB) Update(id string, req models.UpdateBookRequest) (*models.Book, error) {
	if err := req.ValidatePartial(); err != nil {
		return nil, err
	}

	existing, err := d.GetByID(id)
	if err != nil {
		return nil, err
	}

	req.Apply(existing)

	_, err = d.conn.Exec(
		"UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
		existing.Title, existing.Author, existing.Year, existing.ISBN, id,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to update book: %w", err)
	}

	return existing, nil
}

// Delete removes a book by its ID.
func (d *DB) Delete(id string) error {
	result, err := d.conn.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("failed to delete book: %w", err)
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("failed to check rows affected: %w", err)
	}

	if rowsAffected == 0 {
		return fmt.Errorf("book with id %s not found", id)
	}

	return nil
}
