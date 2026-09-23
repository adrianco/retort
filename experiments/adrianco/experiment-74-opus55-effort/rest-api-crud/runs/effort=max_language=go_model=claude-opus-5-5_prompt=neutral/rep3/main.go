// Command bookapi serves a REST API for managing a book collection stored in
// SQLite.
package main

import (
	"cmp"
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	addr := flag.String("addr", ":"+cmp.Or(os.Getenv("PORT"), "8080"),
		"HTTP listen address (default port can be set with $PORT)")
	dbPath := flag.String("db", cmp.Or(os.Getenv("DB_PATH"), "books.db"),
		`SQLite database file, or ":memory:" for a throwaway database (default can be set with $DB_PATH)`)
	flag.Parse()

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	if err := run(*addr, *dbPath, logger); err != nil {
		logger.Error("book API failed", "err", err)
		os.Exit(1)
	}
}

// run serves the API on addr until SIGINT or SIGTERM, then shuts down
// gracefully.
func run(addr, dbPath string, logger *slog.Logger) error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	store, err := OpenStore(dbPath)
	if err != nil {
		return fmt.Errorf("open database %q: %w", dbPath, err)
	}
	defer store.Close()

	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	logger.Info("book API listening", "addr", ln.Addr().String(), "db", dbPath)
	if err := serve(ctx, ln, NewHandler(store, logger)); err != nil {
		return err
	}
	logger.Info("book API stopped")
	return nil
}

// serve handles HTTP requests on ln until ctx is cancelled, then stops
// accepting connections and waits for in-flight requests to finish.
func serve(ctx context.Context, ln net.Listener, handler http.Handler) error {
	srv := &http.Server{
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.Serve(ln) }()

	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown: %w", err)
	}
	if err := <-serveErr; !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}
