package handler

import (
	"encoding/json"
	"net/http"
	"strconv"

	"bookapi/model"

	"github.com/gorilla/mux"
)

type BookHandler struct {
	store *model.BookStore
}

func NewBookHandler(store *model.BookStore) *BookHandler {
	return &BookHandler{store: store}
}

func (h *BookHandler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func (h *BookHandler) ListBooks(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	authorFilter := r.URL.Query().Get("author")
	books, err := h.store.ListBooks(authorFilter)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(model.CreateError("failed to list books", http.StatusInternalServerError))
		return
	}
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(books)
}

func (h *BookHandler) GetBook(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	idStr := mux.Vars(r)["id"]
	id, err := strconv.Atoi(idStr)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(model.CreateError("invalid book ID", http.StatusBadRequest))
		return
	}

	book, err := h.store.GetBook(id)
	if err != nil {
		if err.Error() == "book not found" {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(model.CreateError("book not found", http.StatusNotFound))
			return
		}
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(model.CreateError("failed to get book", http.StatusInternalServerError))
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

func (h *BookHandler) CreateBook(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	var book model.Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(model.CreateError("invalid JSON", http.StatusBadRequest))
		return
	}

	if err := model.ValidateBook(&book); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(model.CreateError(err.Error(), http.StatusBadRequest))
		return
	}

	if err := h.store.CreateBook(&book); err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(model.CreateError("failed to create book", http.StatusInternalServerError))
		return
	}

	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

func (h *BookHandler) UpdateBook(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	idStr := mux.Vars(r)["id"]
	id, err := strconv.Atoi(idStr)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(model.CreateError("invalid book ID", http.StatusBadRequest))
		return
	}

	var book model.Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(model.CreateError("invalid JSON", http.StatusBadRequest))
		return
	}

	book.ID = id

	if err := model.ValidateBook(&book); err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(model.CreateError(err.Error(), http.StatusBadRequest))
		return
	}

	if err := h.store.UpdateBook(&book); err != nil {
		if err.Error() == "book not found" {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(model.CreateError("book not found", http.StatusNotFound))
			return
		}
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(model.CreateError("failed to update book", http.StatusInternalServerError))
		return
	}

	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

func (h *BookHandler) DeleteBook(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	idStr := mux.Vars(r)["id"]
	id, err := strconv.Atoi(idStr)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(model.CreateError("invalid book ID", http.StatusBadRequest))
		return
	}

	if err := h.store.DeleteBook(id); err != nil {
		if err.Error() == "book not found" {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(model.CreateError("book not found", http.StatusNotFound))
			return
		}
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(model.CreateError("failed to delete book", http.StatusInternalServerError))
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
