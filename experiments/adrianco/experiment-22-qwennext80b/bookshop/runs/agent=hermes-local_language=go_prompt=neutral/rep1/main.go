package main

import (
	"fmt"
	"log"
	"net/http"

	"bookapi/handler"
	"bookapi/model"
)

func main() {
	// Initialize the database
	store, err := model.NewBookStore("books.db")
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer store.Close()

	// Create the book handler
	bh := handler.NewBookHandler(store)

	// Create the router
	router := http.NewServeMux()

	// Register handlers
	router.HandleFunc("/health", bh.HealthCheck)
	router.HandleFunc("/books", bh.ListBooks)
	router.HandleFunc("/books", bh.CreateBook)
	router.HandleFunc("/books/{id}", bh.GetBook)
	router.HandleFunc("/books/{id}", bh.UpdateBook)
	router.HandleFunc("/books/{id}", bh.DeleteBook)

	// Start the server
	fmt.Println("Starting server on :8080")
	if err := http.ListenAndServe(":8080", router); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
