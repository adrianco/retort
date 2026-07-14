package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}

	db, err := NewDB(dbPath)
	if err != nil {
		log.Fatalf("failed to initialize database: %v", err)
	}
	defer db.Close()

	handlers := &Handlers{DB: db}

	mux := http.NewServeMux()

	// Health check
	mux.HandleFunc("/health", newJSONHandler(handlers.healthHandler))

	// Books collection
	mux.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			newJSONHandler(handlers.listBooksHandler)(w, r)
		case http.MethodPost:
			newJSONHandler(handlers.createBookHandler)(w, r)
		default:
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		}
	})

	// Individual books
	mux.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			newJSONHandler(handlers.getBookHandler)(w, r)
		case http.MethodPut:
			newJSONHandler(handlers.updateBookHandler)(w, r)
		case http.MethodDelete:
			newJSONHandler(handlers.deleteBookHandler)(w, r)
		default:
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		}
	})

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	addr := ":" + port
	fmt.Printf("Book API server starting on %s\n", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}
