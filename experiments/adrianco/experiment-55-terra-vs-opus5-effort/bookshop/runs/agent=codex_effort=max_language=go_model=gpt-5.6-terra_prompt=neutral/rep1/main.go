package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	databasePath := os.Getenv("BOOKS_DB_PATH")
	if databasePath == "" {
		databasePath = "books.db"
	}

	store, err := OpenStore(databasePath)
	if err != nil {
		log.Fatalf("open book database: %v", err)
	}
	defer store.Close()

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	server := &http.Server{
		Addr:              ":" + port,
		Handler:           NewAPI(store),
		ReadHeaderTimeout: 5 * time.Second,
	}

	go func() {
		log.Printf("book collection API listening on http://localhost:%s", port)
		if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("serve API: %v", err)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := server.Shutdown(ctx); err != nil {
		log.Printf("graceful shutdown failed: %v", err)
	}
}
