// Command bookapi serves a REST API for managing a book collection.
package main

import (
	"log"
	"net/http"
	"os"
	"time"
)

func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func main() {
	store, err := NewStore(getenv("DB_PATH", "books.db"))
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	addr := getenv("ADDR", ":8080")
	srv := &http.Server{
		Addr:              addr,
		Handler:           NewHandler(store),
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Printf("listening on %s", addr)
	log.Fatal(srv.ListenAndServe())
}
