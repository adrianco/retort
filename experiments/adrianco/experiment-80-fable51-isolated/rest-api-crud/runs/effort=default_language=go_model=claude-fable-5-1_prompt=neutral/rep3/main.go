package main

import (
	"log"
	"net/http"
	"os"
	"time"
)

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	addr := getenv("ADDR", ":8080")
	dbPath := getenv("DB_PATH", "books.db")

	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	srv := &http.Server{
		Addr:              addr,
		Handler:           NewHandler(store),
		ReadHeaderTimeout: 10 * time.Second,
	}
	log.Printf("listening on %s (database: %s)", addr, dbPath)
	log.Fatal(srv.ListenAndServe())
}
