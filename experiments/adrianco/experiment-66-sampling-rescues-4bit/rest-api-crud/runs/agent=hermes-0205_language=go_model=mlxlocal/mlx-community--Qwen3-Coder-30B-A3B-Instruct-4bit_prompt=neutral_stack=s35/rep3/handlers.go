package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

// Health check handler
func healthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
 json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

// Create a new book
func createBook(w http.ResponseWriter, r *http.Request) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
	 http.Error(w, "Invalid JSON", http.StatusBadRequest)
	 return
	}

	if book.Title == "" || book.Author == "" {
	 http.Error(w, "Title and author are required", http.StatusBadRequest)
	 return
	}

	// Insert into database
 query := `INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)`
 result, err := db.Exec(query, book.Title, book.Author, book.Year, book.ISBN)
 if err != nil {
	 http.Error(w, "Failed to create book", http.StatusInternalServerError)
	 return
 }

 id, err := result.LastInsertId()
 if err != nil {
	 http.Error(w, "Failed to get book ID", http.StatusInternalServerError)
	 return
 }

 book.ID = int(id)

 w.Header().Set("Content-Type", "application/json")
 w.WriteHeader(http.StatusCreated)
 json.NewEncoder(w).Encode(book)
}

// Get all books with optional author filter
func getAllBooks(w http.ResponseWriter, r *http.Request) {
	// Check if author query parameter exists
 author := r.URL.Query().Get("author")
 var rows *sql.Rows
 var err error

 if author != "" {
	 rows, err = db.Query("SELECT id, title, author, year, isbn FROM books WHERE author LIKE ?", "%"+author+"%")
 } else {
	 rows, err = db.Query("SELECT id, title, author, year, isbn FROM books")
 }

 if err != nil {
	 http.Error(w, "Failed to fetch books", http.StatusInternalServerError)
	 return
 }
 defer rows.Close()

 var books []Book
 for rows.Next() {
	 var b Book
	 err := rows.Scan(&b.ID, &b.Title, &b.Author, &b.Year, &b.ISBN)
	 if err != nil {
		 http.Error(w, "Failed to parse book data", http.StatusInternalServerError)
		 return
	 }
	 books = append(books, b)
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(books)
}

// Get a single book by ID
func getBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
	 http.Error(w, "Invalid book ID", http.StatusBadRequest)
	 return
 }

 var book Book
 err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
 if err != nil {
	 if err == sql.ErrNoRows {
		 http.Error(w, "Book not found", http.StatusNotFound)
	 } else {
		 http.Error(w, "Failed to fetch book", http.StatusInternalServerError)
	 }
	 return
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

// Update a book
func updateBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
	 http.Error(w, "Invalid book ID", http.StatusBadRequest)
	 return
 }

 var book Book
 if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
	 http.Error(w, "Invalid JSON", http.StatusBadRequest)
	 return
 }

 // Check if book exists
 err = db.QueryRow("SELECT id FROM books WHERE id = ?", id).Scan(&book.ID)
 if err != nil {
	 if err == sql.ErrNoRows {
		 http.Error(w, "Book not found", http.StatusNotFound)
	 } else {
		 http.Error(w, "Failed to check book", http.StatusInternalServerError)
	 }
	 return
 }

 // Update the book
 _, err = db.Exec("UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?", book.Title, book.Author, book.Year, book.ISBN, id)
 if err != nil {
	 http.Error(w, "Failed to update book", http.StatusInternalServerError)
 }

 w.Header().Set("Content-Type", "application/json")
 json.NewEncoder(w).Encode(book)
}

// Delete a book
func deleteBook(w http.ResponseWriter, r *http.Request) {
 vars := mux.Vars(r)
 id, err := strconv.Atoi(vars["id"])
 if err != nil {
	 http.Error(w, "Invalid book ID", http.StatusBadRequest)
	 return
 }

 _, err = db.Exec("DELETE FROM books WHERE id = ?", id)
 if err != nil {
	 http.Error(w, "Failed to delete book", http.StatusInternalServerError)
 }

 w.WriteHeader(http.StatusNoContent)
}