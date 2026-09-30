// Command bookapi serves a REST API for managing a book collection, backed by
// an embedded SQLite database.
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

const shutdownTimeout = 10 * time.Second

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "bookapi:", err)
		os.Exit(1)
	}
}

func run() error {
	addr := flag.String("addr", defaultAddr(), "address to listen on (env ADDR, or PORT for just the port)")
	dbPath := flag.String("db", envOr("DB_PATH", "books.db"), "path to the SQLite database file (env DB_PATH)")
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
	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return fmt.Errorf("shutdown: %w", err)
	}
	return nil
}

func defaultAddr() string {
	if addr := os.Getenv("ADDR"); addr != "" {
		return addr
	}
	return ":" + envOr("PORT", "8080")
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
