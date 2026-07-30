package main

import (
	"log"
	"net/http"
	"os"
	"time"
)

func main() {
	dsn := os.Getenv("BOOKS_DB")
	if dsn == "" {
		dsn = "books.db"
	}
	addr := os.Getenv("ADDR")
	if addr == "" {
		addr = ":8080"
	}

	store, err := OpenStore(dsn)
	if err != nil {
		log.Fatalf("open database: %v", err)
	}
	defer store.Close()

	srv := &http.Server{
		Addr:         addr,
		Handler:      NewServer(store),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}
	log.Printf("book API listening on %s (db=%s)", addr, dsn)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server: %v", err)
	}
}
