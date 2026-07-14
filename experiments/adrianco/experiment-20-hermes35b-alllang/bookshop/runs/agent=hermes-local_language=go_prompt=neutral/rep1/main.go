package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
)

func main() {
	// Determine database path: use env var or default to books.db
	dbPath := os.Getenv("BOOK_API_DB")
	if dbPath == "" {
		dbPath = "books.db"
	}

	db, err := NewDatabase(dbPath)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	handler := &Handler{DB: db}

	r := mux.NewRouter()
	r.HandleFunc("/health", handler.HealthCheck).Methods("GET")
	r.HandleFunc("/books", handler.CreateBook).Methods("POST")
	r.HandleFunc("/books", handler.ListBooks).Methods("GET")
	r.HandleFunc("/books/{id}", handler.GetBook).Methods("GET")
	r.HandleFunc("/books/{id}", handler.UpdateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", handler.DeleteBook).Methods("DELETE")

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Starting book API server on :%s", port)
	if err := http.ListenAndServe(":"+port, r); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
