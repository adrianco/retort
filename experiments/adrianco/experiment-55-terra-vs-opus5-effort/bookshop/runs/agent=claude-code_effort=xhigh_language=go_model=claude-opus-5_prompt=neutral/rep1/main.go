// Command bookapi serves a REST API for managing a collection of books,
// backed by an embedded SQLite database.
//
// Usage:
//
//	bookapi [-addr :8080] [-db books.db]
//
// Both flags also read from the environment (BOOKAPI_ADDR, BOOKAPI_DB), with
// the command line taking precedence.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"bookapi/internal/api"
	"bookapi/internal/books"
)

// shutdownGrace is how long in-flight requests get to finish after a signal.
const shutdownGrace = 10 * time.Second

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := run(ctx, os.Args[1:], os.Stderr); err != nil {
		fmt.Fprintf(os.Stderr, "bookapi: %v\n", err)
		os.Exit(1)
	}
}

// run holds the whole program so that failures return an error instead of
// calling os.Exit, which keeps it testable. It blocks until ctx is cancelled
// or the server stops on its own.
func run(ctx context.Context, args []string, logOutput io.Writer) error {
	flags := flag.NewFlagSet("bookapi", flag.ContinueOnError)
	flags.SetOutput(logOutput)
	var (
		addr     = flags.String("addr", envOr("BOOKAPI_ADDR", ":8080"), "host:port to listen on")
		dbPath   = flags.String("db", envOr("BOOKAPI_DB", "books.db"), "path to the SQLite database file")
		logLevel = flags.String("log-level", envOr("BOOKAPI_LOG_LEVEL", "info"), "debug, info, warn or error")
	)
	if err := flags.Parse(args); err != nil {
		return err
	}

	level, err := parseLevel(*logLevel)
	if err != nil {
		return err
	}
	logger := slog.New(slog.NewJSONHandler(logOutput, &slog.HandlerOptions{Level: level}))

	store, err := books.Open(ctx, *dbPath)
	if err != nil {
		return err
	}
	defer store.Close()
	logger.Info("database ready", slog.String("path", *dbPath))

	server := &http.Server{
		Handler:           api.NewServer(store, logger),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
		ErrorLog:          slog.NewLogLogger(logger.Handler(), slog.LevelWarn),
	}

	// Listen before announcing, so a port clash is reported as a startup
	// failure rather than a log line followed by silence.
	listener, err := net.Listen("tcp", *addr)
	if err != nil {
		return fmt.Errorf("listen on %s: %w", *addr, err)
	}
	logger.Info("listening", slog.String("addr", listener.Addr().String()))

	serveErr := make(chan error, 1)
	go func() {
		serveErr <- server.Serve(listener)
	}()

	select {
	case err := <-serveErr:
		if err != nil && !errors.Is(err, http.ErrServerClosed) {
			return fmt.Errorf("serve: %w", err)
		}
		return nil
	case <-ctx.Done():
		logger.Info("shutdown signal received", slog.Duration("grace", shutdownGrace))
	}

	shutdownCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), shutdownGrace)
	defer cancel()
	if err := server.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("graceful shutdown: %w", err)
	}
	logger.Info("stopped cleanly")
	return nil
}

func envOr(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok && value != "" {
		return value
	}
	return fallback
}

func parseLevel(name string) (slog.Level, error) {
	var level slog.Level
	if err := level.UnmarshalText([]byte(name)); err != nil {
		return 0, fmt.Errorf("invalid -log-level %q: want debug, info, warn or error", name)
	}
	return level, nil
}
