package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	// Create SQLite repository
	repo, err := NewSQLiteRepo("books.db")
	if err != nil {
		log.Fatalf("failed to initialize database: %v", err)
	}
	defer repo.Close()

	handler := NewHandler(repo)

	// Setup routes
	mux := http.NewServeMux()
	mux.HandleFunc("/health", handler.healthCheck)
	mux.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			handler.createBook(w, r)
		case http.MethodGet:
			handler.listBooks(w, r)
		default:
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		}
	})
	mux.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			handler.getBook(w, r)
		case http.MethodPut:
			handler.updateBook(w, r)
		case http.MethodDelete:
			handler.deleteBook(w, r)
		default:
			http.Error(w, `{"error":"method not allowed"}`, http.StatusMethodNotAllowed)
		}
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	addr := fmt.Sprintf(":%s", port)
	fmt.Printf("Server starting on %s\n", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("failed to start server: %v", err)
	}
}
