// Command bookapi serves a REST API for managing a book collection.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"bookapi/internal/api"
	"bookapi/internal/store"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "bookapi:", err)
		os.Exit(1)
	}
}

func run() error {
	addr := flag.String("addr", envOr("ADDR", ":8080"), "HTTP listen address (env ADDR)")
	dbPath := flag.String("db", envOr("DB_PATH", "books.db"), "SQLite database file (env DB_PATH)")
	flag.Parse()

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	st, err := store.Open(*dbPath)
	if err != nil {
		return err
	}
	defer st.Close()

	srv := &http.Server{
		Addr:              *addr,
		Handler:           api.New(st, logger),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	serveErr := make(chan error, 1)
	go func() {
		logger.Info("listening", "addr", *addr, "db", *dbPath)
		serveErr <- srv.ListenAndServe()
	}()

	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
	}

	logger.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("shutdown: %w", err)
	}
	return nil
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
