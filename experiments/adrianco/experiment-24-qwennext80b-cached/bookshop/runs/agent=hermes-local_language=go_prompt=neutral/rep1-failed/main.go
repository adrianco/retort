package main

import (
	"log"
	"net/http"

	"github.com/gorilla/mux"
)

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status":"healthy"}`))
}

func main() {
	// Initialize the database
	db, err := NewDatabase("books.db")
	if err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	// Ensure tables exist
	if err := db.Init(); err != nil {
		log.Fatal(err)
	}

	// Create repositories
	bookRepo := NewBookRepository(db)

	// Create handlers
	bookHandler := NewBookHandler(bookRepo)

	// Create router
	router := mux.NewRouter()

	// Routes
	router.HandleFunc("/health", healthHandler).Methods("GET")
	router.HandleFunc("/books", bookHandler.CreateBook).Methods("POST")
	router.HandleFunc("/books", bookHandler.ListBooks).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.GetBook).Methods("GET")
	router.HandleFunc("/books/{id}", bookHandler.UpdateBook).Methods("PUT")
	router.HandleFunc("/books/{id}", bookHandler.DeleteBook).Methods("DELETE")

	// Start server
	log.Println("Server starting on :8080")
	if err := http.ListenAndServe(":8080", router); err != nil {
		log.Fatal(err)
	}
}
