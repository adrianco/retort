// Command bookapi serves a small REST API for managing a book collection,
// backed by an embedded SQLite database.
package main

import (
	"context"
	"errors"
	"flag"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	if err := run(); err != nil {
		slog.Error("fatal", "error", err)
		os.Exit(1)
	}
}

func run() error {
	var (
		addr     = flag.String("addr", envOr("ADDR", ":8080"), "host:port to listen on")
		dbPath   = flag.String("db", envOr("DB_PATH", "books.db"), "path to the SQLite database file")
		logLevel = flag.String("log-level", envOr("LOG_LEVEL", "info"), "log level: debug, info, warn or error")
	)
	flag.Parse()

	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: parseLevel(*logLevel)}))
	slog.SetDefault(logger)

	// Cancelled on SIGINT/SIGTERM to start a graceful shutdown.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	openCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	store, err := OpenStore(openCtx, *dbPath)
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

	errCh := make(chan error, 1)
	go func() {
		logger.Info("listening", "addr", *addr, "db", *dbPath)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
		close(errCh)
	}()

	select {
	case err := <-errCh:
		return err
	case <-ctx.Done():
		logger.Info("shutting down")
	}

	shutdownCtx, cancelShutdown := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancelShutdown()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return err
	}
	return nil
}

func envOr(key, fallback string) string {
	if v, ok := os.LookupEnv(key); ok && v != "" {
		return v
	}
	return fallback
}

func parseLevel(s string) slog.Level {
	var level slog.Level
	if err := level.UnmarshalText([]byte(s)); err != nil {
		return slog.LevelInfo
	}
	return level
}
