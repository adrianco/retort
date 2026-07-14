package main

import (
	"book-api/db"
	"book-api/handlers"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
)

func main() {
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}

	database, err := db.New(dbPath)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer database.Close()

	h := handlers.NewBooksHandler(database)

	r := mux.NewRouter()

	// Health check
	r.HandleFunc("/health", h.HealthCheck).Methods("GET")

	// Books endpoints
	r.HandleFunc("/books", h.CreateBook).Methods("POST")
	r.HandleFunc("/books", h.GetBooks).Methods("GET")

	// Books with ID - must be registered after /books to avoid conflicts
	r.HandleFunc("/books/{id}", h.GetBook).Methods("GET")
	r.HandleFunc("/books/{id}", h.UpdateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", h.DeleteBook).Methods("DELETE")

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	fmt.Printf("Server starting on port %s\n", port)
	if err := http.ListenAndServe(":"+port, r); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
