package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	dbPath := os.Getenv("DATABASE_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}

	repo, err := NewBookRepository(dbPath)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer repo.Close()

	app := &App{Repo: repo}

	http.HandleFunc("/health", app.HealthCheck)
	http.HandleFunc("/books/", app.handleBookByID)
	http.HandleFunc("/books", app.handleBooks)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	addr := fmt.Sprintf(":%s", port)
	fmt.Printf("Book API server starting on %s\n", addr)
	log.Fatal(http.ListenAndServe(addr, nil))
}
