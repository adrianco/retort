package main

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

type BookHandler struct {
	repo BookRepository
}

func NewBookHandler(repo BookRepository) *BookHandler {
	return &BookHandler{repo: repo}
}

func (h *BookHandler) CreateBook(w http.ResponseWriter, r *http.Request) {
	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid JSON"}`, http.StatusBadRequest)
		return
	}

	// Validate input
	if err := ValidateStruct(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	book := &Book{
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	if err := h.repo.Create(book); err != nil {
		http.Error(w, `{"error":"failed to create book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func (h *BookHandler) ListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	filters := make(map[string]string)
	if author != "" {
		filters["author"] = author
	}

	books, err := h.repo.List(filters)
	if err != nil {
		http.Error(w, `{"error":"failed to list books"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(books)
}

func (h *BookHandler) GetBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, `{"error":"invalid book ID"}`, http.StatusBadRequest)
		return
	}

	book, err := h.repo.GetByID(id)
	if err != nil {
		http.Error(w, `{"error":"book not found"}`, http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

func (h *BookHandler) UpdateBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, `{"error":"invalid book ID"}`, http.StatusBadRequest)
		return
	}

	book, err := h.repo.GetByID(id)
	if err != nil {
		http.Error(w, `{"error":"book not found"}`, http.StatusNotFound)
		return
	}

	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error":"invalid JSON"}`, http.StatusBadRequest)
		return
	}

	// Update fields
	if req.Title != "" {
		book.Title = req.Title
	}
	if req.Author != "" {
		book.Author = req.Author
	}
	book.Year = req.Year
	book.ISBN = req.ISBN

	// Validate
	if err := ValidateStruct(book); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if err := h.repo.Update(book); err != nil {
		http.Error(w, `{"error":"failed to update book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

func (h *BookHandler) DeleteBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		http.Error(w, `{"error":"invalid book ID"}`, http.StatusBadRequest)
		return
	}

	if err := h.repo.Delete(id); err != nil {
		http.Error(w, `{"error":"failed to delete book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNoContent)
}
