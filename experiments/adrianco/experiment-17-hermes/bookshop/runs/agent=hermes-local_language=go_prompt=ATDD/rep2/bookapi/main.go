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

	// Initialize the book service
	bookService := NewBookService(db)

	// Define routes
	r.HandleFunc("/books", bookService.CreateBook).Methods("POST")
	r.HandleFunc("/books", bookService.ListBooks).Methods("GET")
	r.HandleFunc("/books/{id}", bookService.GetBook).Methods("GET")
	r.HandleFunc("/books/{id}", bookService.UpdateBook).Methods("PUT")
	r.HandleFunc("/books/{id}", bookService.DeleteBook).Methods("DELETE")
	r.HandleFunc("/health", healthCheck).Methods("GET")

	// Start the server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("Server starting on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}

func healthCheck(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status": "healthy"}`))
}