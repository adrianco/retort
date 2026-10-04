// Command books serves a REST API for managing a book collection stored in SQLite.
package main

import (
	"context"
	"errors"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	addr := flag.String("addr", envOr("ADDR", ":8080"), "address to listen on (env ADDR)")
	dbPath := flag.String("db", envOr("DB_PATH", "books.db"), "path to the SQLite database file (env DB_PATH)")
	flag.Parse()

	if err := run(*addr, *dbPath); err != nil {
		log.Fatal(err)
	}
}

func run(addr, dbPath string) error {
	store, err := OpenStore(dbPath)
	if err != nil {
		return err
	}
	defer store.Close()

	srv := &http.Server{
		Addr:              addr,
		Handler:           NewHandler(store),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	serveErr := make(chan error, 1)
	go func() {
		log.Printf("listening on %s (database %s)", addr, dbPath)
		serveErr <- srv.ListenAndServe()
	}()

	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
		log.Print("shutting down")
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return err
	}
	if err := <-serveErr; !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
