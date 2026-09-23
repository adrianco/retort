// Command bookapi serves a REST API for managing a book collection, backed by SQLite.
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
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	if err := run(os.Args[1:], logger); err != nil {
		logger.Error("server exited", "err", err)
		os.Exit(1)
	}
}

func run(args []string, logger *slog.Logger) error {
	fs := flag.NewFlagSet("bookapi", flag.ContinueOnError)
	addr := fs.String("addr", defaultAddr(os.Getenv), "listen address (env ADDR, or PORT)")
	dbPath := fs.String("db", envOr("DB_PATH", "books.db"), `SQLite database file, or ":memory:" (env DB_PATH)`)
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return nil
		}
		return err
	}

	store, err := OpenStore(*dbPath)
	if err != nil {
		return err
	}
	defer store.Close()

	srv := &http.Server{
		Addr:              *addr,
		Handler:           NewServer(store, logger),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	errCh := make(chan error, 1)
	go func() {
		logger.Info("listening", "addr", *addr, "db", *dbPath)
		errCh <- srv.ListenAndServe()
	}()

	select {
	case err := <-errCh:
		return fmt.Errorf("listen: %w", err)
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

// defaultAddr prefers ADDR, then PORT (as used by most hosting platforms), then :8080.
func defaultAddr(getenv func(string) string) string {
	if addr := getenv("ADDR"); addr != "" {
		return addr
	}
	if port := getenv("PORT"); port != "" {
		return ":" + port
	}
	return ":8080"
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
