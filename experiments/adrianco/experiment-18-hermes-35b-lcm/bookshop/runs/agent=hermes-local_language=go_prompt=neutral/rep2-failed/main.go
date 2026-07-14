package main

import (
	"fmt"
	"log"
	"net/http"

	"book-api/database"
	"book-api/handlers"
)

func main() {
	// Initialize the database
	db, err := database.New("books.db")
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	// Create handlers
	bookHandler := handlers.NewBookHandler(db)

	// Register routes
	mux := http.NewServeMux()
	handlers.RegisterRoutes(mux, bookHandler)

	// Start server
	port := 8080
	addr := fmt.Sprintf(":%d", port)
	fmt.Printf("Server starting on http://localhost%s\n", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}
