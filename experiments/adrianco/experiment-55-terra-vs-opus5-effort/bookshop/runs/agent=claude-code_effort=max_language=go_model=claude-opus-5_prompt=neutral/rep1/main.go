// Command bookapi serves a small REST API over a SQLite-backed book
// collection. See README.md for the endpoint reference.
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
	"strings"
	"syscall"
	"time"
)

const shutdownTimeout = 15 * time.Second

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if err := run(ctx, os.Args[1:], os.Stderr); err != nil {
		fmt.Fprintf(os.Stderr, "bookapi: %v\n", err)
		os.Exit(1)
	}
}

// run holds everything main does, but takes its arguments and log sink as
// parameters and returns errors instead of exiting, so a test can drive it.
func run(ctx context.Context, args []string, logOut io.Writer) error {
	fs := flag.NewFlagSet("bookapi", flag.ContinueOnError)
	fs.SetOutput(logOut)
	var (
		addr     = fs.String("addr", envOr("BOOKAPI_ADDR", ":8080"), "address to listen on (host:port)")
		dbPath   = fs.String("db", envOr("BOOKAPI_DB", "books.db"), "path to the SQLite database file")
		logLevel = fs.String("log-level", envOr("BOOKAPI_LOG_LEVEL", "info"), "log level: debug, info, warn or error")
	)
	if err := fs.Parse(args); err != nil {
		if errors.Is(err, flag.ErrHelp) {
			return nil
		}
		return err
	}

	level, err := parseLevel(*logLevel)
	if err != nil {
		return err
	}
	logger := slog.New(slog.NewTextHandler(logOut, &slog.HandlerOptions{Level: level}))

	store, err := OpenStore(*dbPath)
	if err != nil {
		return err
	}
	defer func() {
		if err := store.Close(); err != nil {
			logger.Error("closing database", "err", err)
		}
	}()

	// Listen before serving so a port conflict is reported as a startup error,
	// and so the resolved address can be logged when :0 was requested.
	listener, err := net.Listen("tcp", *addr)
	if err != nil {
		return fmt.Errorf("listen on %s: %w", *addr, err)
	}

	srv := &http.Server{
		Handler:           NewServer(store, logger),
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       60 * time.Second,
		ErrorLog:          slog.NewLogLogger(logger.Handler(), slog.LevelError),
	}

	serveErr := make(chan error, 1)
	go func() {
		logger.Info("listening", "addr", listener.Addr().String(), "db", *dbPath)
		serveErr <- srv.Serve(listener)
	}()

	select {
	case err := <-serveErr:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return fmt.Errorf("serve: %w", err)
	case <-ctx.Done():
		logger.Info("shutting down", "timeout", shutdownTimeout.String())
		shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
		defer cancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			return fmt.Errorf("shutdown: %w", err)
		}
		logger.Info("stopped")
		return nil
	}
}

func envOr(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return fallback
}

func parseLevel(s string) (slog.Level, error) {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "debug":
		return slog.LevelDebug, nil
	case "info", "":
		return slog.LevelInfo, nil
	case "warn", "warning":
		return slog.LevelWarn, nil
	case "error":
		return slog.LevelError, nil
	default:
		return 0, fmt.Errorf("unknown log level %q: want debug, info, warn or error", s)
	}
}
