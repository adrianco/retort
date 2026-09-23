// Command bookapi serves a REST API for managing a book collection stored in SQLite.
package main

import (
	"context"
	"errors"
	"flag"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := run(ctx, os.Args[1:], os.Getenv, logger, nil); err != nil {
		logger.Error("server exited", "err", err)
		os.Exit(1)
	}
}

// run starts the API and blocks until ctx is cancelled or the server fails.
// If ready is non-nil the bound listen address is sent on it once the server
// is accepting connections.
func run(ctx context.Context, args []string, getenv func(string) string, logger *slog.Logger, ready chan<- string) error {
	fs := flag.NewFlagSet("bookapi", flag.ContinueOnError)
	addr := fs.String("addr", envOr(getenv, "ADDR", ":8080"), "listen address (env ADDR)")
	dbPath := fs.String("db", envOr(getenv, "DB_PATH", "books.db"), `SQLite database file, or ":memory:" (env DB_PATH)`)
	if err := fs.Parse(args); err != nil {
		return err
	}

	store, err := OpenStore(*dbPath)
	if err != nil {
		return err
	}
	defer store.Close()

	ln, err := net.Listen("tcp", *addr)
	if err != nil {
		return err
	}

	srv := &http.Server{
		Handler:           NewServer(store, logger),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
		ErrorLog:          slog.NewLogLogger(logger.Handler(), slog.LevelWarn),
	}

	errCh := make(chan error, 1)
	go func() { errCh <- srv.Serve(ln) }()
	logger.Info("listening", "addr", ln.Addr().String(), "db", *dbPath)
	if ready != nil {
		ready <- ln.Addr().String()
	}

	select {
	case err := <-errCh:
		return err
	case <-ctx.Done():
	}

	logger.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return err
	}
	if err := <-errCh; !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

func envOr(getenv func(string) string, key, fallback string) string {
	if v := getenv(key); v != "" {
		return v
	}
	return fallback
}
