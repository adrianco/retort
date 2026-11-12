package main

import (
	"fmt"
	"log"
	"net/http"
)

func main() {
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/books", listBooksHandler)
	http.HandleFunc("/books/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/books" {
			switch r.Method {
			case http.MethodPost:
				createBookHandler(w, r)
			default:
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			}
			return
		}
		switch r.Method {
		case http.MethodGet:
			getBookHandler(w, r)
		case http.MethodPut:
			updateBookHandler(w, r)
		case http.MethodDelete:
			deleteBookHandler(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	fmt.Println("Server starting on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
