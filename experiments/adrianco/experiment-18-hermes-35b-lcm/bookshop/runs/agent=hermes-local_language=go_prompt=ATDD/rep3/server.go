package main

import (
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gorilla/mux"
)

// Server is an HTTP handler that exposes the Book REST API.
type Server struct {
	db     *Database
	router *mux.Router
}

// NewServer creates a new Server wired to the given database.
func NewServer(db *Database) *Server {
	s := &Server{db: db, router: mux.NewRouter()}
	s.setupRoutes()
	return s
}

// ServeHTTP implements the http.Handler interface.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.router.ServeHTTP(w, r)
}

// setupRoutes registers all API endpoint handlers.
func (s *Server) setupRoutes() {
	r := s.router

	r.HandleFunc("/health", s.handleHealth).Methods("GET")
	r.HandleFunc("/books", s.handleCreateBook).Methods("POST")
	r.HandleFunc("/books", s.handleListBooks).Methods("GET")
	r.HandleFunc("/books/{id}", s.handleGetBook).Methods("GET")
	r.HandleFunc("/books/{id}", s.handleUpdateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", s.handleDeleteBook).Methods("DELETE")
}

// --- helpers ---

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// --- endpoints ---

// GET /health
func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// POST /books
func (s *Server) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if err := book.Validate(); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	if err := s.db.CreateBook(&book); err != nil {
		writeError(w, http.StatusInternalServerError, "failed to create book")
		return
	}

	writeJSON(w, http.StatusCreated, book)
}

// GET /books
func (s *Server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	author := r.URL.Query().Get("author")

	var books []*Book
	var err error
	if author != "" {
		books, err = s.db.ListBooksByAuthor(author)
	} else {
		books, err = s.db.ListBooks()
	}

	if err != nil {
		writeError(w, http.StatusInternalServerError, "failed to list books")
		return
	}

	writeJSON(w, http.StatusOK, books)
}

// GET /books/{id}
func (s *Server) handleGetBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book ID")
		return
	}

	book, err := s.db.GetBook(id)
	if err != nil {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// PUT /books/{id}
func (s *Server) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book ID")
		return
	}

	var book Book
	if err := json.NewDecoder(r.Body).Decode(&book); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	book.ID = id

	if err := book.Validate(); err != nil {
		writeError(w, http.StatusBadRequest, err.Error())
		return
	}

	// Verify existence before updating
	if _, err := s.db.GetBook(id); err != nil {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	if err := s.db.UpdateBook(&book); err != nil {
		writeError(w, http.StatusInternalServerError, "failed to update book")
		return
	}

	writeJSON(w, http.StatusOK, book)
}

// DELETE /books/{id}
func (s *Server) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	id, err := strconv.Atoi(vars["id"])
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid book ID")
		return
	}

	if _, err := s.db.GetBook(id); err != nil {
		writeError(w, http.StatusNotFound, "book not found")
		return
	}

	if err := s.db.DeleteBook(id); err != nil {
		writeError(w, http.StatusInternalServerError, "failed to delete book")
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNoContent)
}
