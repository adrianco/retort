package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gorilla/mux"
)

func main() {
	// Create a new router
	r := mux.NewRouter()

	// Initialize the database
	db, err := initDB()
	if err != nil {
		log.Fatal("Failed to initialize database:", err)
	}
	defer db.Close()

	// Create a handler with the database
	handler := &Handler{db: NewSQLiteStore(db)}

	// Define routes
	r.HandleFunc("/books", handler.createBook).Methods("POST")
	r.HandleFunc("/books", handler.getBooks).Methods("GET")
	r.HandleFunc("/books/{id}", handler.getBook).Methods("GET")
	r.HandleFunc("/books/{id}", handler.updateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", handler.deleteBook).Methods("DELETE")
	r.HandleFunc("/health", handler.healthCheck).Methods("GET")

	// Start the server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Server starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}