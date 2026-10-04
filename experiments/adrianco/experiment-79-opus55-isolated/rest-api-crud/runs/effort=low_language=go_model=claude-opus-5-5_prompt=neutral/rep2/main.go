package main

import (
	"log"
	"net/http"
	"os"
	"time"
)

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	addr := envOr("ADDR", ":8080")
	dbPath := envOr("DB_PATH", "books.db")

	store, err := NewStore(dbPath)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	srv := &http.Server{
		Addr:              addr,
		Handler:           NewHandler(store),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
	}
	log.Printf("listening on %s (database %s)", addr, dbPath)
	log.Fatal(srv.ListenAndServe())
}
