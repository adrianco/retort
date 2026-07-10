package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"
)

type Server struct {
	db *Database
}

func NewServer(db *Database) *Server {
	return &Server{db: db}
}

// HandleHealth responds to /health.
func (s *Server) HandleHealth(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	resp := HealthResponse{
		Status:    "ok",
		Timestamp: fmt.Sprintf("%d", time.Now().Unix()),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

// HandleBooks handles all book-related routes.
func (s *Server) HandleBooks(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path

	if path == "/books" {
		switch r.Method {
		case http.MethodGet:
			s.HandleListBooks(w, r)
		case http.MethodPost:
			s.HandleCreateBook(w, r)
		default:
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		}
		return
	}

	// /books/{id}
	idStr := strings.TrimPrefix(path, "/books/")
	if idStr != path { // actually had /books/ prefix
		if id, err := strconv.Atoi(idStr); err == nil {
			switch r.Method {
			case http.MethodGet:
				s.HandleGetBook(w, r, id)
			case http.MethodPut:
				s.HandleUpdateBook(w, r, id)
			case http.MethodDelete:
				s.HandleDeleteBook(w, r, id)
			default:
				http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			}
			return
		}
	}

	http.Error(w, "not found", http.StatusNotFound)
}

// HandleCreateBook handles POST /books.
func (s *Server) HandleCreateBook(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req CreateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error: "invalid JSON body",
		})
		return
	}

	// Validation
	if errs := validateCreate(req); len(errs) > 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error:      "validation failed",
			Validation: errs,
		})
		return
	}

	book, err := s.db.CreateBook(req.Title, req.Author, req.Year, req.ISBN)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error: "failed to create book",
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(book)
}

// HandleListBooks handles GET /books?author=X.
func (s *Server) HandleListBooks(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	authorFilter := r.URL.Query().Get("author")

	books, err := s.db.GetAllBooks(authorFilter)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error: "failed to list books",
		})
		return
	}

	if books == nil {
		books = []Book{}
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(books)
}

// HandleGetBook handles GET /books/{id}.
func (s *Server) HandleGetBook(w http.ResponseWriter, r *http.Request, id int) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	book, err := s.db.GetBook(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(ErrorResponse{
				Error: "book not found",
			})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error: "failed to get book",
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

// HandleUpdateBook handles PUT /books/{id}.
func (s *Server) HandleUpdateBook(w http.ResponseWriter, r *http.Request, id int) {
	if r.Method != http.MethodPut {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req UpdateBookRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error: "invalid JSON body",
		})
		return
	}

	book, err := s.db.UpdateBook(id, &req)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(ErrorResponse{
				Error: "book not found",
			})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error: "failed to update book",
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(book)
}

// HandleDeleteBook handles DELETE /books/{id}.
func (s *Server) HandleDeleteBook(w http.ResponseWriter, r *http.Request, id int) {
	if r.Method != http.MethodDelete {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	err := s.db.DeleteBook(id)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(ErrorResponse{
				Error: "book not found",
			})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ErrorResponse{
			Error: "failed to delete book",
		})
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

// validateCreate checks the CreateBookRequest for required fields.
func validateCreate(req CreateBookRequest) []ValidationError {
	var errs []ValidationError
	if strings.TrimSpace(req.Title) == "" {
		errs = append(errs, ValidationError{
			Field:   "title",
			Message: "title is required",
		})
	}
	if strings.TrimSpace(req.Author) == "" {
		errs = append(errs, ValidationError{
			Field:   "author",
			Message: "author is required",
		})
	}
	return errs
}
