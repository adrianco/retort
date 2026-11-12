package main

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func createBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CreateBookRequest
	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		http.Error(w, `{"error": "Invalid request body"}`, http.StatusBadRequest)
		return
	}

	// Validate required fields
	if req.Title == "" {
		http.Error(w, `{"error": "Title is required"}`, http.StatusBadRequest)
		return
	}
	if req.Author == "" {
		http.Error(w, `{"error": "Author is required"}`, http.StatusBadRequest)
		return
	}

	book, err := createBook(req)
	if err != nil {
		http.Error(w, `{"error": "Failed to create book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func listBooksHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	author := r.URL.Query().Get("author")

	books, err := getAllBooks(author)
	if err != nil {
		http.Error(w, `{"error": "Failed to fetch books"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(books)
}

func getBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, `{"error": "Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	book, err := getBookByID(id)
	if err != nil {
		http.Error(w, `{"error": "Book not found"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func updateBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, `{"error": "Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	var req UpdateBookRequest
	err = json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		http.Error(w, `{"error": "Invalid request body"}`, http.StatusBadRequest)
		return
	}

	// Validate required fields if provided
	if req.Title != nil && *req.Title == "" {
		http.Error(w, `{"error": "Title cannot be empty"}`, http.StatusBadRequest)
		return
	}
	if req.Author != nil && *req.Author == "" {
		http.Error(w, `{"error": "Author cannot be empty"}`, http.StatusBadRequest)
		return
	}

	book, err := updateBook(id, req)
	if err != nil {
		http.Error(w, `{"error": "Book not found"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(book)
}

func deleteBookHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	idStr := strings.TrimPrefix(r.URL.Path, "/books/")
	id, err := strconv.Atoi(idStr)
	if err != nil {
		http.Error(w, `{"error": "Invalid book ID"}`, http.StatusBadRequest)
		return
	}

	err = deleteBook(id)
	if err != nil {
		http.Error(w, `{"error": "Book not found"}`, http.StatusNotFound)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
