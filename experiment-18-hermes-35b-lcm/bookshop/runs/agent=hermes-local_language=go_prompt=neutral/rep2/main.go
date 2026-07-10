package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	dbPath := os.Getenv("BOOKAPI_DB")
	if dbPath == "" {
		dbPath = "./books.db"
	}

	db, err := NewDatabase(dbPath)
	if err != nil {
		log.Fatalf("failed to initialize database: %v", err)
	}
	defer db.Close()

	srv := NewServer(db)

	http.HandleFunc("/health", srv.HandleHealth)
	http.HandleFunc("/books", srv.HandleBooks)
	http.HandleFunc("/books/", srv.HandleBooks)

	addr := ":8080"
	if port := os.Getenv("PORT"); port != "" {
		addr = ":" + port
	}

	log.Printf("Book API server starting on %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
