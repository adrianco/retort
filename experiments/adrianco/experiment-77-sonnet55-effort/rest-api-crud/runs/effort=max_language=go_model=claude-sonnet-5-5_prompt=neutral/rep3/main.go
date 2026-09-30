// Command bookapi serves a REST API for managing a collection of books,
// stored in an embedded SQLite database.
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
	"bookapi/internal/sqlite"
)

const (
	defaultAddr   = ":8080"
	defaultDBPath = "books.db"

	// shutdownGrace is how long in-flight requests get to finish after an
	// interrupt or SIGTERM.
	shutdownGrace = 10 * time.Second
)

type config struct {
	addr   string
	dbPath string
}

// parseConfig resolves the settings in increasing order of precedence: the
// built-in defaults, the PORT and DB_PATH environment variables, then the
// -addr and -db flags. Flag diagnostics and usage are written to out.
func parseConfig(args []string, getenv func(string) string, out io.Writer) (config, error) {
	cfg := config{addr: defaultAddr, dbPath: defaultDBPath}
	if port := getenv("PORT"); port != "" {
		cfg.addr = ":" + port
	}
	if path := getenv("DB_PATH"); path != "" {
		cfg.dbPath = path
	}

	fs := flag.NewFlagSet("bookapi", flag.ContinueOnError)
	fs.SetOutput(out)
	fs.StringVar(&cfg.addr, "addr", cfg.addr, "`address` to listen on, as host:port")
	fs.StringVar(&cfg.dbPath, "db", cfg.dbPath, "path of the SQLite database `file` (\":memory:\" for a throwaway database)")
	if err := fs.Parse(args); err != nil {
		return config{}, err
	}
	if fs.NArg() > 0 {
		return config{}, fmt.Errorf("unexpected argument %q", fs.Arg(0))
	}
	return cfg, nil
}

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	// Once the first signal has started a graceful shutdown, give signal
	// handling back to the runtime so that a second Ctrl+C aborts at once
	// instead of being swallowed until the grace period runs out.
	context.AfterFunc(ctx, stop)

	err := run(ctx, os.Args[1:], os.Getenv, logger)
	stop()
	if err != nil && !errors.Is(err, flag.ErrHelp) {
		logger.Error("bookapi failed", "err", err)
		os.Exit(1)
	}
}

// run opens the database and serves the API until ctx is cancelled.
func run(ctx context.Context, args []string, getenv func(string) string, logger *slog.Logger) error {
	cfg, err := parseConfig(args, getenv, os.Stderr)
	if err != nil {
		return err
	}

	// Claim the port before touching the database, so that a bad address does
	// not leave a freshly created database file behind.
	ln, err := net.Listen("tcp", cfg.addr)
	if err != nil {
		return fmt.Errorf("listen on %q: %w", cfg.addr, err)
	}
	store, err := sqlite.Open(cfg.dbPath)
	if err != nil {
		ln.Close()
		return err
	}
	defer store.Close()
	logger.Info("listening", "addr", ln.Addr().String(), "database", cfg.dbPath)

	return serve(ctx, ln, api.New(store, logger), logger)
}

// serve answers requests arriving on ln with handler until ctx is cancelled,
// then lets in-flight requests finish before returning.
func serve(ctx context.Context, ln net.Listener, handler http.Handler, logger *slog.Logger) error {
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
		return err // Serve only returns http.ErrServerClosed after Shutdown, so this is a real failure
	case <-ctx.Done():
	}

	logger.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownGrace)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shut down: %w", err)
	}
	return nil
}
