package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}

	store, err := NewBookStore(dbPath)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer store.Close()

	api := NewAPI(store)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", api.HealthCheck)

	// POST /books
	mux.HandleFunc("POST /books", func(w http.ResponseWriter, r *http.Request) {
		api.CreateBook(w, r)
	})

	// GET /books (with optional ?author= filter)
	mux.HandleFunc("GET /books", func(w http.ResponseWriter, r *http.Request) {
		api.ListBooks(w, r)
	})

	// GET /books/{id}, PUT /books/{id}, DELETE /books/{id}
	mux.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case "GET":
			api.GetBook(w, r)
		case "PUT":
			api.UpdateBook(w, r)
		case "DELETE":
			api.DeleteBook(w, r)
		default:
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		}
	})

	addr := fmt.Sprintf(":%s", port)
	log.Printf("Server starting on %s (db=%s)", addr, dbPath)

	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
