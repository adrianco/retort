package main

import (
	"log"
	"net/http"
	"strconv"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

func main() {
	log.Println("Starting Book API server...")

	store, err := NewBookStore(":memory:")
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer store.Close()

	handler := NewBookHandler(store)

	mux := http.NewServeMux()
	mux.HandleFunc("/health", handler.Health)
	mux.HandleFunc("/books", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			handler.listBooks(w, r)
		case http.MethodPost:
			handler.createBook(w, r)
		default:
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
		}
	})
	mux.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet && r.Method != http.MethodPut && r.Method != http.MethodDelete {
			writeError(w, http.StatusMethodNotAllowed, "method not allowed")
			return
		}

		idStr := strings.TrimPrefix(r.URL.Path, "/books/")
		if idStr == "" {
			writeError(w, http.StatusBadRequest, "book ID is required")
			return
		}

		id, err := strconv.Atoi(idStr)
		if err != nil {
			writeError(w, http.StatusBadRequest, "invalid book ID")
			return
		}

		switch r.Method {
		case http.MethodGet:
			handler.getBook(w, id)
		case http.MethodPut:
			handler.updateBook(w, id, r)
		case http.MethodDelete:
			handler.deleteBook(w, id)
		}
	})

	addr := ":8080"
	log.Printf("Server listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
