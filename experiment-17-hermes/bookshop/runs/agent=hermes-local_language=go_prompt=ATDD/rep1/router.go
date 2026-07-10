package main

import (
	"database/sql"
	"encoding/json"
	"net/http"

	"github.com/gorilla/mux"
)

func initRouter(db *sql.DB) *mux.Router {
	r := mux.NewRouter()

	// Routes
	r.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case "GET":
			getBooks(w, r, db)
		case "POST":
			createBook(w, r, db)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	}).Methods("GET", "POST")

	r.HandleFunc("/books/{id}", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case "GET":
			getBook(w, r, db)
		case "PUT":
			updateBook(w, r, db)
		case "DELETE":
			deleteBook(w, r, db)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	}).Methods("GET", "PUT", "DELETE")

	r.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
	}).Methods("GET")

	return r
}
