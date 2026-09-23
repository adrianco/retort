// Command bookapi serves a REST API for managing a book collection stored in
// SQLite.
//
// Usage:
//
//	bookapi [-addr :8080] [-db books.db]
//
// The PORT and DB_PATH environment variables set the defaults for the flags.
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

// shutdownTimeout bounds how long in-flight requests get to finish on exit.
const shutdownTimeout = 10 * time.Second

func main() {
	cfg, err := parseConfig(os.Args[1:], os.Getenv)
	if errors.Is(err, flag.ErrHelp) {
		return
	}
	if err != nil {
		os.Exit(2) // the flag package has already reported the problem
	}

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	err = run(ctx, cfg, logger)
	stop()
	if err != nil {
		logger.Error("server failed", "error", err)
		os.Exit(1)
	}
}

// config holds the server settings.
type config struct {
	addr   string // TCP address to listen on
	dbPath string // SQLite database file
}

// parseConfig reads the settings from command-line flags, whose defaults come
// from the environment.
func parseConfig(args []string, getenv func(string) string) (config, error) {
	port := getenv("PORT")
	if port == "" {
		port = "8080"
	}
	dbPath := getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "books.db"
	}

	var cfg config
	fs := flag.NewFlagSet("bookapi", flag.ContinueOnError)
	fs.StringVar(&cfg.addr, "addr", ":"+port, "`address` to listen on; $PORT sets the default port")
	fs.StringVar(&cfg.dbPath, "db", dbPath, "SQLite database `file`, or :memory:; $DB_PATH sets the default")
	err := fs.Parse(args)
	return cfg, err
}

// run serves the API until ctx is cancelled, then shuts down gracefully,
// letting in-flight requests finish.
func run(ctx context.Context, cfg config, logger *slog.Logger) error {
	store, err := OpenStore(ctx, cfg.dbPath)
	if err != nil {
		return err
	}
	defer store.Close()

	ln, err := net.Listen("tcp", cfg.addr)
	if err != nil {
		return err
	}
	srv := &http.Server{
		Handler:           NewServer(store, logger),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
	}
	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.Serve(ln) }()
	logger.Info("listening", "addr", ln.Addr().String(), "db", cfg.dbPath)

	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
	}

	logger.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), shutdownTimeout)
	defer cancel()
	return srv.Shutdown(shutdownCtx)
}
