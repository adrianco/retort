package main

import (
	"log"
	"net/http"
)

func main() {
	// Initialize database
	db, err := InitDB("books.db")
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}

	// Auto-migrate schema
	err = db.AutoMigrate(&Book{})
	if err != nil {
		log.Fatalf("Failed to migrate database: %v", err)
	}

	// Initialize handlers
	h := NewHandler(db)

	// Setup routes
	mux := http.NewServeMux()

	// Health check
	mux.HandleFunc("/health", h.handleHealth)

	// Book endpoints
	mux.HandleFunc("/books", h.handleBooks)
	mux.HandleFunc("/books/{id}", h.handleBookByID)

	log.Println("Starting server on :8080")
	log.Fatal(http.ListenAndServe(":8080", mux))
}
