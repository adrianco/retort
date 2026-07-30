package main

import (
	"errors"
	"log"
	"net/http"
	"os"
	"time"
)

func main() {
	databasePath := os.Getenv("DATABASE_PATH")
	if databasePath == "" {
		databasePath = "books.db"
	}

	store, err := NewStore(databasePath)
	if err != nil {
		log.Fatalf("initialize database: %v", err)
	}
	defer store.Close()

	address := os.Getenv("ADDR")
	if address == "" {
		address = ":8080"
	}

	server := &http.Server{
		Addr:              address,
		Handler:           NewHandler(store),
		ReadHeaderTimeout: 5 * time.Second,
	}

	log.Printf("book API listening on %s", address)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}
