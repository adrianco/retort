package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

func getBooks(w http.ResponseWriter, r *http.Request, db *sql.DB) {
	w.Header().Set("Content-Type", "application/json")

	author := r.URL.Query().Get("author")
	
	var query string
	var rows *sql.Rows
	var err error
	
	if author != "" {
		query = "SELECT id, title, author, year, isbn FROM books WHERE author = ?"
		rows, err = db.Query(query, author)
	} else {
		query = "SELECT id, title, author, year, isbn FROM books"
		rows, err = db.Query(query)
	}
	
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	books := []Book{}
	for rows.Next() {
		var book Book
		err := rows.Scan(&book.ID, &book.Title, &book.Author, &book.Year, &book.ISBN)
		if err != nil {
			http.Error(w, "Database scan error", http.StatusInternalServerError)
			return
		}
		books = append(books, book)
	}

	json.NewEncoder(w).Encode(books)
}

func getBook(w http.ResponseWriter, r *http.Request, db *sql.DB) {
	w.Header().Set("Content-Type", "application/json")
	
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
			http.Error(w, "Database error", http.StatusInternalServerError)
		}
		return
	}

	json.NewEncoder(w).Encode(book)
}

func createBook(w http.ResponseWriter, r *http.Request, db *sql.DB) {
	w.Header().Set("Content-Type", "application/json")
	
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Validation
	if book.Title == "" || book.Author == "" {
		http.Error(w, "Title and author are required", http.StatusBadRequest)
		return
	}

	result, err := db.Exec("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", book.Title, book.Author, book.Year, book.ISBN)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	id, err := result.LastInsertId()
	if err != nil {
		http.Error(w, "Failed to get book ID", http.StatusInternalServerError)
		return
	}

	book.ID = int(id)
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func updateBook(w http.ResponseWriter, r *http.Request, db *sql.DB) {
	w.Header().Set("Content-Type", "application/json")
	
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

	// Validation
	if book.Title == "" || book.Author == "" {
		http.Error(w, "Title and author are required", http.StatusBadRequest)
		return
	}

	_, err = db.Exec("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", book.Title, book.Author, book.Year, book.ISBN, id)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	// Return updated book
	var updatedBook Book
	err = db.QueryRow("SELECT id, title, author, year, isbn FROM books WHERE id = ?", id).Scan(&updatedBook.ID, &updatedBook.Title, &updatedBook.Author, &updatedBook.Year, &updatedBook.ISBN)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	json.NewEncoder(w).Encode(updatedBook)
}

func deleteBook(w http.ResponseWriter, r *http.Request, db *sql.DB) {
	w.Header().Set("Content-Type", "application/json")
	
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, "Invalid book ID", http.StatusBadRequest)
		return
	}

	result, err := db.Exec("DELETE FROM books WHERE id = ?", id)
	if err != nil {
		http.Error(w, "Database error", http.StatusInternalServerError)
		return
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		http.Error(w, "Failed to get rows affected", http.StatusInternalServerError)
		return
	}

	if rowsAffected == 0 {
		http.Error(w, "Book not found", http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
