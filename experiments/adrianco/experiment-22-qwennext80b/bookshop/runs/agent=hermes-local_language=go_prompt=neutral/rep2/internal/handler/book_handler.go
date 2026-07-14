package handler

import (
	"encoding/json"
	"net/http"
	"strconv"

	"book-api/internal/model"

	"github.com/gorilla/mux"
)

type BookHandler struct {
	bookStore *model.BookStore
}

func NewBookHandler(bookStore *model.BookStore) *BookHandler {
	return &BookHandler{bookStore: bookStore}
}

type BookRequest struct {
	Title  string `json:"title"`
	Author string `json:"author"`
	Year   int    `json:"year"`
	ISBN   string `json:"isbn"`
}

func (h *BookHandler) CreateBook(w http.ResponseWriter, r *http.Request) {
	var req BookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "invalid JSON"}`, http.StatusBadRequest)
		return
	}

	if req.Title == "" {
		http.Error(w, `{"error": "title is required"}`, http.StatusBadRequest)
		return
	}

	if req.Author == "" {
		http.Error(w, `{"error": "author is required"}`, http.StatusBadRequest)
		return
	}

	book := &model.Book{
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	if err := h.bookStore.CreateBook(book); err != nil {
		http.Error(w, `{"error": "failed to create book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func (h *BookHandler) GetBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	idStr := vars["id"]
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		http.Error(w, `{"error": "invalid book ID"}`, http.StatusBadRequest)
		return
	}

	book, err := h.bookStore.GetBook(id)
	if err != nil {
		if err.Error() == "book not found" {
			http.Error(w, `{"error": "book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"error": "failed to get book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

func (h *BookHandler) ListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")
	var books []*model.Book
	var err error

	if author != "" {
		books, err = h.bookStore.GetBooksByAuthor(author)
	} else {
		books, err = h.bookStore.GetAllBooks()
	}

	if err != nil {
		http.Error(w, `{"error": "failed to list books"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(books)
}

func (h *BookHandler) UpdateBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	idStr := vars["id"]
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		http.Error(w, `{"error": "invalid book ID"}`, http.StatusBadRequest)
		return
	}

	var req BookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, `{"error": "invalid JSON"}`, http.StatusBadRequest)
		return
	}

	if req.Title == "" {
		http.Error(w, `{"error": "title is required"}`, http.StatusBadRequest)
		return
	}

	if req.Author == "" {
		http.Error(w, `{"error": "author is required"}`, http.StatusBadRequest)
		return
	}

	book := &model.Book{
		Title:  req.Title,
		Author: req.Author,
		Year:   req.Year,
		ISBN:   req.ISBN,
	}

	err = h.bookStore.UpdateBook(id, book)
	if err != nil {
		if err.Error() == "book not found" {
			http.Error(w, `{"error": "book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"error": "failed to update book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

func (h *BookHandler) DeleteBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	idStr := vars["id"]
	id, err := strconv.ParseInt(idStr, 10, 64)
	if err != nil {
		http.Error(w, `{"error": "invalid book ID"}`, http.StatusBadRequest)
		return
	}

	err = h.bookStore.DeleteBook(id)
	if err != nil {
		if err.Error() == "book not found" {
			http.Error(w, `{"error": "book not found"}`, http.StatusNotFound)
			return
		}
		http.Error(w, `{"error": "failed to delete book"}`, http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNoContent)
}

func (h *BookHandler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}
